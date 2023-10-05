# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing_extensions import runtime
from aws_cdk import (
    Aws,
    CfnOutput,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    Duration,
    aws_lambda_python_alpha as lambda_python,
    aws_iam as iam
)
from constructs import Construct
from sm_pipeline_cdk.services import Services      

class MlaasApiGateway(Construct):

    @property
    def api_gateway(self) -> apigateway.RestApi:
        return self._api_gateway
    
    @property
    def api_gateway_arn(self) -> str:
        return self._api_gateway_arn
    
    
    def __init__(self, scope: Construct, construct_id: str, tenant_id: str, services: Services, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        
        # Create API gateway
        api_gateway = apigateway.RestApi(self, "TenantAPIGateway", 
            rest_api_name = f"mlaas-api-gateway-{tenant_id}-{Aws.REGION}",
            deploy = False
            )
            
        jwt = api_gateway.root.add_resource("jwt")
        
        # Create API Lambda Token Authorizer
        api_lambda_auth = apigateway.TokenAuthorizer(self, "s3UploadAuthorizer", handler=services.authorizer_lambda)

        # JWT API
        jwt.add_method(
             "GET",
             apigateway.LambdaIntegration(
                 handler=services.jwt_token_lambda
             ),
             method_responses=[
                 {
                     "statusCode": "200"
                 }
             ]
        )
        
        # Upload API
        upload = api_gateway.root.add_resource("upload")
        upload.add_method(
             "PUT",
             apigateway.LambdaIntegration(handler=services.s3_uploader_lambda,proxy=True),
             authorizer = api_lambda_auth
        )
        
        deployment = apigateway.Deployment(self, "Deployment", 
            api=api_gateway,
        )

        
        
        inference_api = api_gateway.root.add_resource("inference")  
        
        inference_api_method = inference_api.add_method(
            "POST",
            apigateway.LambdaIntegration(handler=services.inference_processor_lambda,proxy=True),
            authorizer = api_lambda_auth
        )

        if (tenant_id == "pooled"):
            # Basic Tier Inference API
            basic_tier_inference_api = api_gateway.root.add_resource("basic_inference")  
            
            basic_tier_inference_api_method = basic_tier_inference_api.add_method(
                "POST",
                apigateway.LambdaIntegration(handler=services.basic_tier_inference_processor_lambda,proxy=True),
                authorizer = api_lambda_auth
            )    



        apiStage = apigateway.Stage(self, "V1",
            deployment=deployment,
            stage_name="v1"
        )     
        api_gateway.deployment_stage = apiStage
        
        #REST Api arn
        api_gateway_arn = f'arn:aws:apigateway:{Aws.REGION}::/restapis/{api_gateway.rest_api_id}/stages/{apiStage.stage_name}'

        self._api_gateway = api_gateway
        self._api_gateway_arn = api_gateway_arn
        
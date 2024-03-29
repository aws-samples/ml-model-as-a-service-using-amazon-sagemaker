# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing_extensions import runtime
from aws_cdk import (
    Aws,
    CfnOutput,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_iam as iam
)
from constructs import Construct


class MlaasApiGateway(Construct):

    @property
    def api_gateway_url(self) -> str:
        return self._api_gateway_url
    
    @property
    def api_gateway_id(self) -> str:
        return self._api_gateway_id
    
    @property
    def api_gateway_root_resource_id(self) -> str:
        return self._api_gateway_root_resource_id
    
    @property
    def api_gateway_arn(self) -> str:
        return self._api_gateway_arn
    
    
    def __init__(self, scope: Construct, construct_id: str, bucket_arn: str, tenant_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Uploader Lambda Role
        s3_uploader_lambda_role = iam.Role(self, "S3UploaderRole",
                                           role_name=f'mlaas-s3-uploader-role-{tenant_id}-{Aws.REGION}',
                                           assumed_by=iam.ServicePrincipal(
                                               "lambda.amazonaws.com"),
                                           managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="S3UploaderCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                             iam.ManagedPolicy.from_managed_policy_arn(self, id="S3UploaderAWSLambdaBasicExecutionRole",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                           )

        # s3 Uploader Lambda
        s3_uploader_lambda = lambda_python.PythonFunction(self, "s3UploadFunction",
                                                          entry="../sm-pipeline-cdk/functions",
                                                          runtime=lambda_.Runtime.PYTHON_3_9,
                                                          index="s3_uploader.py",
                                                          handler="lambda_handler",
                                                          function_name=f"mlaas-s3-uploader-{tenant_id}-{Aws.REGION}",
                                                          role=s3_uploader_lambda_role

                                                          )

        layer = lambda_python.PythonLayerVersion(self, "MyLayer",
                                                 entry="../layers/",
                                                 compatible_runtimes=[
                                                     lambda_.Runtime.PYTHON_3_9],
                                                 description="MLaaS utilities",
                                                 layer_version_name="MlaasUploaderLayer"
                                                 )

        # Authorizer Lambda Role
        auth_lambda_role = iam.Role(self, "AuthorizerRole",
                                    role_name=f'mlaas-authorizer-role-{tenant_id}-{Aws.REGION}',
                                    assumed_by=iam.ServicePrincipal(
                                        "lambda.amazonaws.com"),
                                    managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="CloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                      iam.ManagedPolicy.from_managed_policy_arn(self, id="AuthLambdaBasicExecutionRole",
                                                                                                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                    )

        auth_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["sts:TagSession"],
            resources=["*"]
        ))

        auth_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"]
        ))

        # ABAC for pooled tenants
        # if (tenant_id == 'pooled'):

        abac_tenant_access_policy = iam.Policy(self, "AbacTenantAccessAPolicy",
                                               policy_name="abac-mlaas-tenant-access-policy",
                                               statements=[iam.PolicyStatement(
                                                   actions=[
                                                           "s3:GetObject", "s3:PutObject"],
                                                   effect=iam.Effect.ALLOW,
                                                   resources=[
                                                       f"{bucket_arn}/${{aws:PrincipalTag/TenantId}}",
                                                       f"{bucket_arn}/${{aws:PrincipalTag/TenantId}}/*"],
                                               ),
                                                   iam.PolicyStatement(
                                                   actions=[
                                                       "dynamodb:GetItem"],
                                                   effect=iam.Effect.ALLOW,
                                                   resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"])
                                               ])

        abac_tenant_access_role = iam.Role(self, "AbacTenantAccessRole",
                                           role_name=f'mlaas-abac-access-role-{tenant_id}-{Aws.REGION}',
                                           assumed_by=iam.CompositePrincipal(
                                               iam.ServicePrincipal(
                                                   "lambda.amazonaws.com")
                                           ),
                                           managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="AbacCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                             iam.ManagedPolicy.from_managed_policy_arn(self, id="AbacAWSLambdaBasicExecutionRole",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                           )

        abac_tenant_access_role.attach_inline_policy(
            abac_tenant_access_policy)

        abac_tenant_access_role.assume_role_policy.add_statements(iam.PolicyStatement(
            actions=["sts:TagSession", "sts:AssumeRole"],
            effect=iam.Effect.ALLOW,
            principals=[auth_lambda_role]
        ))

        # Token Authorizer Lambda
        auth_lambda = lambda_python.PythonFunction(self, "AuthorizerLambda",
                                                   entry="../sm-pipeline-cdk/functions/authorizer",
                                                   runtime=lambda_.Runtime.PYTHON_3_9,
                                                   index="tenant_authorizer.py",
                                                   handler="lambda_handler",
                                                   function_name=f"mlaas-api-authorizer-{tenant_id}-{Aws.REGION}",
                                                   role=auth_lambda_role,
                                                   layers=[
                                                       layer],
                                                   environment={
                                                       'ROLE_TO_ASSUME_ARN': abac_tenant_access_role.role_arn,
                                                   }
                                                   )

        # JWT Token role
        get_jwt_lambda_role = iam.Role(self, 'GetJWTLambdaRole',
                                       role_name=f'mlaas-get-jwt-role-{tenant_id}-{Aws.REGION}',
                                       assumed_by=iam.ServicePrincipal(
                                           'lambda.amazonaws.com'),
                                       managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="JWTLambdaBasicExecutionRole",
                                                                                                   managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                                                        #  iam.ManagedPolicy.from_managed_policy_arn(self, id="AmazonDynamoDBReadOnlyRole",
                                                        #                                            managed_policy_arn="arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess")
                                                        ]
                                       )

        get_jwt_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:Query"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails", 
                       f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails/index/*"]
        ))         

        # get jwt token Lambda
        get_jwt_token_lambda = lambda_python.PythonFunction(self, "getJwtTokenFunction",
                                                            entry="../sm-pipeline-cdk/functions",
                                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                                            index="get_jwt_token.py",
                                                            handler="lambda_handler",
                                                            function_name=f"get-jwt-token-{tenant_id}-{Aws.REGION}",
                                                            role=get_jwt_lambda_role

                                                            )

        # Create API gateway
        api_gateway = apigateway.RestApi(self, "TenantAPIGateway", 
            rest_api_name = f"mlaas-api-gateway-{tenant_id}-{Aws.REGION}",
            deploy = False
            )
            
        jwt = api_gateway.root.add_resource("jwt")
        
        # Create API Lambda Token Authorizer
        s3_uploader_api_auth = apigateway.TokenAuthorizer(self, "s3UploadAuthorizer", handler=auth_lambda)

        jwt.add_method(
             "GET",
             apigateway.LambdaIntegration(
                 handler=get_jwt_token_lambda
             ),
             method_responses=[
                 {
                     "statusCode": "200"
                 }
             ]
        )
        
        upload = api_gateway.root.add_resource("upload")
        upload.add_method(
             "PUT",
             apigateway.LambdaIntegration(handler=s3_uploader_lambda,proxy=True),
             authorizer = s3_uploader_api_auth
        )
        
        deployment = apigateway.Deployment(self, "Deployment", 
            api=api_gateway,
        )  
        
        apiStage = apigateway.Stage(self, "V1",
            deployment=deployment,
            stage_name="v1"
        )     
        api_gateway.deployment_stage = apiStage
        
        #REST Api arn
        api_gateway_arn = f'arn:aws:apigateway:{Aws.REGION}::/restapis/{api_gateway.rest_api_id}/stages/{apiStage.stage_name}'

        self._api_gateway_url = api_gateway.url
        self._api_gateway_id = api_gateway.rest_api_id
        self._api_gateway_arn = api_gateway_arn
        self._api_gateway_root_resource_id = api_gateway.rest_api_root_resource_id
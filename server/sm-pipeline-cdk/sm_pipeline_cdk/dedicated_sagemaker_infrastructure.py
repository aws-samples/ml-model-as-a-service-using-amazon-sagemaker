# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import pathlib

from constructs import Construct

import aws_cdk as cdk

from aws_cdk import (
    Aws,
    Stack,
    Stage,
    CfnOutput,
    aws_apigateway as apigateway,
    NestedStack,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n
)

from aws_cdk.aws_apigateway import RestApi

class DedicatedSageMakerInfrastructure(Construct):

    def __init__(self, scope: Construct, id_: str, endpoint_name: str, tenant_id: str, sagemaker_model_bucket_name: str,  api_gateway_id: str, api_gateway_root_resource_id: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        
        inference_request_processor_lambda_role = iam.Role(self, "InferenceRequestProcessorRole",
            role_name=f'mlaas-dedicated-infer-role-{tenant_id}-{Aws.REGION}',
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorAWSLambdaBasicExecutionRole",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorAmazonSageMakerFullAccess",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")])
                                           
        lambda_inference_request_processor = lambda_.Function(
            self,
            f"RequestProcessorLambdaFn",
            function_name=f"mlaas-request-processor-{tenant_id}-{Aws.REGION}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="dedicated_request_processor.lambda_handler",
            timeout = cdk.Duration.minutes(2),
            code=lambda_.Code.from_asset("../sm-pipeline-cdk/functions"),
            role=inference_request_processor_lambda_role,            
            environment={
                "ENDPOINT_NAME": endpoint_name
            }            
        )        

        auth_lambda_role = iam.Role(self, "InferenceAuthorizerLambdaRole",
            role_name=f'mlaas-inference-authz-role-{tenant_id}-{Aws.REGION}',
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceAuthorizerCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceAuthorizerAWSLambdaBasicExecutionRole",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceAuthorizerAmazonDynamoDBReadOnlyAccess",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess")])


        layer = lambda_python.PythonLayerVersion(self, "MyLayer",
            entry="../layers/",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            license="Apache-2.0",
            description="MLaaS utilities",
            layer_version_name="MlaasUploaderLayer"
        ) 
        
        auth_lambda = lambda_python.PythonFunction(
            self, 
            "AuthorizerLambdaFn",
            entry="../sm-pipeline-cdk/functions",
            runtime=lambda_.Runtime.PYTHON_3_9,
            index="dedicated_tenant_authorizer.py",
            handler="lambda_handler",
            function_name=f"mlaas-api-authorizer-{tenant_id}-{Aws.REGION}-sagemaker",
            role=auth_lambda_role,
            layers=[layer]
        )
        
        auth_lambda.add_environment(
            "TENANT_ID", tenant_id,
        )          
        
        api_gateway = RestApi.from_rest_api_attributes(self, "RestApi",
            rest_api_id=api_gateway_id,
            root_resource_id=api_gateway_root_resource_id
        )    

        inference_api = api_gateway.root.add_resource("inference")
        
        inference_api_api_auth = apigateway.TokenAuthorizer(self, "inferenceAuthorizer",
            handler=auth_lambda
        )
        
        inference_api_method = inference_api.add_method(
            "POST",
            apigateway.LambdaIntegration(handler=lambda_inference_request_processor,proxy=True),
            authorizer = inference_api_api_auth
        )

        deployment = apigateway.Deployment(self, "Deployment", 
            api=api_gateway,
        )  
        deployment.node.add_dependency(inference_api_method)
        
        apiStage = apigateway.Stage(self, "V2",
            deployment=deployment,
            stage_name="v2"
        )
        
        sagemaker_bucket_update_event = events.Rule(self, 
            "rule", 
            rule_name=f's3rule-endpoint-deployer-{tenant_id}-{Aws.REGION}',
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": { 
                        "name": [sagemaker_model_bucket_name] 
                    },
                    "object": {
                        "key": [{
                            "prefix":f"{tenant_id}/model_artifacts/"
                        }]
                    }
                }
            )
        ) 
        
        sagemaker_model_deployer_lambda_role = iam.Role(self, 'SageMakerModelDeployerLambdaRole',
            role_name=f'mlaas-model-deployer-role-{tenant_id}-{Aws.REGION}',
            assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("lambda.amazonaws.com"),
                    iam.ServicePrincipal("sagemaker.amazonaws.com")),
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSLambdaBasicExecutionRole",managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSCloudFormationReadOnlyAccess",managed_policy_arn="arn:aws:iam::aws:policy/AWSCloudFormationReadOnlyAccess"),
                iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AmazonSageMakerFullAccess",managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AmazonDynamoDBReadOnlyAccess", managed_policy_arn="arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess")
            ]
        )
        
        sagemaker_model_deployer_lambda_role.add_to_policy(iam.PolicyStatement(
                actions=["s3:*"],
                resources=[f"arn:aws:s3:::{sagemaker_model_bucket_name}",
                           f"arn:aws:s3:::{sagemaker_model_bucket_name}/*"]
            ))        
        
        sagemaker_model_deployer_lambda = lambda_python.PythonFunction(self, "SageMakerModelDeployerLambda",
            function_name=f'mlaas-model-deployer-{tenant_id}-{Aws.REGION}',
            runtime=lambda_.Runtime.PYTHON_3_8,
            entry="../sm-pipeline-cdk/functions",
            index="dedicated_sagemaker_deployer.py",
            handler="handler",
            timeout = cdk.Duration.minutes(15),
            role = sagemaker_model_deployer_lambda_role,
        )
        
        sagemaker_model_deployer_lambda.add_environment(
            "TENANT_ID", tenant_id
        ) 

        sagemaker_model_deployer_lambda.add_environment(
            "ENDPOINT_NAME", endpoint_name
        ) 
        
        sagemaker_model_deployer_lambda.add_environment(
            "ROLE_ARN", sagemaker_model_deployer_lambda_role.role_arn
        )         
        
        # queue = sqs.Queue(self, "Queue")
        
        sagemaker_bucket_update_event.add_target(targets.LambdaFunction(sagemaker_model_deployer_lambda,
                                        # dead_letter_queue=queue,
                                        max_event_age=cdk.Duration.hours(2),
                                        retry_attempts=2
                                    )
        )
        
        # sagemaker_model_bucket_name.add_event_notification(
        #     s3.EventType.OBJECT_CREATED,
        #     s3n.LambdaDestination(sagemaker_model_deployer_lambda),
        #     prefix="model_artifacts/",
        #     suffix=".tar.gz"
        # )
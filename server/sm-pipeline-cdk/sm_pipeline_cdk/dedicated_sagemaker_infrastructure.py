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
    aws_s3_notifications as s3n,
    aws_sagemaker as sagemaker
)

from aws_cdk.aws_apigateway import RestApi

class DedicatedSageMakerInfrastructure(Construct):

    def __init__(self, scope: Construct, id_: str, model_endpoint: sagemaker.CfnEndpoint, tenant_id: str, sagemaker_model_bucket_name: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        
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
            "ENDPOINT_NAME", model_endpoint.endpoint_name
        ) 
        
        sagemaker_model_deployer_lambda.add_environment(
            "ROLE_ARN", sagemaker_model_deployer_lambda_role.role_arn
        )         
        
        
        sagemaker_bucket_update_event.add_target(targets.LambdaFunction(sagemaker_model_deployer_lambda,
                                        max_event_age=cdk.Duration.hours(2),
                                        retry_attempts=2
                                    )
        )
        
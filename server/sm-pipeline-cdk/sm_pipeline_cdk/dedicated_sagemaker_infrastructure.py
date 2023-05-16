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
    aws_s3 as s3
)

from aws_cdk.aws_apigateway import RestApi

class DedicatedSageMakerInfrastructure(NestedStack):

    def __init__(self, scope: Construct, id_: str, endpoint_name: str, tenant_id: str, sagemaker_model_bucket_name: str,  api_gateway_id: str, api_gateway_root_resource_id: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        
    ## ADD CODE HERE        
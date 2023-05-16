# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing_extensions import runtime
from aws_cdk import (
    Aws,
    Stack,    
    NestedStack,
    CfnOutput,
    aws_s3 as s3,
    aws_iam as iam,
    CfnMapping,
    aws_sagemaker as sagemaker
)
from constructs import Construct

import aws_cdk as cdk

INITIAL_INSTANCE_COUNT = 1
INITIAL_INSTANCE_WEIGHT = 1.0
INSTANCE_TYPE = "ml.t2.medium"

class DedicatedSageMakerEndpoint(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, tenant_id: str, bucket_arn: str, tenant_iam_role:iam.Role, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        #SageMaker XGBoost Image Locations
        xgboost_container_mapping = CfnMapping(self, "sagemakerEc2ArnMapping",
            mapping={
                "us-east-1": {
                    "containerImageUri": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.3-1",
                },
                "us-west-2": {
                    "containerImageUri": "246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-xgboost:1.3-1",
                }
 
            }
        )  
        
    ## ADD CODE HERE
        
    def generate_container_definition_property(self, models_bucket: s3.Bucket, container_image_uri: str) -> sagemaker.CfnModel.ContainerDefinitionProperty:
            """
            Generate a SageMaker container definition for the gold tenant model
            """
            gold_tenant_model_s3_path = models_bucket.s3_url_for_object("model_artifacts_mme/sample-data.model.0.tar.gz")
    
            tenant_model_primary_container = sagemaker.CfnModel.ContainerDefinitionProperty(
                image=container_image_uri,
                image_config=sagemaker.CfnModel.ImageConfigProperty(
                    repository_access_mode="Platform"
                ),
                model_data_url=gold_tenant_model_s3_path
            )
    
            return tenant_model_primary_container 
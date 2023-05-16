# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import pathlib

from constructs import Construct

from aws_cdk import (
    Aws,
    NestedStack,
    CfnMapping,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker
)

INITIAL_INSTANCE_COUNT = 1
INITIAL_INSTANCE_WEIGHT = 1.0
INSTANCE_TYPE = "ml.t2.medium"

class PooledSageMakerEndpoint(NestedStack):
    def __init__(self, scope: Construct, id_: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

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

    def attach_sagemaker_bucket_policy(
        self, bucket: s3.Bucket, principle_role: iam.Role
    ) -> None:
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[principle_role],
                actions=["s3:GetBucket*", "s3:List*", "s3:DeleteObject*"],
                resources=[
                    bucket.bucket_arn,
                    bucket.arn_for_objects("*"),
                ],
            )
        )

    def generate_pooled_container_definition_property(
        self, models_bucket: s3.Bucket, container_image_uri: str
    ) -> sagemaker.CfnModel.ContainerDefinitionProperty:
        """
        Generate a SageMaker container definition for bronze multi-model
        """
        bronze_multi_model_s3_path = models_bucket.s3_url_for_object("model_artifacts_mme/")

        tenant_model_primary_container = sagemaker.CfnModel.ContainerDefinitionProperty(
            image=container_image_uri,
            image_config=sagemaker.CfnModel.ImageConfigProperty(
                repository_access_mode="Platform"
            ),
            mode="MultiModel",
            model_data_url=bronze_multi_model_s3_path,
        )

        return tenant_model_primary_container        
        
    def create_pooled_multi_model_iam_role(self, models_bucket: s3.Bucket) -> iam.Role:
        """
        Creates an IAM role for brozne SageMaker Multi-Model
        """
        pooled_s3_multi_model_arn_path = models_bucket.arn_for_objects(f"model_artifacts_mme/*")

        allow_access_to_s3_multi_model_files = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    resources=[models_bucket.bucket_arn],
                    actions=["s3:ListBucket"],
                    effect=iam.Effect.ALLOW,
                ),
                iam.PolicyStatement(
                    resources=[pooled_s3_multi_model_arn_path],
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                    ],
                    effect=iam.Effect.ALLOW,
                ),
            ]
        )

        pooled_multi_model_role = iam.Role(
            self,
            f"Pooled-Multi-Model-IAM-Role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description=f"IAM role for Amazon SageMaker to assume to access bronze's multi-model artifacts",
            inline_policies={
                "AllowAccessToS3ModelFiles": allow_access_to_s3_multi_model_files
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                )
            ],
        )
        return pooled_multi_model_role        
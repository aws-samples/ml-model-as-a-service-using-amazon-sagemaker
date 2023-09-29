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
    aws_sagemaker as sagemaker,
    aws_lambda_python_alpha as python_lambda,
    aws_lambda as lambda_,
    custom_resources as cr,
    CustomResource
)
from constructs import Construct

import aws_cdk as cdk

INITIAL_INSTANCE_COUNT = 1
INITIAL_INSTANCE_WEIGHT = 1.0
INSTANCE_TYPE = "ml.t2.medium"

class DedicatedSageMakerEndpoint(Construct):

    @property
    def model_endpoint_name(self) -> str:
        return self._model_endpoint_name

    def __init__(self, scope: Construct, construct_id: str, tenant_id: str, bucket: s3.Bucket, tenant_iam_role:iam.Role, **kwargs) -> None:
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
        
        # mlaas_application_bucket = s3.Bucket.from_bucket_attributes(self, 
        #     "ImportedBucket",
        #     bucket_arn=f'arn:aws:s3:::sagemaker-mlaas-pooled-{Aws.REGION}-{Aws.ACCOUNT_ID}'
        # )

        upload_sample_model_execution_role = iam.Role(self, "UploadSampleModelExecutionRole",
                                                        assumed_by=iam.ServicePrincipal(
                                                            "lambda.amazonaws.com"),
                                                        managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="CloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                                    managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                                          iam.ManagedPolicy.from_managed_policy_arn(self, id="AWSLambdaBasicExecutionRole",
                                                                                                                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                                        )

        upload_sample_model_execution_role.add_to_policy(iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[f"arn:aws:s3:::{bucket.bucket_name}",
                       f"arn:aws:s3:::{bucket.bucket_name}/*"
                ]
            )
            )

        upload_sample_model_function = python_lambda.PythonFunction(self, "update_tenant_details",
                                                                      entry="../custom_resources",
                                                                      runtime=lambda_.Runtime.PYTHON_3_9,
                                                                      index="update_sample_model.py",
                                                                      handler="handler",
                                                                      role=upload_sample_model_execution_role)

        upload_sample_model_provider = cr.Provider(self, "UploadSampleModelProvider",
                                                     on_event_handler=upload_sample_model_function
                                                     )

        upload_sample_model_custom_resource = CustomResource(self, "UploadSampleModelCustomResource", 
                                                service_token=upload_sample_model_provider.service_token,
                                                properties={
                                                    "S3Bucket": bucket.bucket_name
                                                })

        tenant_model_container = self.generate_container_definition_property(bucket, 
            xgboost_container_mapping.find_in_map(Aws.REGION,"containerImageUri"))
            
        tenant_model = sagemaker.CfnModel(
            self,
            f'SageMaker-Model',
            execution_role_arn=tenant_iam_role.role_arn,
            model_name=f'{tenant_id}-SageMaker-Model-Sample',
            primary_container=tenant_model_container,
        )

        tenant_model.node.add_dependency(upload_sample_model_custom_resource)

        model_endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "Endpoint-Config",
            endpoint_config_name=f'{tenant_id}-EndpointConfig-Sample',
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    initial_instance_count=INITIAL_INSTANCE_COUNT,
                    initial_variant_weight=INITIAL_INSTANCE_WEIGHT,
                    instance_type=INSTANCE_TYPE,
                    model_name=tenant_model.model_name,
                    variant_name=f"Variant0",
                ),
            ],
        )
        model_endpoint_config.node.add_dependency(tenant_model)

        model_endpoint = sagemaker.CfnEndpoint(
            self,
            f"SageMaker-Endpoint",
            endpoint_config_name=model_endpoint_config.attr_endpoint_config_name,
            endpoint_name=f'{tenant_id}-SageMaker-Endpoint',
        )        
        model_endpoint.node.add_dependency(model_endpoint_config)

        self._model_endpoint_name = model_endpoint.endpoint_name


        
    def generate_container_definition_property(self, models_bucket: s3.Bucket, container_image_uri: str) -> sagemaker.CfnModel.ContainerDefinitionProperty:
            """
            Generate a SageMaker container definition for the premium tenant model
            """
            premium_tenant_model_s3_path = models_bucket.s3_url_for_object("model_artifacts/model.tar.gz")
    
            tenant_model_primary_container = sagemaker.CfnModel.ContainerDefinitionProperty(
                image=container_image_uri,
                image_config=sagemaker.CfnModel.ImageConfigProperty(
                    repository_access_mode="Platform"
                ),
                model_data_url=premium_tenant_model_s3_path
            )
    
            return tenant_model_primary_container 
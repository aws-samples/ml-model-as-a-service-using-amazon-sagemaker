from aws_cdk import (
    Aws,
    aws_iam as iam,
    aws_s3 as s3,
    aws_apigateway as apigateway,
)
from constructs import Construct

from sm_pipeline_cdk.services import Services

from sm_pipeline_cdk.dedicated_sagemaker_infrastructure import DedicatedSageMakerInfrastructure
from sm_pipeline_cdk.dedicated_sagemaker_endpoint import DedicatedSageMakerEndpoint


class SiloedInfrastructure(Construct):
    def __init__(self, scope: Construct, id: str, tenant_id: str, 
    tenant_api: apigateway.RestApi, bucket: s3.Bucket, 
    services: Services, **kwargs):
        super().__init__(scope, id, **kwargs)
        

        dedicated_sagemaker_endpoint_stack = DedicatedSageMakerEndpoint(self, "DedicatedSageMakerEndpoint", bucket=bucket, tenant_id=tenant_id)
            
        dedicated_sagemaker_infrastructure_stack = DedicatedSageMakerInfrastructure(self, "DedicatedSageMakerInfrastructure", 
                tenant_id = tenant_id, 
                endpoint_name = dedicated_sagemaker_endpoint_stack.model_endpoint_name, 
                sagemaker_model_bucket_name = bucket.bucket_name,
                api_gateway_id = tenant_api.api_gateway.rest_api_id,
                api_gateway_root_resource_id = tenant_api.api_gateway.rest_api_root_resource_id)

        services.s3_uploader_role.add_to_policy(iam.PolicyStatement(
        actions=["s3:PutObject", "s3:GetObject","s3:ListBucket", "s3:DeleteObject"],
        resources=[f"arn:aws:s3:::{bucket.bucket_name}",
                    f"arn:aws:s3:::{bucket.bucket_name}/*"
                    ]
        )
        )

        services.inference_processor_role.add_to_policy(iam.PolicyStatement(
        actions=["sagemaker:InvokeEndpoint"],
        resources=[f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:endpoint/{dedicated_sagemaker_endpoint_stack.model_endpoint_name}"]
        )
        )

        services.sm_pipe_exec_role.add_to_policy(iam.PolicyStatement(
        actions=["s3:PutObject", "s3:GetObject","s3:ListBucket", "s3:DeleteObject"],
        resources=[f"arn:aws:s3:::{bucket.bucket_name}",
                    f"arn:aws:s3:::{bucket.bucket_name}/*"
                    ]
        )
        )

        services.inference_processor_lambda.add_environment("ENDPOINT_NAME", dedicated_sagemaker_endpoint_stack.model_endpoint_name)
        
        # Note: For silo tenants, prefix tenant_id/input/ 
        # and its notification are be added 
        # in update_tenant_details.py custom resource

       
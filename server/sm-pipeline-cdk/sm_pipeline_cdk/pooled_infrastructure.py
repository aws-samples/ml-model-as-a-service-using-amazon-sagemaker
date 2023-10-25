from aws_cdk import (
    Aws,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct
from sm_pipeline_cdk.services import Services
from sm_pipeline_cdk.pooled_sagemaker_endpoint import PooledSageMakerEndpoint

class PooledInfrastructure(Construct):
    def __init__(self, scope: Construct, id: str, tenant_id: str, bucket: s3.Bucket, services: Services, **kwargs):
        super().__init__(scope, id, **kwargs)

        pooled_sagemaker_endpoint_stack = PooledSageMakerEndpoint(self, "PooledSageMakerEndpoint", bucket)

        abac_tenant_iam_role = iam.Role(self, "MLaaSPooledTenantAbacRole",
                                                        role_name=f'ml-saas-tenant-abac-role-{tenant_id}-{Aws.REGION}',
                                                        assumed_by=iam.ServicePrincipal(
                                                            "lambda.amazonaws.com")
                                                        )
        abac_tenant_iam_role.add_to_policy(iam.PolicyStatement(
        actions=["s3:PutObject", "s3:GetObject","s3:ListBucket", "s3:DeleteObject"],
        resources=[f"arn:aws:s3:::{bucket.bucket_name}/${{aws:PrincipalTag/TenantID}}/*"
                    ]
        )
        )

        abac_tenant_iam_role.add_to_policy(iam.PolicyStatement(
        actions=["sagemaker:InvokeEndpoint"],
        resources=[pooled_sagemaker_endpoint_stack.model_endpoint.ref],
        conditions={
            "StringLike": {
                "sagemaker:TargetModel": f"${{aws:PrincipalTag/TenantID}}*.tar.gz"
                }
            },
        )
        )

        abac_tenant_iam_role.assume_role_policy.add_statements(iam.PolicyStatement(
            actions=["sts:AssumeRole","sts:TagSession"],
            effect=iam.Effect.ALLOW,
            principals=[iam.ArnPrincipal(services.sm_pipe_exec_role.role_arn),
                        iam.ArnPrincipal(services.authorizer_role.role_arn)],
            conditions={"StringLike": {"aws:RequestTag/TenantID":"*"}}
        ))

        services.inference_processor_lambda.add_environment("ENDPOINT_NAME", pooled_sagemaker_endpoint_stack.model_endpoint.endpoint_name) 
        services.authorizer_lambda.add_environment("ROLE_TO_ASSUME_ARN", abac_tenant_iam_role.role_arn) 
        services.sm_pipeline_execution_lambda.add_environment("S3_ACCESS_ROLE_ARN", abac_tenant_iam_role.role_arn)
        
        # TODO: Lab4 - comment below role policy statements 
        # to enable tenant isolation using ABAC role
        services.inference_processor_role.add_to_policy(iam.PolicyStatement(
        actions=["sagemaker:InvokeEndpoint"],
        resources=[pooled_sagemaker_endpoint_stack.model_endpoint.ref]
        ))

        services.s3_uploader_role.add_to_policy(iam.PolicyStatement(
        actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"],
        resources=[f"arn:aws:s3:::{bucket.bucket_name}/*"
                    ]
        )
        )

    
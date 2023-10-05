from constructs import Construct

from aws_cdk import (
    Aws,
    CfnOutput,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    Duration,
    aws_lambda_python_alpha as lambda_python,
    aws_iam as iam,
    CustomResource,
    custom_resources as cr,
    aws_s3 as s3,
)

from sm_pipeline_cdk.services import Services


class CustomResources(Construct):
    
    def __init__(self, scope: Construct, construct_id: str, tenant_id: str, bucket: s3.Bucket, services: Services, 
    tenant_api: apigateway.RestApi, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
            

        # Custom Resource to Write Details to DynamoDB
        update_tenant_details_execution_role = iam.Role(self, "UpdateTenantDetailsExecutionRole",
                                                        role_name=f'cus-res-exe-role-{tenant_id}-{Aws.REGION}',
                                                        assumed_by=iam.ServicePrincipal(
                                                            "lambda.amazonaws.com"),
                                                        managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="CloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                                    managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                                            iam.ManagedPolicy.from_managed_policy_arn(self, id="AWSLambdaBasicExecutionRole",
                                                                                                                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                                        )

        update_tenant_details_execution_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:UpdateItem", "dynamodb:PutItem"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails",
                        f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-Setting"]
        )
        )

        update_tenant_details_execution_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject"],
            resources=[f"arn:aws:s3:::{bucket.bucket_name}",
                        f"arn:aws:s3:::{bucket.bucket_name}/*"
                        ]
        )
        )

        update_tenant_details_execution_role.add_to_policy(iam.PolicyStatement(
            actions=["events:PutRule","events:PutTargets"],
            resources=[f"arn:aws:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:rule/*"]
        )
        )

        update_tenant_details_function = lambda_python.PythonFunction(self, "update_tenant_details",
                                                                        entry="../custom_resources",
                                                                        runtime=lambda_.Runtime.PYTHON_3_9,
                                                                        index="update_tenant_details.py",
                                                                        handler="handler",
                                                                        role=update_tenant_details_execution_role,
                                                                        function_name=f'UpdateTenantDtls-{tenant_id}-{Aws.REGION}')

        update_tenant_details_provider = cr.Provider(self, "UpdateTenantDetailsProvider",
                                                        on_event_handler=update_tenant_details_function
                                                        )

        update_tenant_details_custom_resource = CustomResource(self, "UpdateTenantDetailsCustomResource", 
                                                service_token=update_tenant_details_provider.service_token,
                                                properties={
                                                    "TenantId": tenant_id,
                                                    "TenantApiGatewayUrl": tenant_api.api_gateway.url,
                                                    "S3Bucket": bucket.bucket_name, 
                                                    "TenantDetailsTableName": "MLaaS-TenantDetails",
                                                    "SettingsTableName": "MLaaS-Setting",
                                                    "SagemakerS3Bucket": bucket.bucket_name,
                                                    "SagemakerPipelineExecFnArn": services.sm_pipeline_execution_lambda.function_arn
                                                })

        update_tenant_details_custom_resource.node.add_dependency(bucket)
        update_tenant_details_custom_resource.node.add_dependency(tenant_api)   

        
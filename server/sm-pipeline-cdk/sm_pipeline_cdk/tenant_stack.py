# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import resource
import string

import aws_cdk as cdk
from aws_cdk import (
    Aws,
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    CfnOutput,
    custom_resources as cr,
    aws_lambda_python_alpha as python_lambda,
    aws_lambda as lambda_,
    CustomResource,
    aws_events as events,
    aws_sqs as sqs,
    aws_events_targets as targets,
    aws_wafv2 as waf,
)
from constructs import Construct

from sm_pipeline_cdk.api_gateway import MlaasApiGateway
from sm_pipeline_cdk.waf_rules import Waf

from sm_pipeline_cdk.pooled_sagemaker_endpoint import PooledSageMakerEndpoint

from sm_pipeline_cdk.dedicated_sagemaker_infrastructure import DedicatedSageMakerInfrastructure
from sm_pipeline_cdk.dedicated_sagemaker_endpoint import DedicatedSageMakerEndpoint

class TenantCdkStack(Stack):
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        tenant_id = self.node.try_get_context("tenant_id")
        
        if not tenant_id:
            tenant_id = "pooled"
        
        
        bucket = s3.Bucket(self, 'TenantDataInputBucket',
                           encryption=s3.BucketEncryption.S3_MANAGED,
                           bucket_name=f'sagemaker-mlaas-{tenant_id}-{Aws.REGION}-{Aws.ACCOUNT_ID}',
                           block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                           auto_delete_objects=True,
                           removal_policy=cdk.RemovalPolicy.DESTROY,
                           event_bridge_enabled=True,
                           enforce_ssl=True
                           )
        
        CfnOutput(self, "TenantDataInputBucketName", value=bucket.bucket_name)

        # From the above TenantDataInputBucket we split the input data into train, validation and test data set 
        # and then copy all those datasets to below SagemakerDataInputBucket. And Sagemaker will read the data from 
        # SagemakerDataInputBucket. We implement it this way so that we can manage data upload events to these 
        # buckets seperately and easily.
        # sm_bucket = s3.Bucket(self, 'SagemakerDataInputBucket',
        #                    encryption=s3.BucketEncryption.S3_MANAGED,
        #                    bucket_name=f'sagemaker-mlaas-{tenant_id}-{Aws.REGION}-{Aws.ACCOUNT_ID}',
        #                    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        #                    auto_delete_objects=True,
        #                    removal_policy=cdk.RemovalPolicy.DESTROY,
        #                    event_bridge_enabled=True,
        #                    enforce_ssl=True
        #                    )
        
        # CfnOutput(self, "SagemakerDataInputBucketName", value=sm_bucket.bucket_name)

        # Call the apigateway construct
        tenant_api_gateway = MlaasApiGateway(self, "TenantResources", bucket_arn=bucket.bucket_arn, tenant_id=tenant_id)
        
        # Call the waf rules construct
        waf_rules = Waf(self, "WafRules", api_target_arn=tenant_api_gateway.api_gateway_arn, tenant_id=tenant_id)

        lambda_pipe_exec_iam_role = iam.Role(self, 'LambdaPipeExecRole',
        role_name=f'mlaas-pipe-exec-lambda-role-{tenant_id}-{Aws.REGION}',
        assumed_by=iam.CompositePrincipal(
            iam.ServicePrincipal("lambda.amazonaws.com")
            ),
        managed_policies=[
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSLambdaBasicExecutionRole",managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AmazonSageMakerFullAccess",managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"),
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSCloudFormationReadOnlyAccess",managed_policy_arn="arn:aws:iam::aws:policy/AWSCloudFormationReadOnlyAccess")
            ]
        )

        lambda_pipe_exec_iam_role.add_to_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            resources=["*"]
            )
        )

        dynamodb_access_role=iam.Role(self, "MLaaSDynamoDBAccessRole",
                                                        role_name=f'ml-saas-db-access-role-{tenant_id}-{Aws.REGION}',
                                                        assumed_by=iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn))

        sagemaker_execute_pipeline_fn = python_lambda.PythonFunction(self, "ExecuteSMPipelineFn",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions",
            index="sm_pipeline_execution.py",
            handler="handler",
            timeout = cdk.Duration.minutes(15),
            role = lambda_pipe_exec_iam_role,
            function_name=f'SMPipelineExeFunction-{tenant_id}-{Aws.REGION}'
        )

        # Adding permission for eventbrige to invoke sagemaker pipeline execution function     
        sagemaker_execute_pipeline_fn.add_permission(
            id="eventbridge-sagemaker-pipeline-id",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:rule/*"
        )
        

        # Get deployment type from context
        tenant_iam_role = ""

        if (tenant_id == "pooled"):
            tenant_iam_role = iam.Role(self, "MLaaSPooledTenantS3Role",
                                                        role_name=f'ml-saas-tenant-s3-role-{tenant_id}-{Aws.REGION}',
                                                        assumed_by=iam.ServicePrincipal(
                                                            "lambda.amazonaws.com"),
                                                        managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="AmazonSageMakerFullAccessPolicy",
                                                                                                                    managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")]
                                                        )
            tenant_iam_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject","s3:ListBucket", "s3:DeleteObject"],
            resources=[f"arn:aws:s3:::{bucket.bucket_name}/${{aws:PrincipalTag/TenantID}}/*"
                        # ,f"arn:aws:s3::::{sm_bucket.bucket_name}/${{aws:PrincipalTag/TenantID}}/*"
                       ]
            )
            )
            
            pooled_sagemaker_endpoint_stack = PooledSageMakerEndpoint(self, "PooledSageMakerEndpoint")

            tenant_iam_role.assume_role_policy.add_statements(iam.PolicyStatement(
                actions=["sts:AssumeRole","sts:TagSession"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn)],
                conditions={"StringLike": {"aws:RequestTag/TenantID":"*"}}
            ))

            dynamodb_access_role.assume_role_policy.add_statements(iam.PolicyStatement(
                actions=["sts:AssumeRole","sts:TagSession"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn)],
                conditions={"StringLike": {"aws:RequestTag/TenantID":"*"}}
            ))

            dynamodb_access_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"],
            conditions={"ForAllValues:StringEquals":{
                    "dynamodb:LeadingKeys": [
                        f"${{aws:PrincipalTag/TenantID}}"
                    ]
                    }
                }
            )
            )

        else:
        
            tenant_iam_role = iam.Role(self, 'SageMakerTenantIamRole',
                role_name=f'mlaas-tenant-role-{tenant_id}-{Aws.REGION}',
                assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("sagemaker.amazonaws.com")
                ),
                managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="AmazonSageMakerFullAccess",managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")]
                )
            tenant_iam_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject","s3:ListBucket", "s3:DeleteObject"],
            resources=[f"arn:aws:s3:::{bucket.bucket_name}",
                       f"arn:aws:s3:::{bucket.bucket_name}/*"
                    #    ,f"arn:aws:s3::::{sm_bucket.bucket_name}",
                    #    f"arn:aws:s3::::{sm_bucket.bucket_name}/*"
                       ]
            )
            )

            dedicated_samgemaker_endpoint_stack = DedicatedSageMakerEndpoint(self, "DedicatedSageMakerEndpoint", bucket=bucket, tenant_id=tenant_id, tenant_iam_role=tenant_iam_role)
            
            dedicated_samgemaker_infrastructure_stack = DedicatedSageMakerInfrastructure(self, "DedicatedSageMakerInfrastructure", 
                 tenant_id = tenant_id, 
                 endpoint_name = dedicated_samgemaker_endpoint_stack.model_endpoint_name, 
                 sagemaker_model_bucket_name = bucket.bucket_name,
                 api_gateway_id = tenant_api_gateway._api_gateway_id,
                 api_gateway_root_resource_id = tenant_api_gateway._api_gateway_root_resource_id)

            tenant_iam_role.assume_role_policy.add_statements(iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn)]
            ))

            dynamodb_access_role.assume_role_policy.add_statements(iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn)]
            ))

            dynamodb_access_role.add_to_policy(iam.PolicyStatement(
             actions=["dynamodb:GetItem"],
             resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"],
             conditions={"ForAllValues:StringEquals":{
                     "dynamodb:LeadingKeys": [
                         f"{tenant_id}"
                     ]
                     }
                 }
             )
             )
            
            # Note: For silo tenants, prefix tenant_id/input/ 
            # and its notification are be added 
            # in update_tenant_details.py custom resource

        sagemaker_execute_pipeline_fn.add_environment("dynamodb_access_role_arn", dynamodb_access_role.role_arn) 
        sagemaker_execute_pipeline_fn.add_environment("tenant_type", tenant_id)

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
                    #    ,f"arn:aws:s3:::{sm_bucket.bucket_name}",
                    #    f"arn:aws:s3:::{sm_bucket.bucket_name}/*"
                       ]
        )
        )

        update_tenant_details_execution_role.add_to_policy(iam.PolicyStatement(
            actions=["events:PutRule","events:PutTargets"],
            resources=[f"arn:aws:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:rule/*"]
        )
        )

        update_tenant_details_function = python_lambda.PythonFunction(self, "update_tenant_details",
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
                                                    "TenantApiGatewayUrl": tenant_api_gateway.api_gateway_url,
                                                    "S3Bucket": bucket.bucket_name, 
                                                    "TenantRoleArn": tenant_iam_role.role_arn,
                                                    "TenantDetailsTableName": "MLaaS-TenantDetails",
                                                    "SettingsTableName": "MLaaS-Setting",
                                                    "SagemakerS3Bucket": bucket.bucket_name,
                                                    "SagemakerPipelineExecFnArn": sagemaker_execute_pipeline_fn.function_arn
                                                })

        #Depends on
        # update_tenant_details_custom_resource.node.add_dependency(s3_upload_api)
        update_tenant_details_custom_resource.node.add_dependency(bucket)
        update_tenant_details_custom_resource.node.add_dependency(tenant_api_gateway)         
        
        
        CfnOutput(self, "APIGatewayURL", value=tenant_api_gateway.api_gateway_url)
        CfnOutput(self, "APIGatewayID", value=tenant_api_gateway.api_gateway_id)
        CfnOutput(self, "APIGatewayRootResourceID", value=tenant_api_gateway.api_gateway_root_resource_id)
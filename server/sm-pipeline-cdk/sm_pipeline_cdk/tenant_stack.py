# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import resource
import string

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
    RemovalPolicy,
)
from constructs import Construct

from sm_pipeline_cdk.services import Services
from sm_pipeline_cdk.api_gateway import MlaasApiGateway
from sm_pipeline_cdk.waf_rules import Waf

from sm_pipeline_cdk.pooled_infrastructure import PooledInfrastructure
from sm_pipeline_cdk.siloed_infrastructure import SiloedInfrastructure
from sm_pipeline_cdk.custom_resources import CustomResources



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
                           removal_policy=RemovalPolicy.DESTROY,
                           event_bridge_enabled=True,
                           enforce_ssl=True
                           )
        
        CfnOutput(self, "TenantDataInputBucketName", value=bucket.bucket_name)

        services = Services(self, "Services", tenant_id=tenant_id)

        # Call the apigateway construct
        tenant_api = MlaasApiGateway(self, "TenantResources", tenant_id=tenant_id, services=services)
        
        # Call the waf rules construct
        waf_rules = Waf(self, "WafRules", api_target_arn=tenant_api.api_gateway_arn, tenant_id=tenant_id)


        if (tenant_id == "pooled"):
            pooled_infra = PooledInfrastructure(self, "PooledInfrastructure", tenant_id=tenant_id, bucket=bucket, services=services)

        else:
            siloed_infra = SiloedInfrastructure(self, "SiloedInfrastructure", tenant_id=tenant_id, 
                                tenant_api=tenant_api, bucket=bucket, services=services)

        
        custom_resources = CustomResources(self, "CustomResources", tenant_id=tenant_id, bucket=bucket, services=services, tenant_api=tenant_api)       
        
        
        CfnOutput(self, "APIGatewayURL", value=tenant_api.api_gateway.url)
        CfnOutput(self, "APIGatewayID", value=tenant_api.api_gateway.rest_api_id)
        CfnOutput(self, "APIGatewayRootResourceID", value=tenant_api.api_gateway.rest_api_root_resource_id)
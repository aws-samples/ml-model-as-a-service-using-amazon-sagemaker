# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#!/usr/bin/env python3
import os

import aws_cdk as cdk

from sm_pipeline_cdk.sm_pipeline_cdk_stack import SmPipelineCdkStack
from sm_pipeline_cdk.networking_stack import NetworkingCdkStack
from sm_pipeline_cdk.tenant_stack import TenantCdkStack

env_USA = cdk.Environment(account=cdk.Aws.ACCOUNT_ID, region=cdk.Aws.REGION)

app = cdk.App()

custom_stack_name = app.node.try_get_context("stack_name")

if not custom_stack_name:
    custom_stack_name = "mlaas-stack-pooled"
    
network_stack = NetworkingCdkStack(app, "NetworkingCdkStack", env=env_USA)
sagemaker_stack = SmPipelineCdkStack(app, "SmPipelineCdkStack", vpc_id=network_stack.vpc_id, public_subnet_ids=network_stack.public_subnet_ids, env=env_USA, stack_name="mlaas-cdk-shared-template")
tenant_stack = TenantCdkStack(app, "TenantCdkStack", env=env_USA, stack_name=custom_stack_name)

app.synth()

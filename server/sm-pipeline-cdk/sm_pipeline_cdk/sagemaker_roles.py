# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import builtins
from constructs import Construct
from aws_cdk import (
    Aws,
    aws_iam as iam
    )

class SageMakerRoles(Construct):

    @property
    def sm_execution_role(self):
        return self._sm_execution_role
    


    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        #SageMaker Execution Role
        sm_execution_role = iam.Role(self, 'AmazonSageMakerExecutionRole', 
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
		    role_name=f"AmazonSagemakerExecutionRole-ml-saas-workshop-{Aws.REGION}",
            path="/service-role/",
		    managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self,id="AmazonSagemakerFullAccess",
                managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_managed_policy_arn(self,id="AmazonDynamoDBFullAccess",
                managed_policy_arn="arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess")
                ])
        
        sm_execution_role.add_to_policy(iam.PolicyStatement(
                actions=["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket",
                "cloudformation:DescribeStacks", "cognito-idp:AdminSetUserPassword"],
                resources=["arn:aws:s3:::sagemaker-*",
                           "arn:aws:s3:::sagemaker-*/*"
                            "arn:aws:s3:::mlaas-*",
                            "arn:aws:s3:::mlaas-*/*",
                            f"arn:aws:cloudformation:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/*/*",
                            f"arn:aws:cognito-idp:{Aws.REGION}:{Aws.ACCOUNT_ID}:userpool/*"]
            ))
        
        self._sm_execution_role = sm_execution_role
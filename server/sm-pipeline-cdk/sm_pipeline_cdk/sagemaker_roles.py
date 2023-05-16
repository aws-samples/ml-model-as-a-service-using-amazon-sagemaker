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
    
    @property
    def sm_sc_product_use_role(self):
        return self._sm_sc_product_use_role
    
    @property
    def sm_sc_product_codebuild_role(self):
        return self._sm_sc_product_codebuild_role
    
    @property
    def sm_sc_product_codepipeline_role(self):
        return self._sm_sc_product_codepipeline_role
    
    @property
    def sm_sc_product_launch_role(self):
        return self._sm_sc_product_launch_role
    


    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        #SageMaker Execution Role
        sm_execution_role = iam.Role(self, 'AmazonSageMakerExecutionRole', 
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
		    role_name=f"AmazonSagemakerExecutionRole-ml-saas-workshop-{Aws.REGION}",
            path="/service-role/",
		    managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self,id="SagemakerFullAccess",
                managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")
                ])
        
        sm_execution_role.add_to_policy(iam.PolicyStatement(
                actions=["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
                resources=["arn:aws:s3:::sagemaker-*",
                           "arn:aws:s3:::sagemaker-*/*"
                            "arn:aws:s3:::mlaas-*",
                            "arn:aws:s3:::mlaas-*/*"]
            ))
        
        self._sm_execution_role = sm_execution_role

        # SageMaker Product Use Role Policy Document
        sm_product_use_role_policy = iam.PolicyDocument(
            statements=[
            iam.PolicyStatement(
                actions= ["cloudformation:CreateChangeSet",
				"cloudformation:CreateStack",
				"cloudformation:DescribeChangeSet",
				"cloudformation:DeleteChangeSet",
				"cloudformation:DeleteStack",
				"cloudformation:DescribeStacks",
				"cloudformation:ExecuteChangeSet",
				"cloudformation:SetStackPolicy",
				"cloudformation:UpdateStack"],
                resources=["arn:aws:cloudformation:*:*:stack/sagemaker-*"],
                effect=iam.Effect.ALLOW), 
            iam.PolicyStatement(
                actions= ["cloudwatch:PutMetricData"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["codebuild:BatchGetBuilds",
				"codebuild:StartBuild"],
                resources=["arn:aws:codebuild:*:*:project/sagemaker-*",
				"arn:aws:codebuild:*:*:build/sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["codecommit:CancelUploadArchive",
				"codecommit:GetBranch",
				"codecommit:GetCommit",
				"codecommit:GetUploadArchiveStatus",
				"codecommit:UploadArchive"],
                resources=["arn:aws:codecommit:*:*:sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["codepipeline:StartPipelineExecution"],
                resources=["arn:aws:codepipeline:*:*:sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["ec2:DescribeRouteTables"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["ecr:BatchCheckLayerAvailability",
				"ecr:BatchGetImage",
				"ecr:Describe*",
				"ecr:GetAuthorizationToken",
				"ecr:GetDownloadUrlForLayer"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["ecr:BatchDeleteImage",
				"ecr:CompleteLayerUpload",
				"ecr:CreateRepository",
				"ecr:DeleteRepository",
				"ecr:InitiateLayerUpload",
				"ecr:PutImage",
				"ecr:UploadLayerPart"],
                resources=["arn:aws:ecr:*:*:repository/sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["events:DeleteRule",
				"events:DescribeRule",
				"events:PutRule",
				"events:PutTargets",
				"events:RemoveTargets"],
                resources=["arn:aws:events:*:*:rule/sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["firehose:PutRecord",
				"firehose:PutRecordBatch"],
                resources=["arn:aws:firehose:*:*:deliverystream/sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["glue:BatchCreatePartition",
				"glue:BatchDeletePartition",
				"glue:BatchDeleteTable",
				"glue:BatchDeleteTableVersion",
				"glue:BatchGetPartition",
				"glue:CreateDatabase",
				"glue:CreatePartition",
				"glue:CreateTable",
				"glue:DeletePartition",
				"glue:DeleteTable",
				"glue:DeleteTableVersion",
				"glue:GetDatabase",
				"glue:GetPartition",
				"glue:GetPartitions",
				"glue:GetTable",
				"glue:GetTables",
				"glue:GetTableVersion",
				"glue:GetTableVersions",
				"glue:SearchTables",
				"glue:UpdatePartition",
				"glue:UpdateTable",
				"glue:GetUserDefinedFunctions"],
                resources=["arn:aws:glue:*:*:catalog",
				"arn:aws:glue:*:*:database/default",
				"arn:aws:glue:*:*:database/global_temp",
				"arn:aws:glue:*:*:database/sagemaker-*",
				"arn:aws:glue:*:*:table/sagemaker-*",
				"arn:aws:glue:*:*:tableVersion/sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["iam:PassRole"],
                resources=["arn:aws:iam::*:role/service-role/AmazonSageMakerServiceCatalogProductsUse*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["lambda:InvokeFunction"],
                resources=["arn:aws:lambda:*:*:function:sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["logs:CreateLogDelivery",
				"logs:CreateLogGroup",
				"logs:CreateLogStream",
				"logs:DeleteLogDelivery",
				"logs:Describe*",
				"logs:GetLogDelivery",
				"logs:GetLogEvents",
				"logs:ListLogDeliveries",
				"logs:PutLogEvents",
				"logs:PutResourcePolicy",
				"logs:UpdateLogDelivery"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["s3:CreateBucket",
				"s3:DeleteBucket",
				"s3:GetBucketAcl",
				"s3:GetBucketCors",
				"s3:GetBucketLocation",
				"s3:ListAllMyBuckets",
				"s3:ListBucket",
				"s3:ListBucketMultipartUploads",
				"s3:PutBucketCors",
				"s3:PutObjectAcl",
                "s3:AbortMultipartUpload",
				"s3:DeleteObject",
				"s3:GetObject",
				"s3:GetObjectVersion",
				"s3:PutObject"],
                resources=["arn:aws:s3:::aws-glue-*",
				"arn:aws:s3:::sagemaker-*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["sagemaker:*"],
                not_resources=["arn:aws:sagemaker:*:*:domain/*",
				"arn:aws:sagemaker:*:*:user-profile/*",
				"arn:aws:sagemaker:*:*:app/*",
				"arn:aws:sagemaker:*:*:flow-definition/*"]),
            iam.PolicyStatement(
                actions= ["states:DescribeExecution",
				"states:DescribeStateMachine",
				"states:DescribeStateMachineForExecution",
				"states:GetExecutionHistory",
				"states:ListExecutions",
				"states:ListTagsForResource",
				"states:StartExecution",
				"states:StopExecution",
				"states:TagResource",
				"states:UntagResource",
				"states:UpdateStateMachine"],
                resources=["arn:aws:states:*:*:stateMachine:sagemaker-*",
				"arn:aws:states:*:*:execution:sagemaker-*:*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["states:ListStateMachines"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions= ["codestar-connections:UseConnection"],
                resources=["arn:aws:codestar-connections:*:*:connection/*"],
                conditions=
                    {
                        "StringEqualsIgnoreCase" :{
                            "aws:ResourceTag/sagemaker": "true"
                        }
                     },
                effect=iam.Effect.ALLOW)
            ]
        )
        
        #SageMaker Product Use Role
        sm_sc_product_use_role = iam.Role(self, 'AmazonSageMakerServiceCatalogProductsUseRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('sagemaker.amazonaws.com'),
                iam.ServicePrincipal('glue.amazonaws.com'),
                iam.ServicePrincipal('codebuild.amazonaws.com'),
                iam.ServicePrincipal('codepipeline.amazonaws.com'),
                iam.ServicePrincipal('apigateway.amazonaws.com'),
                iam.ServicePrincipal('states.amazonaws.com'),
                iam.ServicePrincipal('cloudformation.amazonaws.com'),
                iam.ServicePrincipal('lambda.amazonaws.com'),
                iam.ServicePrincipal('events.amazonaws.com'),
                iam.ServicePrincipal('firehose.amazonaws.com')
            ),
            role_name="AmazonSageMakerServiceCatalogProductsUseRole",
            path="/service-role/",
            inline_policies={"AmazonSageMakerServiceCatalogProductsUseRolyPolicy": sm_product_use_role_policy}
        )

        sm_sc_product_use_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:UpdateItem"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"]
        ))    

        self._sm_sc_product_use_role = sm_sc_product_use_role
        
        #SageMaker Product Codebuild Role
        sm_sc_product_codebuild_role = iam.Role(self, 'AmazonSageMakerServiceCatalogProductsCodeBuildRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('codebuild.amazonaws.com'),
            ),
            role_name="AmazonSageMakerServiceCatalogProductsCodeBuildRole",
            path="/service-role/",
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self,id="AmazonSageMakerServiceCatalogProductsCodeBuildRolePolicy",
                managed_policy_arn="arn:aws:iam::aws:policy/AWSCodeBuildDeveloperAccess")
            ])
        
        self._sm_sc_product_codebuild_role = sm_sc_product_codebuild_role
        
        #SageMake Product Pipeline Role
        sm_sc_product_codepipeline_role = iam.Role(self, 'AmazonSageMakerServiceCatalogProductsCodePipelineRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('codepipeline.amazonaws.com'),
            ),
            role_name="AmazonSageMakerServiceCatalogProductsCodePipelineRole",
            path="/service-role/",
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self,id="AmazonSageMakerServiceCatalogProductsCodePipelineRolePolicy",
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonSageMakerServiceCatalogProductsCodePipelineServiceRolePolicy"),
            ])
        
        self._sm_sc_product_codepipeline_role = sm_sc_product_codepipeline_role
        
        #SageMaker Product Launch Role
        sm_sc_product_launch_role = iam.Role(self, 'AmazonSageMakerServiceCatalogProductsLaunchRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('servicecatalog.amazonaws.com')
            ),
            role_name="AmazonSageMakerServiceCatalogProductsLaunchRole",
            path="/service-role/",
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self,id="AmazonSageMakerAdmin-ServiceCatalogProductsServiceRolePolicy",
                managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerAdmin-ServiceCatalogProductsServiceRolePolicy")]
        )

        self._sm_sc_product_launch_role = sm_sc_product_launch_role

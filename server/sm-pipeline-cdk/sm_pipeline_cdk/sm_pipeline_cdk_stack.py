# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from encodings import utf_8
from aws_cdk import (
    Aws,
    Stack,
    CfnOutput,
    CfnMapping,
    aws_sagemaker as sagemaker,
    aws_iam as iam,
    aws_servicecatalog as sc,
    custom_resources as cr,
    )

from constructs import Construct
from .sagemaker_roles import SageMakerRoles
from .sagemaker_service_catalogue import SageMakerServiceCatalogue
from .sagemaker_project import SageMakerProject

class SmPipelineCdkStack(Stack):
    
    @property
    def sm_domain_id(self):
        return self._sm_domain_id

    @property
    def service_catalog_portfolio_id(self):
        return self._service_catalog_portfolio_id

    def __init__(self, scope: Construct, construct_id: str, vpc_id: str, public_subnet_ids: list , **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #SageMaker EC2 Arn Map
        sagemaker_ec2_arn_table = CfnMapping(self, "sagemakerEc2ArnMapping",
            mapping={
                "us-east-1": {
                    "jupyterserver": "arn:aws:sagemaker:us-east-1:081325390199:image/jupyter-server",
                    "jupyterserver3": "arn:aws:sagemaker:us-east-1:081325390199:image/jupyter-server-3"
                },
                "us-west-2": {
                    "jupyterserver": "arn:aws:sagemaker:us-west-2:236514542706:image/jupyter-server",
                    "jupyterserver3": "arn:aws:sagemaker:us-west-2:236514542706:image/jupyter-server-3"
                }
 
            }
        )

        sagemaker_roles = SageMakerRoles(self, "SageMakerRoles")
        sm_execution_role = sagemaker_roles.sm_execution_role

        sagemaker_service_catalog = SageMakerServiceCatalogue(self, "SageMakerServiceCatalogue", sm_execution_role)
        self._service_catalog_portfolio_id =sagemaker_service_catalog.service_catalog_portfolio_id
        

        CfnOutput(self, "SageMakerExecutionRoleArn",
                       value=sagemaker_roles.sm_execution_role.role_arn)
        
        CfnOutput(self, "AmazonSageMakerServiceCatalogProductsUseRoleArn",
                       value=sagemaker_roles.sm_sc_product_use_role.role_arn)

        CfnOutput(self, "AmazonSageMakerServiceCatalogProductsCodeBuildRoleArn",
                       value=sagemaker_roles.sm_sc_product_codebuild_role.role_arn)

        CfnOutput(self, "AmazonSageMakerServiceCatalogProductsCodePipelineRoleArn",
                       value=sagemaker_roles.sm_sc_product_codepipeline_role.role_arn)


        CfnOutput(self, "SageMakerServiceCatalogProductLaunchRoleArn",
                       value=sagemaker_roles.sm_sc_product_launch_role.role_arn)
        
        CfnOutput(self, "Service Catalog Portfolio ID", 
                  value=sagemaker_service_catalog.service_catalog_portfolio_id)

        sm_domain = sagemaker.CfnDomain(
            
            self, "Sagemaker_Domain",
            auth_mode='IAM',
            default_user_settings={"executionRole": sm_execution_role.role_arn},
            domain_name="mlaas-workshop",
            subnet_ids=public_subnet_ids,
            vpc_id=vpc_id,
        )

        self._sm_domain_id = sm_domain.attr_domain_id

        CfnOutput(self, "SmDomainID",
                       value=sm_domain.attr_domain_id)

        #Create SageMaker User for Pooled Tenants
        mlaas_pool_sagemaker_user_profile = sagemaker.CfnUserProfile(self, "SagemakerUserProfilePool",
            domain_id=self._sm_domain_id,
            user_profile_name="mlaas-provider-user",

            user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                execution_role=sm_execution_role.role_arn,
                jupyter_server_app_settings=sagemaker.CfnUserProfile.JupyterServerAppSettingsProperty(
                    default_resource_spec=sagemaker.CfnUserProfile.ResourceSpecProperty(
                        sage_maker_image_arn=sagemaker_ec2_arn_table.find_in_map(Aws.REGION,"jupyterserver3"),
                    )
                )
            )
        )

        #Create Sagemaker App
        cfn_app_pool = sagemaker.CfnApp(self, "SageMakerPoolApp",
            app_name="default",
            app_type="JupyterServer",
            domain_id=self._sm_domain_id,
            user_profile_name="mlaas-provider-user",

            # the properties below are optional
            resource_spec=sagemaker.CfnApp.ResourceSpecProperty(
                sage_maker_image_arn=sagemaker_ec2_arn_table.find_in_map(Aws.REGION,"jupyterserver3"),
            )
        )

        #Create SageMaker Project
        sm_project = SageMakerProject(self, "SageMakerProject", self._service_catalog_portfolio_id, self._sm_domain_id)

        CfnOutput(self,"MlaasPoolSagemakerProjectName", 
                  value=sm_project.sagemaker_project_name, export_name="MlaasPoolSagemakerProjectProjectName")


        # #Depends on
        cfn_app_pool.node.add_dependency(mlaas_pool_sagemaker_user_profile)
        sm_domain.node.add_dependency(sagemaker_roles)
        mlaas_pool_sagemaker_user_profile.node.add_dependency(sm_domain)
        cfn_app_pool.node.add_dependency(mlaas_pool_sagemaker_user_profile)
        sm_project.node.add_dependency(sm_domain)
        
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    custom_resources as cr,
    aws_sagemaker as sagemaker,
)

class SageMakerProject(Construct):
    
    @property
    def sagemaker_project_name(self) -> str:
        return self._sagemaker_project_name

    def __init__(self, scope: Construct, id: str, service_catalog_portfolio_id: str, sm_domain_id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #Create SageMaker Project  
        #Get the Service Catalogic ProductID
        aws_sc_search_products_custom_resource = cr.AwsCustomResource(self, "AwsServiceCatalogSearchProducts",
            on_create=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="searchProductsAsAdmin",
                parameters={
                    "Filters": {
                        "FullTextSearch": ["MLOps template for model building and training"]
                    },
                    # "PortfolioId": self._service_catalog_portfolio_id
                    "PortfolioId": service_catalog_portfolio_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogSearchProducts")
            ),

            on_update=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="searchProductsAsAdmin",
                parameters={
                    "Filters": {
                        "FullTextSearch": ["MLOps template for model building and training"]
                    },
                    # "PortfolioId": self._service_catalog_portfolio_id
                    "PortfolioId": service_catalog_portfolio_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogSearchProducts")
            ),

            on_delete=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="searchProductsAsAdmin",
                parameters={
                    "Filters": {
                        "FullTextSearch": ["MLOps template for model building and training"]
                    },
                    # "PortfolioId": self._service_catalog_portfolio_id
                    "PortfolioId": service_catalog_portfolio_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogSearchProducts")
            ),


            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )
        
        self._sm_sc_mlops_product_id=aws_sc_search_products_custom_resource.get_response_field('ProductViewDetails.0.ProductViewSummary.ProductId')
        
        #Get the Service Catalog Provisioning Artifact
        aws_sc_search_products_custom_resource = cr.AwsCustomResource(self, "AwsServiceCatalogProvisioningArtifact",
            on_create=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="listProvisioningArtifacts",
                parameters={
                    "ProductId": self._sm_sc_mlops_product_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogProvisioningArtifact")
            ),

            on_update=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="listProvisioningArtifacts",
                parameters={
                    "ProductId": self._sm_sc_mlops_product_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogProvisioningArtifact")
            ),

            on_delete=cr.AwsSdkCall(
                service="ServiceCatalog",
                action="listProvisioningArtifacts",
                parameters={
                    "ProductId": self._sm_sc_mlops_product_id
                },
                physical_resource_id=cr.PhysicalResourceId.of("AwsServiceCatalogProvisioningArtifact")
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )

        # aws_sc_search_products_custom_resource.node.add_dependency(sagemaker_service_catalog_portfolio)
        
        self._sm_sc_mlops_provisioning_artifact_id=aws_sc_search_products_custom_resource.get_response_field('ProvisioningArtifactDetails.1.Id')
        
        service_catalog_provisioning_details={
            "ProductId": self._sm_sc_mlops_product_id,
            "ProvisioningArtifactId": self._sm_sc_mlops_provisioning_artifact_id
        }

        cfn_pool_sagemaker_project = sagemaker.CfnProject(self, "SageMakerProjectPool",
            project_name=f'mlaas-workshop-{sm_domain_id}',
            service_catalog_provisioning_details=service_catalog_provisioning_details,

            # the properties below are optional
            project_description="ML-as-a-Service Workshop Project",
        )

        self._sagemaker_project_name=cfn_pool_sagemaker_project.project_name        
        



# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from constructs import Construct
from aws_cdk import (
    Aws,
    aws_iam as iam,
    custom_resources as cr,
    CfnOutput,
    aws_servicecatalog as sc
)


class SageMakerServiceCatalogue(Construct):

    @property
    def service_catalog_portfolio_id(self) -> str:
        return self._service_catalog_portfolio_id

    def __init__(self, scope: Construct, id: str, sm_execution_role: iam.Role , **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cdk_role_arn = f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/cdk-hnb659fds-cfn-exec-role-{Aws.ACCOUNT_ID}-{Aws.REGION}"

        # Enable SageMaker Service Catalog Portfolio
        aws_sm_custom_resource_enable_service_catalog = cr.AwsCustomResource(self, "AwsSagemakerCustomResource",
                                                                             on_create=cr.AwsSdkCall(
                                                                                 service="SageMaker",
                                                                                 action="enableSagemakerServicecatalogPortfolio",
                                                                                 physical_resource_id=cr.PhysicalResourceId.of(
                                                                                     "AwsSagemakerCustomResource")
                                                                             ),
                                                                             policy=cr.AwsCustomResourcePolicy.from_statements(
                                                                                 statements=[
                                                                                     iam.PolicyStatement(
                                                                                         actions=["servicecatalog:ListAcceptedPortfolioShares",
                                                                                                  "servicecatalog:AcceptPortfolioShare",
                                                                                                  "sagemaker:EnableSagemakerServicecatalogPortfolio"],
                                                                                         resources=[
                                                                                             "*"],
                                                                                         effect=iam.Effect.ALLOW
                                                                                     )
                                                                                 ]
                                                                             )
                                                                             )

        aws_sc_list_accepted_portfolios_custom_resource = cr.AwsCustomResource(self, "AwsSericeCatalogListAccesptedPortfolios",
                                                                               on_create=cr.AwsSdkCall(
                                                                                   service="ServiceCatalog",
                                                                                   action="listAcceptedPortfolioShares",
                                                                                   physical_resource_id=cr.PhysicalResourceId.of(
                                                                                       "AwsSericeCatalogListAcceptedPortfolios")
                                                                               ),
                                                                               on_update=cr.AwsSdkCall(
                                                                                   service="ServiceCatalog",
                                                                                   action="listAcceptedPortfolioShares",
                                                                                   physical_resource_id=cr.PhysicalResourceId.of(
                                                                                       "AwsSericeCatalogListAcceptedPortfolios")
                                                                               ),
                                                                               policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                                                                                   resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
                                                                               ),
                                                                               on_delete=cr.AwsSdkCall(
                                                                                   service="ServiceCatalog",
                                                                                   action="listAcceptedPortfolioShares",
                                                                                   physical_resource_id=cr.PhysicalResourceId.of(
                                                                                       "AwsSericeCatalogListAcceptedPortfolios")
                                                                               )
                                                                               )

        self._service_catalog_portfolio_id = aws_sc_list_accepted_portfolios_custom_resource.get_response_field(
            "PortfolioDetails.0.Id")
        self._service_catalog_portfolio_arn = aws_sc_list_accepted_portfolios_custom_resource.get_response_field(
            "PortfolioDetails.0.ARN")

        # Grant CDK Exec Role access to SageeMaker Service catalog Portfolio
        sagemaker_service_catalog_portfolio = sc.Portfolio.from_portfolio_arn(
            self, "SageMakerSolutionsServiceCatalog", self._service_catalog_portfolio_arn)
        cdk_role = iam.Role.from_role_arn(self, "CdkRole", cdk_role_arn)

        # Associate CDK role from the Service Catalog
        aws_sc_associate_cdk_role_cr = cr.AwsCustomResource(self, "AwsServiceCatalogAssociateCdkRole",
                                                            on_create=cr.AwsSdkCall(
                                                                service="ServiceCatalog",
                                                                action="associatePrincipalWithPortfolio",
                                                                parameters={
                                                                    "PortfolioId": self._service_catalog_portfolio_id,
                                                                    "PrincipalARN": cdk_role_arn,
                                                                    "PrincipalType": "IAM"
                                                                },
                                                                physical_resource_id=cr.PhysicalResourceId.of(
                                                                    "AwsServiceCatalogAssociateCdkRole")
                                                            ),
                                                            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                                                                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
                                                            )
                                                            )

        # Dependecy
        sagemaker_service_catalog_portfolio.node.add_dependency(
            aws_sc_list_accepted_portfolios_custom_resource)
        aws_sc_list_accepted_portfolios_custom_resource.node.add_dependency(
            aws_sm_custom_resource_enable_service_catalog)

        aws_sc_get_portfolio_id_custom_resource = cr.AwsCustomResource(self, "AwsSericeCatalogGetPortfolioID",
                                                                       on_create=cr.AwsSdkCall(
                                                                           service="ServiceCatalog",
                                                                           action="associatePrincipalWithPortfolio",
                                                                           parameters={
                                                                               "PortfolioId": self._service_catalog_portfolio_id,
                                                                               "PrincipalARN": sm_execution_role.role_arn,
                                                                               "PrincipalType": "IAM"

                                                                           },
                                                                           physical_resource_id=cr.PhysicalResourceId.of(
                                                                               "AwsSericeCatalogGetPortfolioID")
                                                                       ),

                                                                       policy=cr.AwsCustomResourcePolicy.from_statements(
                                                                           statements=[
                                                                               iam.PolicyStatement(
                                                                                   actions=["servicecatalog:ListAcceptedPortfolioShares",
                                                                                            "servicecatalog:AmazonSageMakerAdmin",
                                                                                            "servicecatalog:AcceptPortfolioShare",
                                                                                            "sagemaker:EnableSagemakerServicecatalogPortfolio",
                                                                                            "servicecatalog:AssociatePrincipalWithPortfolio",
                                                                                            "iam:GetRole",

                                                                                            ],
                                                                                   resources=[
                                                                                       "*"],
                                                                                   effect=iam.Effect.ALLOW
                                                                               )
                                                                           ]
                                                                       )
                                                                       )
        


# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_wafv2 as waf,
)
from constructs import Construct

class Waf(Construct):

    def __init__(self, scope: Construct, id: str, api_target_arn: str, tenant_id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        waf_rules = []

        # 1, AWS general rules
        aws_managed_rules = waf.CfnWebACL.RuleProperty(
            name='AWS-AWSManagedRulesCommonRuleSet',
            priority=1,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesCommonRuleSet',
                    vendor_name='AWS',
                    excluded_rules=[waf.CfnWebACL.ExcludedRuleProperty(name='SizeRestrictions_BODY')]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='awsCommonRules',
                sampled_requests_enabled=True,
            ),

        )
        waf_rules.append(aws_managed_rules)

        # 2, AWS AnonIPAddress
        aws_anoniplist = waf.CfnWebACL.RuleProperty(
            name='awsAnonymousIP',
            priority=2,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesAnonymousIpList',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='awsAnonymous',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_anoniplist)

        # 3 AWS ip reputation List
        aws_ip_rep_list = waf.CfnWebACL.RuleProperty(
            name='aws_Ipreputation',
            priority=3,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesAmazonIpReputationList',
                    vendor_name='AWS',
                    excluded_rules=[]
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='aws_reputation',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(aws_ip_rep_list)

        # 4 GeoBlock USA from accessing gateway
        geoblock_rule = waf.CfnWebACL.RuleProperty(
            name='geoblocking_rule',
            priority=4,
            action=waf.CfnWebACL.RuleActionProperty(allow={}),
            statement=waf.CfnWebACL.StatementProperty(
                geo_match_statement=waf.CfnWebACL.GeoMatchStatementProperty(
                    country_codes=['US'],
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='geoblock',
                sampled_requests_enabled=True,
            )
        )
        waf_rules.append(geoblock_rule)

        # Create the Waf ACL
        WebACL = waf.CfnWebACL(self, 'WebACL',
                               default_action=waf.CfnWebACL.DefaultActionProperty(
                                   allow={}
                               ),
                               scope="REGIONAL",  # vs 'CLOUDFRONT'
                               visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                                   cloud_watch_metrics_enabled=True,
                                   metric_name='webACL',
                                   sampled_requests_enabled=True
                               ),
                               name=f'MlaasACL-{tenant_id}',
                               rules=waf_rules
                               )

        # Associate it with the resource provided.

        waf.CfnWebACLAssociation(self, 'WAFAssnAPI',
                                 web_acl_arn=WebACL.attr_arn,
                                 resource_arn=api_target_arn
                                 )
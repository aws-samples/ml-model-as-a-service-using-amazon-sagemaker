# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Aws,
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct

class NetworkingCdkStack(Stack):

    @property
    def public_subnet_ids(self) -> list:
        return self._public_subnet_ids
    
    @property
    def vpc_id(self) -> str:
        return self._vpc_id

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        self.vpc = ec2.Vpc(self,"VPC",
                    max_azs=2,
                    # cidr="10.0.0.0/16",
                    ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                    subnet_configuration=[ec2.SubnetConfiguration(
                        subnet_type=ec2.SubnetType.PUBLIC,
                        name="Public",
                        cidr_mask=24
                        ), ec2.SubnetConfiguration(
                            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                            name="Private",
                            cidr_mask=24
                        ), ec2.SubnetConfiguration(
                            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                            name="DB",
                            cidr_mask=24
                        )
                        ])

        self._public_subnet_ids = [public_subnet.subnet_id for public_subnet in self.vpc.public_subnets]
        self._vpc_id = self.vpc.vpc_id

        CfnOutput(self, "VPCID", value=self.vpc.vpc_id)
from aws_cdk import (
    App,
    assertions
)
from sm_pipeline_cdk.networking_stack import NetworkingCdkStack

def test_vpc_created():
    app = App()
    network_stack = NetworkingCdkStack(app, "NetworkingCdkStack")
    template = assertions.Template.from_stack(network_stack)

    template.resource_count_is("AWS::EC2::VPC", 1)
    template.resource_count_is("AWS::EC2::Subnet", 6)
    template.has_resource_properties("AWS::EC2::VPC", { 
        "CidrBlock": "10.0.0.0/16" 
    })
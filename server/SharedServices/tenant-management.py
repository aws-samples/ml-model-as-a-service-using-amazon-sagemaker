# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import boto3
from boto3.dynamodb.conditions import Key
import utils
from botocore.exceptions import ClientError
import logger
import metrics_manager
import auth_manager
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth

from aws_lambda_powertools import Tracer
tracer = Tracer()


region = os.environ['AWS_REGION']

#This method has been locked down to be only
def create_tenant(event, context):
    pass

def get_tenants(event, context):
    
    table_tenant_details = __getTenantManagementTable(event)

    try:
        response = table_tenant_details.scan()
    except Exception as e:
        raise Exception('Error getting all tenants', e)
    else:
        return utils.generate_response(response['Items'])    

def __getTenantManagementTable(event):
    
    dynamodb = boto3.resource('dynamodb')
    table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')
    
    return table_tenant_details

class TenantInfo:
    def __init__(self, tenant_name, tenant_address, tenant_email, tenant_phone):
        self.tenant_name = tenant_name
        self.tenant_address = tenant_address
        self.tenant_email = tenant_email
        self.tenant_phone = tenant_phone
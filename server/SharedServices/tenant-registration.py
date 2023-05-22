# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import os
import utils
import shortuuid
import logger
import requests
import re

region = os.environ['AWS_REGION']
create_tenant_admin_user_resource_path = os.environ['CREATE_TENANT_ADMIN_USER_RESOURCE_PATH']
create_tenant_resource_path = os.environ['CREATE_TENANT_RESOURCE_PATH']
provision_tenant_resource_path = os.environ['PROVISION_TENANT_RESOURCE_PATH']


lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')


def register_tenant(event, context):
    try:
        tenant_id = shortuuid.uuid().lower()
        tenant_details = json.loads(event['body'])

        # TODO: Lab4 - uncomment below Gold tier code
        # tenant_details['dedicatedTenancy'] = 'false'

        # if (tenant_details['tenantTier'].upper() == utils.TenantTier.GOLD.value.upper()):
        #     tenant_details['dedicatedTenancy'] = 'true'
        
        tenant_details['tenantId'] = tenant_id

        logger.info(tenant_details)

        stage_name = event['requestContext']['stage']
        host = event['headers']['Host']
        auth = utils.get_auth(host, region)
        headers = utils.get_headers(event)
        create_user_response = __create_tenant_admin_user(tenant_details, headers, auth, host, stage_name)
        
        logger.info (create_user_response)
        tenant_details['userPoolId'] = create_user_response['message']['userPoolId']
        tenant_details['appClientId'] = create_user_response['message']['appClientId']
        tenant_details['tenantAdminUserName'] = create_user_response['message']['tenantAdminUserName']

        
        create_tenant_response = __create_tenant(tenant_details, headers, auth, host, stage_name)
        logger.info (create_tenant_response)

        
        provision_tenant_response = __provision_tenant(tenant_details, headers, auth, host, stage_name)
        logger.info(provision_tenant_response)

        
    except Exception as e:
        logger.error('Error registering a new tenant')
        raise Exception('Error registering a new tenant', e)
    else:
        return utils.create_success_response("You have been registered in our system")


def __create_tenant_admin_user(tenant_details, headers, auth, host, stage_name):
    try:
        url = ''.join(['https://', host, '/', stage_name, create_tenant_admin_user_resource_path])
        logger.info(url)
        response = requests.post(url, data=json.dumps(tenant_details), auth=auth, headers=headers) 
        response_json = response.json()
    except Exception as e:
        logger.error('Error occured while calling the create tenant admin user service')
        raise Exception('Error occured while calling the create tenant admin user service', e)
    else:
        return response_json

def __create_tenant(tenant_details, headers, auth, host, stage_name):
    try:
        url = ''.join(['https://', host, '/', stage_name, create_tenant_resource_path])
        response = requests.post(url, data=json.dumps(tenant_details), auth=auth, headers=headers) 
        response_json = response.json()
    except Exception as e:
        logger.error('Error occured while creating the tenant record in table')
        raise Exception('Error occured while creating the tenant record in table', e) 
    else:
        return response_json

def __provision_tenant(tenant_details, headers, auth, host, stage_name):
    try:
        url = ''.join(['https://', host, '/', stage_name, provision_tenant_resource_path])
        logger.info(url)
        response = requests.post(url, data=json.dumps(tenant_details), auth=auth, headers=headers) 
        response_json = response.json()['message']
    except Exception as e:
        logger.error('Error occured while provisioning the tenant')
        raise Exception('Error occured while creating the tenant record in table', e) 
    else:
        return response_json
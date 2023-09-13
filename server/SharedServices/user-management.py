# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import os
import sys
import logger
import utils
import metrics_manager
import auth_manager
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Tracer
tracer = Tracer()

client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
table_tenant_user_map = dynamodb.Table('MLaaS-TenantUserMapping')
table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')


def create_tenant_admin_user(event, context):
    tenant_user_pool_id = os.environ['TENANT_USER_POOL_ID']
    tenant_app_client_id = os.environ['TENANT_APP_CLIENT_ID']
    
    tenant_details = json.loads(event['body'])
    tenant_id = tenant_details['tenantId']
    logger.info(tenant_details)

    user_mgmt = UserManagement()
    
    if (tenant_details['dedicatedTenancy'] == 'true'):
        user_pool_response = user_mgmt.create_user_pool(tenant_id)
        user_pool_id = user_pool_response['UserPool']['Id']
        logger.info (user_pool_id)
        
        app_client_response = user_mgmt.create_user_pool_client(user_pool_id)
        logger.info(app_client_response)
        app_client_id = app_client_response['UserPoolClient']['ClientId']
        user_pool_domain_response = user_mgmt.create_user_pool_domain(user_pool_id, tenant_id)
        
        logger.info ("New Tenant Created")
    else:
        user_pool_id = tenant_user_pool_id
        app_client_id = tenant_app_client_id

    #Add tenant admin now based upon user pool
    tenant_user_group_response = user_mgmt.create_user_group(user_pool_id,tenant_id,"User group for tenant {0}".format(tenant_id))

    tenant_admin_user_name = tenant_details['tenantEmail']

    create_tenant_admin_response = user_mgmt.create_tenant_admin(user_pool_id, tenant_admin_user_name, tenant_details)
    
    add_tenant_admin_to_group_response = user_mgmt.add_user_to_group(user_pool_id, tenant_admin_user_name, tenant_user_group_response['Group']['GroupName'])
    
    tenant_user_mapping_response = user_mgmt.create_user_tenant_mapping(tenant_admin_user_name,tenant_id)
    
    response = {"userPoolId": user_pool_id, "appClientId": app_client_id, "tenantAdminUserName": tenant_admin_user_name}
    return utils.create_success_response(response)


class UserManagement:
    def create_user_pool(self, tenant_id):
        response = client.create_user_pool(
            PoolName=tenant_id + '-MLaaSUserPool',
            AutoVerifiedAttributes=['email'],
            AccountRecoverySetting={
                'RecoveryMechanisms': [
                    {
                        'Priority': 1,
                        'Name': 'verified_email'
                    },
                ]
            },
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                },
                {
                    'Name': 'tenantId',
                    'AttributeDataType': 'String',
                    'Required': False,
                },
                {
                    'Name': 'userRole',
                    'AttributeDataType': 'String',
                    'Required': False,
                }
            ]
        )
        return response

    def create_user_pool_client(self, user_pool_id):
        user_pool_callback_url = "https://example.com/"
        response = client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName='MLaaSClient',
            GenerateSecret=False,
            ExplicitAuthFlows=['ALLOW_CUSTOM_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH',
                               'ALLOW_USER_PASSWORD_AUTH', 'ALLOW_USER_SRP_AUTH'],
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=[
                'code', 'implicit'
            ],
            SupportedIdentityProviders=[
                'COGNITO',
            ],
            CallbackURLs=[
                user_pool_callback_url,
            ],
            LogoutURLs=[
                user_pool_callback_url,
            ],
            AllowedOAuthScopes=[
                'email',
                'openid',
                'profile'
            ],
            WriteAttributes=[
                'email',
                'custom:tenantId'
            ]
        )
        return response

    def create_user_pool_domain(self, user_pool_id, tenant_id):
        response = client.create_user_pool_domain(
            Domain=tenant_id + '-mlaas',
            UserPoolId=user_pool_id
        )
        return response

    def create_user_group(self, user_pool_id, group_name, group_description):
        response = client.create_group(
            GroupName=group_name,
            UserPoolId=user_pool_id,
            Description=group_description,
            Precedence=0
        )
        return response

    def create_tenant_admin(self, user_pool_id, tenant_admin_user_name, user_details):
        response = client.admin_create_user(
            Username=tenant_admin_user_name,
            UserPoolId=user_pool_id,
            ForceAliasCreation=True,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': user_details['tenantEmail']
                },
                {
                    'Name': 'custom:userRole',
                    'Value': 'TenantAdmin'
                },
                {
                    'Name': 'custom:tenantId',
                    'Value': user_details['tenantId']
                }
            ]
        )

        # Set a default password
        client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=tenant_admin_user_name,
            Password='Mlaa$1234',
            Permanent=True
        )

        return response

    def add_user_to_group(self, user_pool_id, user_name, group_name):
        response = client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=user_name,
            GroupName=group_name
        )
        return response

    def create_user_tenant_mapping(self, user_name, tenant_id):
        response = table_tenant_user_map.put_item(
            Item={
                'tenantId': tenant_id,
                'userName': user_name
            }
        )

        return response
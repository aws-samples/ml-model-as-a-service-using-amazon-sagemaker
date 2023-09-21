# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import argparse
import boto3
import requests
import logging
import json

logger = logging.getLogger(__name__)

def onboard_tenant(tenant_details):

    try:
        tenant_details = json.loads(tenant_details)
        outputs = get_cft_outputs()
        cognito_client = boto3.client('cognito-idp')
        create_user_response = create_saas_admin_user(cognito_client, tenant_details, outputs)
        username = create_user_response['User']['Username']
        id_token = get_id_token(cognito_client,username, outputs)
        register_tenant(id_token, tenant_details, outputs)
        update_tenant_stack_mapping()
        invoke_pipeline()
        

    except Exception as e:
        logger.error("Error while pre-provisioning the tenant", e)
        exit(1)

def create_saas_admin_user(cognito_client, tenant_details, outputs):
    
    try:
        
        logger.info('Creating saas admin user')
        response = cognito_client.admin_create_user(
            Username=tenant_details['tenantEmail'],
            UserPoolId=outputs['userPoolId'],
            ForceAliasCreation=True,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': tenant_details['tenantEmail']
                },
                {
                    'Name': 'custom:userRole',
                    'Value': 'SystemAdmin'
                },
                {
                    'Name': 'custom:tenantId',
                    'Value': 'system_admins'
                }
            ]
        )

        # Set a default password
        cognito_client.admin_set_user_password(
            UserPoolId=outputs['userPoolId'],
            Username=tenant_details['tenantEmail'],
            Password='Mlaa$1234',
            Permanent=True
        )
       
       # Add user to group
        cognito_client.admin_add_user_to_group(
            UserPoolId=outputs['userPoolId'],
            Username=tenant_details['tenantEmail'],
            GroupName=outputs['groupName']
        )

        return response
        
    except Exception as e:
        logger.error('Error occured while creating the saas admin user')
        raise Exception('Error occured while creating the saas admin user', e)

def get_id_token(cognito_client, username, outputs):

    cognito_response = cognito_client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": 'Mlaa$1234'
            },
            ClientId=outputs['appClientId']
        )
    
    return cognito_response['AuthenticationResult']['IdToken']
 

def get_cft_outputs():
    logger.info('get cloudformation outputs')
    outputs = {}
    cf_client = boto3.client('cloudformation')

    response = cf_client.describe_stacks(StackName='mlaas')
    stack = response['Stacks'][0]

    for output in stack['Outputs']:
        if output['OutputKey'] == 'CognitoOperationUsersUserPoolId':
            outputs['userPoolId'] = output['OutputValue']
        if output['OutputKey'] == 'CognitoAdminUserGroupName':
            outputs['groupName'] = output['OutputValue'] 
        if output['OutputKey'] == 'CognitoOperationUsersUserPoolClientId':
            outputs['appClientId'] = output['OutputValue']
        if output['OutputKey'] == 'AdminApi':
            outputs['adminApi'] = output['OutputValue']     
    
    if 'userPoolId' not in outputs or 'groupName' not in outputs or 'appClientId' not in outputs or 'adminApi' not in outputs:
        logger.error('Error while getting cloudformation outputs')
        raise Exception('Error while getting cloudformation outputs')
    else:
        return outputs    

def register_tenant(id_token, tenant_details, outputs):
    
    try:
        logger.info("Onboarding the tenant")
        print("Onboarding the tenant")
        
        print(tenant_details)
        response = requests.post(outputs['adminApi']+'registration', data=json.dumps(tenant_details), headers={'Authorization': 'Bearer '+id_token}) 
        if response.status_code == 200:
            response_json = response.json()
            print(response_json)
            return response_json
        else:
            logger.error('POST request failed with status code '+ response.status_code)
            raise Exception('POST request failed with status code ', response.status_code)
        
    except Exception as e:
        logger.error('Error occured while calling the register tenant service')
        raise Exception('Error occured while calling the register tenant service', e)
    
def update_tenant_stack_mapping():
    try:
        dynamodb = boto3.resource('dynamodb')
        tenant_id = get_tenant_id(dynamodb)

        logger.info("Updating tenant stack mapping table")
        stack_name = 'mlaas-stack-{0}'
        table_tenant_stack_mapping = dynamodb.Table('MLaaS-TenantStackMapping')
        response_ddb = table_tenant_stack_mapping.put_item(
                Item={
                    'tenantId': tenant_id,
                    'stackName': stack_name.format(tenant_id),
                    'applyLatestRelease': True,
                    'codeCommitId': ''
                }
            )   

        return response_ddb
    except Exception as e:
        logger.error('Error occured while updating the tenant stack mapping table')
        raise Exception('Error occured while updating the tenant stack mapping table', e)    

def get_tenant_id(dynamodb):
    try:
        logger.info("Scanning tenant details table for tenant id")
        table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')
        response = table_tenant_details.scan()
        item = response['Items'][0]
        tenant_id = item['tenantId']

        return tenant_id
    except Exception as e:
        logger.error('Error occured while getting the tenant id')
        raise Exception('Error occured while getting the tenant id', e)  


def invoke_pipeline():
    try:
        logger.info("Invoking CI/CD pipeline")
        codepipeline = boto3.client('codepipeline')
        response = codepipeline.start_pipeline_execution(name='ml-saas-pipeline')
        return response
    except Exception as e:
        logger.error('Error occured while invoking the pipeline')
        raise Exception('Error occured while invoking the pipeline', e)         

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Onboard tenant')
    parser.add_argument('--tenant-details', type=str, help='tenant details in json format {"tenantName": "", "tenantEmail": "", "tenantTier": ""}', required=True)

    args = parser.parse_args()

    onboard_tenant(**vars(args))
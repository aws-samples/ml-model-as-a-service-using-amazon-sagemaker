# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import argparse
import boto3
import requests
import logging

logger = logging.getLogger()

def onboard_tenant(tenant_details):

    try:
        
        register_tenant(tenant_details)
        update_tenant_stack_mapping()
        invoke_pipeline()
        

    except Exception as e:
        logger.error("Error while pre-provisioning the tenant", e)
        exit(1)

def register_tenant(tenant_details):
    
    try:
        logger.info("Create SaaS admin")
        url=None
        cft_client = boto3.client('cloudformation')
        stack_response = cft_client.describe_stacks(StackName='mlaas')
        stack = stack_response['Stacks'][0]

        for output in stack['Outputs']:
            if output['OutputKey'] == 'AdminApi':
                url = output['OutputValue']
                break
        
        response = requests.post(url+'registration', data=tenant_details) 
        response_json = response.json()
        return response_json
    except Exception as e:
        logger.error('Error occured while calling the register tenant  service')
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
        response = codepipeline.start_pipeline_execution(name='serverless-saas-pipeline')
        return response
    except Exception as e:
        logger.error('Error occured while invoking the pipeline')
        raise Exception('Error occured while invoking the pipeline', e)         

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Onboard tenant')
    parser.add_argument('--tenant-details', type=str, help='tenant details in json format {"tenantName": "", "tenantEmail": "", "tenantTier": ""}', required=True)

    args = parser.parse_args()

    onboard_tenant(**vars(args))
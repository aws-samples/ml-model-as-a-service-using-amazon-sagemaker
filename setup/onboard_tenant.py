# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import argparse
import boto3
import requests
import logging
import json
import time
import pre_provision_utils
from boto3.dynamodb.conditions import Key


logger = logging.getLogger(__name__)
dynamodb_client = boto3.resource('dynamodb')
eventbridge = boto3.client('events')
codepipeline = boto3.client('codepipeline')
region = boto3.Session().region_name

def onboard_tenant(saas_admin_username, tenant_details, model_file):

    try:
        tenant_details = json.loads(tenant_details)
        tenant_tier = tenant_details['tenantTier']
        bucket_name=None
        pre_provision_utils.register_tenant(saas_admin_username, tenant_details)

        tenant_id = pre_provision_utils.get_tenant_id(tenant_details['tenantName'])

        if (tenant_tier.upper() == 'PREMIUM'):
            __update_tenant_stack_mapping(tenant_id)
            __invoke_pipeline()
            bucket_name = pre_provision_utils.get_bucket_name(f'mlaas-stack-{tenant_id}')
        elif (tenant_tier.upper() == 'ADVANCED'):
            rule_name = f's3rule-{tenant_id}-{region}'
            prefix = ''.join([tenant_id, '/','input','/'])
            bucket_name = pre_provision_utils.get_bucket_name('mlaas-stack-pooled')
            pre_provision_utils.put_object(bucket_name, prefix)
            __create_eventbridge_rule(tenant_id, prefix, rule_name, bucket_name)
        
        pre_provision_utils.upload_model(
            bucket_name,
            f'{tenant_id}/model_artifacts/{tenant_id}.model.1.tar.gz',
            model_file
        )
        logger.info("Tenant successfully onboarded")
        print("Tenant successfully onboarded")

    except Exception as e:
        logger.error("Error while pre-provisioning the tenant", e)
        exit(1)
    

def __update_tenant_stack_mapping(tenant_id):
    try:
        
        logger.info("Updating tenant stack mapping table")
        stack_name = 'mlaas-stack-{0}'
        table_tenant_stack_mapping = dynamodb_client.Table('MLaaS-TenantStackMapping')
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


def __invoke_pipeline():
    try:
        logger.info("Invoking CI/CD pipeline")
        
        response = codepipeline.start_pipeline_execution(name='ml-saas-pipeline')
        pipeline_execution_id = response['pipelineExecutionId']
        __wait_for_pipeline_to_complete(codepipeline, 'ml-saas-pipeline', pipeline_execution_id, 1800)
        logger.info("Tenant successfully onboarded")
        return response
    except Exception as e:
        logger.error('Error occured while invoking the pipeline')
        raise Exception('Error occured while invoking the pipeline', e)  


def __wait_for_pipeline_to_complete(client, pipeline_name, pipeline_execution_id, timeout_seconds):
    time.sleep(15)  # Wait for 15 seconds so that pipeline can start executing
    start_time = time.time()
    
    while True:
        
        if time.time() - start_time >= timeout_seconds:
            raise Exception(f'Pipeline {pipeline_name} did not complete within the specified timeout.')
            
        response = client.get_pipeline_execution(
            pipelineName=pipeline_name,
            pipelineExecutionId=pipeline_execution_id
        )
        
        # Get the status of the pipeline execution
        status = response['pipelineExecution']['status']
        
        if status == 'Succeeded':
            logger.info('Pipeline execution succeeded!')
            break
        elif status == 'Failed':
            raise Exception('Pipeline execution failed!')
        else:
            logger.info(f'Pipeline execution is still in progress. Status: {status}')
            print(f'Pipeline execution is still in progress. Status: {status}')
            time.sleep(60)  # Wait for 60 seconds before checking again

def __get_setting_value(setting_name):
    try:
        table_system_settings = dynamodb_client.Table('MLaaS-Setting')
        settings_response = table_system_settings.get_item(
                    Key={
                        'settingName': setting_name
                    } 
            )
        setting_value = settings_response['Item']['settingValue']

        return setting_value
        
    except Exception as e:
        logger.error('Error occured while getting settings')
        raise Exception('Error occured while getting settings', e) 


def __create_eventbridge_rule(tenant_id, prefix, rule_name, bucket_name):
    try:
        
        sagemaker_pipeline_exec_lambda_arn = __get_setting_value('sagemaker-pipeline-exec-fn-arn-pooled')

        event_pattern = {
            "detail": {
                "bucket": {
                    "name": [bucket_name]
                },
                "object": {
                    "key": [{
                        "prefix": prefix
                    }]
                }
            },
            "detail-type": ["Object Created"],
            "source": ["aws.s3"]
        }

        eventbridge.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(event_pattern),
            State='ENABLED'
        )

        eventbridge.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': tenant_id,
                    'Arn': sagemaker_pipeline_exec_lambda_arn,
                    'RetryPolicy': {
                        'MaximumRetryAttempts': 2,
                        'MaximumEventAgeInSeconds': 3600
                    }
                }
            ])
    except Exception as e:
        logger.error('Error occured while creating eventbridge rule')
        raise Exception('Error occured while creating eventbridge rule', e) 
        
         

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Onboard tenant')
    parser.add_argument('--saas-admin-username', type=str, help='saas admin username to be used to onboard tenant', required=True)
    parser.add_argument('--tenant-details', type=str, help='tenant details in json format {"tenantName": "", "tenantEmail": "", "tenantTier": ""}', required=True)
    parser.add_argument('--model-file', type=str, help='initial model tar gz file which needs to be uploaded', required=True)

    args = parser.parse_args()

    onboard_tenant(**vars(args))
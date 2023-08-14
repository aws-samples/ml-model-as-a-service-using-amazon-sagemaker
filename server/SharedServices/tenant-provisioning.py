# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import utils
from botocore.exceptions import ClientError
import logger
import os
import subprocess
from aws_lambda_powertools import Tracer
tracer = Tracer()

tenant_stack_mapping_table_name = os.environ['TENANT_STACK_MAPPING_TABLE_NAME']
system_settings_table_name = os.environ['SYSTEM_SETTINGS_TABLE_NAME']
tenant_details_table_name = os.environ['TENANT_DETAILS_TABLE_NAME']
# tenant_template_url = os.environ['TENANT_TEMPLATE_URL']
region = os.environ['AWS_REGION']

dynamodb = boto3.resource('dynamodb')
codepipeline = boto3.client('codepipeline')
cloudformation = boto3.client('cloudformation')
s3 = boto3.client('s3')
iam = boto3.client('iam')
table_tenant_stack_mapping = dynamodb.Table(tenant_stack_mapping_table_name)
table_system_settings = dynamodb.Table(system_settings_table_name)
table_tenant_details = dynamodb.Table(tenant_details_table_name)

stack_name = 'mlaas-stack-{0}'
@tracer.capture_lambda_handler
def provision_tenant(event, context):
    
    tenant_details = json.loads(event['body'])
    tenant_id = tenant_details['tenantId']

    try:
        # TODO: Lab4 - uncomment below Premium tier code
        # if (tenant_details['dedicatedTenancy'].upper() == 'TRUE'):
        #     response_ddb = table_tenant_stack_mapping.put_item(
                
        #         Item={
        #             'tenantId': tenant_id,
        #             'stackName': stack_name.format(tenant_id),
        #             'applyLatestRelease': True,
        #             'codeCommitId': ''
        #         }
        #     )    
        
        #     logger.info(response_ddb)
        #     # Invoke CI/CD pipeline
        #     response_codepipeline = codepipeline.start_pipeline_execution(name='ml-saas-pipeline')
        # else:
            if (tenant_details['tenantTier'].upper() != utils.TenantTier.BASIC.value.upper()):
                # Create tenantId prefix in S3 buckets
                s3bucket_pooled = __get_setting_value('s3bucket-pooled')
                s3.put_object(Bucket=s3bucket_pooled, Key=''.join([tenant_id, '/']))

                sagemaker_s3bucket_pooled = __get_setting_value('sagemaker-s3bucket-pooled')
                s3.put_object(Bucket=sagemaker_s3bucket_pooled, Key=''.join([tenant_id, '/']))
            
                __update_tenant_details(tenant_id, s3bucket_pooled,
                                        sagemaker_s3bucket_pooled)
            else:
                # For basic tier tenant just update the tenant details table with api gateway url
                __update_tenant_details(tenant_id) 

        
    except Exception as e:
        raise
    else:
        return utils.create_success_response("Tenant Provisioning Started")


def __update_tenant_details(tenant_id, s3bucket_name, sagemaker_s3bucket_name):
    try:
        apigatewayurl_pooled = __get_setting_value('apigatewayurl-pooled')
        s3_bucket_tenant_role_pooled = __get_setting_value('s3bucket-tenant-role-pooled') 

        response = table_tenant_details.update_item(
            Key={'tenantId':tenant_id},
            UpdateExpression="set s3Bucket=:s3Bucket, apiGatewayUrl=:apiGatewayUrl, s3BucketTenantRole=:s3BucketTenantRole, sagemakerS3Bucket=:sagemakerS3Bucket",
            ExpressionAttributeValues={
                ':s3Bucket':s3bucket_name,
                ':apiGatewayUrl':apigatewayurl_pooled,
                ':s3BucketTenantRole': s3_bucket_tenant_role_pooled,
                ':sagemakerS3Bucket': sagemaker_s3bucket_name
            },
            ReturnValues="UPDATED_NEW"
        )

    except Exception as e:
        logger.error('Error occured while getting settings and updating tenant details')
        raise Exception('Error occured while getting settings and updating tenant details', e) 

def __update_tenant_details(tenant_id):
    try:
        apigatewayurl_pooled = __get_setting_value('apigatewayurl-pooled')

        response = table_tenant_details.update_item(
            Key={'tenantId':tenant_id},
            UpdateExpression="set apiGatewayUrl=:apiGatewayUrl",
            ExpressionAttributeValues={
                ':apiGatewayUrl':apigatewayurl_pooled 
            },
            ReturnValues="UPDATED_NEW"
        )

    except Exception as e:
        logger.error('Error occured while getting settings and updating tenant details')
        raise Exception('Error occured while getting settings and updating tenant details', e)     
    
def __get_setting_value(setting_name):
    try:
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
         
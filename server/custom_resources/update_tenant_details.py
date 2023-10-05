# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from crhelper import CfnResource
helper = CfnResource()

try:
    client = boto3.client('dynamodb')
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    eventbridge = boto3.client('events')
    region = os.environ['AWS_REGION']
except Exception as e:
    helper.init_failure(e)
    
@helper.create
@helper.update
def do_action(event, _):
    
    tenant_details_table_name = event['ResourceProperties']['TenantDetailsTableName']
    settings_table_name = event['ResourceProperties']['SettingsTableName']
    tenant_id = event['ResourceProperties']['TenantId']
    tenant_api_gateway_url = event['ResourceProperties']['TenantApiGatewayUrl']
    sm_s3_bucket = event['ResourceProperties']['SagemakerS3Bucket']
    sm_pipeline_exec_fn_arn= event['ResourceProperties']['SagemakerPipelineExecFnArn']
    
    if(tenant_id.lower() !='pooled'):
        
        tenant_details = dynamodb.Table(tenant_details_table_name)
        response = tenant_details.update_item(
            Key={'tenantId': tenant_id},
            UpdateExpression="set apiGatewayUrl=:apiGatewayUrl, sagemakerS3Bucket=:sagemakerS3Bucket",
            ExpressionAttributeValues={
            ':apiGatewayUrl': tenant_api_gateway_url,
            ':sagemakerS3Bucket': sm_s3_bucket
            },
            ReturnValues="NONE") 
        
        # Create tenantId/input prefix in S3 buckets. 
        # For pooled tenants tenantId/input prefix will 
        # be added during onboarding in the tenant provisioning service  
        prefix = ''.join([tenant_id, '/','input','/'])
        s3.put_object(Bucket=sm_s3_bucket, Key=prefix)
        
        # Create notification for tenantId/output prefix 
        # to invoke Sagemaker pipeline execution lamdba function.
        rule_name = f's3rule-{tenant_id}-{region}'
        event_pattern = {
            "detail": {
                "bucket": {
                    "name": [sm_s3_bucket]
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
                    'Arn': sm_pipeline_exec_fn_arn,
                    'RetryPolicy': {
                        'MaximumRetryAttempts': 2,
                        'MaximumEventAgeInSeconds': 3600
                    }
                }
            ])
        
    else:
        
        table_system_settings = dynamodb.Table(settings_table_name)
        
        response = table_system_settings.put_item(
                Item={
                        'settingName': 'apigatewayurl-pooled',
                        'settingValue' : tenant_api_gateway_url
                    }
                )
        
        response = table_system_settings.put_item(
                Item={
                        'settingName': 'sagemaker-s3bucket-pooled',
                        'settingValue' : sm_s3_bucket
                    }
                )
        
        response = table_system_settings.put_item(
                Item={
                        'settingName': 'sagemaker-pipeline-exec-fn-arn-pooled',
                        'settingValue' : sm_pipeline_exec_fn_arn
                }
        )

                   
    
@helper.delete
def do_nothing(_, __):
    pass

def handler(event, context):   
    helper(event, context)


    
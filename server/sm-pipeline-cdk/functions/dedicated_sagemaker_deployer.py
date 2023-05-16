# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import boto3
import pandas as pd
import numpy as np
from io import StringIO

sm = boto3.client('sagemaker')
dynamo = boto3.client('dynamodb')
sm_client = boto3.client('sagemaker')

endpoint_name = os.getenv("ENDPOINT_NAME")
tenant_id = os.getenv("TENANT_ID")
region = os.environ['AWS_REGION']
role_arn = os.environ['ROLE_ARN']

def handler(event, context):
    print('## EVENT')
    print(event)
    
    print('## Region:' + region)
    bucket_name = event['detail']['bucket']['name']
    print('## Bucket_Name:' + bucket_name)
    object_key = event['detail']['object']['key']
    print('## Object_Key:' + object_key)
    
    dynamo_item = dynamo.get_item(
        TableName='MLaaS-TenantDetails',
        Key={
            'tenantId': {
                'S': tenant_id
                }
        }
    )    
   
    model_version_int = int(dynamo_item['Item']['modelVersion']['N'])
    version = str(model_version_int)
    model_data_uri = 's3://'+ bucket_name+ '/' + object_key
    
    updated_model_name = tenant_id + "-SageMaker-Model-" + version
    updated_endpoint_config_name = tenant_id + "-EndpointConfig-" + version
    
    describe_endpoint = sm_client.describe_endpoint(
        EndpointName = endpoint_name 
    )
    
    endpoint_config_name = describe_endpoint['EndpointConfigName']
    
    endpoint_config_desc = sm_client.describe_endpoint_config(
        EndpointConfigName=endpoint_config_name
    )
    
    current_model_name = ''
    initial_instance_count = 0
    instance_type = ""
    for val in endpoint_config_desc['ProductionVariants']:
        if val['InitialVariantWeight'] ==  1.0:
           current_model_name = val['ModelName']
           initial_instance_count = val['InitialInstanceCount']
           instance_type = val['InstanceType']
           break
    
    model_desc = sm_client.describe_model(ModelName=current_model_name)
    image_uri = model_desc['PrimaryContainer']['Image']
    
    response = sm_client.create_model(
        ModelName=updated_model_name,
        PrimaryContainer={
            'Image': image_uri,
            'ModelDataUrl': model_data_uri,
        },
        ExecutionRoleArn=role_arn
    )
    
    response = sm_client.create_endpoint_config(
    EndpointConfigName = updated_endpoint_config_name,
        ProductionVariants=[
            {
                'VariantName': 'Variant0',
                'ModelName':  updated_model_name,
                'InitialInstanceCount': initial_instance_count,
                'InstanceType': instance_type,
                'InitialVariantWeight': 1
            }
    ])
     
    response = sm_client.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=updated_endpoint_config_name,
        RetainAllVariantProperties=False,
    )
    
    sm_client.get_waiter('endpoint_in_service').wait(EndpointName=endpoint_name)
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "Region ": region, 
            "ProjectDescription" : "proj_desc" 
        })
    }
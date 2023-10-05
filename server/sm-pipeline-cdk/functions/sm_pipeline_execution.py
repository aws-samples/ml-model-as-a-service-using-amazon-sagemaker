# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import boto3
import pandas as pd
import numpy as np
from io import StringIO
import utils


sm = boto3.client('sagemaker')


def create_temp_tenant_session(access_role_arn, session_name,duration_sec, tenant_id):
    """
    Create a temporary session
    :param access_role_arn: The ARN of the role that the caller is assuming
    :param session_name: An identifier for the assumed session
    :param tenant_id: The tenant identifier the session is created for
    :param duration_sec: The duration, in seconds, of the temporary session
    :return: The session object that allows you to create service clients and resources
    """
    
    print("## Assume Role")
    sts = boto3.client('sts')
    assume_role_response = ""

    assume_role_response = sts.assume_role(
        RoleArn=access_role_arn,
        DurationSeconds=duration_sec,
        RoleSessionName=session_name,
        Tags=[
            {
                'Key': 'TenantID',
                'Value': tenant_id
            }
        ]
    )

    print(assume_role_response)
    session = boto3.Session(aws_access_key_id=assume_role_response['Credentials']['AccessKeyId'],
                    aws_secret_access_key=assume_role_response['Credentials']['SecretAccessKey'],
                    aws_session_token=assume_role_response['Credentials']['SessionToken'])
    return session


def create_boto3_client(
    tenant_id, tenant_tier, session_name):
    """
    Creates a boto3 client. 
    """
    if (tenant_tier.upper() == utils.TenantTier.ADVANCED.value.upper()):
        s3_access_role_arn= os.environ['S3_ACCESS_ROLE_ARN']
        assumed_session = create_temp_tenant_session(s3_access_role_arn, session_name, 900, tenant_id)
        s3_client = assumed_session.resource('s3')
        return s3_client
    else:
        return boto3.resource("s3")


def handler(event, context):
    print('## EVENT')
    print(event)
    json_region = os.environ['AWS_REGION']
    print('## Region:' + json_region)
    bucket_name = event['detail']['bucket']['name']
    print('## Bucket_Name:' + bucket_name)
    object_key = event['detail']['object']['key']
    print('## Object_Key:' + object_key)
    tenant_id = object_key.split('/')[0]
    print('## Tenant ID:' + tenant_id)

    dynamodb_access_role_arn= os.environ['DYNAMODB_ACCESS_ROLE_ARN']
    dynamodb_assumed_session= create_temp_tenant_session(dynamodb_access_role_arn, "dynamodb_assumed_session", 900, tenant_id)

    dynamodb = dynamodb_assumed_session.resource('dynamodb')
    table = dynamodb.Table('MLaaS-TenantDetails')
    dynamo_item = table.get_item(
        Key={
            'tenantId':  tenant_id
        }
    )
    # s3_access_role_arn = dynamo_item['Item']['s3BucketTenantRole']
    tenant_tier = dynamo_item['Item']['tenantTier']
    sm_bucket_name = dynamo_item['Item']['sagemakerS3Bucket']
    model_version_int = int(dynamo_item['Item']['modelVersion']) + 1
    model_version = str(model_version_int)
    
    csv_buffer = StringIO()
    
    # stack = cf.describe_stacks(StackName='mlaas-cdk-shared-template')
    # print('## Stack')
    # print(stack)
    # outputs = stack['Stacks'][0]['Outputs'] 
    # sm_projectname = next(output['OutputValue'] for output in outputs
    #     if output['OutputKey'] == 'MlaasPoolSagemakerProjectName')
    # print("##MlaasPoolSagemakerProjectName:", sm_projectname)
    
    if object_key.endswith('.csv'):
        s3 = create_boto3_client(tenant_id, tenant_tier,"s3_assumed_session")
        
        try:
            data_obj = s3.Object(bucket_name=bucket_name, key=object_key)
            response = data_obj.get()
            data_df = pd.read_csv(response['Body'])
            train = data_df.iloc[:int(0.7 * len(data_df))]
            validation = data_df.iloc[int(0.7 * len(data_df))+1:int(0.85 * len(data_df))]
            test = data_df.iloc[int(0.85 * len(data_df))+1:]
            
            train.to_csv(csv_buffer, index = False)
            train_file = tenant_id + '/data/train.csv'
            train_obj = s3.Object(bucket_name=sm_bucket_name, key=train_file)
            train_obj.put(Body=csv_buffer.getvalue())
            
            validation.to_csv(csv_buffer, index = False)
            validation_file = tenant_id + '/data/validation.csv'
            validation_obj = s3.Object(bucket_name=sm_bucket_name, key=validation_file)
            validation_obj.put(Body=csv_buffer.getvalue())

            test.to_csv(csv_buffer, index = False)
            test_file = tenant_id + '/data/test.csv'
            test_obj = s3.Object(bucket_name=sm_bucket_name, key=test_file)
            test_obj.put(Body=csv_buffer.getvalue())
            
        except Exception as e:
            raise IOError(e) 
        

    
    post_process_object_key = "model_artifacts_mme"
    if tenant_tier.upper() == 'PREMIUM':
        post_process_object_key = f"{tenant_id}/model_artifacts"
        

    pipeline_name = "CustomerChurnPipeline"
    print("## pipeline_name: " + pipeline_name)

    response = sm.start_pipeline_execution(
        PipelineName = pipeline_name,
        PipelineParameters=[
        {
            'Name': 'TrainDataPath',
            'Value': 's3://'+sm_bucket_name+'/' + train_file
        },
        {
            'Name': 'TestDataPath',
            'Value': 's3://'+sm_bucket_name+'/' + test_file
        },
        {
            'Name': 'ValidationDataPath',
            'Value': 's3://'+sm_bucket_name+ '/' + validation_file
        },
        {
            'Name': 'ModelPath',
            'Value': 's3://'+sm_bucket_name+'/model_artifacts'
        },
        {
            'Name': 'ModelPackageGroupName',
            'Value': tenant_id
        },
        {
            'Name': 'TenantID',
            'Value': tenant_id
        },
        {
            'Name': 'ObjectKey',
            'Value': post_process_object_key
        },
        {
            'Name': 'BucketName',
            'Value': sm_bucket_name
        },
        {
            'Name': 'ModelVersion',
            'Value': model_version
        }
    ]   
    )
    

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "Region ": json_region, 
            "ProjectDescription" : "proj_desc" 
        })
    }

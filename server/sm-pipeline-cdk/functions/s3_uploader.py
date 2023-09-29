# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import base64
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

response  = {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true'
    },
    'body': ''
}

def lambda_handler(event, context):

    filename = event['headers']['file-name']
    file_content = (event['body'])
    tenant_id = event['requestContext']['authorizer']['principalId']
    tenant_tier = event['requestContext']['authorizer']['tier']
    bucket_name = event['requestContext']['authorizer']['bucket']
    access_key = event['requestContext']['authorizer']['aws_access_key_id']
    secret_key = event['requestContext']['authorizer']['aws_secret_access_key']
    session_token = event['requestContext']['authorizer']['aws_session_token']

    s3_prefix = f'{tenant_id}/input/{filename}'
    s3_client = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, aws_session_token=session_token)
  
    try:
        object = s3_client.Object(bucket_name, s3_prefix)
        s3_response = object.put(Body=file_content)  
        logger.info(f"S3 Response: {s3_response}")
        response['body'] = f'{filename} has been uploaded successfully.'

        return response

    except Exception as e:
        logger.info(f"Error uploading {filename}")
        raise IOError(e) 

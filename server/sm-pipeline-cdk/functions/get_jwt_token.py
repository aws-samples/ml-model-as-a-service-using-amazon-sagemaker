# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import base64
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')


def response_handler(response):
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }


def lambda_handler(event, context):

    table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')
    
    try:
        authN = base64.b64decode(event['headers']['Authorization'].split()[
            1].split(':')[0]).decode('utf-8')

        tenant_name = event['headers']['tenant-name']
        username = authN.split(':')[0]
        password = authN.split(':')[1]

        tenant_details = table_tenant_details.query(
            IndexName='tenantName-index',
            KeyConditionExpression=Key('tenantName').eq(tenant_name)
        )

        cognito_client_id = tenant_details['Items'][0]['appClientId']
        cognito_tenant_email = tenant_details['Items'][0]['tenantEmail']

        if cognito_tenant_email != username:
            raise Exception ("Invalid Username for Tenant")

    except Exception as error:
        print(f'[Error]: {error}')
        response = {
            "Error": "Invalid Tenant Name, Username or Missing Authorization Header"
        }
        return response_handler(response)
        

    try:
        cognito_response = client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            },
            ClientId=cognito_client_id
        )
        response = {
            "jwt": cognito_response['AuthenticationResult']['IdToken']
        }

        return response_handler(response)

    except ClientError as error:
        print(f'[Error]: {error}')
        response = {
            "Error": "Invalid Username or Password"
        }
        return response_handler(response)
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os

import boto3

HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_ERROR = 500
HTTP_OK = 200

pooled_endpoint_name = os.getenv("POOLED_ENDPOINT_NAME")

root = logging.getLogger()
root.setLevel("INFO")

dynamodb = boto3.resource('dynamodb')
table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')

def lambda_handler(event, context):
    
    # Get the HTTP body data from the event
    request_body_data = event["body"]

    # Get all the necessary parameters from the request context
    tenant_id = event["requestContext"]["authorizer"]["principalId"]
    endpoint_name = pooled_endpoint_name
    aws_access_key_id = event["requestContext"]["authorizer"]["aws_access_key_id"]
    aws_secret_access_key = event["requestContext"]["authorizer"]["aws_secret_access_key"]
    aws_session_token = event["requestContext"]["authorizer"]["aws_session_token"]

    logging.info(f"tenant_id: {tenant_id}")
    logging.info(f"endpoint_name: {endpoint_name}")
    
    # get tenant informationto extract the latest model version
    tenant_details = table_tenant_details.get_item(
        Key={
            'tenantId': tenant_id
        }
    )    
    
    model_version = tenant_details['Item']['modelVersion']
    logging.info(f"latest model version: {model_version}")
    
    # Generate a python session object from the session parameters created by the authorizer
    try:
        temp_boto3_session = create_temp_boto3_session(
            aws_access_key_id, aws_secret_access_key, aws_session_token
        )
    except Exception as e:
        logging.error(e)
        return return_json(HTTP_INTERNAL_ERROR, "[Error] {}", e)    
        
    # Create a boto3 runtime.sagemaker client using the assumed session object
    temp_client = temp_boto3_session.client("runtime.sagemaker")
    
    # Invoke the SageMaker endpoint
    try:
        result = invoke_sagemaker_endpoint(
            request_body_data, tenant_id, endpoint_name, model_version, temp_client
        )
    except Exception as e:
        logging.error(e)
        return return_json(HTTP_INTERNAL_ERROR, "[Error] {}", e)

    logging.info(f"Result: {result}")    
        
    # Upon succesful invokation, return the results
    return return_json(HTTP_OK, "result: {}", result)

def invoke_sagemaker_endpoint(
    request_body_data: str,
    tenant_id: str,
    endpoint_name: str,
    model_version: str,
    temp_client: boto3.client,
):
    """
    Invokes a SageMaker endpoint.
    If the tenant_tier is TENANT_TIER_POOL_STR then invoke the pool SageMaker Endpoint.
    Returns the results of the InvokeEndpoint call.
    """
    logging.info("Invoking bronze endpoint")
    logging.info(
        f"""temp_client.invoke_endpoint(
        EndpointName={endpoint_name},
        ContentType=\"text/csv\",
        Body={request_body_data},
        TargetModel={tenant_id}.model.{model_version}.tar.gz,
    )""")
    
    response = temp_client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="text/csv",
        TargetModel=f"{tenant_id}.model.{model_version}.tar.gz",
        Body=request_body_data,
    )
    
    logging.info(request_body_data)

    result = response["Body"].read().decode()
    return result


def create_temp_boto3_session(
    aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
) -> boto3.Session:
    """
    Creates a python object representing the temporary session created by the authorizer.
    """
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )

    return session


def return_json(status_code: int, body: str, *args) -> None:
    """
    Creates a JSON response for the Lambda Function to return.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": f'{{"message": "{body.format(*args)}"}}',
    }
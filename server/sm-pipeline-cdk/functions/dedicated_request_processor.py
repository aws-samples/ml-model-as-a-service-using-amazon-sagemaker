# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os

import boto3

HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_ERROR = 500
HTTP_OK = 200

endpoint_name = os.getenv("ENDPOINT_NAME")

root = logging.getLogger()
root.setLevel("INFO")

dynamodb = boto3.resource('dynamodb')
table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')

def lambda_handler(event, context):
 # Get the HTTP body data from the event
    request_body_data = event["body"]

    # Get all the necessary parameters from the request context
    logging.info(f"endpoint_name: {endpoint_name}")
    
    # Create a boto3 sagemaker runtime
    client = boto3.client("runtime.sagemaker")
    
    # Invoke the SageMaker endpoint
    try:
        result = invoke_sagemaker_endpoint(
            request_body_data, endpoint_name, client
        )
    except Exception as e:
        logging.error(e)
        return return_json(HTTP_INTERNAL_ERROR, "[Error] {}", e)

    logging.info(f"Result: {result}")    
        
    # Upon succesful invokation, return the results
    return return_json(HTTP_OK, "result: {}", result)

def invoke_sagemaker_endpoint(
    request_body_data: str,
    endpoint_name: str,
    client: boto3.client,
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
    )""")
    
    response = client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="text/csv",
        Body=request_body_data,
    )
    
    logging.info(request_body_data)

    result = response["Body"].read().decode()
    return result


def return_json(status_code: int, body: str, *args) -> None:
    """
    Creates a JSON response for the Lambda Function to return.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": f'{{"message": "{body.format(*args)}"}}',
    }
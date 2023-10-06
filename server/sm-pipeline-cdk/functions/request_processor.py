# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import utils

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
    tenant_id = event["requestContext"]["authorizer"]["principalId"]
    aws_access_key_id = event["requestContext"]["authorizer"]["aws_access_key_id"]
    aws_secret_access_key = event["requestContext"]["authorizer"]["aws_secret_access_key"]
    aws_session_token = event["requestContext"]["authorizer"]["aws_session_token"]
    tenant_tier = event["requestContext"]["authorizer"]["tier"]
    model_version = event["requestContext"]["authorizer"]["modelVersion"]

    logging.info(f"tenant_id: {tenant_id}")
    logging.info(f"endpoint_name: {endpoint_name}")
    logging.info(f"tenant_tier: {tenant_tier}")
    logging.info(f"model_version: {model_version}")
    
    
    # Generate a python session object from the session parameters created by the authorizer
    try:
        
        client = create_boto3_client(
            tenant_tier, aws_access_key_id, aws_secret_access_key, aws_session_token
        )
    except Exception as e:
        logging.error(e)
        return return_json(HTTP_INTERNAL_ERROR, "[Error] {}", e)    
        

    # Invoke the SageMaker endpoint
    try:
        result = invoke_sagemaker_endpoint(
            request_body_data, tenant_id, tenant_tier, endpoint_name, model_version, client
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
    tenant_tier: str,  
    endpoint_name: str,
    model_version: str,
    temp_client: boto3.client,
):
    """
    Invokes specific SageMaker endpoint based on the tenant tier.
    Returns the results of the InvokeEndpoint call.
    """
    response=""
    if (tenant_tier.upper() == utils.TenantTier.ADVANCED.value.upper()):
        logging.info("Invoking pooled endpoint")
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
    
    else:
        logging.info("Invoking dedicated  endpoint")
        logging.info(
            f"""client.invoke_endpoint(
            EndpointName={endpoint_name},
            ContentType=\"text/csv\",
            Body={request_body_data},
        )""")
    
        response = temp_client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="text/csv",
            Body=request_body_data,
        )
        
        logging.info(request_body_data)

    result = response["Body"].read().decode()   
    return result


def create_boto3_client(
    tenant_tier: str, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
) -> boto3.client:
    """
    Creates a boto3 client. 
    """
    if (tenant_tier.upper() == utils.TenantTier.ADVANCED.value.upper()):

        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )
        return session.client("sagemaker-runtime")

    else:
        return boto3.client("sagemaker-runtime")    


def return_json(status_code: int, body: str, *args) -> None:
    """
    Creates a JSON response for the Lambda Function to return.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": f'{{"message": "{body.format(*args)}"}}',
    }
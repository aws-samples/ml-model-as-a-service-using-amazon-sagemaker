# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import urllib.request
import json
import os
import boto3
from jose import jwk, jwt
from jose.utils import base64url_decode
import time
import logger
import re
import authorizer_layer
from authorizer_layer import SessionParameters
import auth_manager
import utils
from collections import namedtuple

region = os.environ['AWS_REGION']

dynamodb = boto3.resource('dynamodb')
sts_client = boto3.client('sts')
table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')


def lambda_handler(event, context):

    role_to_assume_arn = str(os.environ.get("ROLE_TO_ASSUME_ARN"))

    aws_account_id = context.invoked_function_arn.split(":")[4]
    methodArn = event["methodArn"]

    # get JWT token after Bearer from authorization
    token = event['authorizationToken'].split(" ")
    if (token[0] != 'Bearer'):
        raise Exception(
            'Authorization header should have a format Bearer <JWT> Token')
    jwt_bearer_token = token[1]

    # only to get tenant id to get user pool info
    unauthorized_claims = jwt.get_unverified_claims(jwt_bearer_token)
    logger.info(unauthorized_claims)

    # get tenant user pool and app client to validate jwt token against
    tenant_details = table_tenant_details.get_item(
        Key={
            'tenantId': unauthorized_claims['custom:tenantId']
        }
    )
    logger.info(tenant_details)

    userpool_id = tenant_details['Item']['userPoolId']
    appclient_id = tenant_details['Item']['appClientId']
    # apigateway_url = tenant_details['Item']['apiGatewayUrl']
    tenant_tier = tenant_details['Item']['tenantTier']
    bucket = tenant_details['Item']['s3Bucket']

    # get keys for tenant user pool to validate
    keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(
        region, userpool_id)
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    # authenticate against cognito user pool using the key
    response = authorizer_layer.validateJWT(
        jwt_bearer_token, appclient_id, keys)

    # get authenticated claims
    if (response == False):
        logger.error('Unauthorized')
        raise Exception('Unauthorized')
    else:
        logger.info(response)
        principal_id = response["sub"]
        user_name = response["cognito:username"]
        tenant_id = response["custom:tenantId"]
        user_role = response["custom:userRole"]

    logger.info(tenant_id)

    try:
        # TODO Add missing code to create temporary credentials
        pass
        
    except Exception as e:
        logger.error("Error Authorizing Tenant")
        return authorizer_layer.create_auth_denied_policy(methodArn)

def assume_role(access_role_arn: str, tenant_id: str, duration_sec: int = 900) -> SessionParameters:

    logger.info(
        f"Trying to assume role ARN: {access_role_arn} with tag TenantID={tenant_id}"
    )

    sts = boto3.client("sts")

    try:
        assume_role_response = sts.assume_role(
            RoleArn=access_role_arn,
            DurationSeconds=duration_sec,
            RoleSessionName=tenant_id,
            Tags=[{"Key": "TenantID", "Value": tenant_id}],
        )
    except Exception as exception:
        logger.error(exception)
        return None

    logger.info(
        f"Assumed role ARN: {assume_role_response['AssumedRoleUser']['Arn']}")

    session_parameters = SessionParameters(
        aws_access_key_id=assume_role_response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=assume_role_response["Credentials"]["SecretAccessKey"],
        aws_session_token=assume_role_response["Credentials"]["SessionToken"],
    )

    return session_parameters
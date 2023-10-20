import boto3
import logging
import requests
import json
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
s3 = boto3.resource('s3')
cf_client = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
cognito_client = boto3.client('cognito-idp') 

def get_bucket_name(stack_name):
    bucket_name = None
    response = cf_client.describe_stacks(StackName=stack_name)
    stack = response['Stacks'][0]

    for output in stack['Outputs']:
        if output['OutputKey'] == 'TenantDataInputBucketName':
            bucket_name = output['OutputValue']
            break

    if bucket_name is None:
        logger.error('Error while getting cloudformation outputs')
        raise Exception('Error while getting cloudformation outputs')
    else:
        return bucket_name   

def upload_model(bucket_name, key, file_path):
    s3.Bucket(bucket_name).upload_file(file_path, key)
    logger.info("Successfully uploaded the model file")
      
def put_object(bucket_name, key):
    s3.Object(bucket_name, key)



def get_control_plane_stack_outputs():
    logger.info('get cloudformation outputs')
    outputs = {}
    response = cf_client.describe_stacks(StackName='mlaas')
    stack = response['Stacks'][0]

    for output in stack['Outputs']:
        if output['OutputKey'] == 'CognitoOperationUsersUserPoolId':
            outputs['userPoolId'] = output['OutputValue']
        if output['OutputKey'] == 'CognitoAdminUserGroupName':
            outputs['groupName'] = output['OutputValue'] 
        if output['OutputKey'] == 'CognitoOperationUsersUserPoolClientId':
            outputs['appClientId'] = output['OutputValue']
        if output['OutputKey'] == 'AdminApi':
            outputs['adminApi'] = output['OutputValue']     
    
    if 'userPoolId' not in outputs or 'groupName' not in outputs or 'appClientId' not in outputs or 'adminApi' not in outputs:
        logger.error('Error while getting cloudformation outputs')
        raise Exception('Error while getting cloudformation outputs')
    else:
        return outputs


def get_tenant_id(tenant_name):
    try:
        logger.info("Get tenand id from  tenant details table")
        table_tenant_details = dynamodb.Table('MLaaS-TenantDetails')

        response = table_tenant_details.query(
            IndexName='tenantName-index',
            KeyConditionExpression=Key('tenantName').eq(tenant_name)
        )
        
        item = response['Items'][0]
        tenant_id = item['tenantId']

        return tenant_id
    except Exception as e:
        logger.error('Error occured while getting the tenant id')
        raise Exception('Error occured while getting the tenant id', e)


def get_id_token(username, outputs):
    cognito_response = cognito_client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": 'Mlaa$1234'
            },
            ClientId=outputs['appClientId']
        )
    
    return cognito_response['AuthenticationResult']['IdToken'] 

def register_tenant(saas_admin_username, tenant_details):
    try:
        logger.info("Onboarding the tenant")
        outputs = get_control_plane_stack_outputs()
        id_token = get_id_token(saas_admin_username, outputs)
        
        print(tenant_details)
        response = requests.post(outputs['adminApi']+'registration', data=json.dumps(tenant_details), headers={'Authorization': 'Bearer '+id_token}) 
        if response.status_code == 200:
            response_json = response.json()
            return response_json
        else:
            logger.error('POST request failed with status code '+ response.status_code)
            raise Exception('POST request failed with status code ', response.status_code)
        
    except Exception as e:
        logger.error('Error occured while calling the register tenant service')
        raise Exception('Error occured while calling the register tenant service', e)
    

import boto3
import logging
import argparse
import pre_provision_utils

logger = logging.getLogger(__name__)


cognito_client = boto3.client('cognito-idp')
def create_saas_admin_user(username):
    
    try:
        outputs = pre_provision_utils.get_control_plane_stack_outputs()

        logger.info('Creating saas admin user')
        response = cognito_client.admin_create_user(
            Username=username,
            UserPoolId=outputs['userPoolId'],
            ForceAliasCreation=True,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': username+'@example.com'
                },
                {
                    'Name': 'custom:userRole',
                    'Value': 'SystemAdmin'
                },
                {
                    'Name': 'custom:tenantId',
                    'Value': 'system_admins'
                }
            ]
        )

        # Set a default password
        cognito_client.admin_set_user_password(
            UserPoolId=outputs['userPoolId'],
            Username=username,
            Password='Mlaa$1234',
            Permanent=True
        )
       
       # Add user to group
        cognito_client.admin_add_user_to_group(
            UserPoolId=outputs['userPoolId'],
            Username=username,
            GroupName=outputs['groupName']
        )

        return response
        
    except Exception as e:
        logger.error('Error occured while creating the saas admin user')
        raise Exception('Error occured while creating the saas admin user', e)
    



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create saas admin')
    parser.add_argument('--username', type=str, help='saas admin username ', required=True)

    args = parser.parse_args()

    create_saas_admin_user(**vars(args))
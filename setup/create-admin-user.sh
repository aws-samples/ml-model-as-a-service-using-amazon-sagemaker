#!/bin/bash -e

ADMIN_USERPOOLID=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolId'].OutputValue" --output text)
ADMIN_USER_GROUP_NAME=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoAdminUserGroupName'].OutputValue" --output text)
ADMIN_SITE_URL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminAppSite'].OutputValue" --output text)

# Create admin-user in OperationUsers userpool with given input email address
CREATE_ADMIN_USER=$(aws cognito-idp admin-create-user \
--user-pool-id $ADMIN_USERPOOLID \
--username admin-user \
--user-attributes Name=email,Value=admin-user@example.com Name=phone_number,Value="+11234567890" Name="custom:userRole",Value="SystemAdmin" Name="custom:tenantId",Value="system_admins" \
--desired-delivery-mediums EMAIL)

# echo "$CREATE_ADMIN_USER"

# Add admin-user to admin user group
ADD_ADMIN_USER_TO_GROUP=$(aws cognito-idp admin-add-user-to-group \
--user-pool-id $ADMIN_USERPOOLID \
--username admin-user \
--group-name $ADMIN_USER_GROUP_NAME)

# Setting admin-user password
SET_ADMIN_USER_PASSWORD=$(aws cognito-idp admin-set-user-password \
--user-pool-id $ADMIN_USERPOOLID \
--username admin-user \
--password 'Mlaa$1234' \
--permanent)

echo "Admin user created successfully."
echo "Please use admin username: admin-user and password: Mlaa\$1234 to login to Control Plane admin site URL: https://$ADMIN_SITE_URL"
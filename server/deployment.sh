#!/bin/bash -e

if [[ "$#" -eq 0 ]]; then
  echo "Invalid parameters"
  echo "Command to deploy client code: deployment.sh -c --email <email address>"
  echo "Command to deploy server code: deployment.sh -s --email <email address>" 
  echo "Command to deploy server & client code: deployment.sh -s -c --email <email address>"
  exit 1      
fi

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s) server=1 ;;
        -c) client=1 ;;
        --email) email=$2
          shift ;;  
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done


if [[ $server -eq 1 ]]; then
  echo "Server code is getting deployed"
  # cd ../server
  REGION=$(aws configure get region)


  DEFAULT_SAM_S3_BUCKET=$(grep s3_bucket samconfig-shared.toml|cut -d'=' -f2 | cut -d \" -f2)
  echo "aws s3 ls s3://$DEFAULT_SAM_S3_BUCKET"
  if aws s3 ls "s3://$DEFAULT_SAM_S3_BUCKET"; then
    DEFAULT_SAM_S3_BUCKET_REGION=$(aws s3api get-bucket-location --bucket $DEFAULT_SAM_S3_BUCKET | jq -r ".LocationConstraint")
    # The above get-bucket-location returns "null" for S3 buckets created in us-east-1 region 
    if [ $DEFAULT_SAM_S3_BUCKET_REGION = "null" ] ; then
      DEFAULT_SAM_S3_BUCKET_REGION="us-east-1"
    fi
  fi

  
  
  if ! aws s3 ls "s3://$DEFAULT_SAM_S3_BUCKET" || [ $DEFAULT_SAM_S3_BUCKET_REGION != $REGION ] ; then
      echo "S3 Bucket: $DEFAULT_SAM_S3_BUCKET specified in samconfig.toml is not readable.
      So creating a new S3 bucket and will update samconfig.toml with new bucket name."
    
      UUID=$(uuidgen | awk '{print tolower($0)}')
      SAM_S3_BUCKET=sam-bootstrap-bucket-$UUID
      aws s3 mb s3://$SAM_S3_BUCKET --region $REGION
      aws s3api put-bucket-encryption \
        --bucket $SAM_S3_BUCKET \
        --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
      if [[ $? -ne 0 ]]; then
        exit 1
      fi
      # Updating samconfig.toml with new bucket name
      ex -sc '%s/s3_bucket = .*/s3_bucket = \"'$SAM_S3_BUCKET'\"/|x' samconfig-shared.toml
  fi

  cd sm-pipeline-cdk
  python3 -m pip install -r requirements.txt
  cdk synth 
  cdk bootstrap
  cdk deploy NetworkingCdkStack
  cdk deploy SmPipelineCdkStack
  
  
  cd ..

  sam build -t shared-template.yaml --use-container
  sam deploy --config-file samconfig-shared.toml --region=$REGION
  
  if [[ $? -ne 0 ]]; then
    exit 1
  fi
  
  cd sm-pipeline-cdk
  cdk deploy TenantCdkStack
  cd ..

fi  

ADMIN_SITE_URL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminAppSite'].OutputValue" --output text)

if [[ $client -eq 1 ]]; then
  if [[ -z "$email" ]]; then
    echo "Please provide email address to setup an admin user" 
    echo "Note: Invoke script without parameters to know the list of script parameters"
    exit 1  
  fi
  echo "Client code is getting deployed"
  ADMIN_SITE_BUCKET=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminSiteBucket'].OutputValue" --output text)
  
  ADMIN_APIGATEWAYURL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminApi'].OutputValue" --output text)
  ADMIN_APPCLIENTID=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolClientId'].OutputValue" --output text)
  ADMIN_AUTHSERVERURL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolProviderURL'].OutputValue" --output text)
  ADMIN_USERPOOLID=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolId'].OutputValue" --output text)
  ADMIN_USER_GROUP_NAME=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoAdminUserGroupName'].OutputValue" --output text)

  # Create admin-user in OperationUsers userpool with given input email address
  CREATE_ADMIN_USER=$(aws cognito-idp admin-create-user \
  --user-pool-id $ADMIN_USERPOOLID \
  --username admin-user \
  --user-attributes Name=email,Value=$email Name=phone_number,Value="+11234567890" Name="custom:userRole",Value="SystemAdmin" Name="custom:tenantId",Value="system_admins" \
  --desired-delivery-mediums EMAIL)
  
  echo "$CREATE_ADMIN_USER"

  # Add admin-user to admin user group
  ADD_ADMIN_USER_TO_GROUP=$(aws cognito-idp admin-add-user-to-group \
  --user-pool-id $ADMIN_USERPOOLID \
  --username admin-user \
  --group-name $ADMIN_USER_GROUP_NAME)

  echo "$ADD_ADMIN_USER_TO_GROUP"

  # Configuring admin UI 

  echo "aws s3 ls s3://$ADMIN_SITE_BUCKET"
  aws s3 ls s3://$ADMIN_SITE_BUCKET 
  if [ $? -ne 0 ]; then
      echo "Error! S3 Bucket: $ADMIN_SITE_BUCKET not readable"
      exit 1
  fi

  cd ../clients/Admin

  echo "Configuring environment for Admin Client"

  cat << EoF > ./src/environments/environment.prod.ts
  export const environment = {
    production: true,
    apiUrl: '$ADMIN_APIGATEWAYURL'
  };
EoF
  cat << EoF > ./src/environments/environment.ts
  export const environment = {
    production: false,
    apiUrl: '$ADMIN_APIGATEWAYURL'
  };
EoF
  cat <<EoF >./src/aws-exports.ts
  const awsmobile = {
      "aws_project_region": "$REGION",
      "aws_cognito_region": "$REGION",
      "aws_user_pools_id": "$ADMIN_USERPOOLID",
      "aws_user_pools_web_client_id": "$ADMIN_APPCLIENTID",
  };
  export default awsmobile;
EoF

  # enable yarn
  corepack enable || npm install --global yarn
  
  echo no | yarn install && yarn build

  echo "aws s3 sync --delete --cache-control no-store dist s3://$ADMIN_SITE_BUCKET"
  aws s3 sync --delete --cache-control no-store dist s3://$ADMIN_SITE_BUCKET 

  if [[ $? -ne 0 ]]; then
      exit 1
  fi

  echo "Completed configuring environment for Admin Client"



  echo "Successfully completed deploying Admin UI"

fi  
echo "Admin site URL: https://$ADMIN_SITE_URL"
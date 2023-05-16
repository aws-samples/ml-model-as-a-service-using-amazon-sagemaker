#!/bin/bash -e
rm -rf .aws-sam/
python3 -m pylint -E -d E0401,E1120,E1123 $(find . -iname "*.py" -not -path "./.aws-sam/*" -not -path "./sm-pipeline-cdk/cdk.out/*")
  if [[ $? -ne 0 ]]; then
    echo "****ERROR: Please fix above code errors and then rerun script!!****"
    exit 1
  fi
#Deploying shared services changes
REGION=$(aws configure get region)
echo "Deploying shared services changes" 
echo Y | sam sync --stack-name mlaas -t shared-template.yaml --code --resource-id LambdaFunctions/ProvisionTenantFunction --resource-id LambdaFunctions/CreateTenantAdminUserFunction --resource-id LambdaFunctions/RegisterTenantFunction --resource-id LambdaFunctions/CreateTenantFunction -u --region $REGION

#Deploying Admin UI changes
echo "Deploying Admin UI changes"
ADMIN_APIGATEWAYURL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminApi'].OutputValue" --output text)
ADMIN_SITE_URL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminAppSite'].OutputValue" --output text)
ADMIN_SITE_BUCKET=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminSiteBucket'].OutputValue" --output text)  
ADMIN_APPCLIENTID=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolClientId'].OutputValue" --output text)
ADMIN_USERPOOLID=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='CognitoOperationUsersUserPoolId'].OutputValue" --output text)
    

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

echo "Admin site URL: https://$ADMIN_SITE_URL"
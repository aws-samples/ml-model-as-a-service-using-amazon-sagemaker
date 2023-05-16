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
echo Y | sam sync --stack-name mlaas -t shared-template.yaml --code --resource-id LambdaFunctions/CreateTenantAdminUserFunction --resource-id LambdaFunctions/RegisterTenantFunction --resource-id LambdaFunctions/CreateTenantFunction -u --region $REGION 

#Deploying shared training infrastructure component changes
echo "Deploying shared training infrastructure component changes" 
cd sm-pipeline-cdk
cdk deploy TenantCdkStack -c tenant_id="pooled" -c stack_name="mlaas-stack-pooled" --hotswap
  

ADMIN_SITE_URL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminAppSite'].OutputValue" --output text)
echo "Admin site URL: https://$ADMIN_SITE_URL"

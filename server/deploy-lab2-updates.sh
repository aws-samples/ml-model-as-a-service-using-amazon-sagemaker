#!/bin/bash -e
rm -rf .aws-sam/

#python3 -m pylint -E -d E0401,E1101 $(find . -iname "*.py" -not -path "./.aws-sam/*" -not -path "./sm-pipeline-cdk/cdk.out/*")
#  if [[ $? -ne 0 ]]; then
#    echo "****ERROR: Please fix above code errors and then rerun script!!****"
#    exit 1
#  fi


#Deploying shared training infrastructure component changes
echo "Deploying shared training infrastructure component changes" 
cd sm-pipeline-cdk
cdk deploy TenantCdkStack -c tenant_id="pooled" -c stack_name="mlaas-stack-pooled"
  


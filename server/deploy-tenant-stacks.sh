#!/bin/bash -e

cd sm-pipeline-cdk

TENANT_STACKS=$(aws dynamodb scan --table-name MLaaS-TenantStackMapping)

for item in $( echo "$TENANT_STACKS" | jq  -r '.Items[].stackName.S' ); do

 rm -rf cdk.out

 STACK_NAME=$item
 TENANT_ID=$(echo "$STACK_NAME"|cut -d'-' -f3)
 
 echo "Started deploying: "$STACK_NAME
 cdk deploy TenantCdkStack -c stack_name=$STACK_NAME -c tenant_id=$TENANT_ID --require-approval never --no-previous-parameters
 echo "Completed deploying: "$STACK_NAME
done

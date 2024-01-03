#!/bin/bash -e

echo "Deploy tenant pipeline"
REGION="$AWS_REGION"
  if [ -z "$REGION" ]; then
    # AWS_REGION is empty, try to get region using aws configure
    TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 5")
    REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed 's/\(.*\)[a-z]/\1/')
  fi
echo "Region: $REGION"

if ! aws codecommit get-repository --repository-name ml-saas-workshop; then
  echo "ml-saas-workshop codecommit repo is not present, will create one now"
  CREATE_REPO=$(aws codecommit create-repository --repository-name ml-saas-workshop --repository-description "ML saas workshop repository")
  echo "$CREATE_REPO"
fi  
REPO_URL="codecommit::${REGION}://ml-saas-workshop"
if ! git remote add cc "$REPO_URL"; then
  echo "Setting url to remote cc"
  git remote set-url cc "$REPO_URL"
fi
git push cc "$(git branch --show-current)":main

# enable yarn
corepack enable || npm install --global yarn

# Deploying CI/CD pipeline
cd TenantPipeline/ || exit # stop execution if cd fails
yarn install && yarn build

cdk bootstrap

if ! cdk deploy --require-approval never; then
  exit 1
fi  


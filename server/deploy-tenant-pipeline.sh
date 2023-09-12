#!/bin/bash -e

echo "Deploy tenant pipeline"
REGION="$AWS_REGION"
  if [ -z "$REGION" ]; then
    # AWS_REGION is empty, try to get region using aws configure
    REGION=$(aws configure get region)
  fi
echo "Region: $REGION"

if ! aws codecommit get-repository --repository-name ml-saas-workshop; then
  echo "ml-saas-workshop codecommit repo is not present, will create one now"
  CREATE_REPO=$(aws codecommit create-repository --repository-name ml-saas-workshop --repository-description "ML saas workshop repository")
  echo "$CREATE_REPO"
  REPO_URL="codecommit::${REGION}://ml-saas-workshop"
  if ! git remote add cc "$REPO_URL"; then
    echo "Setting url to remote cc"
    git remote set-url cc "$REPO_URL"
  fi
  git push --set-upstream cc main
  git add -u .
  git commit -m 'Commit changes'
  git push
fi

# enable yarn
corepack enable || npm install --global yarn

# Deploying CI/CD pipeline
cd TenantPipeline/ || exit # stop execution if cd fails
yarn install && yarn build

cdk bootstrap

if ! cdk deploy --require-approval never; then
  exit 1
fi  


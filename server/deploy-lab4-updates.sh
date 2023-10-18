#!/bin/bash -e

python3 -m pip install git-remote-codecommit==1.15.1

REGION="$AWS_REGION"
REPO_URL="codecommit::${REGION}://ml-saas-workshop"
if ! git remote add cc "$REPO_URL"; then
  echo "Setting url to remote cc"
  git remote set-url cc "$REPO_URL"
fi
git config user.email "test@example.com"
git config user.name "test"
git add .
git commit -m 'lab4 changes'
git push cc "$(git branch --show-current)":main
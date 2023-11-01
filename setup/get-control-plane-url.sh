#!/bin/bash -e
ADMIN_SITE_URL=$(aws cloudformation describe-stacks --stack-name mlaas --query "Stacks[0].Outputs[?OutputKey=='AdminAppSite'].OutputValue" --output text)

echo "Control Plane admin site URL: https://$ADMIN_SITE_URL"
#!/bin/bash -e

./initial-setup.sh

cd ../server/
./deployment.sh -s -c --email test@test.com
./deploy-tenant-pipeline.sh

cd ../setup/

python3 -m pip install -r requirements.txt --user
# For Lab1 - create basic tier model sagemaker endpoint 
python3 create_basic_tier_sagemaker_endpoint.py
# Create saas admin user 
python3 pre_provision_user_management.py --username pre-pro-saas-admin-user
# For Lab2 - onboard two advanced tier tenants and upload a model files
python3 onboard_tenant.py --saas-admin-username pre-pro-saas-admin-user --tenant-details "{\"tenantName\":\"advanced100\", \"tenantEmail\": \"advanced100@example.com\",\"tenantTier\": \"Advanced\"}" --model-file "models/advanced100.model.1.tar.gz"
python3 onboard_tenant.py --saas-admin-username pre-pro-saas-admin-user --tenant-details "{\"tenantName\":\"advanced200\", \"tenantEmail\": \"advanced200@example.com\",\"tenantTier\": \"Advanced\"}" --model-file "models/advanced200.model.1.tar.gz"
# For Lab3 - onboard a premium tier tenant and upload a model file
python3 onboard_tenant.py --saas-admin-username pre-pro-saas-admin-user --tenant-details "{\"tenantName\":\"premium100\", \"tenantEmail\": \"premium100@example.com\",\"tenantTier\": \"Premium\"}" --model-file "models/premium100.model.1.tar.gz"

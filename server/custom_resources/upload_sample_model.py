# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import boto3
from crhelper import CfnResource
helper = CfnResource()

try:
    s3 = boto3.client('s3')
except Exception as e:
    helper.init_failure(e)
    
@helper.create
@helper.update
def do_action(event, _):
    
    model_data_key = 'model_artifacts/model.tar.gz'
    s3_bucket = event['ResourceProperties']['S3Bucket']
    s3.Bucket(s3_bucket).upload_file('model.tar.gz', model_data_key)
    
               
    
@helper.delete
def do_nothing(_, __):
    pass

def handler(event, context):   
    helper(event, context)


    
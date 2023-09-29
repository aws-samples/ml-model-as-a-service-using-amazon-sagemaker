import argparse
import logging
import os
import pathlib
import requests
import tempfile

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def update_model_version(region, tenant_id, model_version):
    dynamo = boto3.resource('dynamodb',region_name=region)
    table = dynamo.Table('MLaaS-TenantDetails')

    try:
        response = table.update_item(
            Key={'tenantId': tenant_id},
            UpdateExpression="set modelVersion = :val",
            ConditionExpression=Attr('tenantId').eq(tenant_id),
            ExpressionAttributeValues={':val': int(model_version)},
            ReturnValues="UPDATED_NEW")
    except dynamo.meta.client.exceptions.ConditionalCheckFailedException as err:
        logger.info(
            "Couldn't update model_version for tenant_id %s in table %s because tenant_id is missing. Error details: %s: %s",
            tenant_id, table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        return    
    except ClientError as err:
        logger.error(
            "Couldn't update model_version %s in table %s. Here's why: %s: %s",
            tenant_id, table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Attributes']


if __name__ == "__main__":
    logger.info("Starting postprocessing.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", type=str, required=True)
    parser.add_argument("--bucket-name", type=str, required=True)
    parser.add_argument("--object-key", type=str, required=True)
    parser.add_argument("--model-version", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)

    args = parser.parse_args()
    
    local_file = "/opt/ml/processing/model/model.tar.gz"
    
    s3 = boto3.resource("s3")
    
    file_name = f"{args.tenant_id}.model.{args.model_version}.tar.gz"
    
    object_key = f"{args.object_key}/{file_name}"
    
    s3.Bucket(args.bucket_name).upload_file(local_file, object_key)
    logger.info("Copying model artifacts ended")

    update_model_version(args.region, args.tenant_id, args.model_version)
    logger.info("Update model version ended")
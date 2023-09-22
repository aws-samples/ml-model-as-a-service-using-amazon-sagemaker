import boto3
import sagemaker

def create_sagemaker_endpoint():
    model_name='GenericModel'
    endpoint_config_name = f"EndpointConfig-{model_name}"
    endpoint_name = f"Endpoint-{model_name}"
    model_data_key = 'model_artifacts/basic_tier/output/model.tar.gz'

    try:
        client = boto3.client('sagemaker')
        region = boto3.Session().region_name
        role = sagemaker.get_execution_role()
        account_number = boto3.client('sts').get_caller_identity().get('Account')
        generic_model_data_bucket_name = f"sagemaker-mlaas-pooled-{region}-{account_number}"

        upload_initial_model(generic_model_data_bucket_name, model_data_key)

        # get image URI
        image_uri = sagemaker.image_uris.retrieve(
            framework="xgboost",
            region=region,
            version="1.0-1",
            py_version="py3",
            instance_type='ml.t2.medium',
        )

        # create sagemaker model
        create_model_api_response = client.create_model(
                                    ModelName=model_name,
                                    PrimaryContainer={
                                        'Image': image_uri,
                                        'ModelDataUrl': f"s3://{generic_model_data_bucket_name}/{model_data_key}",
                                        'Environment': {}
                                    },
                                    ExecutionRoleArn=role
                            )
        print("create_model API response", create_model_api_response)
        
        # create sagemaker endpoint config
        create_endpoint_config_api_response = client.create_endpoint_config(
                                            EndpointConfigName=f"EndpointConfig-{model_name}",
                                            ProductionVariants=[
                                                {
                                                    'VariantName': 'prod1',
                                                    'ModelName': model_name,
                                                    'InitialInstanceCount': 1,
                                                    'InstanceType': 'ml.t2.medium'
                                                },
                                            ]
                                       )

        print ("create_endpoint_config API response", create_endpoint_config_api_response)

        # create sagemaker endpoint
        create_endpoint_api_response = client.create_endpoint(
                                    EndpointName=endpoint_name,
                                    EndpointConfigName=endpoint_config_name,
                                )

        print ("create_endpoint API response", create_endpoint_api_response)    

        print(f"Creating endpoint {endpoint_name}...")
        waiter = client.get_waiter('endpoint_in_service')
        waiter.wait(EndpointName=endpoint_name)
        print(f"Endpoint {endpoint_name} is in service.")


    except Exception as e:
        print('Error occured while creating sagemaker endpoint')
        raise Exception('Error occured while creating sagemaker endpoint', e)     


def upload_initial_model(bucket_name, key):
    s3 = boto3.resource('s3')
    s3.Bucket(bucket_name).upload_file('model.tar.gz', key)


if __name__ == '__main__':
    
    create_sagemaker_endpoint()
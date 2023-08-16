# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import argparse
import boto3
import time



def run_document(document_name, instance):

    try:
        print(f"Running document: {document_name} on instance: {instance}")
        client = boto3.client('ssm')
        response = client.send_command(
            DocumentName=document_name,
            Targets=[
                    {
                      'Key':'tag:aws:cloud9:environment',
                      'Values': [ instance ]
                    }
                  ],
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True
            }
        )
        print(response)
        command_id = response['Command']['CommandId']
        timeout_seconds = 900
        start_time = time.time()

        while True:
            invocation_response = client.list_command_invocations(
                CommandId=command_id
            )
            invocation_status = invocation_response['CommandInvocations'][0]['Status']
            if invocation_status == 'Success':
                print("SSM Document execution succeeded!")
                break
            elif invocation_status == 'Failed':
                print("SSM Document execution failed!")
                raise Exception("SSM Document execution failed!")
            
            if time.time() - start_time >= timeout_seconds:
                 raise Exception("SSM Document execution timed out!")
            
            print("SSM Document execution is still in progress...")
            time.sleep(30)

    except Exception as e:
        print("Error executing document", e)
        exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SSM Document')
    parser.add_argument('--document-name', type=str, help='document name', required=True)
    parser.add_argument('--instance', type=str, help='instance', required=True)
    
    args = parser.parse_args()

    run_document(**vars(args))
import os

import boto3
import logging
import sagemaker
import sagemaker.session

from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model_metrics import (
    MetricsSource,
    ModelMetrics,
)
from sagemaker.processing import (
    ProcessingInput,
    ProcessingOutput,
    ScriptProcessor,
)
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.conditions import (
    ConditionLessThanOrEqualTo,
    ConditionEquals,
)
from sagemaker.workflow.condition_step import (
    ConditionStep,
    JsonGet,
)

from sagemaker.workflow.conditions import ConditionLessThanOrEqualTo

from sagemaker.workflow.parameters import (
    ParameterInteger,
    ParameterString,
)
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import (
    ProcessingStep,
    TrainingStep,
)
from sagemaker.workflow.model_step import ModelStep
from sagemaker.model import Model
from sagemaker.workflow.pipeline_context import PipelineSession

from botocore.exceptions import ClientError

from sagemaker.workflow.step_collections import RegisterModel

def get_session(region, default_bucket):
    """Gets the sagemaker session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        `sagemaker.session.Session instance
    """

    boto_session = boto3.Session(region_name=region)

    sagemaker_client = boto_session.client("sagemaker")
    runtime_client = boto_session.client("sagemaker-runtime")
    return sagemaker.session.Session(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        sagemaker_runtime_client=runtime_client,
        default_bucket=default_bucket,
    )

def get_pipeline_session(region, default_bucket):
    """Gets the pipeline session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        PipelineSession instance
    """

    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")

    return PipelineSession(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        default_bucket=default_bucket,
    )

def resolve_ecr_uri_from_image_versions(sagemaker_session, image_versions, image_name):
    """ Gets ECR URI from image versions
    Args:
        sagemaker_session: boto3 session for sagemaker client
        image_versions: list of the image versions
        image_name: Name of the image

    Returns:
        ECR URI of the image version
    """

    #Fetch image details to get the Base Image URI
    for image_version in image_versions:
        if image_version['ImageVersionStatus'] == 'CREATED':
            image_arn = image_version["ImageVersionArn"]
            version = image_version["Version"]
            logger.info(f"Identified the latest image version: {image_arn}")
            response = sagemaker_session.sagemaker_client.describe_image_version(
                ImageName=image_name,
                Version=version
            )
            return response['ContainerImage']
    return None

def resolve_ecr_uri(sagemaker_session, image_arn):
    """Gets the ECR URI from the image name

    Args:
        sagemaker_session: boto3 session for sagemaker client
        image_name: name of the image

    Returns:
        ECR URI of the latest image version
    """
    image_name = image_arn.partition("image/")[2]
    try:
        # Fetch the image versions
        next_token=''
        while True:
            response = sagemaker_session.sagemaker_client.list_image_versions(
                ImageName=image_name,
                MaxResults=100,
                SortBy='VERSION',
                SortOrder='DESCENDING',
                NextToken=next_token
            )
            ecr_uri = resolve_ecr_uri_from_image_versions(sagemaker_session, response['ImageVersions'], image_name)
            if "NextToken" in response:
                next_token = response["NextToken"]

            if ecr_uri is not None:
                return ecr_uri

        # Return error if no versions of the image found
        error_message = (
            f"No image version found for image name: {image_name}"
            )
        logger.error(error_message)
        raise Exception(error_message)

    except (ClientError, sagemaker_session.sagemaker_client.exceptions.ResourceNotFound) as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)
        
BASE_DIR = os.path.dirname(os.path.realpath(__file__))        

def get_pipeline(
    region,
    role=None,
    default_bucket=None,
    sagemaker_project_arn=None,
    model_package_group_name="CustomerChurnGroup",
    pipeline_name="CustomerChurnPipeline",
    base_job_prefix="CustomerChurn",
    project_id="SageMakerProjectId",
    processing_instance_type="ml.m5.xlarge",
    training_instance_type="ml.m5.xlarge"
):
    """Gets a SageMaker ML Pipeline instance working with on abalone data. 2

    Args:
        region: AWS region to create and run the pipeline.
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        an instance of a pipeline
    """
    sagemaker_session = get_session(region, default_bucket)

    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    pipeline_session = get_pipeline_session(region, default_bucket)
        
    # parameters for pipeline execution
    processing_instance_type = ParameterString(
        name="ProcessingInstanceType", default_value="ml.t3.large"
    )
    processing_instance_count = ParameterInteger(
        name="ProcessingInstanceCount", default_value=1
    )
    train_data_path = ParameterString(
        name="TrainDataPath", default_value="",
    )
    test_data_path = ParameterString(
        name="TestDataPath", default_value="",
    )
    val_data_path = ParameterString(
        name="ValidationDataPath", default_value="",
    )
    model_path = ParameterString(
        name="ModelPath", default_value="",
    )
    model_package_group_name = ParameterString(
        name="ModelPackageGroupName", default_value="",
    )
    model_version = ParameterString(
        name="ModelVersion", default_value="0",
    )
    tenant_id = ParameterString(
        name="TenantID", default_value="generic",
    )
    bucket_name = ParameterString(
        name="BucketName", default_value="",
    )
    object_key = ParameterString(
        name="ObjectKey", default_value="",
    )
    
    # training step for generating model artifacts 
    image_uri = sagemaker.image_uris.retrieve(
        framework="xgboost",
        region=region,
        version="1.0-1",
        py_version="py3",
        instance_type=training_instance_type,
    )
    xgb_train = Estimator(
        image_uri=image_uri,
        instance_type=training_instance_type,
        instance_count=1,
        output_path=model_path,
        base_job_name=f"{base_job_prefix}/customer-churn-train",
        sagemaker_session=sagemaker_session,
        role=role,
    )
    xgb_train.set_hyperparameters(
        objective="reg:linear",
        num_round=50,
        max_depth=5,
        eta=0.2,
        gamma=4,
        min_child_weight=6,
        subsample=0.7,
        silent=0,
    )
    
    step_train = TrainingStep(
        name="TrainModel",
        estimator=xgb_train,
        inputs={
            "train": TrainingInput(
                s3_data = train_data_path,              
                content_type="text/csv",
            ),
            "validation": TrainingInput(
                s3_data = val_data_path,
                content_type="text/csv",
            ),
        },
    )
    
    step_register = RegisterModel(
        name="CustomerChurnModel",
        estimator=xgb_train,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.t2.medium", "ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=model_package_group_name,
        approval_status="Approved"
    )
        
    sklearn_processor = SKLearnProcessor(
        framework_version="0.20.0", 
        role=role, 
        instance_type=processing_instance_type,
        instance_count=1,
        sagemaker_session=pipeline_session,
        command=["python3"],
        base_job_name=f"{base_job_prefix}/copy_model_postprocess",
    )    
        
    step_args = sklearn_processor.run(        
        code=os.path.join(BASE_DIR, "postprocess.py"),
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            )
        ],
        arguments=["--bucket-name", bucket_name, "--tenant-id", tenant_id, "--object-key", object_key, "--model-version", model_version, "--region", region],
    )    
    
    step_post_process = ProcessingStep(
        name="CopyModelArtifactsToS3",
        step_args=step_args,
    )
    
    step_post_process.add_depends_on([step_register])
    
    
    # processing step for evaluation
    script_eval = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=processing_instance_type,
        instance_count=1,
        base_job_name=f"{base_job_prefix}/script-eval",
        sagemaker_session=sagemaker_session,
        role=role,
    )
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json",
    )
    
    step_eval = ProcessingStep(
        name="EvaluateModel",
        processor=script_eval,
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source = test_data_path,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[
            ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation"),
        ],
        code=os.path.join(BASE_DIR, "evaluate.py"),
        property_files=[evaluation_report],
    )

    # register model step that will be conditionally executed
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri="{}/evaluation.json".format(
                step_eval.arguments["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"]
            ),
            content_type="application/json"
        )
    )
    
    
    # condition step for evaluating model quality and branching execution
    cond_lte = ConditionLessThanOrEqualTo(
        left=JsonGet(
            step=step_eval,
            property_file=evaluation_report,
            json_path="regression_metrics.mse.value",
        ),
        right=0.5,
    )
    
    step_cond = ConditionStep(
        name="CheckMSEvaluation",
        conditions=[cond_lte],
        if_steps=[step_register,step_post_process],
        else_steps=[],
    )
    
    
    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            processing_instance_type,
            processing_instance_count,
            training_instance_type,
            train_data_path,
            test_data_path,
            val_data_path,
            model_path,
            model_package_group_name,
            model_version,
            tenant_id,
            bucket_name,
            object_key,
        ],
        steps=[step_train, step_eval, step_cond],
        sagemaker_session=pipeline_session,
    )
    return pipeline
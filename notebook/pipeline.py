"""Example workflow pipeline script for abalone pipeline.

                                               . -ModelStep
                                              .
    Process-> Train -> Evaluate -> Condition .
                                              .
                                               . -(stop)

Implements a get_pipeline(**kwargs) method.
"""
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
from sagemaker.workflow.functions import (
    JsonGet,
)
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


BASE_DIR = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)


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
    account_number = boto3.client('sts').get_caller_identity().get('Account')

    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    pipeline_session = get_pipeline_session(region, default_bucket)
    
    sample_data_bucket_name = f"sagemaker-mlaas-pooled-{region}-{account_number}"
    print(sample_data_bucket_name)
    
    # parameters for pipeline execution
    processing_instance_type = ParameterString(
        name="ProcessingInstanceType", default_value=""
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
    
    """ Lab 2 """
    tenant_id = ParameterString(
        name="TenantID", default_value="sample-data",
    )
    tenant_tier = ParameterString(
        name="TenantTier", default_value="Bronze",
    )
    mme_bucket_name = ParameterString(
        name="BucektName", default_value=f"{sample_data_bucket_name}",
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
        name="Train_Customer_Churn_Model",
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
        name="RegisterCustomerChurnModel",
        estimator=xgb_train,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.t2.medium", "ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=model_package_group_name,
        approval_status="Approved",
        model_metrics=model_metrics,
    )
    
    
    """ Lab 2 """
    
    # condition step for an extra model artifacts copy to MME folder for Advanced Tier

    step_args = sklearn_processor.run(
        
        code=os.path.join(BASE_DIR, "postprocess.py"),
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            )
        ],
        arguments=["--sm-bucket-name", sm_bucket_name, "--tenant-id",tenant_id],
    )    
    
    step_post_process_advanced = ProcessingStep(
        name="Copy_Model_Artifacts_To_S3_Folder_For_MME",
        step_args=step_args,
    )
   
    
    step_cond_copy_model_for_advanced = ConditionStep(
        name="Check_Tenant_Tier_Is_Advanced",
        conditions=[cond_advanced_tier],
        if_steps=[step_post_process_advanced],
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
             
            # Lab 2 -> Uncomment the following lines
            tenant_id,
            tenant_tier,
            mme_bucket_name
            
        ],
        
        # steps=[step_train, step_register],
        
        # Lab 2 -> Comment out the above line and uncomment the following line
        steps=[step_train, step_register,step_cond_copy_model_for_advanced ],
        sagemaker_session=pipeline_session,
    )
    return pipeline
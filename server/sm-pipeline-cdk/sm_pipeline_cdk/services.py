
from constructs import Construct

from aws_cdk import (
    Aws,
    CfnOutput,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    Duration,
    aws_lambda_python_alpha as lambda_python,
    aws_iam as iam,
    Duration
)

class Services(Construct):
    
    @property
    def s3_uploader_lambda(self) -> lambda_.Function:
        return self._s3_uploader_lambda

    @property
    def s3_uploader_role(self) -> iam.Role:
        return self._s3_uploader_role    

    @property
    def lambda_layer(self) -> lambda_.LayerVersion:
        return self._lambda_layer

    @property
    def authorizer_lambda(self) -> lambda_.Function:
        return self._authorizer_lambda

    @property
    def authorizer_role(self) -> iam.Role:
        return self._authorizer_role    

    @property
    def jwt_token_lambda(self) -> lambda_.Function:
        return self._get_jwt_token_lambda

    @property
    def inference_processor_role(self) -> iam.Role:
        return self._inference_processor_role

    @property
    def inference_processor_lambda(self) -> lambda_.Function:
        return self._inference_processor_lambda

    @property
    def sm_pipe_exec_role(self) -> iam.Role:
        return self._sm_pipe_exec_role

    @property
    def sm_pipeline_execution_lambda(self) -> lambda_.Function:
        return self._sm_pipeline_execution_lambda

    @property
    def basic_tier_inference_processor_lambda(self) -> lambda_.Function:
        return self._basic_tier_inference_processor_lambda                        

    def __init__(self, scope: Construct, construct_id: str, tenant_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        layer = lambda_python.PythonLayerVersion(self, "MyLayer",
                                                 entry="../layers/",
                                                 compatible_runtimes=[
                                                     lambda_.Runtime.PYTHON_3_9],
                                                 description="MLaaS utilities",
                                                 layer_version_name="MlaasUploaderLayer"
                                                 )
        self._lambda_layer = layer

        # ------------- S3 Uoloader Lambda --------------------------
        # S3 Uploader Lambda Role
        s3_uploader_lambda_role = iam.Role(self, "S3UploaderRole",
                                           role_name=f'mlaas-s3-uploader-role-{tenant_id}-{Aws.REGION}',
                                           assumed_by=iam.ServicePrincipal(
                                               "lambda.amazonaws.com"),
                                           managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="S3UploaderCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                             iam.ManagedPolicy.from_managed_policy_arn(self, id="S3UploaderAWSLambdaBasicExecutionRole",
                                                                                                       managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                           )

        self._s3_uploader_role = s3_uploader_lambda_role
        # s3 Uploader Lambda
        s3_uploader_lambda = lambda_python.PythonFunction(self, "s3UploadFunction",
                                                          entry="../sm-pipeline-cdk/functions",
                                                          runtime=lambda_.Runtime.PYTHON_3_9,
                                                          index="s3_uploader.py",
                                                          handler="lambda_handler",
                                                          function_name=f"mlaas-s3-uploader-{tenant_id}-{Aws.REGION}",
                                                          role=s3_uploader_lambda_role,
                                                          layers=[layer]
                                                          )

        self._s3_uploader_lambda = s3_uploader_lambda

        
        # ------------- Authorizer Lambda --------------------------
        # Authorizer Lambda Role
        auth_lambda_role = iam.Role(self, "AuthorizerRole",
                                    role_name=f'mlaas-authorizer-role-{tenant_id}-{Aws.REGION}',
                                    assumed_by=iam.ServicePrincipal(
                                        "lambda.amazonaws.com"),
                                    managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="CloudWatchLambdaInsightsExecutionRolePolicy",
                                                                                                managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                                      iam.ManagedPolicy.from_managed_policy_arn(self, id="AuthLambdaBasicExecutionRole",
                                                                                                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")]
                                    )

        

        auth_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"]
        ))
        self._authorizer_role = auth_lambda_role 

        # Token Authorizer Lambda
        auth_lambda = lambda_python.PythonFunction(self, "AuthorizerLambda",
                                                   entry="../sm-pipeline-cdk/functions",
                                                   runtime=lambda_.Runtime.PYTHON_3_9,
                                                   index="tenant_authorizer.py",
                                                   handler="lambda_handler",
                                                   function_name=f"mlaas-api-authorizer-{tenant_id}-{Aws.REGION}",
                                                   role=auth_lambda_role,
                                                   layers=[layer]
                                                #        ,
                                                #    environment={
                                                #        'ROLE_TO_ASSUME_ARN': abac_tenant_access_role.role_arn,
                                                #    }
                                                   )
        self._authorizer_lambda = auth_lambda

        # JWT Token role
        get_jwt_lambda_role = iam.Role(self, 'GetJWTLambdaRole',
                                       role_name=f'mlaas-get-jwt-role-{tenant_id}-{Aws.REGION}',
                                       assumed_by=iam.ServicePrincipal(
                                           'lambda.amazonaws.com'),
                                       managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="JWTLambdaBasicExecutionRole",
                                                                                                   managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                                                        ]
                                       )

        get_jwt_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:Query"],
            resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails", 
                       f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails/index/*"]
        ))         

        # get jwt token Lambda
        get_jwt_token_lambda = lambda_python.PythonFunction(self, "getJwtTokenFunction",
                                                            entry="../sm-pipeline-cdk/functions",
                                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                                            index="get_jwt_token.py",
                                                            handler="lambda_handler",
                                                            function_name=f"get-jwt-token-{tenant_id}-{Aws.REGION}",
                                                            role=get_jwt_lambda_role

                                                            )

        self._get_jwt_token_lambda = get_jwt_token_lambda


        inference_request_processor_lambda_role = iam.Role(self, "InferenceRequestProcessorRole",
            role_name=f'mlaas-infer-req-pro-role-{tenant_id}-{Aws.REGION}',
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorAWSLambdaBasicExecutionRole",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                              iam.ManagedPolicy.from_managed_policy_arn(self, id="InferenceRequestProcessorAmazonSageMakerFullAccess",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")])

        self._inference_processor_role = inference_request_processor_lambda_role
        
        lambda_inference_request_processor = lambda_.Function(
            self,
            f"RequestProcessorLambdaFn",
            function_name=f"mlaas-req-pro-{tenant_id}-{Aws.REGION}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="request_processor.lambda_handler",
            timeout = Duration.minutes(2),
            code=lambda_.Code.from_asset("../sm-pipeline-cdk/functions"),
            role=inference_request_processor_lambda_role,
            layers=[layer]            
        )
        self._inference_processor_lambda = lambda_inference_request_processor

        if (tenant_id == "pooled"):
            basic_tier_inference_processor_lambda_role = iam.Role(self, "BasicTierInferenceProcessorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(self, id="BasicInferenceProcessorCloudWatchLambdaInsightsExecutionRolePolicy",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"),
                                iam.ManagedPolicy.from_managed_policy_arn(self, id="BasicInferenceProcessorAWSLambdaBasicExecutionRole",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                                iam.ManagedPolicy.from_managed_policy_arn(self, id="BasicInferenceProcessorAmazonSageMakerFullAccess",
                                                                            managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")])
            basic_tier_inference_processor_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpoint"],
            resources=[f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:endpoint/basic-tier-sagemaker-endpoint"]
            )
            )
            # ------------- Basic Tier Tenant Infrastructure --------------------------
            lambda_basic_tier_inference_request_processor = lambda_.Function(
                self,
                f"BasicTierRequestProcessorLambdaFn",
                function_name=f"mlaas-basic-tier-req-pro-{tenant_id}-{Aws.REGION}",
                runtime=lambda_.Runtime.PYTHON_3_9,
                handler="request_processor.lambda_handler",
                timeout = Duration.minutes(2),
                code=lambda_.Code.from_asset("../sm-pipeline-cdk/functions"),
                role=basic_tier_inference_processor_lambda_role,            
                environment={
                    "ENDPOINT_NAME": "basic-tier-sagemaker-endpoint"
                }            
            )
            self._basic_tier_inference_processor_lambda = lambda_basic_tier_inference_request_processor


        lambda_pipe_exec_iam_role = iam.Role(self, 'LambdaPipeExecRole',
        role_name=f'mlaas-pipe-exec-lambda-role-{tenant_id}-{Aws.REGION}',
        assumed_by=iam.CompositePrincipal(
            iam.ServicePrincipal("lambda.amazonaws.com")
            ),
        managed_policies=[
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSLambdaBasicExecutionRole",managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AmazonSageMakerFullAccess",managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"),
            iam.ManagedPolicy.from_managed_policy_arn(self, id="lambda_AWSCloudFormationReadOnlyAccess",managed_policy_arn="arn:aws:iam::aws:policy/AWSCloudFormationReadOnlyAccess")
            ]
        )

        lambda_pipe_exec_iam_role.add_to_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            resources=["*"]
            )
        )

        self._sm_pipe_exec_role =lambda_pipe_exec_iam_role
        

        sagemaker_execute_pipeline_fn = lambda_python.PythonFunction(self, "ExecuteSMPipelineFn",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions",
            index="sm_pipeline_execution.py",
            handler="handler",
            timeout = Duration.minutes(15),
            role = lambda_pipe_exec_iam_role,
            function_name=f'SMPipelineExeFunction-{tenant_id}-{Aws.REGION}',
            layers=[layer]
        )

        self._sm_pipeline_execution_lambda = sagemaker_execute_pipeline_fn

        # Adding permission for eventbrige to invoke sagemaker pipeline execution function     
        sagemaker_execute_pipeline_fn.add_permission(
            id="eventbridge-sagemaker-pipeline-id",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:rule/*"
        )

        dynamodb_access_abac_role=iam.Role(self, "MLaaSDynamoDBAccessRole",
                                                        role_name=f'ml-saas-db-access-role-{tenant_id}-{Aws.REGION}',
                                                        assumed_by=iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn))

        dynamodb_access_abac_role.assume_role_policy.add_statements(iam.PolicyStatement(
            actions=["sts:AssumeRole","sts:TagSession"],
            effect=iam.Effect.ALLOW,
            principals=[iam.ArnPrincipal(lambda_pipe_exec_iam_role.role_arn)],
            conditions={"StringLike": {"aws:RequestTag/TenantID":"*"}}
        ))

        dynamodb_access_abac_role.add_to_policy(iam.PolicyStatement(
        actions=["dynamodb:GetItem"],
        resources=[f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/MLaaS-TenantDetails"],
        conditions={"ForAllValues:StringEquals":{
                "dynamodb:LeadingKeys": [
                    f"${{aws:PrincipalTag/TenantID}}"
                ]
                }
            }
        )
        )

        sagemaker_execute_pipeline_fn.add_environment("DYNAMODB_ACCESS_ROLE_ARN", dynamodb_access_abac_role.role_arn)    
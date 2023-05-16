// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';

import * as s3 from 'aws-cdk-lib/aws-s3';
import * as codecommit from 'aws-cdk-lib/aws-codecommit';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';

import { Role, ServicePrincipal, ManagedPolicy} from 'aws-cdk-lib/aws-iam';


export class MLSaaSStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const artifactsBucket = new s3.Bucket(this, "ArtifactsBucket", {
        encryption: s3.BucketEncryption.S3_MANAGED,
    });

    
    // Pipeline creation starts
    const pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: 'ml-saas-pipeline',
      artifactBucket: artifactsBucket
    });

    // Import existing CodeCommit sam-app repository
    const codeRepo = codecommit.Repository.fromRepositoryName(
      this,
      'AppRepository', 
      'ml-saas-workshop' 
    );

    // Declare source code as an artifact
    const sourceOutput = new codepipeline.Artifact();

    // Add source stage to pipeline
    const source = pipeline.addStage({
      stageName: 'Source',
      actions: [
        new codepipeline_actions.CodeCommitSourceAction({
          actionName: 'CodeCommit_Source',
          repository: codeRepo,
          branch: 'main',
          output: sourceOutput,
          variablesNamespace: 'SourceVariables'
        }),
      ],
    });

    // Declare build output as artifacts
    const buildOutput = new codepipeline.Artifact();

   
    const codeBuildRole = new Role(this, 'Role', {
      assumedBy: new ServicePrincipal('codebuild.amazonaws.com'),
    });

    codeBuildRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess"))

    //Declare a new CodeBuild project
    const buildProject = new codebuild.PipelineProject(this, 'PoolBuild', {
      buildSpec : codebuild.BuildSpec.fromSourceFilename("server/tenant-buildspec.yml"),
      environment: { buildImage: codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
        privileged: true },
      environmentVariables: {
        'PACKAGE_BUCKET': {
          value: artifactsBucket.bucketName
        }
      },
      role: codeBuildRole
    });
    
    // Add the build stage to our pipeline
    const build =pipeline.addStage({
      stageName: 'Build',
      actions: [
        new codepipeline_actions.CodeBuildAction({
          actionName: 'Build-MLaaS',
          project: buildProject,
          input: sourceOutput,
          outputs: [buildOutput]
        }),
      ]
    });
    
    
  }
}

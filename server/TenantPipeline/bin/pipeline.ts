#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { MLSaaSStack } from '../lib/ml-saas-stack';

const app = new cdk.App();
new MLSaaSStack(app, 'ml-saas-pipeline');

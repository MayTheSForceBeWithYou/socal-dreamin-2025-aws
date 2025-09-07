#!/bin/bash
set -e

# Set project root
PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "Deploying Salesforce to OpenSearch Lab Infrastructure..."

# Deploy infrastructure
cd $PROJECT_ROOT/aws/terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Get outputs
EC2_IP=$(terraform output -raw ec2_public_ip)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
SECRETS_ARN=$(terraform output -raw secrets_manager_secret_arn)

echo "Infrastructure deployment completed!"
echo "EC2 Instance IP: $EC2_IP"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "Secrets ARN: $SECRETS_ARN"
echo ""
echo "To deploy the application, run:"
echo "  bash scripts/deploy-application.sh"
echo ""
echo "SSH to instance: ssh -i $PROJECT_ROOT/aws/certs/aws-ec2 ec2-user@$EC2_IP"

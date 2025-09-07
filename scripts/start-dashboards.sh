#!/bin/bash
# OpenSearch Dashboards Access Setup Script

set -e

PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "🔍 OpenSearch Dashboards Access Setup"
echo "===================================="
echo ""

# Get infrastructure outputs
cd $PROJECT_ROOT/aws/terraform
EC2_IP=$(terraform output -raw ec2_public_ip)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)

echo "Infrastructure Details:"
echo "  EC2 Instance IP: $EC2_IP"
echo "  OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo ""

# Check if AWS CLI is configured
echo "Checking AWS CLI configuration..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS CLI not configured or credentials expired"
    echo "Please run: aws configure"
    exit 1
fi

AWS_IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
echo "✅ AWS CLI configured: $AWS_IDENTITY"
echo ""

# Check if SSH key exists
SSH_KEY="$PROJECT_ROOT/aws/terraform/salesforce-opensearch-lab-key.pem"
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    echo "Please ensure the SSH key exists"
    exit 1
fi

echo "✅ SSH key found: $SSH_KEY"
echo ""

echo "🚀 Setting up OpenSearch Dashboards Access..."
echo ""

# Method 1: Authentication Proxy with SSH Tunnel (Recommended)
echo "Method 1: Authentication Proxy with SSH Tunnel (Recommended)"
echo "============================================================"
echo ""
echo "This method creates a local proxy server that handles AWS authentication"
echo "and forwards requests through an SSH tunnel to OpenSearch Dashboards."
echo ""

echo "Starting authentication proxy with SSH tunnel..."
echo "Access Dashboards at: http://localhost:8080/_dashboards/"
echo ""
echo "Press Ctrl+C to stop the proxy server"
echo ""

# Start the proxy server with SSH tunnel
python3 $PROJECT_ROOT/scripts/opensearch-proxy-tunnel.py 8080 9200 $EC2_IP

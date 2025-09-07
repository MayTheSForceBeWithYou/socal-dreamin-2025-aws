#!/bin/bash
# Simple OpenSearch Dashboards Access using AWS CLI

set -e

OPENSEARCH_ENDPOINT="https://search-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com"
PORT=8080

echo "🔍 OpenSearch Dashboards Access"
echo "==============================="
echo ""
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "Local Port: $PORT"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS CLI not configured or credentials expired"
    echo "Please run: aws configure"
    exit 1
fi

AWS_IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
echo "✅ AWS CLI configured: $AWS_IDENTITY"
echo ""

echo "🚀 Starting OpenSearch Dashboards Access..."
echo ""
echo "Method 1: AWS Console (Recommended)"
echo "-----------------------------------"
echo "1. Go to AWS Console: https://console.aws.amazon.com/"
echo "2. Navigate to OpenSearch service"
echo "3. Find your domain: salesforce-opensearch-lab-os"
echo "4. Look for 'OpenSearch Dashboards' button (not just URL)"
echo "5. Click that button for automatic authentication"
echo ""

echo "Method 2: Direct Browser Access"
echo "-------------------------------"
echo "1. Open your browser"
echo "2. Go to: $OPENSEARCH_ENDPOINT/_dashboards/"
echo "3. Sign in with your AWS credentials when prompted"
echo ""

echo "Method 3: CLI Testing"
echo "--------------------"
echo "Test OpenSearch connectivity:"
echo "  curl -X GET '$OPENSEARCH_ENDPOINT/'"
echo ""

echo "Method 4: EC2 Access (Guaranteed to Work)"
echo "-----------------------------------------"
echo "SSH into your EC2 instance and test from there:"
echo "  ssh -i aws/certs/aws-ec2 ec2-user@52.52.231.148"
echo "  curl -X GET 'https://search-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com/'"
echo ""

echo "📝 Recommendation:"
echo "Try Method 1 (AWS Console) first - it's the most reliable."
echo "If that doesn't work, try Method 2 (Direct Browser Access)."
echo ""

echo "Press any key to continue..."
read -n 1 -s

#!/bin/bash
# Simple OpenSearch Dashboards Access Script

set -e

PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "🔍 OpenSearch Dashboards Access"
echo "==============================="
echo ""

# Get infrastructure outputs
cd $PROJECT_ROOT/aws/terraform
EC2_IP="54.241.255.154"
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
SSH_KEY="$PROJECT_ROOT/aws/certs/aws-ec2"
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    echo "Please ensure the SSH key exists"
    exit 1
fi

echo "✅ SSH key found: $SSH_KEY"
echo ""

echo "🚀 OpenSearch Dashboards Access Methods"
echo "======================================="
echo ""

echo "Method 1: AWS Console (Easiest)"
echo "------------------------------"
echo "1. Go to AWS Console: https://console.aws.amazon.com/"
echo "2. Navigate to OpenSearch service"
echo "3. Find your domain: salesforce-opensearch-lab-os"
echo "4. Click 'OpenSearch Dashboards URL'"
echo "5. You'll be automatically authenticated with your AWS credentials"
echo ""

echo "Method 2: SSH Tunnel + Browser"
echo "------------------------------"
echo "1. Run this command in a separate terminal:"
echo "   ssh -i $SSH_KEY -L 9200:localhost:9200 ec2-user@$EC2_IP"
echo ""
echo "2. Keep that terminal open (don't close it)"
echo ""
echo "3. In your browser, go to: https://localhost:9200/_dashboards/"
echo ""
echo "4. You'll see a security warning - click 'Advanced' and 'Proceed to localhost'"
echo ""
echo "5. You'll get an authentication error - this is expected"
echo "   The browser can't authenticate with AWS IAM directly"
echo ""

echo "Method 3: CLI Access (For Testing)"
echo "----------------------------------"
echo "Test OpenSearch connectivity from EC2:"
echo "  ssh -i $SSH_KEY ec2-user@$EC2_IP"
echo "  curl -X GET 'https://localhost:9200/'"
echo ""

echo "Method 4: Programmatic Access"
echo "------------------------------"
echo "Use the test script we created:"
echo "  ssh -i $SSH_KEY ec2-user@$EC2_IP"
echo "  python3 /opt/salesforce-streamer/test-opensearch-iam.py"
echo ""

echo "📝 Recommendation:"
echo "For the easiest access, use Method 1 (AWS Console)."
echo "For development/testing, use Method 3 or 4."
echo ""

echo "Press any key to continue..."
read -n 1 -s


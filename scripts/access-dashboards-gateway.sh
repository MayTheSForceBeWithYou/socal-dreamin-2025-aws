#!/bin/bash
# OpenSearch Dashboards Access via IP Gateway (Bastion Host)

set -e

PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "🔍 OpenSearch Dashboards Access via IP Gateway"
echo "=============================================="
echo ""

# Get infrastructure outputs
cd $PROJECT_ROOT/aws/terraform

# Check if terraform has been applied
if ! terraform output bastion_public_ip >/dev/null 2>&1; then
    echo "❌ Bastion host not found in terraform outputs"
    echo "Please run: terraform apply"
    exit 1
fi

BASTION_IP=$(terraform output -raw bastion_public_ip)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
OPENSEARCH_PROXY_URL=$(terraform output -raw opensearch_proxy_url)

echo "Infrastructure Details:"
echo "  Bastion Host IP: $BASTION_IP"
echo "  OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "  Proxy URL: $OPENSEARCH_PROXY_URL"
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

# Check bastion host connectivity
echo "Checking bastion host connectivity..."
if ! curl -s --connect-timeout 10 "https://$BASTION_IP" >/dev/null 2>&1; then
    echo "❌ Cannot reach bastion host at $BASTION_IP"
    echo "Please check:"
    echo "  1. Bastion host is running"
    echo "  2. Your IP is in allowed_cidr_blocks"
    echo "  3. Security groups allow HTTPS access"
    exit 1
fi

echo "✅ Bastion host is reachable"
echo ""

echo "🚀 OpenSearch Dashboards Access Ready!"
echo "====================================="
echo ""
echo "🌐 Direct Access (Recommended):"
echo "  Open your browser and go to: $OPENSEARCH_PROXY_URL"
echo ""
echo "🔧 Alternative Methods:"
echo "  1. AWS Console: Go to OpenSearch service → Click 'OpenSearch Dashboards URL'"
echo "  2. SSH to bastion: ssh -i aws/certs/aws-ec2 ec2-user@$BASTION_IP"
echo ""
echo "📋 Troubleshooting:"
echo "  - SSL Certificate Error: Click 'Advanced' → 'Proceed to $BASTION_IP'"
echo "  - Connection Refused: Check bastion host status"
echo "  - Access Denied: Verify your IP is in allowed_cidr_blocks"
echo ""
echo "🔐 Security Notes:"
echo "  - Only your IP can access the bastion host"
echo "  - All traffic is encrypted via HTTPS"
echo "  - OpenSearch uses AWS IAM authentication"
echo ""

# Optional: Open browser automatically (if on macOS)
if command -v open >/dev/null 2>&1; then
    echo "🌐 Opening browser..."
    open "$OPENSEARCH_PROXY_URL"
elif command -v xdg-open >/dev/null 2>&1; then
    echo "🌐 Opening browser..."
    xdg-open "$OPENSEARCH_PROXY_URL"
else
    echo "💡 Tip: Copy and paste this URL into your browser: $OPENSEARCH_PROXY_URL"
fi

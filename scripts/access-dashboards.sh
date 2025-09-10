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

echo "🚀 OpenSearch Dashboards Access Methods"
echo "======================================="
echo ""

echo "Method 1: IP Gateway (Recommended - New Approach)"
echo "--------------------------------------------------"
echo "Direct HTTPS access through bastion host:"
echo "  Open your browser and go to: $OPENSEARCH_PROXY_URL"
echo "  ✅ Secure, encrypted, no SSH tunneling needed"
echo ""

echo "Method 2: AWS Console (Alternative)"
echo "-----------------------------------"
echo "1. Go to AWS Console: https://console.aws.amazon.com/"
echo "2. Navigate to OpenSearch service"
echo "3. Find your domain: sf-opensearch-lab-os"
echo "4. Click 'OpenSearch Dashboards URL'"
echo "5. You'll be automatically authenticated with your AWS credentials"
echo ""

echo "Method 3: SSH to Bastion (For Advanced Users)"
echo "---------------------------------------------"
echo "1. SSH into bastion host:"
echo "   ssh -i aws/certs/aws-ec2 ec2-user@$BASTION_IP"
echo ""
echo "2. Check nginx status:"
echo "   sudo systemctl status nginx"
echo ""
echo "3. View logs:"
echo "   sudo tail -f /var/log/nginx/access.log"
echo ""

echo "Method 4: CLI Access (For Testing)"
echo "----------------------------------"
echo "Test OpenSearch connectivity from bastion:"
echo "  ssh -i aws/certs/aws-ec2 ec2-user@$BASTION_IP"
echo "  curl -X GET 'https://localhost/'"
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

echo "📝 Recommendation:"
echo "Use Method 1 (IP Gateway) for the easiest and most secure access to OpenSearch Dashboards."
echo ""

echo "Press any key to continue..."
read -n 1 -s


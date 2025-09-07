#!/bin/bash
set -e

# Set project root
PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "Setting up OpenSearch Dashboards tunnel..."

# Get infrastructure outputs
cd $PROJECT_ROOT/aws/terraform
EC2_IP=$(terraform output -raw ec2_public_ip)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)

echo "EC2 Instance IP: $EC2_IP"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"

# Extract the internal OpenSearch endpoint (without https://)
OPENSEARCH_INTERNAL=$(echo $OPENSEARCH_ENDPOINT | sed 's/https:\/\///')

echo ""
echo "🔗 SSH Tunnel Setup Instructions:"
echo "================================"
echo ""
echo "1. Open a new terminal and run this command to create the tunnel:"
echo ""
echo "   ssh -i $PROJECT_ROOT/aws/certs/aws-ec2 -L 9200:$OPENSEARCH_INTERNAL:443 ec2-user@$EC2_IP"
echo ""
echo "2. Keep that terminal open and visit these URLs in your browser:"
echo ""
echo "   OpenSearch API: http://localhost:9200"
echo "   OpenSearch Dashboards: http://localhost:9200/_dashboards"
echo ""
echo "3. For IAM authentication, you'll need to use AWS SigV4 signed requests"
echo "   (See Part 2 for authentication setup)"
echo ""
echo "4. To stop the tunnel, press Ctrl+C in the SSH terminal"
echo ""
echo "📋 Alternative: Using AWS SSM Session Manager (if SSM is enabled):"
echo "================================================================"
echo ""
echo "If your EC2 instance has SSM agent installed, you can use:"
echo ""
echo "   aws ssm start-session --target $(terraform output -raw ec2_instance_id) --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"443\"],\"localPortNumber\":[\"9200\"]}'"
echo ""
echo "Then access: http://localhost:9200/_dashboards"
echo ""

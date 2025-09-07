#!/bin/bash
set -e

# Set project root
PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "Deploying Salesforce Streamer Application..."

# Get infrastructure outputs
cd $PROJECT_ROOT/aws/terraform
EC2_IP=$(terraform output -raw ec2_public_ip)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
SECRETS_ARN=$(terraform output -raw secrets_manager_secret_arn)
SALESFORCE_INSTANCE_URL=$(terraform output -raw salesforce_instance_url)

echo "EC2 Instance IP: $EC2_IP"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"

# Wait for instance to be ready (if needed)
echo "Checking EC2 instance connectivity..."
if ! ssh -i $PROJECT_ROOT/aws/certs/aws-ec2 -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$EC2_IP "echo 'Instance is ready'" 2>/dev/null; then
    echo "Waiting for EC2 instance to be ready..."
    sleep 30
fi

# Deploy application code
echo "Deploying application code to EC2..."
scp -i $PROJECT_ROOT/aws/certs/aws-ec2 -o StrictHostKeyChecking=no \
    -r $PROJECT_ROOT/aws/ec2-app/ ec2-user@$EC2_IP:/tmp/

# Install and start the application
ssh -i $PROJECT_ROOT/aws/certs/aws-ec2 -o StrictHostKeyChecking=no ec2-user@$EC2_IP << EOF
# Create application directory and user
sudo mkdir -p /opt/salesforce-streamer
sudo useradd -r -s /bin/false salesforce-streamer || true
sudo chown salesforce-streamer:salesforce-streamer /opt/salesforce-streamer

# Copy application files
sudo cp /tmp/ec2-app/*.py /opt/salesforce-streamer/
sudo cp /tmp/ec2-app/requirements.txt /opt/salesforce-streamer/
sudo cp /tmp/ec2-app/salesforce-streamer.service /etc/systemd/system/

# Create environment file
sudo tee /opt/salesforce-streamer/.env > /dev/null << ENVEOF
AWS_REGION=us-west-1
SECRETS_MANAGER_SECRET_ARN=$SECRETS_ARN
OPENSEARCH_ENDPOINT=https://$OPENSEARCH_ENDPOINT
OPENSEARCH_INDEX=salesforce-login-events
POLL_INTERVAL_SECONDS=60
SALESFORCE_INSTANCE_URL=$SALESFORCE_INSTANCE_URL
ENVEOF

# Set proper ownership
sudo chown -R salesforce-streamer:salesforce-streamer /opt/salesforce-streamer/
sudo chmod 600 /opt/salesforce-streamer/.env

# Reload systemd and install dependencies
sudo systemctl daemon-reload
cd /opt/salesforce-streamer
sudo pip3 install -r requirements.txt

# Restart the service
sudo systemctl stop salesforce-streamer || true
sudo systemctl start salesforce-streamer
sudo systemctl enable salesforce-streamer
sudo systemctl status salesforce-streamer
EOF

echo "Application deployment completed!"
echo "SSH to instance: ssh -i $PROJECT_ROOT/aws/certs/aws-ec2 ec2-user@$EC2_IP"
echo "Check logs: sudo journalctl -u salesforce-streamer -f"
echo "Check service status: sudo systemctl status salesforce-streamer"

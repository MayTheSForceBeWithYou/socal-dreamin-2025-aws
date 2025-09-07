#!/bin/bash
yum update -y
yum install -y python3 python3-pip git

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install and configure SSM Agent
# Amazon Linux 2 comes with SSM Agent pre-installed, but let's ensure it's running
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Verify SSM Agent is running
systemctl status amazon-ssm-agent

# Log SSM Agent status
echo "SSM Agent status: $(systemctl is-active amazon-ssm-agent)" >> /var/log/user-data-completion.log

# Create application user
useradd -m -s /bin/bash salesforce-streamer
usermod -aG wheel salesforce-streamer

# Create application directory
mkdir -p /opt/salesforce-streamer
chown salesforce-streamer:salesforce-streamer /opt/salesforce-streamer

# Clone application code (you'll need to set this up as a Git repo or use S3)
cd /opt/salesforce-streamer

# For now, create the application files directly
cat > requirements.txt << 'EOF'
requests==2.31.0
boto3==1.28.57
opensearch-py==2.3.1
pyjwt[crypto]==2.8.0
cryptography==41.0.7
python-dotenv==1.0.0
EOF

# Install Python dependencies
pip3 install -r requirements.txt

# Set environment variables
cat > /opt/salesforce-streamer/.env << 'EOF'
OPENSEARCH_ENDPOINT=${opensearch_endpoint}
SALESFORCE_INSTANCE_URL=${salesforce_instance_url}
SECRETS_MANAGER_SECRET_ARN=${secrets_manager_secret_arn}
POLL_INTERVAL_SECONDS=${poll_interval_seconds}
AWS_REGION=${aws_region}
OPENSEARCH_INDEX=salesforce-login-events
EOF

# Create systemd service
cat > /etc/systemd/system/salesforce-streamer.service << 'EOF'
[Unit]
Description=Salesforce Login Event Streamer
After=network.target

[Service]
Type=simple
User=salesforce-streamer
WorkingDirectory=/opt/salesforce-streamer
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/salesforce-streamer/.env
ExecStart=/usr/bin/python3 /opt/salesforce-streamer/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Change ownership
chown -R salesforce-streamer:salesforce-streamer /opt/salesforce-streamer

# Enable service (but don't start yet - need to deploy code first)
systemctl enable salesforce-streamer

# Log completion
echo "EC2 instance initialization completed at $(date)" > /var/log/user-data-completion.log

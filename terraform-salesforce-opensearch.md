# Simplified EC2-Based Salesforce to OpenSearch Integration

## Project Structure

```
socal-dreamin-2025-aws/
├── README.md
├── .gitignore
├── Makefile
│
├── aws/
│   ├── ec2-app/                            # Simple Python app for EC2
│   │   ├──  app.py                         # Main application
│   │   ├── requirements.txt                # Python dependencies
│   │   ├── config.py                       # Configuration
│   │   ├── salesforce_client.py            # Salesforce JWT client
│   │   ├── opensearch_client.py            # OpenSearch client
│   │   ├── install.sh                      # Installation script
│   │   └── systemd/
│   │       └── salesforce-streamer.service # Systemd service file
│   │
│   ├── lambda/                             # Keep existing Lambda code
│   │   └── (existing structure)
│   │
│   ├── terraform/
│   │   ├── main.tf                         # Root module
│   │   ├── variables.tf                    # Input variables
│   │   ├── outputs.tf                      # Output values
│   │   ├── terraform.tfvars                # Variable values (add to .gitignore)
│   │   ├── terraform.tfvars.example        # Example variable file
│   │   ├── versions.tf                     # Provider versions
│   │   ├── user-data.sh                    # EC2 initialization script
│   │   │
│   │   └── modules/
│   │       ├── opensearch/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       ├── ec2/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       ├── iam/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       └── networking/
│   │           ├── main.tf
│   │           ├── variables.tf
│   │           └── outputs.tf
│
├── salesforce/
│   ├── config/                         # Keep existing
│   ├── force-app/                      # Keep existing  
│   ├── connected-app/
│   │   ├── README.md
│   │   └── setup-guide.md
│   └── certificates/
│       └── README.md
│
└── scripts/
    ├── deploy.sh                       # Simple deployment
    ├── generate-certificates.sh        # Certificate generation
    └── ssh-to-instance.sh             # SSH helper
```

## Root Terraform Configuration

### `aws/terraform/main.tf`
```hcl
terraform {
  required_version = ">= 1.0"
  
  # Using local state storage for workshop simplicity
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "salesforce-opensearch/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
      Owner     = var.owner
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Key Pair for EC2 SSH access
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-keypair"
  public_key = var.ssh_public_key
  
  tags = {
    Name = "${var.project_name}-keypair"
  }
}

# Networking
module "networking" {
  source = "./modules/networking"
  
  project_name         = var.project_name
  vpc_cidr            = var.vpc_cidr
  availability_zones  = data.aws_availability_zones.available.names
}

# IAM Roles
module "iam" {
  source = "./modules/iam"
  
  project_name = var.project_name
}

# OpenSearch Domain
module "opensearch" {
  source = "./modules/opensearch"
  
  project_name    = var.project_name
  vpc_id          = module.networking.vpc_id
  subnet_ids      = module.networking.private_subnet_ids
  security_groups = [module.networking.opensearch_security_group_id]
  
  instance_type   = var.opensearch_instance_type
  instance_count  = var.opensearch_instance_count
  ebs_volume_size = var.opensearch_ebs_volume_size
}

# EC2 Instance
module "ec2" {
  source = "./modules/ec2"
  
  project_name           = var.project_name
  vpc_id                 = module.networking.vpc_id
  subnet_id              = module.networking.public_subnet_ids[0]  # Use public subnet for easy access
  security_group_ids     = [module.networking.ec2_security_group_id]
  key_pair_name          = aws_key_pair.main.key_name
  iam_instance_profile   = module.iam.ec2_instance_profile_name
  
  instance_type          = var.ec2_instance_type
  opensearch_endpoint    = module.opensearch.endpoint
  salesforce_instance_url = var.salesforce_instance_url
  secrets_manager_secret_arn = aws_secretsmanager_secret.salesforce_creds.arn
  poll_interval_seconds  = var.poll_interval_seconds
}

# Secrets Manager for Salesforce credentials
resource "aws_secretsmanager_secret" "salesforce_creds" {
  name        = "${var.project_name}-salesforce-creds"
  description = "Salesforce JWT credentials for login event streaming"
  
  tags = {
    Name = "${var.project_name}-salesforce-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "salesforce_creds" {
  secret_id = aws_secretsmanager_secret.salesforce_creds.id
  secret_string = jsonencode({
    client_id    = var.salesforce_client_id
    username     = var.salesforce_username
    private_key  = var.salesforce_private_key
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}
```

### `aws/terraform/variables.tf`
```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "salesforce-opensearch-lab"
}

variable "owner" {
  description = "Owner tag"
  type        = string
  default     = "lab-user"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}

# OpenSearch
variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 1
}

variable "opensearch_ebs_volume_size" {
  description = "OpenSearch EBS volume size (GB)"
  type        = number
  default     = 20
}

# EC2
variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "poll_interval_seconds" {
  description = "Polling interval for Salesforce events"
  type        = number
  default     = 60
}

# Salesforce JWT
variable "salesforce_instance_url" {
  description = "Salesforce instance URL"
  type        = string
}

variable "salesforce_client_id" {
  description = "Salesforce Connected App Consumer Key"
  type        = string
  sensitive   = true
}

variable "salesforce_username" {
  description = "Salesforce username for JWT"
  type        = string
  sensitive   = true
}

variable "salesforce_private_key" {
  description = "Private key for JWT (PEM format)"
  type        = string
  sensitive   = true
}
```

### `aws/terraform/outputs.tf`
```hcl
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "EC2 public IP"
  value       = module.ec2.public_ip
}

output "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  value       = module.opensearch.endpoint
}

output "opensearch_kibana_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = module.opensearch.kibana_endpoint
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i ~/.ssh/your-key.pem ec2-user@${module.ec2.public_ip}"
}
```

## EC2 Module

### `aws/terraform/modules/ec2/main.tf`
```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# User data script for EC2 initialization
locals {
  user_data = templatefile("${path.module}/../../user-data.sh", {
    opensearch_endpoint        = var.opensearch_endpoint
    salesforce_instance_url    = var.salesforce_instance_url
    secrets_manager_secret_arn = var.secrets_manager_secret_arn
    poll_interval_seconds      = var.poll_interval_seconds
    aws_region                 = data.aws_region.current.name
  })
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  subnet_id             = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile   = var.iam_instance_profile
  
  user_data = base64encode(local.user_data)
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  tags = {
    Name = "${var.project_name}-streamer"
    Type = "salesforce-opensearch-streamer"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for consistent access
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"
  
  tags = {
    Name = "${var.project_name}-eip"
  }
}

data "aws_region" "current" {}
```

### `aws/terraform/user-data.sh`
```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

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
```

## Simple Python Application

### `aws/ec2-app/app.py`
```python
#!/usr/bin/env python3
"""
Simple Salesforce LoginEventStream to OpenSearch streamer for EC2
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from config import Config
from salesforce_client import SalesforceClient
from opensearch_client import OpenSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/salesforce-streamer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LoginEventStreamer:
    def __init__(self):
        self.config = Config()
        self.sf_client = SalesforceClient(self.config)
        self.os_client = OpenSearchClient(self.config)
        self.last_poll_time = datetime.utcnow() - timedelta(minutes=5)
        
    def run(self):
        """Main processing loop"""
        logger.info(f"Starting Salesforce LoginEvent streamer...")
        logger.info(f"Polling interval: {self.config.poll_interval_seconds} seconds")
        logger.info(f"OpenSearch endpoint: {self.config.opensearch_endpoint}")
        
        # Test connections on startup
        if not self.sf_client.test_connection():
            logger.error("Failed to connect to Salesforce. Exiting.")
            sys.exit(1)
            
        if not self.os_client.test_connection():
            logger.error("Failed to connect to OpenSearch. Exiting.")
            sys.exit(1)
        
        while True:
            try:
                self.process_events()
                time.sleep(self.config.poll_interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(30)  # Wait before retrying on error
    
    def process_events(self):
        """Process a single batch of events"""
        end_time = datetime.utcnow()
        start_time = self.last_poll_time
        
        sf_start = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        sf_end = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        logger.debug(f"Polling for events from {sf_start} to {sf_end}")
        
        # Fetch events from Salesforce
        events = self.sf_client.get_login_events(sf_start, sf_end)
        
        if events:
            # Index to OpenSearch
            success = self.os_client.bulk_index_events(events)
            if success:
                logger.info(f"Successfully processed {len(events)} login events")
            else:
                logger.error(f"Failed to index {len(events)} events")
        else:
            logger.debug("No new events found")
        
        self.last_poll_time = end_time

if __name__ == "__main__":
    try:
        streamer = LoginEventStreamer()
        streamer.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
```

### `aws/ec2-app/config.py`
```python
"""Configuration management for Salesforce streamer"""
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # AWS Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.secrets_manager_secret_arn = os.getenv('SECRETS_MANAGER_SECRET_ARN')
        
        # Application Configuration
        self.opensearch_endpoint = os.getenv('OPENSEARCH_ENDPOINT')
        self.opensearch_index = os.getenv('OPENSEARCH_INDEX', 'salesforce-login-events')
        self.poll_interval_seconds = int(os.getenv('POLL_INTERVAL_SECONDS', '60'))
        
        # Salesforce Configuration
        self.salesforce_instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
        
        # Load Salesforce credentials from Secrets Manager
        self._load_salesforce_credentials()
    
    def _load_salesforce_credentials(self):
        """Load Salesforce JWT credentials from AWS Secrets Manager"""
        if not self.secrets_manager_secret_arn:
            raise ValueError("SECRETS_MANAGER_SECRET_ARN environment variable required")
        
        try:
            client = boto3.client('secretsmanager', region_name=self.aws_region)
            response = client.get_secret_value(SecretId=self.secrets_manager_secret_arn)
            
            secret_data = json.loads(response['SecretString'])
            
            self.salesforce_client_id = secret_data['client_id']
            self.salesforce_username = secret_data['username']
            self.salesforce_private_key = secret_data['private_key']
            
        except Exception as e:
            raise ValueError(f"Failed to load Salesforce credentials: {e}")
```

### `aws/ec2-app/salesforce_client.py`
```python
"""Salesforce JWT authentication client"""
import time
import jwt
import requests
import logging
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class SalesforceClient:
    def __init__(self, config):
        self.config = config
        self.access_token = None
        self.token_expires_at = None
    
    def _create_jwt_assertion(self):
        """Create JWT assertion for authentication"""
        now = int(time.time())
        
        payload = {
            'iss': self.config.salesforce_client_id,
            'sub': self.config.salesforce_username,
            'aud': self.config.salesforce_instance_url,
            'exp': now + 300,
            'iat': now
        }
        
        private_key_obj = serialization.load_pem_private_key(
            self.config.salesforce_private_key.encode('utf-8'),
            password=None
        )
        
        return jwt.encode(payload, private_key_obj, algorithm='RS256')
    
    def authenticate(self):
        """Authenticate using JWT Bearer Token flow"""
        try:
            jwt_assertion = self._create_jwt_assertion()
            
            auth_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': jwt_assertion
            }
            
            response = requests.post(
                f"{self.config.salesforce_instance_url}/services/oauth2/token",
                data=auth_data,
                timeout=30
            )
            response.raise_for_status()
            
            auth_result = response.json()
            self.access_token = auth_result['access_token']
            self.token_expires_at = datetime.now() + timedelta(hours=1, minutes=45)
            
            logger.info("Successfully authenticated with Salesforce")
            
        except Exception as e:
            logger.error(f"Salesforce authentication failed: {e}")
            raise
    
    def is_token_valid(self):
        """Check if token is still valid"""
        return (self.access_token and 
                self.token_expires_at and 
                datetime.now() < self.token_expires_at)
    
    def ensure_authenticated(self):
        """Ensure we have a valid token"""
        if not self.is_token_valid():
            self.authenticate()
    
    def get_login_events(self, start_time, end_time):
        """Fetch login events from Salesforce"""
        self.ensure_authenticated()
        
        query = f"""
        SELECT Id, UserId, Username, LoginTime, LoginType, LoginUrl, 
               SourceIp, Status, Browser, Platform, Application
        FROM LoginEventStream 
        WHERE LoginTime >= {start_time} AND LoginTime < {end_time}
        ORDER BY LoginTime ASC
        """
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{self.config.salesforce_instance_url}/services/data/v58.0/query",
            headers=headers,
            params={'q': query},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('records', [])
    
    def test_connection(self):
        """Test Salesforce connection"""
        try:
            self.authenticate()
            return True
        except Exception as e:
            logger.error(f"Salesforce connection test failed: {e}")
            return False
```

### `aws/ec2-app/opensearch_client.py`
```python
"""OpenSearch client for indexing login events"""
import boto3
import logging
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

logger = logging.getLogger(__name__)

class OpenSearchClient:
    def __init__(self, config):
        self.config = config
        self.client = self._create_client()
        self._create_index_if_not_exists()
    
    def _create_client(self):
        """Create OpenSearch client with AWS authentication"""
        host = self.config.opensearch_endpoint.replace('https://', '')
        
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        return OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=(credentials.access_key, credentials.secret_key),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
    
    def _create_index_if_not_exists(self):
        """Create index with mapping if it doesn't exist"""
        if not self.client.indices.exists(index=self.config.opensearch_index):
            mapping = {
                "mappings": {
                    "properties": {
                        "Id": {"type": "keyword"},
                        "UserId": {"type": "keyword"},
                        "Username": {"type": "keyword"},
                        "LoginTime": {"type": "date"},
                        "SourceIp": {"type": "ip"},
                        "Status": {"type": "keyword"},
                        "@timestamp": {"type": "date"}
                    }
                }
            }
            
            self.client.indices.create(index=self.config.opensearch_index, body=mapping)
            logger.info(f"Created OpenSearch index: {self.config.opensearch_index}")
    
    def bulk_index_events(self, events):
        """Bulk index events to OpenSearch"""
        if not events:
            return True
        
        bulk_data = []
        for event in events:
            event['@timestamp'] = datetime.utcnow().isoformat()
            
            bulk_data.append({
                "index": {
                    "_index": self.config.opensearch_index,
                    "_id": event.get('Id')
                }
            })
            bulk_data.append(event)
        
        try:
            response = self.client.bulk(body=bulk_data)
            
            if response.get('errors'):
                logger.warning("Some events failed to index")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index events: {e}")
            return False
    
    def test_connection(self):
        """Test OpenSearch connection"""
        try:
            info = self.client.info()
            logger.info(f"Connected to OpenSearch: {info.get('version', {}).get('number')}")
            return True
        except Exception as e:
            logger.error(f"OpenSearch connection test failed: {e}")
            return False
```

## Simple Deployment Scripts

### `scripts/deploy.sh`
```bash
#!/bin/bash
set -e

echo "Deploying Salesforce to OpenSearch Lab Environment..."

# Deploy infrastructure
cd aws/terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Get EC2 instance IP
EC2_IP=$(terraform output -raw ec2_public_ip)
echo "EC2 Instance IP: $EC2_IP"

# Wait for instance to be ready
echo "Waiting for EC2 instance to be ready..."
sleep 60

# Deploy application code
echo "Deploying application code to EC2..."
scp -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no \
    ../aws/ec2-app/* ec2-user@$EC2_IP:/tmp/

# Install and start the application
ssh -i ~/.ssh/your-key.pem -o StrictHostKeyChecking=no ec2-user@$EC2_IP << 'EOF'
sudo cp /tmp/*.py /opt/salesforce-streamer/
sudo cp /tmp/requirements.txt /opt/salesforce-streamer/
sudo chown -R salesforce-streamer:salesforce-streamer /opt/salesforce-streamer/

# Install dependencies
cd /opt/salesforce-streamer
sudo pip3 install -r requirements.txt

# Start the service
sudo systemctl start salesforce-streamer
sudo systemctl status salesforce-streamer
EOF

echo "Deployment completed!"
echo "SSH to instance: ssh -i ~/.ssh/your-key.pem ec2-user@$EC2_IP"
echo "Check logs: sudo journalctl -u salesforce-streamer -f"
```

### `Makefile`
```makefile
.PHONY: help deploy ssh logs clean

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

deploy: ## Deploy the lab environment
	@./scripts/deploy.sh

ssh: ## SSH to the EC2 instance
	@./scripts/ssh-to-instance.sh

logs: ## View application logs
	@./scripts/ssh-to-instance.sh "sudo journalctl -u salesforce-streamer -f"

clean: ## Destroy the environment
	@cd aws/terraform && terraform destroy -var-file="terraform.tfvars"

status: ## Check service status
	@./scripts/ssh-to-instance.sh "sudo systemctl status salesforce-streamer"

restart: ## Restart the service
	@./scripts/ssh-to-instance.sh "sudo systemctl restart salesforce-streamer"
```

This simplified approach gives you:

1. **Single EC2 instance** running a Python service
2. **Systemd service management** for reliability
3. **Direct AWS IAM authentication** for OpenSearch
4. **Simple deployment scripts** without containers
5. **Easy troubleshooting** via SSH and logs
6. **Cost-effective** for lab environments

The total AWS cost should be under $20/month for this setup, and you can easily SSH in to troubleshoot or make changes. Would you like me to add any specific monitoring or alerting components?
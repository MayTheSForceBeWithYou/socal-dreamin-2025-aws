"""Configuration management for Salesforce streamer"""
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # AWS Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-west-1')
        self.secrets_manager_secret_arn = os.getenv('SECRETS_MANAGER_SECRET_ARN')
        
        # Application Configuration
        self.opensearch_endpoint = os.getenv('OPENSEARCH_ENDPOINT')
        self.opensearch_index = os.getenv('OPENSEARCH_INDEX', 'salesforce-login-events')
        self.poll_interval_seconds = int(os.getenv('POLL_INTERVAL_SECONDS', '60'))
        
        # Salesforce Configuration
        self.salesforce_instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
        
        # Validate required configuration
        self._validate_required_config()
        
        # Load Salesforce credentials from Secrets Manager
        self._load_salesforce_credentials()
    
    def _validate_required_config(self):
        """Validate that all required configuration is present"""
        required_vars = {
            'OPENSEARCH_ENDPOINT': self.opensearch_endpoint,
            'SECRETS_MANAGER_SECRET_ARN': self.secrets_manager_secret_arn,
            'SALESFORCE_INSTANCE_URL': self.salesforce_instance_url
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
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

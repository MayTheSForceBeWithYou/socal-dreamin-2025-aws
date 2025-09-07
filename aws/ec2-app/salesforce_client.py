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
            
            if response.status_code != 200:
                logger.error(f"Salesforce authentication failed with status {response.status_code}")
                logger.error(f"Response body: {response.text}")
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
        SELECT Id, UserId, LoginTime, LoginType, LoginUrl, 
               SourceIp, Status, Browser, Platform, Application
        FROM LoginHistory 
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
        
        if response.status_code != 200:
            logger.error(f"SOQL query failed with status {response.status_code}")
            logger.error(f"Query: {query}")
            logger.error(f"Response body: {response.text}")
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

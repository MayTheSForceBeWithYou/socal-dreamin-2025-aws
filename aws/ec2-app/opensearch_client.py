"""OpenSearch client for indexing login events"""
import boto3
import logging
import requests
from datetime import datetime
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

logger = logging.getLogger(__name__)

class OpenSearchClient:
    def __init__(self, config):
        self.config = config
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self._create_index_if_not_exists()
    
    def _make_authenticated_request(self, method, path, data=None):
        """Make an authenticated request to OpenSearch"""
        url = f"{self.config.opensearch_endpoint}{path}"
        
        # Create AWS request
        aws_request = AWSRequest(method=method, url=url, data=data)
        SigV4Auth(self.credentials, 'es', self.config.aws_region).add_auth(aws_request)
        
        # Convert to requests format
        headers = dict(aws_request.headers)
        if data:
            headers['Content-Type'] = 'application/json'
        
        response = requests.request(method, url, headers=headers, data=data, timeout=30)
        return response
    
    def _create_index_if_not_exists(self):
        """Create index with mapping if it doesn't exist"""
        # Check if index exists
        response = self._make_authenticated_request('HEAD', f'/{self.config.opensearch_index}')
        if response.status_code == 404:
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
            
            import json
            response = self._make_authenticated_request('PUT', f'/{self.config.opensearch_index}', json.dumps(mapping))
            if response.status_code == 200:
                logger.info(f"Created OpenSearch index: {self.config.opensearch_index}")
            else:
                logger.error(f"Failed to create index: {response.text}")
    
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
            import json
            bulk_json = '\n'.join([json.dumps(item) for item in bulk_data]) + '\n'
            
            response = self._make_authenticated_request('POST', '/_bulk', bulk_json)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errors'):
                    logger.warning("Some events failed to index")
                    return False
                return True
            else:
                logger.error(f"Failed to index events: {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to index events: {e}")
            return False
    
    def test_connection(self):
        """Test OpenSearch connection"""
        try:
            response = self._make_authenticated_request('GET', '/')
            if response.status_code == 200:
                info = response.json()
                logger.info(f"Connected to OpenSearch: {info.get('version', {}).get('number')}")
                return True
            else:
                logger.error(f"OpenSearch connection test failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"OpenSearch connection test failed: {e}")
            return False

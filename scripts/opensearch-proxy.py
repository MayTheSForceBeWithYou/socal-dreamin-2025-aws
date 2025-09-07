#!/usr/bin/env python3
"""
OpenSearch Dashboards Authentication Proxy
This proxy server handles AWS IAM authentication for OpenSearch Dashboards
and forwards requests to the OpenSearch domain.
"""

import boto3
import requests
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenSearchProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler that proxies requests to OpenSearch with AWS authentication"""
    
    def __init__(self, *args, opensearch_endpoint=None, **kwargs):
        self.opensearch_endpoint = opensearch_endpoint
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        self._proxy_request('GET')
    
    def do_POST(self):
        """Handle POST requests"""
        self._proxy_request('POST')
    
    def do_PUT(self):
        """Handle PUT requests"""
        self._proxy_request('PUT')
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        self._proxy_request('DELETE')
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def _proxy_request(self, method):
        """Proxy the request to OpenSearch with AWS authentication"""
        try:
            # Get request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else None
            
            # Build target URL
            target_url = f"https://{self.opensearch_endpoint}{self.path}"
            
            # Add query parameters
            if self.path and '?' in self.path:
                target_url = f"https://{self.opensearch_endpoint}{self.path}"
            elif hasattr(self, 'query_string') and self.query_string:
                target_url = f"https://{self.opensearch_endpoint}{self.path}?{self.query_string}"
            
            logger.info(f"Proxying {method} {self.path} to {target_url}")
            
            # Create authenticated request
            aws_request = AWSRequest(method=method, url=target_url, data=post_data)
            
            # Get AWS credentials
            session = boto3.Session()
            credentials = session.get_credentials()
            region = session.region_name or 'us-west-1'
            
            # Sign the request
            SigV4Auth(credentials, 'es', region).add_auth(aws_request)
            
            # Prepare headers
            headers = dict(aws_request.headers)
            
            # Copy important headers from original request
            for header in ['Content-Type', 'Accept', 'User-Agent']:
                if header in self.headers:
                    headers[header] = self.headers[header]
            
            # Make the request to OpenSearch
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=post_data,
                timeout=30,
                verify=True
            )
            
            # Send response back to client
            self.send_response(response.status_code)
            
            # Copy response headers
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'transfer-encoding']:
                    self.send_header(header, value)
            
            # Add CORS headers for Dashboards
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            
            self.end_headers()
            
            # Send response body
            if response.content:
                self.wfile.write(response.content)
            
            logger.info(f"Response: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error proxying request: {e}")
            self.send_error(500, f"Proxy error: {str(e)}")

def create_proxy_handler(opensearch_endpoint):
    """Create a proxy handler with the OpenSearch endpoint"""
    def handler(*args, **kwargs):
        return OpenSearchProxyHandler(*args, opensearch_endpoint=opensearch_endpoint, **kwargs)
    return handler

def start_proxy_server(port=8080, opensearch_endpoint=None):
    """Start the proxy server"""
    if not opensearch_endpoint:
        opensearch_endpoint = "vpc-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com"
    
    handler_class = create_proxy_handler(opensearch_endpoint)
    
    server = HTTPServer(('localhost', port), handler_class)
    logger.info(f"Starting OpenSearch proxy server on http://localhost:{port}")
    logger.info(f"Proxying requests to: https://{opensearch_endpoint}")
    logger.info(f"Access Dashboards at: http://localhost:{port}/_dashboards/")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server...")
        server.shutdown()

if __name__ == "__main__":
    import sys
    
    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    start_proxy_server(port)



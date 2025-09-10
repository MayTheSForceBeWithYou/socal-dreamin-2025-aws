#!/usr/bin/env python3
"""
OpenSearch Dashboards Authentication Proxy
This proxy server handles AWS IAM authentication for OpenSearch Dashboards
and forwards requests to the OpenSearch domain.

This version is designed to run on EC2 with IAM role authentication
and accept SSH tunnel connections from local development machines.
"""

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
import requests
import subprocess
import threading
import sys
from urllib.parse import urlparse, parse_qs

# Configure logging with more detail for remote debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/opensearch-proxy.log'),
        logging.StreamHandler()
    ]
)
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
            
            # Add required header for OpenSearch Dashboards
            headers['osd-xsrf'] = 'true'
            
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

def get_opensearch_endpoint():
    """Get OpenSearch endpoint from various sources"""
    # Try environment variable first
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    if endpoint:
        logger.info(f"Using OpenSearch endpoint from environment: {endpoint}")
        return endpoint
    
    # Try config file
    config_file = '/opt/opensearch-proxy/config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                endpoint = config.get('opensearch_endpoint')
                if endpoint:
                    logger.info(f"Using OpenSearch endpoint from config file: {endpoint}")
                    return endpoint
        except Exception as e:
            logger.warning(f"Failed to read config file {config_file}: {e}")
    
    # Try Terraform outputs as fallback (for local development)
    try:
        terraform_dir = Path(__file__).parent.parent / "aws" / "terraform"
        if terraform_dir.exists():
            original_cwd = os.getcwd()
            os.chdir(terraform_dir)
            terraform_outputs = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
            os.chdir(original_cwd)
            
            if terraform_outputs.returncode == 0:
                terraform_outputs = json.loads(terraform_outputs.stdout)
                endpoint = terraform_outputs["opensearch_endpoint"]["value"]
                logger.info(f"Using OpenSearch endpoint from Terraform: {endpoint}")
                return endpoint
    except Exception as e:
        logger.warning(f"Failed to get endpoint from Terraform: {e}")
    
    raise ValueError("No OpenSearch endpoint found. Set OPENSEARCH_ENDPOINT environment variable, create /opt/opensearch-proxy/config.json, or run from Terraform directory")

def start_proxy_server(port=9200, opensearch_endpoint=None, bind_address='0.0.0.0'):
    """Start the proxy server"""
    if not opensearch_endpoint:
        opensearch_endpoint = get_opensearch_endpoint()
    
    handler_class = create_proxy_handler(opensearch_endpoint)
    
    server = HTTPServer((bind_address, port), handler_class)
    logger.info(f"Starting OpenSearch proxy server on http://{bind_address}:{port}")
    logger.info(f"Proxying requests to: https://{opensearch_endpoint}")
    logger.info(f"Access Dashboards at: http://{bind_address}:{port}/_dashboards/")
    logger.info("For SSH tunnel access: ssh -L 8080:localhost:9200 ec2-user@<ec2-ip>")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server...")
        server.shutdown()

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='OpenSearch Proxy Server')
    parser.add_argument('--port', '-p', type=int, default=9200, help='Port to bind to (default: 9200)')
    parser.add_argument('--bind', '-b', default='0.0.0.0', help='Address to bind to (default: 0.0.0.0)')
    parser.add_argument('--endpoint', '-e', help='OpenSearch endpoint override')
    parser.add_argument('--local', action='store_true', help='Run in local mode (bind to localhost only)')
    
    args = parser.parse_args()
    
    # Override bind address for local mode
    bind_address = 'localhost' if args.local else args.bind
    
    logger.info(f"Starting proxy with arguments: port={args.port}, bind={bind_address}, endpoint={args.endpoint}")
    
    try:
        start_proxy_server(port=args.port, opensearch_endpoint=args.endpoint, bind_address=bind_address)
    except Exception as e:
        logger.error(f"Failed to start proxy server: {e}")
        sys.exit(1)



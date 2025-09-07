#!/usr/bin/env python3
"""
OpenSearch Dashboards Authentication Proxy with SSH Tunnel Support
This proxy server handles AWS IAM authentication for OpenSearch Dashboards
and forwards requests through an SSH tunnel to the OpenSearch domain.
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
import subprocess
import time
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenSearchProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler that proxies requests to OpenSearch with AWS authentication"""
    
    def __init__(self, *args, opensearch_endpoint=None, tunnel_port=None, **kwargs):
        self.opensearch_endpoint = opensearch_endpoint
        self.tunnel_port = tunnel_port or 9200
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
            
            # Build target URL - use localhost through SSH tunnel
            target_url = f"https://localhost:{self.tunnel_port}{self.path}"
            
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
            
            # Make the request to OpenSearch through SSH tunnel
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=post_data,
                timeout=30,
                verify=False  # Disable SSL verification for localhost tunnel
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

def create_proxy_handler(opensearch_endpoint, tunnel_port):
    """Create a proxy handler with the OpenSearch endpoint and tunnel port"""
    def handler(*args, **kwargs):
        return OpenSearchProxyHandler(*args, opensearch_endpoint=opensearch_endpoint, tunnel_port=tunnel_port, **kwargs)
    return handler

def start_ssh_tunnel(ec2_ip, tunnel_port=9200):
    """Start SSH tunnel to EC2 instance"""
    logger.info(f"Starting SSH tunnel to {ec2_ip}:{tunnel_port}")
    
    # Kill any existing tunnel on this port
    try:
        subprocess.run(['lsof', '-ti', f':{tunnel_port}', '|', 'xargs', 'kill', '-9'], 
                      shell=True, check=False)
    except:
        pass
    
    # Start SSH tunnel
    ssh_cmd = [
        'ssh', '-N', '-L', f'{tunnel_port}:localhost:9200',
        f'ec2-user@{ec2_ip}', '-o', 'StrictHostKeyChecking=no'
    ]
    
    logger.info(f"Running: {' '.join(ssh_cmd)}")
    tunnel_process = subprocess.Popen(ssh_cmd)
    
    # Wait a moment for tunnel to establish
    time.sleep(3)
    
    return tunnel_process

def start_proxy_server(port=8080, opensearch_endpoint=None, ec2_ip=None, tunnel_port=9200):
    """Start the proxy server with SSH tunnel"""
    if not opensearch_endpoint:
        opensearch_endpoint = "vpc-salesforce-opensearch-lab-os-c35zwrfbfcuzramcu.us-west-1.es.amazonaws.com"
    
    if not ec2_ip:
        logger.error("EC2 IP is required for SSH tunnel")
        return
    
    # Start SSH tunnel
    tunnel_process = start_ssh_tunnel(ec2_ip, tunnel_port)
    
    # Create proxy handler
    handler_class = create_proxy_handler(opensearch_endpoint, tunnel_port)
    
    # Start proxy server
    server = HTTPServer(('localhost', port), handler_class)
    logger.info(f"Starting OpenSearch proxy server on http://localhost:{port}")
    logger.info(f"SSH tunnel established: localhost:{tunnel_port} -> {ec2_ip}:9200")
    logger.info(f"Access Dashboards at: http://localhost:{port}/_dashboards/")
    
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        tunnel_process.terminate()
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server...")
        tunnel_process.terminate()
        server.shutdown()

if __name__ == "__main__":
    import sys
    
    port = 8080
    tunnel_port = 9200
    ec2_ip = None
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        tunnel_port = int(sys.argv[2])
    if len(sys.argv) > 3:
        ec2_ip = sys.argv[3]
    
    if not ec2_ip:
        print("Usage: python3 opensearch-proxy.py [port] [tunnel_port] [ec2_ip]")
        print("Example: python3 opensearch-proxy.py 8080 9200 1.2.3.4")
        sys.exit(1)
    
    start_proxy_server(port, ec2_ip=ec2_ip, tunnel_port=tunnel_port)



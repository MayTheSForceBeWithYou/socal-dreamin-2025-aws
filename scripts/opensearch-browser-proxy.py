#!/usr/bin/env python3
"""
OpenSearch Browser Proxy - Handles AWS SigV4 authentication for browser access
"""

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import sys

class OpenSearchProxyHandler(BaseHTTPRequestHandler):
    def __init__(self, opensearch_endpoint, *args, **kwargs):
        self.opensearch_endpoint = opensearch_endpoint
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def do_PUT(self):
        self._handle_request('PUT')
    
    def do_DELETE(self):
        self._handle_request('DELETE')
    
    def _handle_request(self, method):
        try:
            # Parse the request path
            path = self.path
            if path.startswith('/'):
                path = path[1:]
            
            # Build the target URL
            target_url = f"{self.opensearch_endpoint}/{path}"
            
            # Get request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = None
            if content_length > 0:
                body = self.rfile.read(content_length)
            
            # Create AWS request with minimal headers for signing
            aws_request = AWSRequest(method=method, url=target_url, data=body)
            
            # Only add essential headers for AWS signing
            essential_headers = ['accept', 'content-type', 'user-agent']
            for header in essential_headers:
                if header in self.headers:
                    aws_request.headers[header] = self.headers[header]
            
            # Sign the request
            SigV4Auth(self.credentials, 'es', self.session.region_name or 'us-west-1').add_auth(aws_request)
            
            # Make the request with signed headers
            response = requests.request(
                method=method,
                url=target_url,
                headers=dict(aws_request.headers),
                data=body,
                timeout=30
            )
            
            # Send response back to browser
            self.send_response(response.status_code)
            
            # Copy response headers
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'transfer-encoding']:
                    self.send_header(header, value)
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.content)
            
        except Exception as e:
            self.send_error(500, f"Proxy error: {str(e)}")
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 opensearch-browser-proxy.py <opensearch_endpoint> <port>")
        print("Example: python3 opensearch-browser-proxy.py https://search-domain.us-west-1.es.amazonaws.com 8080")
        sys.exit(1)
    
    opensearch_endpoint = sys.argv[1]
    port = int(sys.argv[2])
    
    print(f"Starting OpenSearch Browser Proxy...")
    print(f"OpenSearch Endpoint: {opensearch_endpoint}")
    print(f"Proxy Port: {port}")
    print(f"Browser URL: http://localhost:{port}/_dashboards/")
    print("Press Ctrl+C to stop")
    
    # Create handler class with endpoint
    handler = lambda *args, **kwargs: OpenSearchProxyHandler(opensearch_endpoint, *args, **kwargs)
    
    # Start server
    server = HTTPServer(('localhost', port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down proxy...")
        server.shutdown()

if __name__ == "__main__":
    main()

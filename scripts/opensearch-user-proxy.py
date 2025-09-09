#!/usr/bin/env python3
"""
OpenSearch User Proxy - Handles OpenSearch user authentication for browser access
"""

import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import sys
import os
import base64
from datetime import datetime
from pathlib import Path
import subprocess

class OpenSearchUserProxyHandler(BaseHTTPRequestHandler):
    def __init__(self, opensearch_endpoint, username, password, *args, **kwargs):
        self.opensearch_endpoint = opensearch_endpoint.rstrip('/')
        self.username = username
        self.password = password
        # Create basic auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def do_PUT(self):
        self._handle_request('PUT')
    
    def do_DELETE(self):
        self._handle_request('DELETE')
    
    def do_HEAD(self):
        self._handle_request('HEAD')
    
    def _handle_request(self, method):
        try:
            # Parse the request path
            path = self.path
            if not path.startswith('/'):
                path = '/' + path
            
            # Build the target URL
            target_url = f"{self.opensearch_endpoint}{path}"
            
            print(f"{datetime.now().isoformat()} {method} {path}")
            
            # Get request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = b''
            if content_length > 0:
                body = self.rfile.read(content_length)
            
            # Prepare headers for the request
            headers = {
                'Authorization': self.auth_header,
                'Content-Type': self.headers.get('content-type', 'application/json'),
                'osd-xsrf': 'true'
            }
            
            # Make the actual request with OpenSearch user authentication
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=30,
                verify=True,
                allow_redirects=False
            )
            
            # Send response back to browser
            self.send_response(response.status_code)
            
            # Copy response headers, filtering out problematic ones
            excluded_headers = {
                'content-encoding', 'transfer-encoding', 'connection', 
                'server', 'date', 'content-length'
            }
            
            for header, value in response.headers.items():
                if header.lower() not in excluded_headers:
                    self.send_header(header, value)
            
            # Always set content-length for the actual response
            if response.content:
                self.send_header('Content-Length', str(len(response.content)))
            
            # Add CORS headers for browser compatibility
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, HEAD, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, osd-xsrf')
            self.send_header('osd-xsrf', 'true')
            
            self.end_headers()
            
            # Send response body (except for HEAD requests)
            if method != 'HEAD' and response.content:
                self.wfile.write(response.content)
            
        except Exception as e:
            print(f"Proxy error: {str(e)}")
            error_response = {
                "error": "Proxy Error",
                "message": str(e),
                "path": self.path
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', '0')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Custom logging
        timestamp = datetime.now().isoformat()
        print(f"{timestamp} {format % args}")

def get_terraform_output(output_name):
    """Get a Terraform output value."""
    try:
        # Change to terraform directory
        terraform_dir = Path(__file__).parent.parent / "aws" / "terraform"

        # Get the output value
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ Failed to get Terraform output '{output_name}': {result.stderr}")
            return None

    except Exception as e:
        print(f"❌ Error getting Terraform output '{output_name}': {e}")
        return None

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print("Usage: python3 opensearch-user-proxy.py <port> [username] [password]")
        print("Example: python3 opensearch-user-proxy.py 8080")
        print("If username/password not provided, will get from Terraform outputs")
        sys.exit(0)
    
    port = int(sys.argv[1])
    
    # Get OpenSearch endpoint from Terraform outputs
    opensearch_endpoint = get_terraform_output("opensearch_endpoint")
    if not opensearch_endpoint:
        print("❌ Could not get OpenSearch endpoint from Terraform outputs")
        print("Make sure Terraform has been applied successfully")
        sys.exit(1)
    
    # Ensure endpoint has https:// scheme
    if not opensearch_endpoint.startswith("https://"):
        opensearch_endpoint = f"https://{opensearch_endpoint}"
    
    # Get username and password
    if len(sys.argv) >= 4:
        username = sys.argv[2]
        password = sys.argv[3]
    else:
        # Get from Terraform outputs
        username = get_terraform_output("opensearch_master_user")
        password = get_terraform_output("opensearch_master_password")
        
        if not username or not password:
            print("❌ Could not get OpenSearch credentials from Terraform outputs")
            print("Make sure Terraform has been applied successfully")
            sys.exit(1)
    
    print(f"Starting OpenSearch User Proxy...")
    print(f"OpenSearch Endpoint: {opensearch_endpoint}")
    print(f"Username: {username}")
    print(f"Proxy Port: {port}")
    print(f"Browser URL: http://localhost:{port}/_dashboards/")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    # Create handler class with endpoint and credentials
    handler = lambda *args, **kwargs: OpenSearchUserProxyHandler(opensearch_endpoint, username, password, *args, **kwargs)
    
    # Start server
    server = HTTPServer(('localhost', port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down proxy...")
        server.shutdown()

if __name__ == "__main__":
    main()

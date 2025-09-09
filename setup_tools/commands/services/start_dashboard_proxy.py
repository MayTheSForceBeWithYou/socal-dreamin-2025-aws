#!/usr/bin/env python3
"""
OpenSearch Dashboard Proxy Server
Provides secure access to OpenSearch Dashboards with authentication
"""

import os
import sys
import json
import time
import base64
import threading
from pathlib import Path
from typing import Dict, Optional
import click
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from rich.console import Console
from rich.panel import Panel

console = Console()


class OpenSearchProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler for OpenSearch proxy requests."""
    
    def __init__(self, opensearch_endpoint: str, username: str, password: str, *args, **kwargs):
        self.opensearch_endpoint = opensearch_endpoint
        self.username = username
        self.password = password
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
    
    def do_OPTIONS(self):
        self._handle_request('OPTIONS')
    
    def _handle_request(self, method: str):
        """Handle HTTP requests and proxy to OpenSearch."""
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
            
            # Create basic auth header
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Prepare headers
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json',
                'User-Agent': 'OpenSearch-Proxy/1.0'
            }
            
            # Copy relevant headers from original request
            relevant_headers = ['accept', 'accept-encoding', 'accept-language', 'cache-control']
            for header in relevant_headers:
                if header in self.headers:
                    headers[header] = self.headers[header]
            
            # Make the request to OpenSearch
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=30,
                verify=True
            )
            
            # Send response back to browser
            self.send_response(response.status_code)
            
            # Copy response headers
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                    self.send_header(header, value)
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.content)
            
        except requests.exceptions.RequestException as e:
            self.send_error(502, f"Proxy error: {str(e)}")
        except Exception as e:
            self.send_error(500, f"Internal error: {str(e)}")
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class OpenSearchProxyServer:
    """OpenSearch Dashboard Proxy Server."""
    
    def __init__(self, opensearch_endpoint: str, username: str, password: str, port: int = 8080):
        self.opensearch_endpoint = opensearch_endpoint
        self.username = username
        self.password = password
        self.port = port
        self.server = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the proxy server."""
        try:
            # Create handler class with endpoint and credentials
            handler = lambda *args, **kwargs: OpenSearchProxyHandler(
                self.opensearch_endpoint, self.username, self.password, *args, **kwargs
            )
            
            # Start server
            self.server = HTTPServer(('localhost', self.port), handler)
            self.running = True
            
            console.print(f"[green]✅ OpenSearch proxy started on port {self.port}[/green]")
            console.print(f"[blue]📊 Dashboard URL: http://localhost:{self.port}/_dashboards/[/blue]")
            console.print(f"[yellow]🔐 Authenticated as: {self.username}[/yellow]")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]")
            
            # Start server in a separate thread
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to start proxy server: {e}[/red]")
            return False
    
    def stop(self):
        """Stop the proxy server."""
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            console.print("[yellow]🛑 Proxy server stopped[/yellow]")


def get_opensearch_credentials() -> tuple[str, str]:
    """Get OpenSearch credentials from Terraform outputs."""
    try:
        # Get Terraform outputs
        terraform_dir = Path(__file__).parent.parent.parent.parent / "aws" / "terraform"
        os.chdir(terraform_dir)
        
        result = subprocess.run(
            ["terraform", "output", "-json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            console.print("[red]❌ Failed to get Terraform outputs[/red]")
            return None, None
        
        outputs = json.loads(result.stdout)
        endpoint = outputs.get("opensearch_endpoint", {}).get("value")
        password = outputs.get("opensearch_master_password", {}).get("value")
        
        return endpoint, password
        
    except Exception as e:
        console.print(f"[red]❌ Error getting credentials: {e}[/red]")
        return None, None
    finally:
        # Return to original directory
        os.chdir(Path(__file__).parent.parent.parent.parent)


@click.command()
@click.option('--port', default=8080, help='Port for the proxy server')
@click.option('--endpoint', help='OpenSearch endpoint (auto-detected if not provided)')
@click.option('--username', default='os_admin', help='OpenSearch username')
@click.option('--password', help='OpenSearch password (auto-detected if not provided)')
def start_dashboard_proxy(port: int, endpoint: Optional[str], username: str, password: Optional[str]):
    """Start OpenSearch Dashboard proxy server."""
    
    console.print(Panel(
        "🔐 OpenSearch Dashboard Proxy Server\n"
        "Provides secure access to OpenSearch Dashboards",
        title="Dashboard Proxy",
        border_style="blue"
    ))
    
    # Get credentials if not provided
    if not endpoint or not password:
        console.print("[yellow]🔍 Auto-detecting OpenSearch credentials...[/yellow]")
        detected_endpoint, detected_password = get_opensearch_credentials()
        
        if not endpoint:
            endpoint = detected_endpoint
        if not password:
            password = detected_password
    
    if not endpoint or not password:
        console.print("[red]❌ Could not determine OpenSearch credentials[/red]")
        console.print("[yellow]Please provide --endpoint and --password options[/yellow]")
        return
    
    # Validate endpoint format
    if not endpoint.startswith('https://'):
        endpoint = f"https://{endpoint}"
    
    console.print(f"[blue]📊 OpenSearch Endpoint: {endpoint}[/blue]")
    console.print(f"[blue]👤 Username: {username}[/blue]")
    console.print(f"[blue]🔐 Password: {'*' * len(password)}[/blue]")
    
    # Test connection
    console.print("[yellow]🔍 Testing connection...[/yellow]")
    try:
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        response = requests.get(
            endpoint,
            headers={'Authorization': f'Basic {encoded_credentials}'},
            timeout=10
        )
        
        if response.status_code == 200:
            console.print("[green]✅ Connection test successful[/green]")
        else:
            console.print(f"[red]❌ Connection test failed: {response.status_code}[/red]")
            return
            
    except Exception as e:
        console.print(f"[red]❌ Connection test failed: {e}[/red]")
        return
    
    # Start proxy server
    proxy = OpenSearchProxyServer(endpoint, username, password, port)
    
    try:
        if proxy.start():
            # Keep running until interrupted
            while proxy.running:
                time.sleep(1)
        else:
            console.print("[red]❌ Failed to start proxy server[/red]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Shutting down proxy server...[/yellow]")
        proxy.stop()
    except Exception as e:
        console.print(f"[red]❌ Proxy server error: {e}[/red]")
        proxy.stop()


if __name__ == "__main__":
    start_dashboard_proxy()

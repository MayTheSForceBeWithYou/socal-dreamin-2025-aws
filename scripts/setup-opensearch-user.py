#!/usr/bin/env python3
"""
Create OpenSearch User for Dashboard Access
"""

import requests
import json
import base64
import sys
import subprocess
import os
from pathlib import Path

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

def create_opensearch_user():
    # Get OpenSearch endpoint from Terraform outputs
    endpoint = get_terraform_output("opensearch_endpoint")
    if not endpoint:
        print("❌ Could not get OpenSearch endpoint from Terraform outputs")
        print("Make sure Terraform has been applied successfully")
        return False
    
    # Ensure endpoint has https:// scheme
    if not endpoint.startswith("https://"):
        endpoint = f"https://{endpoint}"
    
    # Get OpenSearch master password from Terraform outputs
    password = get_terraform_output("opensearch_master_password")
    if not password:
        print("❌ Could not get OpenSearch master password from Terraform outputs")
        print("Make sure Terraform has been applied successfully")
        return False
    
    # Get OpenSearch master username from Terraform outputs
    username = get_terraform_output("opensearch_master_user")
    if not username:
        print("❌ Could not get OpenSearch master username from Terraform outputs")
        print("Make sure Terraform has been applied successfully")
        return False
    
    print("🔧 Setting up OpenSearch User Credentials")
    print("=" * 50)
    print(f"Endpoint: {endpoint}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print("")
    
    # Test the credentials
    print("Testing credentials...")
    
    # Create basic auth header
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test basic connectivity
        response = requests.get(f"{endpoint}/", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Credentials are working!")
            print("")
            print("🚀 Login to OpenSearch Dashboards:")
            print(f"URL: {endpoint}/_dashboards/")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print("")
            print("📝 Note: You can change the password in the OpenSearch Dashboards")
            print("   once you're logged in by going to Security → Internal Users")
            return True
        else:
            print(f"❌ Authentication failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = create_opensearch_user()
    sys.exit(0 if success else 1)

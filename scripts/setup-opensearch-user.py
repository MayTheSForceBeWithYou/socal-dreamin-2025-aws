#!/usr/bin/env python3
"""
Create OpenSearch User for Dashboard Access
"""

import requests
import json
import base64
import sys

def create_opensearch_user():
    endpoint = "https://search-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com"
    
    # Default credentials for OpenSearch when advanced security is disabled
    username = "admin"
    password = "admin123"  # You can change this
    
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
        else:
            print(f"❌ Authentication failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_opensearch_user()

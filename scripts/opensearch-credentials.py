#!/usr/bin/env python3
"""
Reset OpenSearch User Password
"""

import requests
import json
import base64
import sys

def reset_opensearch_password():
    endpoint = "https://search-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com"
    
    print("🔧 OpenSearch User Credentials")
    print("=" * 50)
    print(f"Endpoint: {endpoint}")
    print("")
    
    print("📝 Try these credentials in the login screen:")
    print("")
    print("Option 1:")
    print("  Username: admin")
    print("  Password: admin")
    print("")
    print("Option 2:")
    print("  Username: admin") 
    print("  Password: password")
    print("")
    print("Option 3:")
    print("  Username: (leave blank)")
    print("  Password: (leave blank)")
    print("")
    print("Option 4:")
    print("  Username: opensearch")
    print("  Password: opensearch")
    print("")
    
    print("🚀 If none of these work:")
    print("1. Try accessing the OpenSearch API directly:")
    print(f"   curl -X GET '{endpoint}/'")
    print("")
    print("2. Check if there's a 'Forgot Password' link on the login page")
    print("")
    print("3. Contact AWS Support to reset the OpenSearch domain")

if __name__ == "__main__":
    reset_opensearch_password()

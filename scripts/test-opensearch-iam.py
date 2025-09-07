#!/usr/bin/env python3
"""
Test OpenSearch IAM Authentication using boto3 and requests
This script demonstrates how to make authenticated requests to OpenSearch using IAM credentials
"""

import boto3
import requests
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def make_authenticated_request(method, url, data=None):
    """Make an authenticated request to OpenSearch using AWS SigV4"""
    # Create AWS request
    aws_request = AWSRequest(method=method, url=url, data=data)
    
    # Get credentials from boto3 session
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Sign the request
    region = session.region_name or 'us-west-1'  # Default to us-west-1 if region is None
    SigV4Auth(credentials, 'es', region).add_auth(aws_request)
    
    # Convert to requests format
    headers = dict(aws_request.headers)
    if data:
        headers['Content-Type'] = 'application/json'
    
    # Make the request
    response = requests.request(method, url, headers=headers, data=data, timeout=30)
    return response

def test_opensearch_access():
    """Test various OpenSearch endpoints with IAM authentication"""
    
    # Get OpenSearch endpoint from environment or hardcode for testing
    opensearch_endpoint = "https://vpc-salesforce-opensearch-lab-os-c35zwrfbfcuzrmqgcinxframcu.us-west-1.es.amazonaws.com"
    
    print(f"Testing OpenSearch IAM Authentication")
    print(f"Endpoint: {opensearch_endpoint}")
    print("=" * 60)
    
    # Test 1: Basic cluster info
    print("\n1. Testing basic cluster info...")
    try:
        response = make_authenticated_request('GET', f"{opensearch_endpoint}/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS: Basic cluster access working")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Cluster health
    print("\n2. Testing cluster health...")
    try:
        response = make_authenticated_request('GET', f"{opensearch_endpoint}/_cluster/health")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS: Cluster health access working")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: List indices
    print("\n3. Testing indices listing...")
    try:
        response = make_authenticated_request('GET', f"{opensearch_endpoint}/_cat/indices?v")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS: Indices listing working")
            print(f"Response:\n{response.text}")
        else:
            print(f"❌ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: Dashboards access
    print("\n4. Testing Dashboards access...")
    try:
        response = make_authenticated_request('GET', f"{opensearch_endpoint}/_dashboards/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS: Dashboards access working")
            print("Dashboards are accessible via IAM authentication")
        else:
            print(f"❌ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 5: Create a test index
    print("\n5. Testing index creation...")
    try:
        test_index = "test-iam-access"
        response = make_authenticated_request('PUT', f"{opensearch_endpoint}/{test_index}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS: Index creation working")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            # Clean up - delete the test index
            delete_response = make_authenticated_request('DELETE', f"{opensearch_endpoint}/{test_index}")
            if delete_response.status_code == 200:
                print("✅ Test index cleaned up successfully")
        else:
            print(f"❌ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_opensearch_access()

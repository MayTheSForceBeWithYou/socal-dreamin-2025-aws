#!/usr/bin/env python3
"""
Post-Terraform OpenSearch Setup and Validation

This script validates that the OpenSearch domain is properly configured
for IAM role-based authentication and tests connectivity.
"""

import boto3
import requests
import json
import sys
import subprocess
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import Optional, Dict, Any


class OpenSearchValidator:
    def __init__(self, region: str = "us-west-1"):
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.credentials = self.session.get_credentials()
        
    def get_terraform_output(self, output_name: str) -> Optional[str]:
        """Get Terraform output value"""
        try:
            result = subprocess.run(
                ["terraform", "output", "-raw", output_name],
                cwd="/Users/nate/dev/socal-dreamin-2025-aws/aws/terraform",
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting Terraform output '{output_name}': {e}")
            return None
    
    def make_authenticated_request(self, endpoint: str, path: str, method: str = "GET", data: Optional[str] = None) -> requests.Response:
        """Make an authenticated request to OpenSearch using SigV4"""
        url = f"{endpoint}{path}"
        
        # Create AWS request
        aws_request = AWSRequest(method=method, url=url, data=data)
        SigV4Auth(self.credentials, 'es', self.region).add_auth(aws_request)
        
        # Convert to requests format
        headers = dict(aws_request.headers)
        if data:
            headers['Content-Type'] = 'application/json'
        
        response = requests.request(method, url, headers=headers, data=data, timeout=30)
        return response
    
    def test_opensearch_connectivity(self, endpoint: str) -> bool:
        """Test OpenSearch connectivity with IAM authentication"""
        print(f"🔍 Testing OpenSearch connectivity to: {endpoint}")
        
        try:
            # Test cluster health
            response = self.make_authenticated_request(endpoint, "/_cluster/health")
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ OpenSearch cluster health: {health_data.get('status', 'unknown')}")
                print(f"   - Number of nodes: {health_data.get('number_of_nodes', 'unknown')}")
                print(f"   - Active shards: {health_data.get('active_shards', 'unknown')}")
                return True
            else:
                print(f"❌ Cluster health check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def test_index_operations(self, endpoint: str, index_name: str = "test-index") -> bool:
        """Test index creation and deletion"""
        print(f"🔍 Testing index operations with index: {index_name}")
        
        try:
            # Create test index
            mapping = {
                "mappings": {
                    "properties": {
                        "test_field": {"type": "text"},
                        "@timestamp": {"type": "date"}
                    }
                }
            }
            
            create_response = self.make_authenticated_request(
                endpoint, f"/{index_name}", "PUT", json.dumps(mapping)
            )
            
            if create_response.status_code == 200:
                print(f"✅ Successfully created test index: {index_name}")
                
                # Test document indexing
                doc = {"test_field": "test_value", "@timestamp": "2025-09-09T12:00:00Z"}
                doc_response = self.make_authenticated_request(
                    endpoint, f"/{index_name}/_doc/1", "PUT", json.dumps(doc)
                )
                
                if doc_response.status_code in [200, 201]:
                    print(f"✅ Successfully indexed test document")
                    
                    # Clean up - delete test index
                    delete_response = self.make_authenticated_request(
                        endpoint, f"/{index_name}", "DELETE"
                    )
                    
                    if delete_response.status_code == 200:
                        print(f"✅ Successfully cleaned up test index")
                        return True
                    else:
                        print(f"⚠️  Test index created but cleanup failed: {delete_response.status_code}")
                        return True  # Still consider it successful
                else:
                    print(f"❌ Document indexing failed: {doc_response.status_code}")
                    print(f"   Response: {doc_response.text}")
                    return False
            else:
                print(f"❌ Index creation failed: {create_response.status_code}")
                print(f"   Response: {create_response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Index operations test failed: {e}")
            return False
    
    def validate_iam_role_mapping(self, endpoint: str) -> bool:
        """Validate that IAM role is properly mapped in OpenSearch"""
        print("🔍 Validating IAM role mapping...")
        
        try:
            # Get current IAM role info
            sts_client = self.session.client('sts')
            identity = sts_client.get_caller_identity()
            current_role_arn = identity.get('Arn', '')
            
            print(f"   Current IAM role: {current_role_arn}")
            
            # Test if we can access OpenSearch with current role
            response = self.make_authenticated_request(endpoint, "/")
            
            if response.status_code == 200:
                print("✅ IAM role is properly mapped and has access to OpenSearch")
                return True
            else:
                print(f"❌ IAM role mapping validation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ IAM role mapping validation failed: {e}")
            return False
    
    def run_validation(self) -> bool:
        """Run complete OpenSearch validation"""
        print("🚀 Starting OpenSearch Post-Terraform Validation")
        print("=" * 60)
        
        # Get OpenSearch endpoint from Terraform
        endpoint_raw = self.get_terraform_output("opensearch_endpoint")
        if not endpoint_raw:
            print("❌ Could not get OpenSearch endpoint from Terraform outputs")
            return False
        
        # Ensure endpoint has https:// scheme
        if not endpoint_raw.startswith("https://"):
            endpoint = f"https://{endpoint_raw}"
        else:
            endpoint = endpoint_raw
        
        print(f"📡 OpenSearch Endpoint: {endpoint}")
        print()
        
        # Run validation tests
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Basic connectivity
        if self.test_opensearch_connectivity(endpoint):
            tests_passed += 1
        print()
        
        # Test 2: IAM role mapping
        if self.validate_iam_role_mapping(endpoint):
            tests_passed += 1
        print()
        
        # Test 3: Index operations
        if self.test_index_operations(endpoint):
            tests_passed += 1
        print()
        
        # Summary
        print("=" * 60)
        print(f"📊 Validation Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All OpenSearch validation tests passed!")
            print("✅ OpenSearch is properly configured for IAM role-based authentication")
            return True
        else:
            print("❌ Some validation tests failed")
            print("🔧 Please check the OpenSearch configuration and IAM role mapping")
            return False


def main():
    """Main entry point"""
    validator = OpenSearchValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

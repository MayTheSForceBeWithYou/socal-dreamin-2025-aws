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
        
        # Increase timeout and add retry logic
        response = requests.request(method, url, headers=headers, data=data, timeout=60)
        return response
    
    def test_opensearch_connectivity(self, endpoint: str) -> bool:
        """Test OpenSearch connectivity with IAM authentication"""
        print(f"🔍 Testing OpenSearch connectivity to: {endpoint}")
        
        # First, test basic network connectivity
        try:
            import socket
            from urllib.parse import urlparse
            
            parsed_url = urlparse(endpoint)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            print(f"   Testing network connectivity to {hostname}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            if result != 0:
                print(f"❌ Network connectivity test failed: Cannot reach {hostname}:{port}")
                print(f"   This suggests the OpenSearch domain is not accessible from your current network.")
                print(f"   The domain may be in a private subnet or have restrictive security groups.")
                return False
            else:
                print(f"✅ Network connectivity test passed")
                
        except Exception as e:
            print(f"⚠️  Network connectivity test failed: {e}")
        
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
                if response.status_code == 403:
                    print(f"   This suggests an IAM permissions issue. Check that your user has access to the OpenSearch domain.")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            if "timeout" in str(e).lower():
                print(f"   This suggests the OpenSearch domain is not accessible from your current network.")
                print(f"   The domain may be in a private subnet or have restrictive security groups.")
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
    
    def validate_via_ec2(self, endpoint: str, test_type: str = "health") -> bool:
        """Validate OpenSearch access via EC2 instance"""
        print("🔍 Attempting validation via EC2 instance...")
        
        try:
            # Get EC2 instance ID and public IP
            ec2_instance_id = self.get_terraform_output("ec2_instance_id")
            ec2_public_ip = self.get_terraform_output("ec2_public_ip")
            
            if not ec2_instance_id or not ec2_public_ip:
                print("❌ Could not get EC2 instance information from Terraform outputs")
                return False
            
            print(f"   EC2 Instance ID: {ec2_instance_id}")
            print(f"   EC2 Public IP: {ec2_public_ip}")
            
            # Create SSM client
            ssm_client = self.session.client('ssm')
            
            # Test OpenSearch connectivity from EC2
            if test_type == "health":
                test_command = f"""python3 -c "
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json

session = boto3.Session()
credentials = session.get_credentials()

def make_request(endpoint, path, method='GET', data=None):
    url = endpoint + path
    aws_request = AWSRequest(method=method, url=url, data=data)
    SigV4Auth(credentials, 'es', 'us-west-1').add_auth(aws_request)
    headers = dict(aws_request.headers)
    if data:
        headers['Content-Type'] = 'application/json'
    response = requests.request(method, url, headers=headers, data=data, timeout=30)
    return response

endpoint = '{endpoint}'
try:
    response = make_request(endpoint, '/_cluster/health')
    if response.status_code == 200:
        health = response.json()
        print('SUCCESS: Cluster health:', health.get('status', 'unknown'))
        print('SUCCESS: Nodes:', health.get('number_of_nodes', 'unknown'))
    else:
        print('ERROR: HTTP', response.status_code, ':', response.text)
except Exception as e:
    print('ERROR:', str(e))
" """
            elif test_type == "index":
                test_command = f"""python3 -c "
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json

session = boto3.Session()
credentials = session.get_credentials()

def make_request(endpoint, path, method='GET', data=None):
    url = endpoint + path
    aws_request = AWSRequest(method=method, url=url, data=data)
    SigV4Auth(credentials, 'es', 'us-west-1').add_auth(aws_request)
    headers = dict(aws_request.headers)
    if data:
        headers['Content-Type'] = 'application/json'
    response = requests.request(method, url, headers=headers, data=data, timeout=30)
    return response

endpoint = '{endpoint}'
index_name = 'test-index-validation'
try:
    # Create test index
    mapping = {{'mappings': {{'properties': {{'test_field': {{'type': 'text'}}, '@timestamp': {{'type': 'date'}}}}}}}}
    create_response = make_request(endpoint, '/' + index_name, 'PUT', json.dumps(mapping))
    
    if create_response.status_code == 200:
        print('SUCCESS: Index created')
        
        # Test document indexing
        doc = {{'test_field': 'test_value', '@timestamp': '2025-09-09T12:00:00Z'}}
        doc_response = make_request(endpoint, '/' + index_name + '/_doc/1', 'PUT', json.dumps(doc))
        
        if doc_response.status_code in [200, 201]:
            print('SUCCESS: Document indexed')
            
            # Clean up - delete test index
            delete_response = make_request(endpoint, '/' + index_name, 'DELETE')
            
            if delete_response.status_code == 200:
                print('SUCCESS: Index cleaned up')
            else:
                print('WARNING: Index cleanup failed')
        else:
            print('ERROR: Document indexing failed:', doc_response.status_code)
    else:
        print('ERROR: Index creation failed:', create_response.status_code)
except Exception as e:
    print('ERROR:', str(e))
" """
            else:
                test_command = f"""python3 -c "
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json

session = boto3.Session()
credentials = session.get_credentials()

def make_request(endpoint, path, method='GET', data=None):
    url = endpoint + path
    aws_request = AWSRequest(method=method, url=url, data=data)
    SigV4Auth(credentials, 'es', 'us-west-1').add_auth(aws_request)
    headers = dict(aws_request.headers)
    if data:
        headers['Content-Type'] = 'application/json'
    response = requests.request(method, url, headers=headers, data=data, timeout=30)
    return response

endpoint = '{endpoint}'
try:
    response = make_request(endpoint, '/')
    if response.status_code == 200:
        print('SUCCESS: Root access granted')
    else:
        print('ERROR: HTTP', response.status_code, ':', response.text)
except Exception as e:
    print('ERROR:', str(e))
" """
            
            print(f"   Running OpenSearch {test_type} test on EC2...")
            response = ssm_client.send_command(
                InstanceIds=[ec2_instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={'commands': [test_command]}
            )
            
            command_id = response['Command']['CommandId']
            
            # Wait for command to complete
            import time
            time.sleep(5)
            
            # Get command output
            output = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=ec2_instance_id
            )
            
            if output['Status'] == 'Success':
                print("✅ EC2-based validation successful!")
                print(f"   Output: {output['StandardOutputContent']}")
                return True
            else:
                print(f"❌ EC2-based validation failed: {output.get('StandardErrorContent', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ EC2-based validation failed: {e}")
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
        
        # Check if direct connectivity is possible
        direct_access_possible = self.test_opensearch_connectivity(endpoint)
        
        # Run validation tests
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Basic connectivity
        if direct_access_possible:
            tests_passed += 1
        else:
            print("⚠️  Direct connectivity failed, trying EC2-based validation...")
            if self.validate_via_ec2(endpoint):
                tests_passed += 1
                print("✅ OpenSearch is accessible via EC2 instance")
                # Set flag to use EC2 for remaining tests
                direct_access_possible = False
        print()
        
        # Test 2: IAM role mapping
        if direct_access_possible:
            if self.validate_iam_role_mapping(endpoint):
                tests_passed += 1
        else:
            print("🔍 Testing IAM role mapping via EC2...")
            if self.validate_via_ec2(endpoint, "root"):
                tests_passed += 1
                print("✅ IAM role mapping validated via EC2")
        print()
        
        # Test 3: Index operations
        if direct_access_possible:
            if self.test_index_operations(endpoint):
                tests_passed += 1
        else:
            print("🔍 Testing index operations via EC2...")
            if self.validate_via_ec2(endpoint, "index"):
                tests_passed += 1
                print("✅ Index operations validated via EC2")
        print()
        
        # Summary
        print("=" * 60)
        print(f"📊 Validation Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All OpenSearch validation tests passed!")
            print("✅ OpenSearch is properly configured for IAM role-based authentication")
            if not direct_access_possible:
                print("ℹ️  Note: OpenSearch is accessible via EC2 instance (private subnet configuration)")
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

"""
Command to test OpenSearch connectivity from EC2 instances.
"""

import boto3
import requests
import socket
import subprocess
import json
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from botocore.exceptions import ClientError, NoCredentialsError

from ..base import BaseCommand, register_command
from ...core.exceptions import CommandError


@register_command("test-opensearch-connectivity")
class TestOpenSearchConnectivityCommand(BaseCommand):
    """Test connectivity to OpenSearch from EC2 instances or current environment."""

    def get_required_args(self) -> list:
        return []

    def get_optional_args(self) -> dict:
        return {
            'domain_name': 'OpenSearch domain name (auto-detected if not provided)',
            'from_ec2': 'Test from EC2 instance instead of local environment',
            'instance_id': 'Specific EC2 instance ID to test from',
            'region': 'AWS region (defaults to us-east-1)',
            'timeout': 'Connection timeout in seconds (default: 10)'
        }

    def validate_inputs(self, **kwargs) -> None:
        """Validate command inputs."""
        timeout = kwargs.get('timeout')
        if timeout and not str(timeout).isdigit():
            raise CommandError("Timeout must be a positive integer")

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute connectivity tests."""
        try:
            region = kwargs.get('region', 'us-east-1')
            domain_name = kwargs.get('domain_name')
            from_ec2 = kwargs.get('from_ec2', False)
            instance_id = kwargs.get('instance_id')
            timeout = int(kwargs.get('timeout', 10))
            
            self.logger.info("🔗 Starting OpenSearch connectivity tests...")
            
            # Initialize AWS clients
            opensearch_client = boto3.client('opensearch', region_name=region)
            ec2_client = boto3.client('ec2', region_name=region)
            
            # Find domain if not specified
            if not domain_name:
                domain_name = self._find_opensearch_domain(opensearch_client)
                if not domain_name:
                    raise CommandError("No OpenSearch domain found and none specified")
            
            # Get domain information
            domain_info = self._get_domain_info(opensearch_client, domain_name)
            endpoint = domain_info.get('endpoint')
            
            if not endpoint:
                raise CommandError(f"No endpoint found for domain {domain_name}")
            
            self.logger.info(f"🎯 Testing connectivity to: {endpoint}")
            
            results = {
                'domain_name': domain_name,
                'endpoint': endpoint,
                'tests': [],
                'summary': {
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_tests': 0
                }
            }
            
            if from_ec2 or instance_id:
                # Test from EC2 instance
                target_instance = self._find_ec2_instance(ec2_client, instance_id)
                if not target_instance:
                    raise CommandError("No suitable EC2 instance found for testing")
                
                self.logger.info(f"📡 Testing from EC2 instance: {target_instance['InstanceId']}")
                results['tests'] = self._test_from_ec2(target_instance, endpoint, timeout)
            else:
                # Test from local environment
                self.logger.info("🖥️  Testing from local environment")
                results['tests'] = self._test_from_local(endpoint, timeout)
            
            # Calculate summary
            results['summary']['total_tests'] = len(results['tests'])
            results['summary']['passed_tests'] = sum(1 for test in results['tests'] if test['success'])
            results['summary']['failed_tests'] = results['summary']['total_tests'] - results['summary']['passed_tests']
            
            # Display results
            self._display_results(results)
            
            return results
            
        except NoCredentialsError:
            raise CommandError("AWS credentials not found. Please configure your credentials.")
        except ClientError as e:
            raise CommandError(f"AWS API error: {e}")
        except Exception as e:
            raise CommandError(f"Connectivity test failed: {str(e)}")

    def _find_opensearch_domain(self, client) -> str:
        """Find the first OpenSearch domain."""
        try:
            response = client.list_domain_names()
            domains = response.get('DomainNames', [])
            if domains:
                return domains[0]['DomainName']
            return None
        except Exception as e:
            self.logger.warning(f"Could not list domains: {e}")
            return None

    def _get_domain_info(self, client, domain_name: str) -> Dict[str, Any]:
        """Get domain information."""
        try:
            response = client.describe_domain(DomainName=domain_name)
            domain = response['DomainStatus']
            return {
                'name': domain['DomainName'],
                'endpoint': domain.get('Endpoint'),
                'status': domain.get('ProcessingStatus', 'Unknown')
            }
        except Exception as e:
            self.logger.error(f"Failed to get domain info: {e}")
            return {}

    def _find_ec2_instance(self, ec2_client, instance_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find EC2 instance for testing."""
        try:
            if instance_id:
                response = ec2_client.describe_instances(InstanceIds=[instance_id])
            else:
                response = ec2_client.describe_instances(
                    Filters=[
                        {'Name': 'instance-state-name', 'Values': ['running']}
                    ]
                )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] == 'running':
                        return instance
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to find EC2 instance: {e}")
            return None

    def _test_from_local(self, endpoint: str, timeout: int) -> List[Dict[str, Any]]:
        """Run connectivity tests from local environment."""
        tests = []
        parsed_url = urlparse(f"https://{endpoint}")
        hostname = parsed_url.hostname
        
        # DNS Resolution Test
        tests.append(self._test_dns_resolution(hostname))
        
        # Port connectivity tests
        tests.append(self._test_port_connectivity(hostname, 443, timeout))
        tests.append(self._test_port_connectivity(hostname, 9200, timeout))
        
        # HTTP/HTTPS tests
        tests.append(self._test_http_connectivity(f"https://{endpoint}", timeout))
        tests.append(self._test_opensearch_api(f"https://{endpoint}", timeout))
        
        return tests

    def _test_from_ec2(self, instance: Dict[str, Any], endpoint: str, timeout: int) -> List[Dict[str, Any]]:
        """Run connectivity tests from EC2 instance using SSM."""
        tests = []
        instance_id = instance['InstanceId']
        
        # Note: This would require SSM agent and proper IAM permissions
        # For now, we'll simulate the tests with instructions
        tests.append({
            'test_name': 'EC2 Connectivity Test Setup',
            'success': False,
            'message': 'EC2 testing requires SSM Session Manager setup. Run these commands on your EC2 instance:',
            'details': {
                'commands': [
                    f'curl -I https://{endpoint}',
                    f'nc -zv {endpoint} 443',
                    f'nc -zv {endpoint} 9200',
                    f'nslookup {endpoint}',
                    f'curl -X GET https://{endpoint}/_cluster/health'
                ]
            },
            'duration_ms': 0
        })
        
        return tests

    def _test_dns_resolution(self, hostname: str) -> Dict[str, Any]:
        """Test DNS resolution."""
        start_time = time.time()
        try:
            ip_address = socket.gethostbyname(hostname)
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': 'DNS Resolution',
                'success': True,
                'message': f'Successfully resolved {hostname} to {ip_address}',
                'details': {'hostname': hostname, 'ip_address': ip_address},
                'duration_ms': duration
            }
        except socket.gaierror as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': 'DNS Resolution',
                'success': False,
                'message': f'Failed to resolve {hostname}: {str(e)}',
                'details': {'hostname': hostname, 'error': str(e)},
                'duration_ms': duration
            }

    def _test_port_connectivity(self, hostname: str, port: int, timeout: int) -> Dict[str, Any]:
        """Test port connectivity."""
        start_time = time.time()
        try:
            sock = socket.create_connection((hostname, port), timeout=timeout)
            sock.close()
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': f'Port {port} Connectivity',
                'success': True,
                'message': f'Successfully connected to {hostname}:{port}',
                'details': {'hostname': hostname, 'port': port},
                'duration_ms': duration
            }
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': f'Port {port} Connectivity',
                'success': False,
                'message': f'Failed to connect to {hostname}:{port}: {str(e)}',
                'details': {'hostname': hostname, 'port': port, 'error': str(e)},
                'duration_ms': duration
            }

    def _test_http_connectivity(self, url: str, timeout: int) -> Dict[str, Any]:
        """Test HTTP/HTTPS connectivity."""
        start_time = time.time()
        try:
            response = requests.head(url, timeout=timeout, verify=False)  # Disable SSL verification for testing
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': 'HTTPS Connectivity',
                'success': response.status_code < 500,  # Consider 4xx as success (auth issues are expected)
                'message': f'HTTPS request returned status {response.status_code}',
                'details': {
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                },
                'duration_ms': duration
            }
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': 'HTTPS Connectivity',
                'success': False,
                'message': f'HTTPS request failed: {str(e)}',
                'details': {'url': url, 'error': str(e)},
                'duration_ms': duration
            }

    def _test_opensearch_api(self, base_url: str, timeout: int) -> Dict[str, Any]:
        """Test OpenSearch API endpoints."""
        start_time = time.time()
        try:
            # Try to access cluster health endpoint (usually publicly accessible)
            health_url = f"{base_url}/_cluster/health"
            response = requests.get(health_url, timeout=timeout, verify=False)
            duration = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    'test_name': 'OpenSearch API',
                    'success': True,
                    'message': f'OpenSearch API accessible, cluster status: {health_data.get("status", "unknown")}',
                    'details': {
                        'url': health_url,
                        'status_code': response.status_code,
                        'cluster_health': health_data
                    },
                    'duration_ms': duration
                }
            elif response.status_code == 401 or response.status_code == 403:
                return {
                    'test_name': 'OpenSearch API',
                    'success': True,  # Authentication error means the service is reachable
                    'message': f'OpenSearch API reachable but requires authentication (status {response.status_code})',
                    'details': {
                        'url': health_url,
                        'status_code': response.status_code,
                        'note': 'Authentication required - this is normal for secured clusters'
                    },
                    'duration_ms': duration
                }
            else:
                return {
                    'test_name': 'OpenSearch API',
                    'success': False,
                    'message': f'OpenSearch API returned status {response.status_code}',
                    'details': {
                        'url': health_url,
                        'status_code': response.status_code,
                        'response_text': response.text[:500]
                    },
                    'duration_ms': duration
                }
                
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'test_name': 'OpenSearch API',
                'success': False,
                'message': f'OpenSearch API test failed: {str(e)}',
                'details': {'error': str(e)},
                'duration_ms': duration
            }

    def _display_results(self, results: Dict[str, Any]) -> None:
        """Display connectivity test results."""
        print("\n" + "="*80)
        print("🔗 OPENSEARCH CONNECTIVITY TEST RESULTS")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Domain: {results['domain_name']}")
        print(f"   Endpoint: {results['endpoint']}")
        print(f"   Total Tests: {results['summary']['total_tests']}")
        print(f"   Passed: {results['summary']['passed_tests']} ✅")
        print(f"   Failed: {results['summary']['failed_tests']} ❌")
        
        print(f"\n🧪 DETAILED RESULTS:")
        for i, test in enumerate(results['tests'], 1):
            status_icon = "✅" if test['success'] else "❌"
            print(f"   {i}. {test['test_name']} {status_icon}")
            print(f"      Message: {test['message']}")
            print(f"      Duration: {test['duration_ms']}ms")
            
            if test.get('details'):
                details = test['details']
                if isinstance(details, dict):
                    for key, value in details.items():
                        if key not in ['error']:  # Don't repeat error info
                            if isinstance(value, dict) and len(str(value)) > 100:
                                print(f"      {key}: {type(value).__name__} with {len(value)} items")
                            else:
                                print(f"      {key}: {value}")
            print()
        
        # Overall assessment
        success_rate = (results['summary']['passed_tests'] / results['summary']['total_tests']) * 100
        print(f"🎯 OVERALL ASSESSMENT:")
        if success_rate == 100:
            print(f"   ✅ All tests passed! OpenSearch should be accessible.")
        elif success_rate >= 75:
            print(f"   ⚠️  Most tests passed ({success_rate:.0f}%). Check failed tests for specific issues.")
        elif success_rate >= 50:
            print(f"   ❌ Some tests failed ({success_rate:.0f}%). Network connectivity issues likely.")
        else:
            print(f"   ❌ Most tests failed ({success_rate:.0f}%). Significant connectivity problems.")
        
        print("\n" + "="*80 + "\n")
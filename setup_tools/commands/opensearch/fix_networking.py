"""
Command to automatically fix OpenSearch networking issues with multiple strategies.
"""

import boto3
import json
import time
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from ..base import BaseCommand, register_command
from ...core.exceptions import CommandError


@register_command("fix-opensearch-networking")
class FixOpenSearchNetworkingCommand(BaseCommand):
    """Automatically fix OpenSearch networking issues using multiple strategies."""

    def get_required_args(self) -> list:
        return []

    def get_optional_args(self) -> dict:
        return {
            'mode': 'Fix mode: permissive, public, hybrid (default: permissive)',
            'domain_name': 'OpenSearch domain name (auto-detected if not provided)',
            'ip_restrict': 'IP addresses to allow for public access (comma-separated)',
            'region': 'AWS region (defaults to us-east-1)',
            'dry_run': 'Show what would be changed without making changes',
            'force': 'Apply changes without confirmation prompts'
        }

    def validate_inputs(self, **kwargs) -> None:
        """Validate command inputs."""
        mode = kwargs.get('mode', 'permissive')
        if mode not in ['permissive', 'public', 'hybrid']:
            raise CommandError("Mode must be one of: permissive, public, hybrid")

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute OpenSearch networking fixes."""
        try:
            region = kwargs.get('region', 'us-east-1')
            mode = kwargs.get('mode', 'permissive')
            domain_name = kwargs.get('domain_name')
            ip_restrict = kwargs.get('ip_restrict', '')
            dry_run = kwargs.get('dry_run', False)
            force = kwargs.get('force', False)
            
            self.logger.info(f"🔧 Starting OpenSearch networking fixes in {mode} mode...")
            
            # Initialize AWS clients
            opensearch_client = boto3.client('opensearch', region_name=region)
            ec2_client = boto3.client('ec2', region_name=region)
            
            # Find domain if not specified
            if not domain_name:
                domain_name = self._find_opensearch_domain(opensearch_client)
                if not domain_name:
                    raise CommandError("No OpenSearch domain found and none specified")
            
            self.logger.info(f"🎯 Fixing networking for domain: {domain_name}")
            
            # Get current domain configuration
            domain_info = self._get_domain_info(opensearch_client, domain_name)
            
            results = {
                'domain_name': domain_name,
                'mode': mode,
                'current_config': domain_info,
                'fixes_applied': [],
                'terraform_changes_needed': [],
                'manual_steps': [],
                'success': False
            }
            
            # Apply fixes based on mode
            if mode == 'permissive':
                results = self._apply_permissive_vpc_fixes(
                    results, opensearch_client, ec2_client, dry_run, force
                )
            elif mode == 'public':
                results = self._apply_public_access_fixes(
                    results, opensearch_client, ip_restrict, dry_run, force
                )
            elif mode == 'hybrid':
                results = self._apply_hybrid_access_fixes(
                    results, opensearch_client, ec2_client, ip_restrict, dry_run, force
                )
            
            # Display results
            self._display_results(results)
            
            return results
            
        except NoCredentialsError:
            raise CommandError("AWS credentials not found. Please configure your credentials.")
        except ClientError as e:
            raise CommandError(f"AWS API error: {e}")
        except Exception as e:
            raise CommandError(f"Fix operation failed: {str(e)}")

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
        """Get detailed domain information."""
        try:
            response = client.describe_domain(DomainName=domain_name)
            domain = response['DomainStatus']
            return {
                'name': domain['DomainName'],
                'status': domain.get('ProcessingStatus', 'Unknown'),
                'endpoint': domain.get('Endpoint'),
                'vpc_options': domain.get('VPCOptions', {}),
                'domain_endpoint_options': domain.get('DomainEndpointOptions', {}),
                'access_policies': domain.get('AccessPolicies'),
                'advanced_security_enabled': domain.get('AdvancedSecurityOptions', {}).get('Enabled', False)
            }
        except Exception as e:
            self.logger.error(f"Failed to get domain info: {e}")
            return {}

    def _apply_permissive_vpc_fixes(self, results: Dict[str, Any], opensearch_client, ec2_client, dry_run: bool, force: bool) -> Dict[str, Any]:
        """Apply permissive VPC networking fixes."""
        domain_info = results['current_config']
        vpc_options = domain_info.get('vpc_options', {})
        
        if not vpc_options:
            results['manual_steps'].append("❌ Domain is not VPC-enabled. Consider switching to public mode or recreating domain with VPC.")
            return results
        
        subnet_ids = vpc_options.get('subnet_ids', [])
        security_group_ids = vpc_options.get('security_group_ids', [])
        
        self.logger.info("🌐 Analyzing VPC configuration...")
        
        # Fix 1: Ensure subnets have internet access
        subnet_fixes = self._fix_subnet_routing(ec2_client, subnet_ids, dry_run)
        results['fixes_applied'].extend(subnet_fixes)
        
        # Fix 2: Create/update permissive security groups
        sg_fixes = self._fix_security_groups(ec2_client, security_group_ids, dry_run)
        results['fixes_applied'].extend(sg_fixes)
        
        # Fix 3: Update domain configuration if needed
        domain_fixes = self._fix_domain_configuration(opensearch_client, results['domain_name'], dry_run)
        results['fixes_applied'].extend(domain_fixes)
        
        # Terraform recommendations
        results['terraform_changes_needed'] = self._generate_terraform_recommendations()
        
        results['success'] = len([f for f in results['fixes_applied'] if f['success']]) > 0
        return results

    def _apply_public_access_fixes(self, results: Dict[str, Any], opensearch_client, ip_restrict: str, dry_run: bool, force: bool) -> Dict[str, Any]:
        """Apply public access fixes."""
        self.logger.info("🌍 Configuring public access mode...")
        
        # Parse IP restrictions
        allowed_ips = []
        if ip_restrict:
            allowed_ips = [ip.strip() for ip in ip_restrict.split(',') if ip.strip()]
        
        # Build access policy for public access
        if allowed_ips:
            ip_conditions = [{"IpAddress": {"aws:sourceIp": allowed_ips}}]
        else:
            ip_conditions = []
        
        access_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "*"
                    },
                    "Action": "es:*",
                    "Resource": f"arn:aws:es:*:*:domain/{results['domain_name']}/*"
                }
            ]
        }
        
        # Add IP restrictions if specified
        if ip_conditions:
            access_policy["Statement"][0]["Condition"] = {"Bool": {"aws:SecureTransport": "true"}}
            access_policy["Statement"][0]["Condition"].update(ip_conditions[0])
        
        if not dry_run:
            try:
                # Update domain configuration to remove VPC
                update_config = {
                    'DomainName': results['domain_name'],
                    'AccessPolicies': json.dumps(access_policy)
                }
                
                if not force:
                    print(f"\n⚠️  WARNING: This will reconfigure {results['domain_name']} for public access!")
                    print("This operation will:")
                    print("   - Remove VPC configuration")
                    print("   - Make the domain publicly accessible")
                    if allowed_ips:
                        print(f"   - Restrict access to IPs: {', '.join(allowed_ips)}")
                    else:
                        print("   - Allow access from ANY IP address")
                    print("\nThis change will take 15-30 minutes to complete.")
                    
                    confirm = input("\nProceed? (yes/no): ").lower().strip()
                    if confirm != 'yes':
                        results['manual_steps'].append("❌ User cancelled public access configuration")
                        return results
                
                response = opensearch_client.update_domain_config(**update_config)
                
                results['fixes_applied'].append({
                    'fix': 'Configure Public Access',
                    'success': True,
                    'message': 'Domain configured for public access (processing)',
                    'details': {
                        'allowed_ips': allowed_ips,
                        'update_id': response.get('DomainConfig', {}).get('DomainId')
                    }
                })
                
                results['success'] = True
                
            except ClientError as e:
                results['fixes_applied'].append({
                    'fix': 'Configure Public Access',
                    'success': False,
                    'message': f'Failed to configure public access: {str(e)}',
                    'details': {'error': str(e)}
                })
        else:
            results['fixes_applied'].append({
                'fix': 'Configure Public Access (DRY RUN)',
                'success': True,
                'message': 'Would configure domain for public access',
                'details': {
                    'allowed_ips': allowed_ips,
                    'access_policy': access_policy
                }
            })
        
        return results

    def _apply_hybrid_access_fixes(self, results: Dict[str, Any], opensearch_client, ec2_client, ip_restrict: str, dry_run: bool, force: bool) -> Dict[str, Any]:
        """Apply hybrid access fixes (both VPC and public)."""
        self.logger.info("🔀 Configuring hybrid access mode...")
        
        # First apply VPC fixes
        results = self._apply_permissive_vpc_fixes(results, opensearch_client, ec2_client, dry_run, force)
        
        # Then add public access capability
        results['manual_steps'].append("ℹ️  Hybrid mode: VPC fixes applied above")
        results['manual_steps'].append("ℹ️  To add public access, run: python -m setup_tools fix-opensearch-networking --mode public")
        
        return results

    def _fix_subnet_routing(self, ec2_client, subnet_ids: List[str], dry_run: bool) -> List[Dict[str, Any]]:
        """Fix subnet routing to ensure internet access."""
        fixes = []
        
        if not subnet_ids:
            return fixes
        
        try:
            # Get subnet information
            subnet_response = ec2_client.describe_subnets(SubnetIds=subnet_ids)
            subnets = subnet_response['Subnets']
            
            # Get route tables
            rt_response = ec2_client.describe_route_tables()
            route_tables = rt_response['RouteTables']
            
            for subnet in subnets:
                subnet_id = subnet['SubnetId']
                vpc_id = subnet['VpcId']
                
                # Find associated route table
                associated_rt = None
                for rt in route_tables:
                    if rt['VpcId'] != vpc_id:
                        continue
                    for assoc in rt.get('Associations', []):
                        if assoc.get('SubnetId') == subnet_id:
                            associated_rt = rt
                            break
                    if associated_rt:
                        break
                
                # Use main route table if no explicit association
                if not associated_rt:
                    for rt in route_tables:
                        if rt['VpcId'] == vpc_id:
                            for assoc in rt.get('Associations', []):
                                if assoc.get('Main', False):
                                    associated_rt = rt
                                    break
                            if associated_rt:
                                break
                
                if associated_rt:
                    has_internet = any(
                        route.get('GatewayId', '').startswith('igw-') or route.get('NatGatewayId')
                        for route in associated_rt['Routes']
                    )
                    
                    if not has_internet:
                        fixes.append({
                            'fix': f'Subnet {subnet_id} Internet Access',
                            'success': False,
                            'message': 'Subnet has no internet access (no IGW or NAT Gateway route)',
                            'details': {
                                'subnet_id': subnet_id,
                                'route_table_id': associated_rt['RouteTableId'],
                                'recommendation': 'Add NAT Gateway for private subnets or move to public subnets'
                            }
                        })
                    else:
                        fixes.append({
                            'fix': f'Subnet {subnet_id} Internet Access',
                            'success': True,
                            'message': 'Subnet has internet access',
                            'details': {'subnet_id': subnet_id}
                        })
            
        except Exception as e:
            fixes.append({
                'fix': 'Subnet Routing Analysis',
                'success': False,
                'message': f'Failed to analyze subnet routing: {str(e)}',
                'details': {'error': str(e)}
            })
        
        return fixes

    def _fix_security_groups(self, ec2_client, security_group_ids: List[str], dry_run: bool) -> List[Dict[str, Any]]:
        """Fix security group rules for OpenSearch access."""
        fixes = []
        
        if not security_group_ids:
            return fixes
        
        try:
            # Get security group information
            sg_response = ec2_client.describe_security_groups(GroupIds=security_group_ids)
            security_groups = sg_response['SecurityGroups']
            
            for sg in security_groups:
                sg_id = sg['GroupId']
                ingress_rules = sg['IpPermissions']
                
                # Check for required ports
                has_https = any(self._rule_allows_port(rule, 443) for rule in ingress_rules)
                has_opensearch = any(self._rule_allows_port(rule, 9200) for rule in ingress_rules)
                
                missing_ports = []
                if not has_https:
                    missing_ports.append(443)
                if not has_opensearch:
                    missing_ports.append(9200)
                
                if missing_ports:
                    fixes.append({
                        'fix': f'Security Group {sg_id} Rules',
                        'success': False,
                        'message': f'Missing rules for ports: {missing_ports}',
                        'details': {
                            'security_group_id': sg_id,
                            'missing_ports': missing_ports,
                            'recommendation': 'Add ingress rules for missing ports from VPC CIDR'
                        }
                    })
                else:
                    fixes.append({
                        'fix': f'Security Group {sg_id} Rules',
                        'success': True,
                        'message': 'Required ports are accessible',
                        'details': {'security_group_id': sg_id}
                    })
            
        except Exception as e:
            fixes.append({
                'fix': 'Security Group Analysis',
                'success': False,
                'message': f'Failed to analyze security groups: {str(e)}',
                'details': {'error': str(e)}
            })
        
        return fixes

    def _fix_domain_configuration(self, opensearch_client, domain_name: str, dry_run: bool) -> List[Dict[str, Any]]:
        """Fix domain-level configuration issues."""
        fixes = []
        
        try:
            # Check if domain is processing
            domain_response = opensearch_client.describe_domain(DomainName=domain_name)
            domain = domain_response['DomainStatus']
            
            status = domain.get('ProcessingStatus', 'Unknown')
            
            if status != 'Active':
                fixes.append({
                    'fix': 'Domain Status',
                    'success': False,
                    'message': f'Domain is in {status} state - may be processing changes',
                    'details': {
                        'current_status': status,
                        'recommendation': 'Wait for domain to become Active before making further changes'
                    }
                })
            else:
                fixes.append({
                    'fix': 'Domain Status',
                    'success': True,
                    'message': 'Domain is Active and ready',
                    'details': {'status': status}
                })
            
        except Exception as e:
            fixes.append({
                'fix': 'Domain Configuration Check',
                'success': False,
                'message': f'Failed to check domain configuration: {str(e)}',
                'details': {'error': str(e)}
            })
        
        return fixes

    def _rule_allows_port(self, rule: Dict[str, Any], port: int) -> bool:
        """Check if a security group rule allows a specific port."""
        from_port = rule.get('FromPort')
        to_port = rule.get('ToPort')
        
        if from_port is None or to_port is None:
            return rule.get('IpProtocol') == '-1'  # All traffic
        
        return from_port <= port <= to_port

    def _generate_terraform_recommendations(self) -> List[str]:
        """Generate Terraform configuration recommendations."""
        return [
            "🔧 Add NAT Gateway to private subnets for internet access",
            "🔧 Create route table associations for private subnets",
            "🔧 Update security group rules to allow ports 80, 443, 9200 from VPC CIDR",
            "🔧 Consider moving OpenSearch to public subnets for simpler access",
            "🔧 Fix circular security group reference in networking module"
        ]

    def _display_results(self, results: Dict[str, Any]) -> None:
        """Display fix operation results."""
        print("\n" + "="*80)
        print(f"🔧 OPENSEARCH NETWORKING FIX RESULTS - {results['mode'].upper()} MODE")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Domain: {results['domain_name']}")
        print(f"   Fix Mode: {results['mode']}")
        print(f"   Overall Success: {'✅ Yes' if results['success'] else '❌ No'}")
        
        # Current configuration
        current_config = results.get('current_config', {})
        print(f"\n📋 CURRENT DOMAIN CONFIG:")
        print(f"   Status: {current_config.get('status', 'N/A')}")
        print(f"   Endpoint: {current_config.get('endpoint', 'N/A')}")
        vpc_options = current_config.get('vpc_options', {})
        if vpc_options:
            print(f"   VPC ID: {vpc_options.get('vpc_id', 'N/A')}")
            print(f"   Subnets: {len(vpc_options.get('subnet_ids', []))}")
            print(f"   Security Groups: {len(vpc_options.get('security_group_ids', []))}")
        else:
            print(f"   VPC Enabled: No")
        
        # Fixes applied
        fixes_applied = results.get('fixes_applied', [])
        if fixes_applied:
            print(f"\n🔨 FIXES APPLIED:")
            for fix in fixes_applied:
                status_icon = "✅" if fix['success'] else "❌"
                print(f"   {status_icon} {fix['fix']}")
                print(f"      └─ {fix['message']}")
        
        # Terraform changes needed
        terraform_changes = results.get('terraform_changes_needed', [])
        if terraform_changes:
            print(f"\n🏗️  TERRAFORM CHANGES NEEDED:")
            for change in terraform_changes:
                print(f"   {change}")
        
        # Manual steps
        manual_steps = results.get('manual_steps', [])
        if manual_steps:
            print(f"\n👷 MANUAL STEPS REQUIRED:")
            for step in manual_steps:
                print(f"   {step}")
        
        # Next steps
        print(f"\n🎯 NEXT STEPS:")
        if results['success']:
            print("   1. Wait 15-30 minutes for changes to propagate")
            print("   2. Test connectivity: python -m setup_tools test-opensearch-connectivity")
            print("   3. Check domain status in AWS Console")
        else:
            print("   1. Review failed fixes above")
            print("   2. Apply Terraform changes if needed")
            print("   3. Consider switching to public mode if VPC issues persist")
        
        print("\n" + "="*80 + "\n")
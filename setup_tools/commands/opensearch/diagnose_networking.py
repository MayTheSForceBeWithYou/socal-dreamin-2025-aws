"""
Command to diagnose OpenSearch networking issues, particularly "Pending VPC access" problems.
"""

import boto3
import json
from typing import Dict, List, Any
from botocore.exceptions import ClientError, NoCredentialsError

from ..base import BaseCommand, register_command
from ...core.exceptions import CommandError


@register_command("diagnose-opensearch-networking")
class DiagnoseOpenSearchNetworkingCommand(BaseCommand):
    """Diagnose OpenSearch networking configuration and identify VPC access issues."""

    def get_required_args(self) -> list:
        return []

    def get_optional_args(self) -> dict:
        return {
            'domain_name': 'OpenSearch domain name (auto-detected if not provided)',
            'region': 'AWS region (defaults to us-east-1)'
        }

    def validate_inputs(self, **kwargs) -> None:
        """Validate command inputs."""
        # No specific validation needed - AWS clients will validate credentials
        pass

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the diagnostic analysis."""
        try:
            region = kwargs.get('region', 'us-east-1')
            domain_name = kwargs.get('domain_name')
            
            self.logger.info("🔍 Starting OpenSearch networking diagnostics...")
            
            # Initialize AWS clients
            opensearch_client = boto3.client('opensearch', region_name=region)
            ec2_client = boto3.client('ec2', region_name=region)
            
            # Find domain if not specified
            if not domain_name:
                domain_name = self._find_opensearch_domain(opensearch_client)
                if not domain_name:
                    raise CommandError("No OpenSearch domain found and none specified")
            
            self.logger.info(f"📊 Analyzing domain: {domain_name}")
            
            # Gather diagnostic information
            results = {
                'domain_info': self._get_domain_info(opensearch_client, domain_name),
                'vpc_config': self._analyze_vpc_configuration(ec2_client),
                'subnet_analysis': {},
                'security_groups': {},
                'routing_analysis': {},
                'recommendations': []
            }
            
            # Analyze VPC configuration if domain uses VPC
            if results['domain_info'].get('vpc_options'):
                vpc_options = results['domain_info']['vpc_options']
                results['subnet_analysis'] = self._analyze_subnets(ec2_client, vpc_options.get('subnet_ids', []))
                results['security_groups'] = self._analyze_security_groups(ec2_client, vpc_options.get('security_group_ids', []))
                results['routing_analysis'] = self._analyze_routing(ec2_client, vpc_options.get('subnet_ids', []))
            
            # Generate recommendations
            results['recommendations'] = self._generate_recommendations(results)
            
            # Output results
            self._display_results(results)
            
            return results
            
        except NoCredentialsError:
            raise CommandError("AWS credentials not found. Please configure your credentials.")
        except ClientError as e:
            raise CommandError(f"AWS API error: {e}")
        except Exception as e:
            raise CommandError(f"Diagnostic failed: {str(e)}")

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
                'dashboard_endpoint': domain.get('DomainEndpointOptions', {}).get('CustomEndpoint'),
                'vpc_options': domain.get('VPCOptions', {}),
                'access_policies': domain.get('AccessPolicies'),
                'advanced_security_enabled': domain.get('AdvancedSecurityOptions', {}).get('Enabled', False),
                'encryption_at_rest': domain.get('EncryptionAtRestOptions', {}).get('Enabled', False),
                'node_to_node_encryption': domain.get('NodeToNodeEncryptionOptions', {}).get('Enabled', False)
            }
        except Exception as e:
            self.logger.error(f"Failed to get domain info: {e}")
            return {}

    def _analyze_vpc_configuration(self, ec2_client) -> Dict[str, Any]:
        """Analyze overall VPC configuration."""
        try:
            # Get all VPCs
            vpc_response = ec2_client.describe_vpcs()
            vpcs = vpc_response['Vpcs']
            
            # Get internet gateways
            igw_response = ec2_client.describe_internet_gateways()
            igws = igw_response['InternetGateways']
            
            # Get NAT gateways
            nat_response = ec2_client.describe_nat_gateways()
            nat_gateways = nat_response['NatGateways']
            
            return {
                'vpcs': vpcs,
                'internet_gateways': igws,
                'nat_gateways': nat_gateways
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze VPC: {e}")
            return {}

    def _analyze_subnets(self, ec2_client, subnet_ids: List[str]) -> Dict[str, Any]:
        """Analyze subnet configuration for OpenSearch."""
        if not subnet_ids:
            return {}
        
        try:
            response = ec2_client.describe_subnets(SubnetIds=subnet_ids)
            subnets = response['Subnets']
            
            analysis = {}
            for subnet in subnets:
                subnet_id = subnet['SubnetId']
                analysis[subnet_id] = {
                    'subnet_id': subnet_id,
                    'vpc_id': subnet['VpcId'],
                    'cidr_block': subnet['CidrBlock'],
                    'availability_zone': subnet['AvailabilityZone'],
                    'map_public_ip': subnet.get('MapPublicIpOnLaunch', False),
                    'state': subnet['State'],
                    'available_ip_count': subnet['AvailableIpAddressCount']
                }
            
            return analysis
        except Exception as e:
            self.logger.error(f"Failed to analyze subnets: {e}")
            return {}

    def _analyze_security_groups(self, ec2_client, sg_ids: List[str]) -> Dict[str, Any]:
        """Analyze security group rules for OpenSearch."""
        if not sg_ids:
            return {}
        
        try:
            response = ec2_client.describe_security_groups(GroupIds=sg_ids)
            security_groups = response['SecurityGroups']
            
            analysis = {}
            for sg in security_groups:
                sg_id = sg['GroupId']
                analysis[sg_id] = {
                    'group_id': sg_id,
                    'group_name': sg['GroupName'],
                    'description': sg['Description'],
                    'vpc_id': sg['VpcId'],
                    'ingress_rules': sg['IpPermissions'],
                    'egress_rules': sg['IpPermissionsEgress']
                }
            
            return analysis
        except Exception as e:
            self.logger.error(f"Failed to analyze security groups: {e}")
            return {}

    def _analyze_routing(self, ec2_client, subnet_ids: List[str]) -> Dict[str, Any]:
        """Analyze routing tables for OpenSearch subnets."""
        if not subnet_ids:
            return {}
        
        try:
            # Get route tables
            response = ec2_client.describe_route_tables()
            route_tables = response['RouteTables']
            
            analysis = {}
            for subnet_id in subnet_ids:
                # Find route table associated with this subnet
                associated_rt = None
                for rt in route_tables:
                    for assoc in rt.get('Associations', []):
                        if assoc.get('SubnetId') == subnet_id:
                            associated_rt = rt
                            break
                    if associated_rt:
                        break
                
                # If no explicit association, it uses the main route table
                if not associated_rt:
                    for rt in route_tables:
                        for assoc in rt.get('Associations', []):
                            if assoc.get('Main', False):
                                associated_rt = rt
                                break
                        if associated_rt:
                            break
                
                if associated_rt:
                    analysis[subnet_id] = {
                        'route_table_id': associated_rt['RouteTableId'],
                        'vpc_id': associated_rt['VpcId'],
                        'routes': associated_rt['Routes'],
                        'has_internet_gateway': any(
                            route.get('GatewayId', '').startswith('igw-') 
                            for route in associated_rt['Routes']
                        ),
                        'has_nat_gateway': any(
                            route.get('NatGatewayId') 
                            for route in associated_rt['Routes']
                        )
                    }
            
            return analysis
        except Exception as e:
            self.logger.error(f"Failed to analyze routing: {e}")
            return {}

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the analysis."""
        recommendations = []
        
        domain_info = results.get('domain_info', {})
        subnet_analysis = results.get('subnet_analysis', {})
        routing_analysis = results.get('routing_analysis', {})
        
        # Check if domain is in VPC
        if not domain_info.get('vpc_options'):
            recommendations.append("❌ Domain is not configured for VPC access. Consider enabling VPC options.")
            return recommendations
        
        # Check domain status
        if domain_info.get('status') != 'Active':
            recommendations.append(f"⚠️  Domain status is '{domain_info.get('status')}' - may be processing changes")
        
        # Check subnet routing
        for subnet_id, subnet_info in subnet_analysis.items():
            routing_info = routing_analysis.get(subnet_id, {})
            
            if not routing_info.get('has_internet_gateway') and not routing_info.get('has_nat_gateway'):
                recommendations.append(f"❌ Subnet {subnet_id} has no internet access (no IGW or NAT Gateway)")
                recommendations.append("   → OpenSearch Dashboards requires internet access to AWS managed services")
            
            if subnet_info.get('map_public_ip') and routing_info.get('has_internet_gateway'):
                recommendations.append(f"✅ Subnet {subnet_id} is public - good for Dashboard access")
            elif not routing_info.get('has_nat_gateway'):
                recommendations.append(f"⚠️  Subnet {subnet_id} is private without NAT Gateway")
        
        # Check security groups
        security_groups = results.get('security_groups', {})
        if not security_groups:
            recommendations.append("❌ No security groups found for analysis")
        else:
            for sg_id, sg_info in security_groups.items():
                has_https = any(
                    perm.get('FromPort') == 443 
                    for perm in sg_info.get('ingress_rules', [])
                )
                has_opensearch_port = any(
                    perm.get('FromPort') == 9200 
                    for perm in sg_info.get('ingress_rules', [])
                )
                
                if not has_https:
                    recommendations.append(f"⚠️  Security group {sg_id} missing HTTPS (443) access")
                if not has_opensearch_port:
                    recommendations.append(f"⚠️  Security group {sg_id} missing OpenSearch API (9200) access")
        
        # General recommendations
        if len(recommendations) == 0:
            recommendations.append("✅ Basic networking configuration looks correct")
            recommendations.append("🔧 If still having issues, try switching to public subnets or adding NAT Gateway")
        
        return recommendations

    def _display_results(self, results: Dict[str, Any]) -> None:
        """Display diagnostic results in a readable format."""
        print("\n" + "="*80)
        print("🔍 OPENSEARCH NETWORKING DIAGNOSTIC REPORT")
        print("="*80)
        
        # Domain Information
        domain_info = results.get('domain_info', {})
        print(f"\n📊 DOMAIN INFORMATION:")
        print(f"   Name: {domain_info.get('name', 'N/A')}")
        print(f"   Status: {domain_info.get('status', 'N/A')}")
        print(f"   Endpoint: {domain_info.get('endpoint', 'N/A')}")
        print(f"   VPC Enabled: {'Yes' if domain_info.get('vpc_options') else 'No'}")
        
        if domain_info.get('vpc_options'):
            vpc_opts = domain_info['vpc_options']
            print(f"   VPC ID: {vpc_opts.get('vpc_id', 'N/A')}")
            print(f"   Subnet IDs: {', '.join(vpc_opts.get('subnet_ids', []))}")
            print(f"   Security Groups: {', '.join(vpc_opts.get('security_group_ids', []))}")
        
        # Subnet Analysis
        subnet_analysis = results.get('subnet_analysis', {})
        if subnet_analysis:
            print(f"\n🌐 SUBNET ANALYSIS:")
            for subnet_id, info in subnet_analysis.items():
                print(f"   Subnet: {subnet_id}")
                print(f"   ├─ AZ: {info.get('availability_zone', 'N/A')}")
                print(f"   ├─ CIDR: {info.get('cidr_block', 'N/A')}")
                print(f"   ├─ Public IP: {'Yes' if info.get('map_public_ip') else 'No'}")
                print(f"   └─ Available IPs: {info.get('available_ip_count', 'N/A')}")
        
        # Routing Analysis
        routing_analysis = results.get('routing_analysis', {})
        if routing_analysis:
            print(f"\n🛤️  ROUTING ANALYSIS:")
            for subnet_id, info in routing_analysis.items():
                print(f"   Subnet {subnet_id}:")
                print(f"   ├─ Route Table: {info.get('route_table_id', 'N/A')}")
                print(f"   ├─ Internet Gateway: {'Yes' if info.get('has_internet_gateway') else 'No'}")
                print(f"   └─ NAT Gateway: {'Yes' if info.get('has_nat_gateway') else 'No'}")
        
        # Security Groups
        security_groups = results.get('security_groups', {})
        if security_groups:
            print(f"\n🔒 SECURITY GROUP ANALYSIS:")
            for sg_id, info in security_groups.items():
                print(f"   Group: {sg_id} ({info.get('group_name', 'N/A')})")
                ingress_rules = info.get('ingress_rules', [])
                print(f"   ├─ Ingress Rules: {len(ingress_rules)}")
                for rule in ingress_rules[:3]:  # Show first 3 rules
                    port_range = f"{rule.get('FromPort', 'All')}-{rule.get('ToPort', 'All')}" if rule.get('FromPort') != rule.get('ToPort') else str(rule.get('FromPort', 'All'))
                    print(f"   │  └─ {rule.get('IpProtocol', 'N/A')}:{port_range}")
                if len(ingress_rules) > 3:
                    print(f"   │  └─ ... and {len(ingress_rules) - 3} more rules")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        print(f"\n💡 RECOMMENDATIONS:")
        if recommendations:
            for rec in recommendations:
                print(f"   {rec}")
        else:
            print("   No specific recommendations at this time.")
        
        print("\n" + "="*80 + "\n")
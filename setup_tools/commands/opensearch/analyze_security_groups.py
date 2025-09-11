"""
Command to analyze and create permissive security group configurations for OpenSearch.
"""

import boto3
import json
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from ..base import BaseCommand, register_command
from ...core.exceptions import CommandError


@register_command("analyze-security-groups")
class AnalyzeSecurityGroupsCommand(BaseCommand):
    """Analyze and optionally create permissive security group configurations for OpenSearch."""

    def get_required_args(self) -> list:
        return []

    def get_optional_args(self) -> dict:
        return {
            'service': 'Service to analyze (opensearch, ec2, bastion)',
            'create_permissive': 'Create maximally permissive security group rules',
            'vpc_id': 'VPC ID to create security groups in',
            'region': 'AWS region (defaults to us-east-1)',
            'dry_run': 'Show what would be created without making changes'
        }

    def validate_inputs(self, **kwargs) -> None:
        """Validate command inputs."""
        service = kwargs.get('service')
        if service and service not in ['opensearch', 'ec2', 'bastion']:
            raise CommandError("Service must be one of: opensearch, ec2, bastion")

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute security group analysis and optional creation."""
        try:
            region = kwargs.get('region', 'us-east-1')
            service = kwargs.get('service', 'opensearch')
            create_permissive = kwargs.get('create_permissive', False)
            vpc_id = kwargs.get('vpc_id')
            dry_run = kwargs.get('dry_run', False)
            
            self.logger.info(f"🔒 Analyzing security groups for {service}...")
            
            # Initialize AWS clients
            ec2_client = boto3.client('ec2', region_name=region)
            opensearch_client = boto3.client('opensearch', region_name=region)
            
            results = {
                'analysis': {},
                'recommendations': [],
                'permissive_rules': {},
                'created_resources': []
            }
            
            # Get current configuration
            current_config = self._get_current_configuration(ec2_client, opensearch_client)
            results['analysis'] = current_config
            
            # Analyze current security groups
            if service == 'opensearch':
                results['recommendations'] = self._analyze_opensearch_security_groups(current_config)
                results['permissive_rules'] = self._generate_permissive_opensearch_rules(current_config)
            elif service == 'ec2':
                results['recommendations'] = self._analyze_ec2_security_groups(current_config)
                results['permissive_rules'] = self._generate_permissive_ec2_rules(current_config)
            elif service == 'bastion':
                results['recommendations'] = self._analyze_bastion_security_groups(current_config)
                results['permissive_rules'] = self._generate_permissive_bastion_rules(current_config)
            
            # Create permissive security groups if requested
            if create_permissive:
                if not vpc_id and current_config.get('vpcs'):
                    vpc_id = list(current_config['vpcs'].keys())[0]
                    self.logger.info(f"Using VPC: {vpc_id}")
                
                if not vpc_id:
                    raise CommandError("VPC ID required to create security groups")
                
                if not dry_run:
                    created_sg = self._create_permissive_security_group(
                        ec2_client, vpc_id, service, results['permissive_rules']
                    )
                    results['created_resources'].append(created_sg)
                else:
                    self.logger.info("DRY RUN: Would create security group with permissive rules")
            
            # Display results
            self._display_results(results, service, create_permissive, dry_run)
            
            return results
            
        except NoCredentialsError:
            raise CommandError("AWS credentials not found. Please configure your credentials.")
        except ClientError as e:
            raise CommandError(f"AWS API error: {e}")
        except Exception as e:
            raise CommandError(f"Security group analysis failed: {str(e)}")

    def _get_current_configuration(self, ec2_client, opensearch_client) -> Dict[str, Any]:
        """Get current AWS configuration."""
        config = {
            'vpcs': {},
            'security_groups': {},
            'opensearch_domains': {}
        }
        
        try:
            # Get VPCs
            vpc_response = ec2_client.describe_vpcs()
            for vpc in vpc_response['Vpcs']:
                config['vpcs'][vpc['VpcId']] = {
                    'cidr_block': vpc['CidrBlock'],
                    'state': vpc['State'],
                    'is_default': vpc.get('IsDefault', False)
                }
            
            # Get Security Groups
            sg_response = ec2_client.describe_security_groups()
            for sg in sg_response['SecurityGroups']:
                config['security_groups'][sg['GroupId']] = {
                    'group_name': sg['GroupName'],
                    'description': sg['Description'],
                    'vpc_id': sg['VpcId'],
                    'ingress_rules': sg['IpPermissions'],
                    'egress_rules': sg['IpPermissionsEgress']
                }
            
            # Get OpenSearch domains
            try:
                domains_response = opensearch_client.list_domain_names()
                for domain_info in domains_response.get('DomainNames', []):
                    domain_name = domain_info['DomainName']
                    try:
                        domain_response = opensearch_client.describe_domain(DomainName=domain_name)
                        domain = domain_response['DomainStatus']
                        config['opensearch_domains'][domain_name] = {
                            'status': domain.get('ProcessingStatus', 'Unknown'),
                            'endpoint': domain.get('Endpoint'),
                            'vpc_options': domain.get('VPCOptions', {})
                        }
                    except Exception as e:
                        self.logger.warning(f"Could not describe domain {domain_name}: {e}")
            except Exception as e:
                self.logger.warning(f"Could not list OpenSearch domains: {e}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get current configuration: {e}")
            return config

    def _analyze_opensearch_security_groups(self, config: Dict[str, Any]) -> List[str]:
        """Analyze OpenSearch security groups and provide recommendations."""
        recommendations = []
        
        # Find OpenSearch-related security groups
        opensearch_sgs = []
        for domain_name, domain_info in config.get('opensearch_domains', {}).items():
            vpc_options = domain_info.get('vpc_options', {})
            sg_ids = vpc_options.get('security_group_ids', [])
            opensearch_sgs.extend(sg_ids)
        
        if not opensearch_sgs:
            recommendations.append("❌ No OpenSearch domains with VPC configuration found")
            return recommendations
        
        for sg_id in opensearch_sgs:
            sg_info = config['security_groups'].get(sg_id)
            if not sg_info:
                continue
            
            ingress_rules = sg_info.get('ingress_rules', [])
            
            # Check for required ports
            has_https = any(self._rule_allows_port(rule, 443) for rule in ingress_rules)
            has_opensearch_api = any(self._rule_allows_port(rule, 9200) for rule in ingress_rules)
            has_http = any(self._rule_allows_port(rule, 80) for rule in ingress_rules)
            
            if not has_https:
                recommendations.append(f"❌ Security group {sg_id} missing HTTPS (443) access")
            if not has_opensearch_api:
                recommendations.append(f"❌ Security group {sg_id} missing OpenSearch API (9200) access")
            if not has_http:
                recommendations.append(f"⚠️  Security group {sg_id} missing HTTP (80) access - may be needed for some operations")
            
            # Check source restrictions
            overly_restrictive = True
            for rule in ingress_rules:
                if self._rule_allows_vpc_access(rule, config):
                    overly_restrictive = False
                    break
            
            if overly_restrictive:
                recommendations.append(f"⚠️  Security group {sg_id} may be too restrictive - consider allowing VPC-wide access")
        
        if not recommendations:
            recommendations.append("✅ OpenSearch security groups look properly configured")
        
        return recommendations

    def _analyze_ec2_security_groups(self, config: Dict[str, Any]) -> List[str]:
        """Analyze EC2 security groups."""
        recommendations = []
        
        # This is a simplified analysis - in practice you'd identify EC2 security groups
        # by looking at running instances or by naming conventions
        ec2_sgs = [sg_id for sg_id, sg_info in config['security_groups'].items() 
                   if 'ec2' in sg_info.get('group_name', '').lower()]
        
        if not ec2_sgs:
            recommendations.append("ℹ️  No EC2-specific security groups identified by name")
            return recommendations
        
        for sg_id in ec2_sgs:
            sg_info = config['security_groups'][sg_id]
            ingress_rules = sg_info.get('ingress_rules', [])
            
            has_ssh = any(self._rule_allows_port(rule, 22) for rule in ingress_rules)
            if not has_ssh:
                recommendations.append(f"⚠️  EC2 security group {sg_id} missing SSH (22) access")
        
        return recommendations

    def _analyze_bastion_security_groups(self, config: Dict[str, Any]) -> List[str]:
        """Analyze bastion host security groups."""
        recommendations = []
        
        # Find bastion security groups by naming convention
        bastion_sgs = [sg_id for sg_id, sg_info in config['security_groups'].items() 
                       if 'bastion' in sg_info.get('group_name', '').lower()]
        
        if not bastion_sgs:
            recommendations.append("ℹ️  No bastion security groups identified by name")
            return recommendations
        
        for sg_id in bastion_sgs:
            sg_info = config['security_groups'][sg_id]
            ingress_rules = sg_info.get('ingress_rules', [])
            
            has_ssh = any(self._rule_allows_port(rule, 22) for rule in ingress_rules)
            has_https = any(self._rule_allows_port(rule, 443) for rule in ingress_rules)
            has_http = any(self._rule_allows_port(rule, 80) for rule in ingress_rules)
            
            if not has_ssh:
                recommendations.append(f"❌ Bastion security group {sg_id} missing SSH (22) access")
            if not has_https:
                recommendations.append(f"❌ Bastion security group {sg_id} missing HTTPS (443) access")
            if not has_http:
                recommendations.append(f"⚠️  Bastion security group {sg_id} missing HTTP (80) access")
        
        return recommendations

    def _generate_permissive_opensearch_rules(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate maximally permissive OpenSearch security group rules."""
        vpc_cidrs = [info['cidr_block'] for info in config.get('vpcs', {}).values()]
        
        return {
            'ingress_rules': [
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP access from anywhere'}],
                    'Description': 'HTTP access for OpenSearch'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS access from anywhere'}],
                    'Description': 'HTTPS access for OpenSearch'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 9200,
                    'ToPort': 9200,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'OpenSearch API access from anywhere'}],
                    'Description': 'OpenSearch API access'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 5601,
                    'ToPort': 5601,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Kibana/Dashboard access from anywhere'}],
                    'Description': 'Dashboard access'
                },
                # Add VPC-specific rules for better security option
            ] + ([
                {
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': cidr, 'Description': f'All traffic from VPC {cidr}'}],
                    'Description': f'All traffic from VPC'
                } for cidr in vpc_cidrs[:1]  # Use first VPC CIDR
            ] if vpc_cidrs else []),
            'egress_rules': [
                {
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'All outbound traffic'}],
                    'Description': 'All outbound traffic'
                }
            ]
        }

    def _generate_permissive_ec2_rules(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate permissive EC2 security group rules."""
        return {
            'ingress_rules': [
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access from anywhere'}],
                    'Description': 'SSH access'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP access from anywhere'}],
                    'Description': 'HTTP access'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS access from anywhere'}],
                    'Description': 'HTTPS access'
                }
            ],
            'egress_rules': [
                {
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'All outbound traffic'}],
                    'Description': 'All outbound traffic'
                }
            ]
        }

    def _generate_permissive_bastion_rules(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate permissive bastion security group rules."""
        return {
            'ingress_rules': [
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access from anywhere'}],
                    'Description': 'SSH access'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP proxy access from anywhere'}],
                    'Description': 'HTTP proxy access'
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS proxy access from anywhere'}],
                    'Description': 'HTTPS proxy access'
                }
            ],
            'egress_rules': [
                {
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'All outbound traffic'}],
                    'Description': 'All outbound traffic'
                }
            ]
        }

    def _rule_allows_port(self, rule: Dict[str, Any], port: int) -> bool:
        """Check if a security group rule allows a specific port."""
        from_port = rule.get('FromPort')
        to_port = rule.get('ToPort')
        
        if from_port is None or to_port is None:
            return rule.get('IpProtocol') == '-1'  # All traffic
        
        return from_port <= port <= to_port

    def _rule_allows_vpc_access(self, rule: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Check if a rule allows VPC-wide access."""
        # Check IP ranges for VPC CIDRs
        for ip_range in rule.get('IpRanges', []):
            cidr = ip_range.get('CidrIp', '')
            # Check if this CIDR matches any VPC CIDR or is permissive
            if cidr == '0.0.0.0/0':
                return True
            for vpc_info in config.get('vpcs', {}).values():
                if cidr == vpc_info['cidr_block']:
                    return True
        
        # Check security group references (also indicates VPC access)
        return len(rule.get('UserIdGroupPairs', [])) > 0

    def _create_permissive_security_group(self, ec2_client, vpc_id: str, service: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Create a permissive security group."""
        group_name = f"permissive-{service}-sg"
        description = f"Maximally permissive security group for {service} (LAB USE ONLY)"
        
        try:
            # Create security group
            response = ec2_client.create_security_group(
                GroupName=group_name,
                Description=description,
                VpcId=vpc_id
            )
            
            group_id = response['GroupId']
            self.logger.info(f"Created security group: {group_id}")
            
            # Add ingress rules
            if rules.get('ingress_rules'):
                ec2_client.authorize_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=rules['ingress_rules']
                )
                self.logger.info(f"Added {len(rules['ingress_rules'])} ingress rules")
            
            # Modify egress rules (replace default)
            if rules.get('egress_rules'):
                # First revoke default egress rule
                try:
                    ec2_client.revoke_security_group_egress(
                        GroupId=group_id,
                        IpPermissions=[{
                            'IpProtocol': '-1',
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                        }]
                    )
                except ClientError:
                    pass  # Default rule might not exist
                
                # Add new egress rules
                ec2_client.authorize_security_group_egress(
                    GroupId=group_id,
                    IpPermissions=rules['egress_rules']
                )
                self.logger.info(f"Added {len(rules['egress_rules'])} egress rules")
            
            return {
                'group_id': group_id,
                'group_name': group_name,
                'vpc_id': vpc_id,
                'description': description,
                'rules_added': {
                    'ingress': len(rules.get('ingress_rules', [])),
                    'egress': len(rules.get('egress_rules', []))
                }
            }
            
        except ClientError as e:
            if 'InvalidGroup.Duplicate' in str(e):
                raise CommandError(f"Security group '{group_name}' already exists in VPC {vpc_id}")
            else:
                raise CommandError(f"Failed to create security group: {e}")

    def _display_results(self, results: Dict[str, Any], service: str, create_permissive: bool, dry_run: bool) -> None:
        """Display security group analysis results."""
        print("\n" + "="*80)
        print(f"🔒 SECURITY GROUP ANALYSIS - {service.upper()}")
        print("="*80)
        
        # Current configuration summary
        analysis = results.get('analysis', {})
        print(f"\n📊 CURRENT CONFIGURATION:")
        print(f"   VPCs: {len(analysis.get('vpcs', {}))}")
        print(f"   Security Groups: {len(analysis.get('security_groups', {}))}")
        print(f"   OpenSearch Domains: {len(analysis.get('opensearch_domains', {}))}")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        print(f"\n💡 ANALYSIS & RECOMMENDATIONS:")
        if recommendations:
            for rec in recommendations:
                print(f"   {rec}")
        else:
            print("   No specific recommendations at this time.")
        
        # Permissive rules preview
        permissive_rules = results.get('permissive_rules', {})
        if permissive_rules:
            print(f"\n🚨 PERMISSIVE SECURITY GROUP RULES ({service.upper()}):")
            print("   ⚠️  WARNING: These rules are for LAB/DEMO use only!")
            
            ingress_rules = permissive_rules.get('ingress_rules', [])
            print(f"\n   📥 INGRESS RULES ({len(ingress_rules)}):")
            for rule in ingress_rules:
                protocol = rule.get('IpProtocol', 'N/A')
                if protocol == '-1':
                    port_info = "All ports"
                else:
                    from_port = rule.get('FromPort', 'N/A')
                    to_port = rule.get('ToPort', 'N/A')
                    port_info = f"Port {from_port}" if from_port == to_port else f"Ports {from_port}-{to_port}"
                
                sources = []
                for ip_range in rule.get('IpRanges', []):
                    sources.append(ip_range.get('CidrIp', 'N/A'))
                source_info = ', '.join(sources) if sources else 'N/A'
                
                print(f"      └─ {protocol.upper()}: {port_info} from {source_info}")
            
            egress_rules = permissive_rules.get('egress_rules', [])
            print(f"\n   📤 EGRESS RULES ({len(egress_rules)}):")
            for rule in egress_rules:
                protocol = rule.get('IpProtocol', 'N/A')
                if protocol == '-1':
                    print(f"      └─ All traffic to anywhere")
                else:
                    print(f"      └─ {protocol.upper()} traffic allowed")
        
        # Created resources
        created_resources = results.get('created_resources', [])
        if created_resources:
            print(f"\n✅ CREATED RESOURCES:")
            for resource in created_resources:
                print(f"   Security Group: {resource['group_id']} ({resource['group_name']})")
                print(f"   ├─ VPC: {resource['vpc_id']}")
                print(f"   ├─ Description: {resource['description']}")
                print(f"   └─ Rules: {resource['rules_added']['ingress']} ingress, {resource['rules_added']['egress']} egress")
        elif create_permissive and dry_run:
            print(f"\n🔍 DRY RUN - WOULD CREATE:")
            print(f"   └─ Permissive security group for {service} with {len(permissive_rules.get('ingress_rules', []))} rules")
        
        print("\n" + "="*80 + "\n")
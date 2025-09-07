"""
Configuration management for the setup tools framework.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from .exceptions import ConfigurationError


@dataclass
class SalesforceConfig:
    """Salesforce-specific configuration."""
    org_name: str = "socal-dreamin-2025-aws"
    duration_days: int = 30
    contact_email: str = ""
    instance_url: str = ""
    client_id: str = ""
    username: str = ""
    private_key_path: str = "salesforce/certs/aws-to-sf-cert.key"
    certificate_path: str = "salesforce/certs/aws-to-sf-cert.crt"
    connected_app_xml: str = "salesforce/force-app/main/default/connectedApps/AWS_Lambda_PubSub_App.connectedApp-meta.xml"
    integration_user_def: str = "salesforce/config/integration-user-def.json"
    project_scratch_def: str = "salesforce/config/project-scratch-def.json"


@dataclass
class AWSConfig:
    """AWS-specific configuration."""
    region: str = "us-west-2"
    ssh_key_name: str = "aws-ec2"
    ssh_key_path: str = "aws/certs/aws-ec2"
    terraform_dir: str = "aws/terraform"
    terraform_vars_file: str = "aws/terraform/terraform.tfvars"
    ec2_instance_type: str = "t3.micro"
    certificate_dir: str = "aws/certs"


@dataclass
class ProjectConfig:
    """Project-wide configuration."""
    root_dir: Path = field(default_factory=lambda: Path.cwd())
    log_level: str = "INFO"
    dry_run: bool = False
    verbose: bool = False
    salesforce: SalesforceConfig = field(default_factory=SalesforceConfig)
    aws: AWSConfig = field(default_factory=AWSConfig)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.root_dir, str):
            self.root_dir = Path(self.root_dir)


class ConfigManager:
    """Manages configuration loading and merging."""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        self.config_file = Path(config_file) if config_file else None
        self._config: Optional[ProjectConfig] = None
    
    def load_config(self) -> ProjectConfig:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config
        
        # Start with default configuration
        config_data = self._get_default_config()
        
        # Load from YAML file if specified
        if self.config_file and self.config_file.exists():
            config_data = self._merge_configs(config_data, self._load_yaml_config())
        
        # Override with environment variables
        config_data = self._merge_configs(config_data, self._load_env_config())
        
        # Create configuration object
        self._config = self._create_config_object(config_data)
        
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "root_dir": str(Path.cwd()),
            "log_level": "INFO",
            "dry_run": False,
            "verbose": False,
            "salesforce": {
                "org_name": "socal-dreamin-2025-aws",
                "duration_days": 30,
                "contact_email": "",
                "instance_url": "",
                "client_id": "",
                "username": "",
                "private_key_path": "salesforce/certs/aws-to-sf-cert.key",
                "certificate_path": "salesforce/certs/aws-to-sf-cert.crt",
                "connected_app_xml": "salesforce/force-app/main/default/connectedApps/AWS_Lambda_PubSub_App.connectedApp-meta.xml",
                "integration_user_def": "salesforce/config/integration-user-def.json",
                "project_scratch_def": "salesforce/config/project-scratch-def.json"
            },
            "aws": {
                "region": "us-west-2",
                "ssh_key_name": "aws-ec2",
                "ssh_key_path": "aws/certs/aws-ec2",
                "terraform_dir": "aws/terraform",
                "terraform_vars_file": "aws/terraform/terraform.tfvars",
                "ec2_instance_type": "t3.micro",
                "certificate_dir": "aws/certs"
            }
        }
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file {self.config_file}: {e}")
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to config keys
        env_mappings = {
            'SETUP_TOOLS_LOG_LEVEL': ('log_level',),
            'SETUP_TOOLS_DRY_RUN': ('dry_run', lambda x: x.lower() in ('true', '1', 'yes')),
            'SETUP_TOOLS_VERBOSE': ('verbose', lambda x: x.lower() in ('true', '1', 'yes')),
            'SETUP_TOOLS_ROOT_DIR': ('root_dir',),
            'SF_CONTACT_EMAIL': ('salesforce', 'contact_email'),
            'SF_ORG_NAME': ('salesforce', 'org_name'),
            'SF_DURATION_DAYS': ('salesforce', 'duration_days', int),
            'AWS_REGION': ('aws', 'region'),
            'AWS_SSH_KEY_NAME': ('aws', 'ssh_key_name'),
            'AWS_SSH_KEY_PATH': ('aws', 'ssh_key_path'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle nested keys
                if len(config_path) == 1:
                    key = config_path[0]
                    if key in ('dry_run', 'verbose'):
                        env_config[key] = value.lower() in ('true', '1', 'yes')
                    elif key == 'duration_days':
                        env_config[key] = int(value)
                    else:
                        env_config[key] = value
                else:
                    # Nested configuration
                    section, key = config_path[0], config_path[1]
                    if section not in env_config:
                        env_config[section] = {}
                    
                    if len(config_path) == 3 and config_path[2] == int:
                        env_config[section][key] = int(value)
                    else:
                        env_config[section][key] = value
        
        return env_config
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_config_object(self, config_data: Dict[str, Any]) -> ProjectConfig:
        """Create ProjectConfig object from dictionary."""
        try:
            # Create nested config objects
            salesforce_config = SalesforceConfig(**config_data.get('salesforce', {}))
            aws_config = AWSConfig(**config_data.get('aws', {}))
            
            # Create main config object
            project_config = ProjectConfig(
                root_dir=Path(config_data.get('root_dir', Path.cwd())),
                log_level=config_data.get('log_level', 'INFO'),
                dry_run=config_data.get('dry_run', False),
                verbose=config_data.get('verbose', False),
                salesforce=salesforce_config,
                aws=aws_config
            )
            
            return project_config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create configuration object: {e}")
    
    def save_config(self, config: ProjectConfig, file_path: Union[str, Path]) -> None:
        """Save configuration to YAML file."""
        try:
            config_dict = {
                'log_level': config.log_level,
                'dry_run': config.dry_run,
                'verbose': config.verbose,
                'salesforce': {
                    'org_name': config.salesforce.org_name,
                    'duration_days': config.salesforce.duration_days,
                    'contact_email': config.salesforce.contact_email,
                    'instance_url': config.salesforce.instance_url,
                    'client_id': config.salesforce.client_id,
                    'username': config.salesforce.username,
                    'private_key_path': config.salesforce.private_key_path,
                    'certificate_path': config.salesforce.certificate_path,
                    'connected_app_xml': config.salesforce.connected_app_xml,
                    'integration_user_def': config.salesforce.integration_user_def,
                    'project_scratch_def': config.salesforce.project_scratch_def
                },
                'aws': {
                    'region': config.aws.region,
                    'ssh_key_name': config.aws.ssh_key_name,
                    'ssh_key_path': config.aws.ssh_key_path,
                    'terraform_dir': config.aws.terraform_dir,
                    'terraform_vars_file': config.aws.terraform_vars_file,
                    'ec2_instance_type': config.aws.ec2_instance_type,
                    'certificate_dir': config.aws.certificate_dir
                }
            }
            
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")


def get_config(config_file: Optional[Union[str, Path]] = None) -> ProjectConfig:
    """Get the global configuration instance."""
    manager = ConfigManager(config_file)
    return manager.load_config()

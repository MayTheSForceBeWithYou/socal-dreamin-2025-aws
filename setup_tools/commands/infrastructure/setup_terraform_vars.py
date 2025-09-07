#!/usr/bin/env python3
"""
Setup Terraform Variables Command
Creates terraform.tfvars file from template with user input
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from setup_tools.core.config import get_config
from setup_tools.core.logger import SetupToolsLogger
from setup_tools.core.exceptions import SetupToolsError

console = Console()
logger = SetupToolsLogger()


class TerraformVarsSetup:
    """Handles setup of Terraform variables file."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = get_config(config_path)
        self.project_root = project_root
        self.terraform_dir = self.project_root / "aws" / "terraform"
        self.tfvars_template = self.terraform_dir / "terraform.tfvars.example"
        self.tfvars_file = self.terraform_dir / "terraform.tfvars"
    
    def setup_terraform_vars(self, environment: str = "demo") -> bool:
        """Set up Terraform variables file."""
        console.print(Panel(
            f"🔧 Setting up Terraform Variables\n"
            f"Environment: {environment}",
            title="Terraform Setup",
            border_style="blue"
        ))
        
        try:
            # Check if template exists
            if not self.tfvars_template.exists():
                console.print(f"[red]❌ Template file not found: {self.tfvars_template}[/red]")
                return False
            
            # Check if tfvars already exists
            if self.tfvars_file.exists():
                if not Confirm.ask(f"terraform.tfvars already exists. Overwrite?"):
                    console.print("[yellow]⚠️  Skipping Terraform variables setup[/yellow]")
                    return True
            
            # Read template
            with open(self.tfvars_template, 'r') as f:
                template_content = f.read()
            
            # Get user inputs
            console.print("\n[bold]Please provide the following information:[/bold]")
            
            # AWS Region
            aws_region = Prompt.ask(
                "AWS Region", 
                default="us-west-1",
                show_default=True
            )
            
            # Project name
            project_name = Prompt.ask(
                "Project Name", 
                default=f"salesforce-opensearch-lab-{environment}",
                show_default=True
            )
            
            # Owner
            owner = Prompt.ask(
                "Owner/Contact", 
                default="lab-user",
                show_default=True
            )
            
            # SSH Public Key
            console.print("\n[yellow]SSH Public Key Setup:[/yellow]")
            console.print("You need to provide an SSH public key for EC2 access.")
            console.print("If you don't have one, we can generate it for you.")
            
            if Confirm.ask("Generate new SSH keypair?"):
                ssh_public_key = self._generate_ssh_keypair(environment)
                if not ssh_public_key:
                    console.print("[red]❌ Failed to generate SSH keypair[/red]")
                    return False
            else:
                ssh_public_key = Prompt.ask(
                    "SSH Public Key (paste your public key here)",
                    default="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
                )
            
            # Salesforce Configuration
            console.print("\n[yellow]Salesforce Configuration:[/yellow]")
            console.print("Please provide Salesforce information. If you haven't set up Salesforce yet,")
            console.print("run: python -m setup_tools.main salesforce setup-complete --contact-email your-email@example.com")
            
            # Get Salesforce instance URL
            salesforce_instance_url = Prompt.ask(
                "Salesforce Instance URL", 
                default="https://your-instance.salesforce.com",
                show_default=True
            )
            
            # Get Salesforce client ID (Consumer Key)
            salesforce_client_id = Prompt.ask(
                "Salesforce Connected App Consumer Key", 
                default="your-connected-app-consumer-key",
                show_default=True
            )
            
            # Get Salesforce username
            salesforce_username = Prompt.ask(
                "Salesforce Username", 
                default="your-salesforce-username@your-domain.com",
                show_default=True
            )
            
            # Get Salesforce private key
            salesforce_private_key = self._get_salesforce_private_key()
            if not salesforce_private_key:
                console.print("[yellow]⚠️  Salesforce private key not found. You may need to run certificate generation.[/yellow]")
                salesforce_private_key = Prompt.ask(
                    "Salesforce Private Key (paste your private key here)",
                    default="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
                )
            
            # Replace template variables
            tfvars_content = template_content.replace("us-west-1", aws_region)
            tfvars_content = tfvars_content.replace("salesforce-opensearch-lab", project_name)
            tfvars_content = tfvars_content.replace("lab-user", owner)
            tfvars_content = tfvars_content.replace("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC...", ssh_public_key)
            tfvars_content = tfvars_content.replace("https://your-instance.salesforce.com", salesforce_instance_url)
            tfvars_content = tfvars_content.replace("your-connected-app-consumer-key", salesforce_client_id)
            tfvars_content = tfvars_content.replace("your-salesforce-username@your-domain.com", salesforce_username)
            
            # Replace the private key placeholder with actual content
            private_key_pattern = r'salesforce_private_key = """\s*\n-----BEGIN PRIVATE KEY-----\s*\n.*?\n-----END PRIVATE KEY-----\s*\n"""'
            private_key_replacement = f'salesforce_private_key = """\n{salesforce_private_key}\n"""'
            tfvars_content = re.sub(private_key_pattern, private_key_replacement, tfvars_content, flags=re.DOTALL)
            
            # Write tfvars file
            with open(self.tfvars_file, 'w') as f:
                f.write(tfvars_content)
            
            console.print(f"[green]✅ Created terraform.tfvars: {self.tfvars_file}[/green]")
            
            # Display next steps
            console.print(Panel(
                "Next Steps:\n"
                "1. Edit aws/sfdc-auth-secrets.json with your Salesforce credentials\n"
                "2. Run: python -m setup_tools.main infrastructure deploy-complete-lab --environment demo --validate\n"
                "3. The deployment will create all AWS resources\n"
                "4. Note: Salesforce private key has been automatically populated in terraform.tfvars",
                title="📋 Next Steps",
                border_style="green"
            ))
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to setup Terraform variables: {e}[/red]")
            return False
    
    def _generate_ssh_keypair(self, environment: str = "demo") -> Optional[str]:
        """Generate SSH keypair and return public key."""
        try:
            import subprocess
            
            # Create certs directory if it doesn't exist
            certs_dir = self.project_root / "aws" / "certs"
            certs_dir.mkdir(parents=True, exist_ok=True)
            
            private_key_path = certs_dir / "aws-ec2"
            public_key_path = certs_dir / "aws-ec2.pub"
            
            # Check if keys already exist
            if private_key_path.exists() or public_key_path.exists():
                console.print(f"[yellow]⚠️  SSH keys already exist at {private_key_path}[/yellow]")
                if Confirm.ask("Overwrite existing SSH keys?"):
                    # Remove existing keys
                    if private_key_path.exists():
                        private_key_path.unlink()
                    if public_key_path.exists():
                        public_key_path.unlink()
                else:
                    # Use existing public key
                    if public_key_path.exists():
                        with open(public_key_path, 'r') as f:
                            public_key = f.read().strip()
                        console.print(f"[green]✅ Using existing SSH keypair: {private_key_path}[/green]")
                        return public_key
                    else:
                        console.print("[red]❌ No existing public key found[/red]")
                        return None
            
            # Generate SSH keypair with explicit overwrite flag
            console.print("Generating SSH keypair...")
            result = subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "4096", 
                "-f", str(private_key_path),
                "-N", "",  # No passphrase
                "-C", f"aws-ec2-{environment}",
                "-q"  # Quiet mode - suppress output
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ SSH keygen failed: {result.stderr}[/red]")
                return None
            
            # Read public key
            with open(public_key_path, 'r') as f:
                public_key = f.read().strip()
            
            console.print(f"[green]✅ Generated SSH keypair: {private_key_path}[/green]")
            return public_key
            
        except Exception as e:
            console.print(f"[red]❌ Failed to generate SSH keypair: {e}[/red]")
            return None
    
    def _get_salesforce_private_key(self) -> Optional[str]:
        """Read the Salesforce private key content."""
        try:
            private_key_path = self.project_root / "salesforce" / "certs" / "aws-to-sf-cert.key"
            
            if not private_key_path.exists():
                return None
            
            with open(private_key_path, 'r') as f:
                private_key_content = f.read().strip()
            
            return private_key_content
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Failed to read Salesforce private key: {e}[/yellow]")
            return None


@click.command()
@click.option('--environment', default='demo', help='Environment name')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
def setup_terraform_vars(environment, config):
    """Set up Terraform variables file from template."""
    setup = TerraformVarsSetup(config)
    success = setup.setup_terraform_vars(environment)
    
    if not success:
        console.print("[red]❌ Setup failed. Please check the errors above and try again.[/red]")
        return


if __name__ == "__main__":
    setup_terraform_vars()

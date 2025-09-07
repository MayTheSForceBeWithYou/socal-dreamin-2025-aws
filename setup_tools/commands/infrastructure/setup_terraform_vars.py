#!/usr/bin/env python3
"""
Setup Terraform Variables Command
Creates terraform.tfvars file from template with user input
"""

import os
import sys
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
            
            # Get contact email for Connected App
            contact_email = Prompt.ask(
                "Contact Email for Salesforce Connected App", 
                default="your-email@example.com",
                show_default=True
            )
            
            # Check if Salesforce scratch org already exists
            salesforce_instance_url = self._get_salesforce_instance_url(environment)
            
            if not salesforce_instance_url:
                console.print("No Salesforce scratch org found. Let's create one...")
                if Confirm.ask("Create Salesforce scratch org?"):
                    salesforce_instance_url = self._create_salesforce_org(environment)
                    if not salesforce_instance_url:
                        console.print("[red]❌ Failed to create Salesforce scratch org[/red]")
                        return False
                else:
                    salesforce_instance_url = Prompt.ask(
                        "Salesforce Instance URL", 
                        default="https://your-instance.salesforce.com",
                        show_default=True
                    )
            
            # Set up Connected App and get Consumer Key
            console.print("Setting up Salesforce Connected App...")
            salesforce_client_id = self._setup_connected_app(environment, contact_email)
            if not salesforce_client_id:
                console.print("[red]❌ Failed to setup Connected App[/red]")
                return False
            
            salesforce_username = Prompt.ask(
                "Salesforce Username", 
                default="your-salesforce-username@your-domain.com",
                show_default=True
            )
            
            # Replace template variables
            tfvars_content = template_content.replace("us-west-1", aws_region)
            tfvars_content = tfvars_content.replace("salesforce-opensearch-lab", project_name)
            tfvars_content = tfvars_content.replace("lab-user", owner)
            tfvars_content = tfvars_content.replace("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC...", ssh_public_key)
            tfvars_content = tfvars_content.replace("https://your-instance.salesforce.com", salesforce_instance_url)
            tfvars_content = tfvars_content.replace("your-connected-app-consumer-key", salesforce_client_id)
            tfvars_content = tfvars_content.replace("your-salesforce-username@your-domain.com", salesforce_username)
            
            # Write tfvars file
            with open(self.tfvars_file, 'w') as f:
                f.write(tfvars_content)
            
            console.print(f"[green]✅ Created terraform.tfvars: {self.tfvars_file}[/green]")
            
            # Display next steps
            console.print(Panel(
                "Next Steps:\n"
                "1. Edit aws/sfdc-auth-secrets.json with your Salesforce credentials\n"
                "2. Run: python -m setup_tools.main infrastructure deploy-complete-lab --environment demo --validate\n"
                "3. The deployment will create all AWS resources",
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
    
    def _get_salesforce_instance_url(self, environment: str) -> Optional[str]:
        """Get Salesforce instance URL from existing scratch org."""
        try:
            import subprocess
            import json
            
            salesforce_dir = self.project_root / "salesforce"
            if not salesforce_dir.exists():
                return None
            
            # Try to get org info for the default org
            result = subprocess.run([
                "sf", "org", "display", "--json"
            ], cwd=salesforce_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                org_data = json.loads(result.stdout)
                instance_url = org_data.get('result', {}).get('instanceUrl')
                if instance_url:
                    console.print(f"[green]✅ Found existing Salesforce org: {instance_url}[/green]")
                    return instance_url
            
            return None
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not check for existing Salesforce org: {e}[/yellow]")
            return None
    
    def _create_salesforce_org(self, environment: str) -> Optional[str]:
        """Create Salesforce scratch org and return instance URL."""
        try:
            import subprocess
            import json
            
            salesforce_dir = self.project_root / "salesforce"
            if not salesforce_dir.exists():
                console.print("[red]❌ Salesforce directory not found[/red]")
                return None
            
            # Check if sf CLI is available
            result = subprocess.run(["sf", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                console.print("[red]❌ Salesforce CLI (sf) not found. Please install it first.[/red]")
                return None
            
            org_name = f"socal-dreamin-2025-aws-{environment}"
            
            console.print(f"Creating Salesforce scratch org: {org_name}")
            console.print("[yellow]This may take a few minutes...[/yellow]")
            
            # Create scratch org - pass through output so user can see progress
            result = subprocess.run([
                "sf", "org", "create", "scratch",
                "--definition-file", "config/project-scratch-def.json",
                "--alias", org_name,
                "--set-default",
                "--duration-days", "30"
            ], cwd=salesforce_dir)
            
            if result.returncode != 0:
                console.print("[red]❌ Failed to create scratch org. Check the output above for details.[/red]")
                return None
            
            # Get org info
            result = subprocess.run([
                "sf", "org", "display", "--json"
            ], cwd=salesforce_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                org_data = json.loads(result.stdout)
                instance_url = org_data.get('result', {}).get('instanceUrl')
                if instance_url:
                    console.print(f"[green]✅ Created Salesforce scratch org: {instance_url}[/green]")
                    return instance_url
            
            console.print("[red]❌ Failed to get org instance URL[/red]")
            return None
            
        except Exception as e:
            console.print(f"[red]❌ Failed to create Salesforce org: {e}[/red]")
            return None
    
    def _setup_connected_app(self, environment: str, contact_email: str) -> Optional[str]:
        """Set up Salesforce Connected App and return Consumer Key."""
        try:
            import subprocess
            import json
            
            salesforce_dir = self.project_root / "salesforce"
            if not salesforce_dir.exists():
                console.print("[red]❌ Salesforce directory not found[/red]")
                return None
            
            # Check if certificate exists
            cert_path = self.project_root / "salesforce" / "certs" / "aws-to-sf-cert.crt"
            if not cert_path.exists():
                console.print("[red]❌ Salesforce certificate not found. Run 'python -m setup_tools.main salesforce generate-certificate' first.[/red]")
                return None
            
            # Read certificate content
            with open(cert_path, 'r') as f:
                cert_content = f.read()
            
            # Remove BEGIN/END lines and concatenate
            cert_lines = cert_content.strip().split('\n')
            cert_body = ''.join([line.strip() for line in cert_lines 
                               if not line.startswith('-----BEGIN') and not line.startswith('-----END')])
            
            # Update Connected App XML
            connected_app_path = salesforce_dir / "force-app" / "main" / "default" / "connectedApps" / "AWS_Lambda_PubSub_App.connectedApp-meta.xml"
            if not connected_app_path.exists():
                console.print("[red]❌ Connected App XML not found[/red]")
                return None
            
            # Read and update XML
            with open(connected_app_path, 'r') as f:
                xml_content = f.read()
            
            # Replace contact email and certificate
            xml_content = xml_content.replace('replace@with.your.email', contact_email)
            xml_content = xml_content.replace('FROM_salesforce/certs/aws-to-sf-cert_WITHOUT_BEGIN_OR_END_LINES', cert_body)
            
            # Write updated XML
            with open(connected_app_path, 'w') as f:
                f.write(xml_content)
            
            console.print("Deploying Connected App to Salesforce...")
            
            # Deploy the Connected App
            result = subprocess.run([
                "sf", "project", "deploy", "start",
                "--source-dir", "force-app/main/default/connectedApps",
                "--target-org", f"socal-dreamin-2025-aws-{environment}"
            ], cwd=salesforce_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Failed to deploy Connected App: {result.stderr}[/red]")
                return None
            
            console.print("Retrieving Connected App Consumer Key...")
            
            # Retrieve the Connected App directly
            result = subprocess.run([
                "sf", "project", "retrieve", "start",
                "--source-dir", connected_app_path,
                "--target-org", f"socal-dreamin-2025-aws-{environment}",
                "--json"
            ], cwd=salesforce_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Failed to retrieve Connected App: {result.stderr}[/red]")
                return None
            
            # Parse the result to find our Connected App
            try:
                metadata_result = json.loads(result.stdout)
                connected_apps = metadata_result.get('result', [])
                
                # Look for our Connected App
                for app in connected_apps:
                    if app.get('fullName') == 'AWS_Lambda_PubSub_App':
                        console.print(f"[green]✅ Found Connected App: {app.get('fullName')}[/green]")
                        
                        # Try to get the Consumer Key using a different method
                        # The Consumer Key might be available in the org display
                        org_result = subprocess.run([
                            "sf", "org", "display",
                            "--target-org", f"socal-dreamin-2025-aws-{environment}",
                            "--json"
                        ], cwd=salesforce_dir, capture_output=True, text=True)
                        
                        if org_result.returncode == 0:
                            org_data = json.loads(org_result.stdout)
                            # Check if Consumer Key is in org info
                            consumer_key = org_data.get('result', {}).get('consumerKey')
                            if consumer_key:
                                console.print(f"[green]✅ Connected App Consumer Key: {consumer_key}[/green]")
                                return consumer_key
                        
                        # If not found in org display, try to retrieve the Connected App details
                        # using the org list metadata with specific name
                        detail_result = subprocess.run([
                            "sf", "org", "list", "metadata",
                            "--metadata-type", "ConnectedApp",
                            "--target-org", f"socal-dreamin-2025-aws-{environment}",
                            "--json"
                        ], cwd=salesforce_dir, capture_output=True, text=True)
                        
                        if detail_result.returncode == 0:
                            detail_data = json.loads(detail_result.stdout)
                            # Look for Consumer Key in the detailed result
                            apps = detail_data.get('result', [])
                            for app_detail in apps:
                                if app_detail.get('fullName') == 'AWS_Lambda_PubSub_App':
                                    consumer_key = app_detail.get('consumerKey')
                                    if consumer_key:
                                        console.print(f"[green]✅ Connected App Consumer Key: {consumer_key}[/green]")
                                        return consumer_key
                
                # If we still haven't found it, try a manual approach
                console.print("[yellow]⚠️  Consumer Key not found in metadata. Trying alternative approach...[/yellow]")
                
                # Try to query the Connected App using SOQL
                soql_result = subprocess.run([
                    "sf", "data", "query",
                    "--query", "SELECT Id, Name, ConsumerKey FROM ConnectedApplication WHERE Name = 'AWS Lambda PubSub App'",
                    "--target-org", f"socal-dreamin-2025-aws-{environment}",
                    "--json"
                ], cwd=salesforce_dir, capture_output=True, text=True)
                
                if soql_result.returncode == 0:
                    soql_data = json.loads(soql_result.stdout)
                    records = soql_data.get('result', {}).get('records', [])
                    if records:
                        consumer_key = records[0].get('ConsumerKey')
                        if consumer_key:
                            console.print(f"[green]✅ Connected App Consumer Key: {consumer_key}[/green]")
                            return consumer_key
                
                console.print("[red]❌ Could not find Consumer Key. You may need to check the Connected App manually in Salesforce Setup.[/red]")
                return None
                
            except json.JSONDecodeError as e:
                console.print(f"[red]❌ Failed to parse Connected App metadata: {e}[/red]")
                return None
            
        except Exception as e:
            console.print(f"[red]❌ Failed to setup Connected App: {e}[/red]")
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

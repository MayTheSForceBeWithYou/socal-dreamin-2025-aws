#!/usr/bin/env python3
"""
Complete Lab Infrastructure Deployment Script
Implements the master setup command: python -m setup_tools deploy-complete-lab
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from setup_tools.core.config import get_config
from setup_tools.core.logger import get_logger, SetupToolsLogger
from setup_tools.core.exceptions import SetupToolsError
from setup_tools.utils.shell_executor import ShellExecutor

console = Console()
logger = SetupToolsLogger()


class LabDeploymentManager:
    """Manages the complete lab infrastructure deployment."""
    
    def __init__(self, config_path: Optional[str] = None, dry_run: bool = False):
        self.config = get_config(config_path)
        self.dry_run = dry_run
        self.project_root = project_root
        self.terraform_dir = self.project_root / "aws" / "terraform"
        self.results = {}
        
    def validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met."""
        console.print("[bold blue]🔍 Validating Prerequisites[/bold blue]")
        
        checks = [
            ("AWS CLI", self._check_aws_cli),
            ("Terraform", self._check_terraform),
            ("SSH Key", self._check_ssh_key),
            ("Salesforce Config", self._check_salesforce_config),
            ("Terraform Variables", self._check_terraform_vars),
        ]
        
        all_passed = True
        for name, check_func in checks:
            try:
                if check_func():
                    console.print(f"✅ {name}")
                else:
                    console.print(f"❌ {name}")
                    all_passed = False
            except Exception as e:
                console.print(f"❌ {name}: {e}")
                all_passed = False
        
        if not all_passed:
            console.print("[red]❌ Prerequisites validation failed[/red]")
            return False
            
        console.print("[green]✅ All prerequisites validated[/green]")
        return True
    
    def _check_aws_cli(self) -> bool:
        """Check if AWS CLI is configured."""
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_terraform(self) -> bool:
        """Check if Terraform is installed."""
        try:
            result = subprocess.run(
                ["terraform", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_ssh_key(self) -> bool:
        """Check if SSH key exists."""
        ssh_key_path = self.project_root / "aws" / "certs" / "aws-ec2"
        return ssh_key_path.exists()
    
    def _check_salesforce_config(self) -> bool:
        """Check if Salesforce configuration exists."""
        sfdc_config = self.project_root / "aws" / "sfdc-auth-secrets.json"
        return sfdc_config.exists()
    
    def _check_terraform_vars(self) -> bool:
        """Check if Terraform variables file exists."""
        tfvars = self.terraform_dir / "terraform.tfvars"
        return tfvars.exists()
    
    def deploy_infrastructure(self) -> bool:
        """Deploy the Terraform infrastructure."""
        console.print("[bold blue]🏗️  Deploying Infrastructure[/bold blue]")
        
        if self.dry_run:
            console.print("[yellow]🔍 DRY RUN: Would deploy infrastructure[/yellow]")
            return True
        
        try:
            # Change to terraform directory
            os.chdir(self.terraform_dir)
            
            # Initialize Terraform
            console.print("Initializing Terraform...")
            result = subprocess.run(
                ["terraform", "init"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                console.print(f"[red]❌ Terraform init failed: {result.stderr}[/red]")
                return False
            
            # Plan deployment
            console.print("Planning Terraform deployment...")
            result = subprocess.run(
                ["terraform", "plan"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                console.print(f"[red]❌ Terraform plan failed: {result.stderr}[/red]")
                return False
            
            # Apply deployment
            console.print("Applying Terraform deployment...")
            result = subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                capture_output=True,
                text=True,
                timeout=900  # 15 minutes
            )
            if result.returncode != 0:
                console.print(f"[red]❌ Terraform apply failed: {result.stderr}[/red]")
                return False
            
            console.print("[green]✅ Infrastructure deployed successfully[/green]")
            return True
            
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Terraform deployment timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Infrastructure deployment failed: {e}[/red]")
            return False
        finally:
            # Return to project root
            os.chdir(self.project_root)
    
    def get_infrastructure_outputs(self) -> Dict[str, str]:
        """Get Terraform outputs."""
        try:
            os.chdir(self.terraform_dir)
            result = subprocess.run(
                ["terraform", "output", "-json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                console.print(f"[red]❌ Failed to get Terraform outputs: {result.stderr}[/red]")
                return {}
            
            outputs = json.loads(result.stdout)
            return {k: v["value"] for k, v in outputs.items()}
            
        except Exception as e:
            console.print(f"[red]❌ Error getting outputs: {e}[/red]")
            return {}
        finally:
            os.chdir(self.project_root)
    
    def deploy_application(self) -> bool:
        """Deploy the application to EC2."""
        console.print("[bold blue]📦 Deploying Application[/bold blue]")
        
        if self.dry_run:
            console.print("[yellow]🔍 DRY RUN: Would deploy application[/yellow]")
            return True
        
        try:
            # Get infrastructure outputs
            outputs = self.get_infrastructure_outputs()
            if not outputs:
                console.print("[red]❌ No infrastructure outputs available[/red]")
                return False
            
            ec2_ip = outputs.get("ec2_public_ip")
            if not ec2_ip:
                console.print("[red]❌ EC2 IP not found in outputs[/red]")
                return False
            
            # Wait for EC2 to be ready
            console.print(f"Waiting for EC2 instance {ec2_ip} to be ready...")
            if not self._wait_for_ec2_ready(ec2_ip):
                console.print("[red]❌ EC2 instance not ready[/red]")
                return False
            
            # Deploy application using existing script
            deploy_script = self.project_root / "scripts" / "deploy-application.sh"
            if not deploy_script.exists():
                console.print("[red]❌ Deploy application script not found[/red]")
                return False
            
            console.print("Deploying application to EC2...")
            result = subprocess.run(
                ["bash", str(deploy_script)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                console.print(f"[red]❌ Application deployment failed: {result.stderr}[/red]")
                return False
            
            console.print("[green]✅ Application deployed successfully[/green]")
            return True
            
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Application deployment timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Application deployment failed: {e}[/red]")
            return False
    
    def _wait_for_ec2_ready(self, ec2_ip: str, timeout: int = 300) -> bool:
        """Wait for EC2 instance to be ready."""
        ssh_key = self.project_root / "aws" / "certs" / "aws-ec2"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    [
                        "ssh", "-i", str(ssh_key),
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=10",
                        f"ec2-user@{ec2_ip}",
                        "echo 'ready'"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
            
            time.sleep(10)
        
        return False
    
    def setup_dashboard_access(self) -> bool:
        """Set up OpenSearch dashboard access."""
        console.print("[bold blue]📊 Setting Up Dashboard Access[/bold blue]")
        
        outputs = self.get_infrastructure_outputs()
        if not outputs:
            console.print("[red]❌ No infrastructure outputs available[/red]")
            return False
        
        opensearch_endpoint = outputs.get("opensearch_endpoint")
        opensearch_password = outputs.get("opensearch_master_password")
        
        if not opensearch_endpoint:
            console.print("[red]❌ OpenSearch endpoint not found[/red]")
            return False
        
        # Create dashboard access script
        self._create_dashboard_access_script(opensearch_endpoint, opensearch_password)
        
        console.print("[green]✅ Dashboard access configured[/green]")
        return True
    
    def _create_dashboard_access_script(self, endpoint: str, password: str):
        """Create a script for accessing OpenSearch dashboards."""
        script_content = f'''#!/bin/bash
# OpenSearch Dashboard Access Script
# Generated by setup_tools

set -e

OPENSEARCH_ENDPOINT="{endpoint}"
OPENSEARCH_PASSWORD="{password}"

echo "🔍 OpenSearch Dashboard Access"
echo "=============================="
echo ""
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "Dashboard URL: https://$OPENSEARCH_ENDPOINT/_dashboards/"
echo ""
echo "📝 Login Credentials:"
echo "Username: admin"
echo "Password: $OPENSEARCH_PASSWORD"
echo ""
echo "🚀 Access Methods:"
echo ""
echo "Method 1: Direct Browser Access"
echo "-------------------------------"
echo "1. Open your browser"
echo "2. Go to: https://$OPENSEARCH_ENDPOINT/_dashboards/"
echo "3. Login with:"
echo "   Username: admin"
echo "   Password: $OPENSEARCH_PASSWORD"
echo ""
echo "Method 2: Test Connection"
echo "-------------------------"
echo "Test the connection:"
echo "curl -u admin:$OPENSEARCH_PASSWORD https://$OPENSEARCH_ENDPOINT/"
echo ""
echo "📊 Once logged in, you can:"
echo "- View indexed Salesforce login events"
echo "- Create visualizations and dashboards"
echo "- Search and filter data"
echo "- Set up monitoring alerts"
echo ""
'''
        
        script_path = self.project_root / "scripts" / "access-opensearch-dashboards.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
    
    def validate_deployment(self) -> bool:
        """Validate the complete deployment."""
        console.print("[bold blue]✅ Validating Deployment[/bold blue]")
        
        outputs = self.get_infrastructure_outputs()
        if not outputs:
            console.print("[red]❌ No infrastructure outputs available[/red]")
            return False
        
        validations = [
            ("EC2 Instance", self._validate_ec2),
            ("OpenSearch Domain", self._validate_opensearch),
            ("Application Service", self._validate_application),
            ("Data Pipeline", self._validate_data_pipeline),
        ]
        
        all_passed = True
        for name, validation_func in validations:
            try:
                if validation_func(outputs):
                    console.print(f"✅ {name}")
                else:
                    console.print(f"❌ {name}")
                    all_passed = False
            except Exception as e:
                console.print(f"❌ {name}: {e}")
                all_passed = False
        
        if all_passed:
            console.print("[green]✅ All validations passed[/green]")
        else:
            console.print("[red]❌ Some validations failed[/red]")
        
        return all_passed
    
    def _validate_ec2(self, outputs: Dict[str, str]) -> bool:
        """Validate EC2 instance."""
        ec2_ip = outputs.get("ec2_public_ip")
        if not ec2_ip:
            return False
        
        ssh_key = self.project_root / "aws" / "certs" / "aws-ec2"
        try:
            result = subprocess.run(
                [
                    "ssh", "-i", str(ssh_key),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"ec2-user@{ec2_ip}",
                    "echo 'connected'"
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0
        except:
            return False
    
    def _validate_opensearch(self, outputs: Dict[str, str]) -> bool:
        """Validate OpenSearch domain."""
        endpoint = outputs.get("opensearch_endpoint")
        password = outputs.get("opensearch_master_password")
        
        if not endpoint or not password:
            return False
        
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-u", f"admin:{password}",
                    f"https://{endpoint}/"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _validate_application(self, outputs: Dict[str, str]) -> bool:
        """Validate application service."""
        ec2_ip = outputs.get("ec2_public_ip")
        if not ec2_ip:
            return False
        
        ssh_key = self.project_root / "aws" / "certs" / "aws-ec2"
        try:
            result = subprocess.run(
                [
                    "ssh", "-i", str(ssh_key),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"ec2-user@{ec2_ip}",
                    "sudo systemctl is-active salesforce-streamer"
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0 and "active" in result.stdout
        except:
            return False
    
    def _validate_data_pipeline(self, outputs: Dict[str, str]) -> bool:
        """Validate data pipeline."""
        endpoint = outputs.get("opensearch_endpoint")
        password = outputs.get("opensearch_master_password")
        
        if not endpoint or not password:
            return False
        
        try:
            # Check if there's data in the index
            result = subprocess.run(
                [
                    "curl", "-s", "-u", f"admin:{password}",
                    f"https://{endpoint}/salesforce-login-events/_count"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("count", 0) > 0
            return False
        except:
            return False
    
    def display_summary(self):
        """Display deployment summary."""
        outputs = self.get_infrastructure_outputs()
        if not outputs:
            console.print("[red]❌ No outputs available[/red]")
            return
        
        # Create summary table
        table = Table(title="🚀 Lab Deployment Summary")
        table.add_column("Component", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("EC2 Instance IP", outputs.get("ec2_public_ip", "N/A"))
        table.add_row("OpenSearch Endpoint", outputs.get("opensearch_endpoint", "N/A"))
        table.add_row("Dashboard URL", f"https://{outputs.get('opensearch_endpoint', 'N/A')}/_dashboards/")
        table.add_row("SSH Command", outputs.get("ssh_command", "N/A"))
        
        console.print(table)
        
        # Display credentials
        password = outputs.get("opensearch_master_password")
        if password:
            console.print(Panel(
                f"OpenSearch Login Credentials:\n"
                f"Username: admin\n"
                f"Password: {password}",
                title="🔐 Dashboard Access",
                border_style="green"
            ))
        
        # Display next steps
        console.print(Panel(
            "Next Steps:\n"
            "1. Access OpenSearch Dashboards using the credentials above\n"
            "2. Run: ./scripts/access-opensearch-dashboards.sh\n"
            "3. Check application logs: ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>\n"
            "4. Monitor data pipeline in OpenSearch Dashboards",
            title="📋 Next Steps",
            border_style="blue"
        ))


@click.command()
@click.option('--environment', default='demo', help='Environment name')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--dry-run', is_flag=True, help='Preview operations without executing')
@click.option('--validate', is_flag=True, help='Run validation after deployment')
@click.option('--skip-prereqs', is_flag=True, help='Skip prerequisite validation')
def deploy_complete_lab(environment, config, dry_run, validate, skip_prereqs):
    """Deploy complete lab infrastructure and application."""
    
    console.print(Panel(
        f"🚀 Deploying Complete Lab Infrastructure\n"
        f"Environment: {environment}\n"
        f"Dry Run: {dry_run}\n"
        f"Validate: {validate}",
        title="Lab Deployment",
        border_style="blue"
    ))
    
    # Initialize deployment manager
    manager = LabDeploymentManager(config, dry_run)
    
    try:
        # Step 1: Validate prerequisites
        if not skip_prereqs:
            if not manager.validate_prerequisites():
                console.print("[red]❌ Prerequisites validation failed[/red]")
                return
        
        # Step 2: Deploy infrastructure
        if not manager.deploy_infrastructure():
            console.print("[red]❌ Infrastructure deployment failed[/red]")
            return
        
        # Step 3: Deploy application
        if not manager.deploy_application():
            console.print("[red]❌ Application deployment failed[/red]")
            return
        
        # Step 4: Setup dashboard access
        if not manager.setup_dashboard_access():
            console.print("[red]❌ Dashboard access setup failed[/red]")
            return
        
        # Step 5: Validate deployment
        if validate:
            if not manager.validate_deployment():
                console.print("[red]❌ Deployment validation failed[/red]")
                return
        
        # Step 6: Display summary
        manager.display_summary()
        
        console.print("[green]🎉 Lab deployment completed successfully![/green]")
        
    except KeyboardInterrupt:
        console.print("[yellow]⚠️  Deployment interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Deployment failed: {e}[/red]")
        raise


if __name__ == "__main__":
    deploy_complete_lab()

#!/usr/bin/env python3
"""
Comprehensive Lab Validation Suite
Implements: python -m setup_tools validate-lab --comprehensive
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()


class LabValidator:
    """Comprehensive lab validation system."""
    
    def __init__(self):
        self.project_root = project_root
        self.terraform_dir = self.project_root / "aws" / "terraform"
        self.results = {}
        
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
    
    def validate_terraform_deployment(self) -> Tuple[bool, str]:
        """Validate Terraform deployment."""
        try:
            os.chdir(self.terraform_dir)
            
            # Check if terraform state exists
            if not (self.terraform_dir / "terraform.tfstate").exists():
                return False, "No Terraform state file found"
            
            # Run terraform plan to check for drift
            result = subprocess.run(
                ["terraform", "plan", "-detailed-exitcode"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, "No changes needed"
            elif result.returncode == 2:
                return False, "Infrastructure has drifted from configuration"
            else:
                return False, f"Terraform plan failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Terraform plan timed out"
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            os.chdir(self.project_root)
    
    def validate_ec2_instance(self, outputs: Dict[str, str]) -> Tuple[bool, str]:
        """Validate EC2 instance."""
        ec2_ip = outputs.get("ec2_public_ip")
        if not ec2_ip:
            return False, "EC2 IP not found in outputs"
        
        ssh_key = self.project_root / "aws" / "certs" / "aws-ec2"
        if not ssh_key.exists():
            return False, "SSH key not found"
        
        try:
            # Test SSH connection
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
            
            if result.returncode != 0:
                return False, f"SSH connection failed: {result.stderr}"
            
            # Check if application service is running
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
            
            if result.returncode != 0 or "active" not in result.stdout:
                return False, "Salesforce streamer service not active"
            
            return True, f"EC2 instance {ec2_ip} is healthy and service is running"
            
        except subprocess.TimeoutExpired:
            return False, "SSH connection timed out"
        except Exception as e:
            return False, f"Error: {e}"
    
    def validate_opensearch_cluster(self, outputs: Dict[str, str]) -> Tuple[bool, str]:
        """Validate OpenSearch cluster."""
        endpoint = outputs.get("opensearch_endpoint")
        password = outputs.get("opensearch_master_password")
        
        if not endpoint or not password:
            return False, "OpenSearch endpoint or password not found"
        
        try:
            # Test basic connectivity
            credentials = f"os_admin:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            response = requests.get(
                f"https://{endpoint}/",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code != 200:
                return False, f"OpenSearch connection failed: {response.status_code}"
            
            # Check cluster health
            response = requests.get(
                f"https://{endpoint}/_cluster/health",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code != 200:
                return False, "Failed to get cluster health"
            
            health_data = response.json()
            cluster_status = health_data.get("status")
            
            if cluster_status not in ["green", "yellow"]:
                return False, f"Cluster status is {cluster_status} (should be green or yellow)"
            
            return True, f"OpenSearch cluster is healthy (status: {cluster_status})"
            
        except requests.exceptions.RequestException as e:
            return False, f"OpenSearch connection error: {e}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def validate_salesforce_connectivity(self, outputs: Dict[str, str]) -> Tuple[bool, str]:
        """Validate Salesforce connectivity."""
        ec2_ip = outputs.get("ec2_public_ip")
        if not ec2_ip:
            return False, "EC2 IP not found"
        
        ssh_key = self.project_root / "aws" / "certs" / "aws-ec2"
        
        try:
            # Check application logs for Salesforce connectivity
            result = subprocess.run(
                [
                    "ssh", "-i", str(ssh_key),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"ec2-user@{ec2_ip}",
                    "sudo journalctl -u salesforce-streamer --since '5 minutes ago' --no-pager"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, "Failed to get application logs"
            
            logs = result.stdout.lower()
            
            # Look for success indicators
            if "authentication successful" in logs or "login events retrieved" in logs:
                return True, "Salesforce authentication and data retrieval working"
            elif "authentication failed" in logs or "error" in logs:
                return False, "Salesforce connectivity issues detected in logs"
            else:
                return True, "No connectivity errors detected in recent logs"
                
        except subprocess.TimeoutExpired:
            return False, "Log retrieval timed out"
        except Exception as e:
            return False, f"Error: {e}"
    
    def validate_data_pipeline(self, outputs: Dict[str, str]) -> Tuple[bool, str]:
        """Validate data pipeline functionality."""
        endpoint = outputs.get("opensearch_endpoint")
        password = outputs.get("opensearch_master_password")
        
        if not endpoint or not password:
            return False, "OpenSearch credentials not available"
        
        try:
            credentials = f"os_admin:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Check if the index exists
            response = requests.get(
                f"https://{endpoint}/salesforce-login-events",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code == 404:
                return False, "Salesforce login events index does not exist"
            elif response.status_code != 200:
                return False, f"Failed to check index: {response.status_code}"
            
            # Check document count
            response = requests.get(
                f"https://{endpoint}/salesforce-login-events/_count",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code != 200:
                return False, "Failed to get document count"
            
            count_data = response.json()
            doc_count = count_data.get("count", 0)
            
            if doc_count == 0:
                return False, "No documents found in the index"
            
            # Check for recent documents
            response = requests.get(
                f"https://{endpoint}/salesforce-login-events/_search?size=1&sort=@timestamp:desc",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code != 200:
                return False, "Failed to check recent documents"
            
            search_data = response.json()
            hits = search_data.get("hits", {}).get("hits", [])
            
            if not hits:
                return False, "No recent documents found"
            
            latest_doc = hits[0]["_source"]
            timestamp = latest_doc.get("@timestamp", "unknown")
            
            return True, f"Data pipeline working: {doc_count} documents indexed, latest at {timestamp}"
            
        except requests.exceptions.RequestException as e:
            return False, f"Data pipeline validation error: {e}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def validate_dashboard_access(self, outputs: Dict[str, str]) -> Tuple[bool, str]:
        """Validate dashboard access."""
        endpoint = outputs.get("opensearch_endpoint")
        password = outputs.get("opensearch_master_password")
        
        if not endpoint or not password:
            return False, "OpenSearch credentials not available"
        
        try:
            credentials = f"os_admin:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Test dashboard endpoint
            response = requests.get(
                f"https://{endpoint}/_dashboards/",
                headers={'Authorization': f'Basic {encoded_credentials}'},
                timeout=30
            )
            
            if response.status_code == 200:
                return True, f"Dashboard accessible at https://{endpoint}/_dashboards/"
            elif response.status_code == 401:
                return False, "Dashboard requires authentication"
            else:
                return False, f"Dashboard access failed: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Dashboard access error: {e}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def run_comprehensive_validation(self) -> Dict[str, Tuple[bool, str]]:
        """Run comprehensive validation suite."""
        console.print("[bold blue]🔍 Running Comprehensive Lab Validation[/bold blue]")
        
        # Get infrastructure outputs
        outputs = self.get_infrastructure_outputs()
        if not outputs:
            console.print("[red]❌ No infrastructure outputs available[/red]")
            return {}
        
        # Define validation tests
        validations = [
            ("Terraform Deployment", lambda: self.validate_terraform_deployment()),
            ("EC2 Instance", lambda: self.validate_ec2_instance(outputs)),
            ("OpenSearch Cluster", lambda: self.validate_opensearch_cluster(outputs)),
            ("Salesforce Connectivity", lambda: self.validate_salesforce_connectivity(outputs)),
            ("Data Pipeline", lambda: self.validate_data_pipeline(outputs)),
            ("Dashboard Access", lambda: self.validate_dashboard_access(outputs)),
        ]
        
        results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            for name, validation_func in validations:
                task = progress.add_task(f"Validating {name}...", total=1)
                
                try:
                    success, message = validation_func()
                    results[name] = (success, message)
                    
                    if success:
                        progress.update(task, completed=1, description=f"✅ {name}")
                    else:
                        progress.update(task, completed=1, description=f"❌ {name}")
                        
                except Exception as e:
                    results[name] = (False, f"Validation error: {e}")
                    progress.update(task, completed=1, description=f"❌ {name}")
        
        return results
    
    def display_validation_results(self, results: Dict[str, Tuple[bool, str]]):
        """Display validation results."""
        # Create results table
        table = Table(title="🔍 Validation Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="white")
        
        success_count = 0
        total_count = len(results)
        
        for name, (success, message) in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            table.add_row(name, status, message)
            if success:
                success_count += 1
        
        console.print(table)
        
        # Summary
        console.print(f"\n[bold]Summary: {success_count}/{total_count} validations passed[/bold]")
        
        if success_count == total_count:
            console.print("[green]🎉 All validations passed! Lab is fully operational.[/green]")
        else:
            console.print("[red]❌ Some validations failed. Check the details above.[/red]")
        
        # Display access information
        outputs = self.get_infrastructure_outputs()
        if outputs:
            console.print(Panel(
                f"OpenSearch Dashboard: https://{outputs.get('opensearch_endpoint', 'N/A')}/_dashboards/\n"
                f"Username: os_admin\n"
                f"Password: {outputs.get('opensearch_master_password', 'N/A')}\n"
                f"SSH Command: {outputs.get('ssh_command', 'N/A')}",
                title="🔐 Access Information",
                border_style="green" if success_count == total_count else "yellow"
            ))


@click.command()
@click.option('--comprehensive', is_flag=True, help='Run comprehensive validation suite')
@click.option('--component', help='Validate specific component (terraform, ec2, opensearch, salesforce, pipeline, dashboard)')
def validate_lab(comprehensive: bool, component: Optional[str]):
    """Validate lab infrastructure and functionality."""
    
    console.print(Panel(
        "🔍 Lab Validation Suite\n"
        "Validates infrastructure, services, and data pipeline",
        title="Validation",
        border_style="blue"
    ))
    
    validator = LabValidator()
    
    if comprehensive:
        # Run comprehensive validation
        results = validator.run_comprehensive_validation()
        validator.display_validation_results(results)
        
    elif component:
        # Validate specific component
        outputs = validator.get_infrastructure_outputs()
        if not outputs:
            console.print("[red]❌ No infrastructure outputs available[/red]")
            return
        
        component_validators = {
            'terraform': validator.validate_terraform_deployment,
            'ec2': lambda: validator.validate_ec2_instance(outputs),
            'opensearch': lambda: validator.validate_opensearch_cluster(outputs),
            'salesforce': lambda: validator.validate_salesforce_connectivity(outputs),
            'pipeline': lambda: validator.validate_data_pipeline(outputs),
            'dashboard': lambda: validator.validate_dashboard_access(outputs),
        }
        
        if component not in component_validators:
            console.print(f"[red]❌ Unknown component: {component}[/red]")
            console.print(f"Available components: {', '.join(component_validators.keys())}")
            return
        
        console.print(f"[blue]🔍 Validating {component}...[/blue]")
        success, message = component_validators[component]()
        
        if success:
            console.print(f"[green]✅ {component}: {message}[/green]")
        else:
            console.print(f"[red]❌ {component}: {message}[/red]")
    
    else:
        console.print("[yellow]⚠️  Please specify --comprehensive or --component[/yellow]")


if __name__ == "__main__":
    validate_lab()

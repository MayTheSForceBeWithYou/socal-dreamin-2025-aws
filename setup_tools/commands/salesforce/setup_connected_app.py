"""
Setup Salesforce Connected App command.
"""

import subprocess
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:setup-connected-app")
class SetupConnectedAppCommand(BaseCommand):
    """Set up Salesforce Connected App and return Consumer Key."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, contact_email: Optional[str] = None, environment: str = "demo", **kwargs) -> Dict[str, Any]:
        """
        Set up Salesforce Connected App and return Consumer Key.
        
        Args:
            contact_email: Contact email for the Connected App
            environment: Environment name for org targeting
            
        Returns:
            Dictionary with Connected App setup results
            
        Raises:
            SalesforceError: If Connected App setup fails
        """
        # Use config default if not provided
        contact_email = contact_email or self.config.salesforce.contact_email
        
        self.console.print("[bold blue]Setting up Salesforce Connected App...[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs(contact_email=contact_email)
            
            # Check if sf CLI is available
            if not self.shell.check_command_exists("sf"):
                raise SalesforceError("Salesforce CLI (sf) is not installed or not in PATH")
            
            # Change to Salesforce directory
            salesforce_dir = self.config.root_dir / "salesforce"
            if not salesforce_dir.exists():
                raise SalesforceError(f"Salesforce directory not found: {salesforce_dir}")
            
            # Ensure certificate exists
            if not self._ensure_certificate():
                raise SalesforceError("Failed to ensure Salesforce certificate exists")
            
            # Update Connected App XML with certificate and contact email
            self._update_connected_app_xml(contact_email)
            
            # Deploy the Connected App
            self.console.print("Deploying Connected App to Salesforce...")
            self._deploy_connected_app(salesforce_dir, environment)
            
            # Retrieve and extract Consumer Key
            self.console.print("Retrieving Connected App Consumer Key...")
            consumer_key = self._get_consumer_key(salesforce_dir, environment)
            
            if not consumer_key:
                raise SalesforceError("Failed to retrieve Consumer Key")
            
            self.console.print(f"[green]✅ Connected App setup completed successfully![/green]")
            self.console.print(f"[blue]Consumer Key: {consumer_key}[/blue]")
            
            return {
                'success': True,
                'contact_email': contact_email,
                'environment': environment,
                'consumer_key': consumer_key
            }
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to setup Connected App: {e}")
    
    def validate_inputs(self, contact_email: str, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            contact_email: Contact email for the Connected App
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate email
        self.validators.validate_email(contact_email)
        
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
        
        # Validate Connected App XML exists
        connected_app_path = salesforce_dir / "force-app" / "main" / "default" / "connectedApps" / "AWS_Lambda_PubSub_App.connectedApp-meta.xml"
        self.validators.validate_file_path(connected_app_path, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Set up Salesforce Connected App and retrieve Consumer Key"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'contact_email': 'Contact email for the Connected App (defaults to config)',
            'environment': 'Environment name for org targeting (default: demo)'
        }
    
    def _ensure_certificate(self) -> bool:
        """Ensure Salesforce certificate exists, generate if needed."""
        try:
            salesforce_dir = self.config.root_dir / "salesforce"
            cert_dir = salesforce_dir / "certs"
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            private_key_path = cert_dir / "aws-to-sf-cert.key"
            certificate_path = cert_dir / "aws-to-sf-cert.crt"
            
            # Check if certificate files already exist
            if private_key_path.exists() and certificate_path.exists():
                self.logger.info("Salesforce certificate already exists")
                return True
            
            # Generate certificate if it doesn't exist
            self.console.print("Generating Salesforce certificate...")
            
            # Check if OpenSSL is available
            if not self.shell.check_command_exists("openssl"):
                raise SalesforceError("OpenSSL is not installed or not in PATH")
            
            # Generate private key
            key_command = [
                "openssl", "genrsa",
                "-out", str(private_key_path),
                "2048"
            ]
            
            result = self.shell.execute(key_command, capture_output=True)
            if result.returncode != 0:
                raise SalesforceError(f"Failed to generate private key: {result.stderr}")
            
            # Generate certificate
            cert_command = [
                "openssl", "req", "-new", "-x509",
                "-key", str(private_key_path),
                "-out", str(certificate_path),
                "-days", "365",
                "-subj", "/C=US/ST=CA/L=San Francisco/O=SoCal Dreamin/OU=AWS Demo/CN=salesforce-integration"
            ]
            
            result = self.shell.execute(cert_command, capture_output=True)
            if result.returncode != 0:
                raise SalesforceError(f"Failed to generate certificate: {result.stderr}")
            
            self.console.print("[green]✅ Salesforce certificate generated successfully[/green]")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to ensure Salesforce certificate: {e}")
            return False
    
    def _update_connected_app_xml(self, contact_email: str) -> None:
        """Update Connected App XML with certificate and contact email."""
        try:
            salesforce_dir = self.config.root_dir / "salesforce"
            connected_app_path = salesforce_dir / "force-app" / "main" / "default" / "connectedApps" / "AWS_Lambda_PubSub_App.connectedApp-meta.xml"
            
            # Read certificate content
            cert_path = salesforce_dir / "certs" / "aws-to-sf-cert.crt"
            with open(cert_path, 'r') as f:
                cert_content = f.read()
            
            # Remove BEGIN/END lines and concatenate
            cert_lines = cert_content.strip().split('\n')
            cert_body = ''.join([line.strip() for line in cert_lines 
                               if not line.startswith('-----BEGIN') and not line.startswith('-----END')])
            
            # Read and update XML
            with open(connected_app_path, 'r') as f:
                xml_content = f.read()
            
            # Replace contact email and certificate
            xml_content = xml_content.replace('replace@with.your.email', contact_email)
            xml_content = xml_content.replace('FROM_salesforce/certs/aws-to-sf-cert_WITHOUT_BEGIN_OR_END_LINES', cert_body)
            
            # Write updated XML
            with open(connected_app_path, 'w') as f:
                f.write(xml_content)
            
            self.logger.info(f"Updated Connected App XML with email: {contact_email}")
            
        except Exception as e:
            raise SalesforceError(f"Failed to update Connected App XML: {e}")
    
    def _deploy_connected_app(self, salesforce_dir: Path, environment: str) -> None:
        """Deploy the Connected App to Salesforce."""
        try:
            command = [
                "sf", "project", "deploy", "start",
                "--source-dir", "force-app/main/default/connectedApps",
                "--target-org", f"socal-dreamin-2025-aws-{environment}"
            ]
            
            result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
            
            if result.returncode != 0:
                # Display both stdout and stderr for debugging
                self.console.print(f"[red]❌ Command failed: {' '.join(command)}[/red]")
                if result.stdout:
                    self.console.print(f"[yellow]Standard output:[/yellow]")
                    self.console.print(f"[yellow]{result.stdout}[/yellow]")
                if result.stderr:
                    self.console.print(f"[red]Error output:[/red]")
                    self.console.print(f"[red]{result.stderr}[/red]")
                
                # Try to execute the command again without capture_output to see the actual error
                self.console.print(f"[yellow]Executing command again to show full output...[/yellow]")
                try:
                    self.shell.execute(command, cwd=salesforce_dir, capture_output=False)
                except Exception as debug_error:
                    self.console.print(f"[red]Full error output:[/red]")
                    self.console.print(f"[red]{debug_error}[/red]")
                
                raise SalesforceError(f"Failed to deploy Connected App: {result.stderr}")
            
            self.logger.info("Connected App deployed successfully")
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to deploy Connected App: {e}")
    
    def _get_consumer_key(self, salesforce_dir: Path, environment: str) -> Optional[str]:
        """Retrieve and extract Consumer Key from Connected App."""
        try:
            connected_app_path = salesforce_dir / "force-app" / "main" / "default" / "connectedApps" / "AWS_Lambda_PubSub_App.connectedApp-meta.xml"
            
            # Retrieve the Connected App
            command = [
                "sf", "project", "retrieve", "start",
                "--source-dir", str(connected_app_path),
                "--target-org", f"socal-dreamin-2025-aws-{environment}",
                "--json"
            ]
            
            result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
            
            if result.returncode != 0:
                # Display both stdout and stderr for debugging
                self.console.print(f"[red]❌ Retrieve command failed: {' '.join(command)}[/red]")
                if result.stdout:
                    self.console.print(f"[yellow]Standard output:[/yellow]")
                    self.console.print(f"[yellow]{result.stdout}[/yellow]")
                if result.stderr:
                    self.console.print(f"[red]Error output:[/red]")
                    self.console.print(f"[red]{result.stderr}[/red]")
                raise SalesforceError(f"Failed to retrieve Connected App: {result.stderr}")
            
            # Parse the retrieve result
            retrieve_result = json.loads(result.stdout)
            
            if retrieve_result.get('status') == 0:
                self.logger.info("Successfully retrieved Connected App metadata")
                
                # Try to read the retrieved XML file to get Consumer Key
                if connected_app_path.exists():
                    # Parse the retrieved XML
                    tree = ET.parse(connected_app_path)
                    root = tree.getroot()
                    
                    # Look for consumerKey in the XML - handle namespace properly
                    consumer_key_elem = root.find('.//{http://soap.sforce.com/2006/04/metadata}consumerKey')
                    if consumer_key_elem is not None and consumer_key_elem.text:
                        consumer_key = consumer_key_elem.text.strip()
                        return consumer_key
                
                # If not found in XML, try SOQL query as fallback
                self.logger.warning("Consumer Key not found in XML, trying SOQL query...")
                
                soql_command = [
                    "sf", "data", "query",
                    "--query", "SELECT Id, Name, ConsumerKey FROM ConnectedApplication WHERE Name = 'AWS Lambda PubSub App'",
                    "--target-org", f"socal-dreamin-2025-aws-{environment}",
                    "--json"
                ]
                
                soql_result = self.shell.execute(soql_command, cwd=salesforce_dir, capture_output=True)
                
                if soql_result.returncode == 0:
                    soql_data = json.loads(soql_result.stdout)
                    records = soql_data.get('result', {}).get('records', [])
                    if records:
                        consumer_key = records[0].get('ConsumerKey')
                        if consumer_key:
                            return consumer_key
                else:
                    # Display SOQL query error details
                    self.console.print(f"[red]❌ SOQL query failed: {' '.join(soql_command)}[/red]")
                    if soql_result.stdout:
                        self.console.print(f"[yellow]SOQL Standard output:[/yellow]")
                        self.console.print(f"[yellow]{soql_result.stdout}[/yellow]")
                    if soql_result.stderr:
                        self.console.print(f"[red]SOQL Error output:[/red]")
                        self.console.print(f"[red]{soql_result.stderr}[/red]")
                
                raise SalesforceError("Could not find Consumer Key in retrieved metadata or SOQL query")
            else:
                raise SalesforceError(f"Retrieve command failed: {retrieve_result.get('message', 'Unknown error')}")
                
        except Exception as e:
            raise SalesforceError(f"Failed to get Consumer Key: {e}")

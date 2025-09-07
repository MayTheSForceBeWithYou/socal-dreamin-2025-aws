"""
Generate Salesforce certificate command.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import CertificateError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:generate-certificate")
class GenerateSalesforceCertificateCommand(BaseCommand):
    """Generate digital certificate for Salesforce integration."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Generate digital certificate for Salesforce integration.
        
        Returns:
            Dictionary with certificate generation results
            
        Raises:
            CertificateError: If certificate generation fails
        """
        self.console.print("[bold blue]Generating Salesforce digital certificate...[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs()
            
            # Ensure certificate directory exists
            cert_dir = self.config.root_dir / "salesforce" / "certs"
            self.file_ops.ensure_directory(cert_dir)
            
            # Check if OpenSSL is available
            if not self.shell.check_command_exists("openssl"):
                raise CertificateError("OpenSSL is not installed or not in PATH")
            
            private_key_path = cert_dir / "aws-to-sf-cert.key"
            certificate_path = cert_dir / "aws-to-sf-cert.crt"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Generating private key...", total=None)
                
                # Generate private key
                key_command = [
                    "openssl", "genrsa",
                    "-out", str(private_key_path),
                    "2048"
                ]
                
                self.shell.execute(key_command, capture_output=True)
                
                progress.update(task, description="Generating certificate...")
                
                # Generate certificate
                cert_command = [
                    "openssl", "req", "-new", "-x509",
                    "-key", str(private_key_path),
                    "-out", str(certificate_path),
                    "-days", "365",
                    "-subj", "/C=US/ST=CA/L=San Francisco/O=SoCal Dreamin/OU=AWS Demo/CN=salesforce-integration"
                ]
                
                self.shell.execute(cert_command, capture_output=True)
                
                progress.update(task, description="Certificate generated successfully!")
            
            self.console.print(f"[green]✅ Digital certificate generated successfully![/green]")
            self.console.print(f"[blue]Private key: {private_key_path}[/blue]")
            self.console.print(f"[blue]Certificate: {certificate_path}[/blue]")
            
            return {
                'success': True,
                'private_key_path': str(private_key_path),
                'certificate_path': str(certificate_path),
                'certificate_dir': str(cert_dir)
            }
            
        except Exception as e:
            if isinstance(e, CertificateError):
                raise
            raise CertificateError(f"Failed to generate certificate: {e}")
    
    def validate_inputs(self, **kwargs) -> None:
        """
        Validate command inputs.
        
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Generate digital certificate for Salesforce integration"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {}

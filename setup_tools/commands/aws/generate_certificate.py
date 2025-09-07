"""
Generate AWS EC2 certificate command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import CertificateError, ValidationError
from ...utils.validators import Validators


@register_command("aws:generate-certificate")
class GenerateAWSCertificateCommand(BaseCommand):
    """Generate SSH keypair for AWS EC2 instances."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, key_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate SSH keypair for AWS EC2 instances.
        
        Args:
            key_name: Name for the SSH key
            
        Returns:
            Dictionary with key generation results
            
        Raises:
            CertificateError: If key generation fails
        """
        # Use config default if not provided
        key_name = key_name or self.config.aws.ssh_key_name
        
        self.console.print(f"[bold blue]Generating EC2 SSH keypair: {key_name}[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs(key_name=key_name)
            
            # Ensure certificate directory exists
            cert_dir = self.config.root_dir / self.config.aws.certificate_dir
            self.file_ops.ensure_directory(cert_dir)
            
            # Check if ssh-keygen is available
            if not self.shell.check_command_exists("ssh-keygen"):
                raise CertificateError("ssh-keygen is not installed or not in PATH")
            
            private_key_path = cert_dir / key_name
            public_key_path = cert_dir / f"{key_name}.pub"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Generating SSH keypair...", total=None)
                
                # Generate SSH keypair
                command = [
                    "ssh-keygen",
                    "-t", "rsa",
                    "-b", "4096",
                    "-f", str(private_key_path),
                    "-N", ""  # No passphrase
                ]
                
                self.shell.execute(command, capture_output=True)
                
                progress.update(task, description="SSH keypair generated successfully!")
            
            # Get fingerprint
            fingerprint = self._get_key_fingerprint(public_key_path)
            
            self.console.print(f"[green]✅ SSH keypair generated successfully![/green]")
            self.console.print(f"[blue]🔑 Private key: {private_key_path}[/blue]")
            self.console.print(f"[blue]📄 Public key: {public_key_path}[/blue]")
            if fingerprint:
                self.console.print(f"[blue]🔍 Fingerprint: {fingerprint}[/blue]")
            
            return {
                'success': True,
                'key_name': key_name,
                'private_key_path': str(private_key_path),
                'public_key_path': str(public_key_path),
                'fingerprint': fingerprint,
                'certificate_dir': str(cert_dir)
            }
            
        except Exception as e:
            if isinstance(e, CertificateError):
                raise
            raise CertificateError(f"Failed to generate SSH keypair: {e}")
    
    def validate_inputs(self, key_name: str, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            key_name: Name for the SSH key
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate key name
        self.validators.validate_ssh_key_name(key_name)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Generate SSH keypair for AWS EC2 instances"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'key_name': 'Name for the SSH key (defaults to config)'
        }
    
    def _get_key_fingerprint(self, public_key_path: Path) -> Optional[str]:
        """
        Get SSH key fingerprint.
        
        Args:
            public_key_path: Path to public key file
            
        Returns:
            Key fingerprint or None if failed
        """
        try:
            command = ["ssh-keygen", "-lf", str(public_key_path)]
            result = self.shell.execute(command, capture_output=True)
            return result.stdout.strip()
        except Exception as e:
            self.logger.warning(f"Failed to get key fingerprint: {e}")
            return None

"""
Deploy Salesforce project command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:deploy-project")
class DeployProjectCommand(BaseCommand):
    """Deploy Salesforce project to scratch org."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, environment: str = "demo", **kwargs) -> Dict[str, Any]:
        """
        Deploy Salesforce project to scratch org.
        
        Args:
            environment: Environment name for org targeting
            
        Returns:
            Dictionary with deployment results
            
        Raises:
            SalesforceError: If deployment fails
        """
        self.console.print("[bold blue]Deploying Salesforce project...[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs(environment=environment)
            
            # Check if sf CLI is available
            if not self.shell.check_command_exists("sf"):
                raise SalesforceError("Salesforce CLI (sf) is not installed or not in PATH")
            
            # Change to Salesforce directory
            salesforce_dir = self.config.root_dir / "salesforce"
            if not salesforce_dir.exists():
                raise SalesforceError(f"Salesforce directory not found: {salesforce_dir}")
            
            # Check if force-app directory exists
            force_app_dir = salesforce_dir / "force-app"
            if not force_app_dir.exists():
                raise SalesforceError(f"force-app directory not found: {force_app_dir}")
            
            # Deploy the project
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Deploying Salesforce project...", total=None)
                
                command = [
                    "sf", "project", "deploy", "start",
                    "--source-dir", "force-app",
                    "--target-org", f"socal-dreamin-2025-aws-{environment}",
                    "--wait", "10"  # Wait up to 10 minutes for deployment
                ]
                
                try:
                    result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
                    progress.update(task, description="Salesforce project deployed successfully!")
                except Exception as cmd_error:
                    # Display the command output for debugging
                    self.console.print(f"[red]❌ Command failed: {' '.join(command)}[/red]")
                    
                    # Try to get the actual command output from the shell executor
                    if hasattr(cmd_error, 'args') and len(cmd_error.args) > 0:
                        error_msg = str(cmd_error.args[0])
                        self.console.print(f"[red]Error details:[/red]")
                        self.console.print(f"[red]{error_msg}[/red]")
                    
                    # Also try to get stderr/stdout if available
                    if hasattr(cmd_error, 'stderr') and cmd_error.stderr:
                        self.console.print(f"[red]Error output:[/red]")
                        self.console.print(f"[red]{cmd_error.stderr}[/red]")
                    if hasattr(cmd_error, 'stdout') and cmd_error.stdout:
                        self.console.print(f"[yellow]Standard output:[/yellow]")
                        self.console.print(f"[yellow]{cmd_error.stdout}[/red]")
                    
                    # Try to execute the command again without capture_output to see the actual error
                    self.console.print(f"[yellow]Executing command again to show full output...[/yellow]")
                    try:
                        self.shell.execute(command, cwd=salesforce_dir, capture_output=False)
                    except Exception as debug_error:
                        self.console.print(f"[red]Full error output:[/red]")
                        self.console.print(f"[red]{debug_error}[/red]")
                    
                    raise SalesforceError(f"Failed to deploy Salesforce project: {cmd_error}")
            
            # Parse deployment result
            deployment_id = self._extract_deployment_id(result.stdout)
            
            self.console.print(f"[green]✅ Salesforce project deployed successfully![/green]")
            if deployment_id:
                self.console.print(f"[blue]Deployment ID: {deployment_id}[/blue]")
            
            return {
                'success': True,
                'environment': environment,
                'deployment_id': deployment_id,
                'command_output': result.stdout
            }
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to deploy Salesforce project: {e}")
    
    def validate_inputs(self, environment: str, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            environment: Environment name for org targeting
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate environment name
        if not environment or not isinstance(environment, str):
            raise ValidationError("Environment name must be a non-empty string")
        
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
        
        # Validate force-app directory exists
        force_app_dir = salesforce_dir / "force-app"
        self.validators.validate_directory_path(force_app_dir, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Deploy Salesforce project to scratch org"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'environment': 'Environment name for org targeting (default: demo)'
        }
    
    def _extract_deployment_id(self, output: str) -> Optional[str]:
        """
        Extract deployment ID from sf CLI output.
        
        Args:
            output: Command output string
            
        Returns:
            Deployment ID if found, None otherwise
        """
        try:
            import re
            
            # Look for deployment ID patterns in the output
            patterns = [
                r'Deployment ID: ([a-zA-Z0-9_-]+)',
                r'deploymentId["\']?\s*:\s*["\']?([a-zA-Z0-9_-]+)',
                r'"id"\s*:\s*"([a-zA-Z0-9_-]+)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to extract deployment ID: {e}")
            return None

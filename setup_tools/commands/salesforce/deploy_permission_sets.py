"""
Deploy Salesforce permission sets command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:deploy-permission-sets")
class DeployPermissionSetsCommand(BaseCommand):
    """Deploy Salesforce permission sets to scratch org."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, environment: str = "demo", **kwargs) -> Dict[str, Any]:
        """
        Deploy Salesforce permission sets to scratch org.
        
        Args:
            environment: Environment name for org targeting
            
        Returns:
            Dictionary with deployment results
            
        Raises:
            SalesforceError: If deployment fails
        """
        self.console.print("[bold blue]Deploying Salesforce permission sets...[/bold blue]")
        
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
            
            # Check if permission sets directory exists
            permission_sets_dir = salesforce_dir / "force-app" / "main" / "default" / "permissionsets"
            if not permission_sets_dir.exists():
                raise SalesforceError(f"Permission sets directory not found: {permission_sets_dir}")
            
            # Deploy permission sets
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Deploying permission sets...", total=None)
                
                command = [
                    "sf", "project", "deploy", "start",
                    "--source-dir", "force-app/main/default/permissionsets",
                    "--target-org", f"socal-dreamin-2025-aws-{environment}",
                    "--wait", "5"  # Wait up to 5 minutes for permission sets
                ]
                
                try:
                    result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
                    progress.update(task, description="Permission sets deployed successfully!")
                    
                    deployment_id = self._extract_deployment_id(result.stdout)
                    self.console.print(f"[green]✅ Permission sets deployed successfully![/green]")
                    if deployment_id:
                        self.console.print(f"[blue]Deployment ID: {deployment_id}[/blue]")
                    
                    return {
                        'success': True,
                        'environment': environment,
                        'deployment_id': deployment_id,
                        'command_output': result.stdout
                    }
                    
                except Exception as cmd_error:
                    self.console.print(f"[red]❌ Permission sets deployment failed: {' '.join(command)}[/red]")
                    
                    # Display error details
                    if hasattr(cmd_error, 'args') and len(cmd_error.args) > 0:
                        error_msg = str(cmd_error.args[0])
                        self.console.print(f"[red]Error details:[/red]")
                        self.console.print(f"[red]{error_msg}[/red]")
                    
                    if hasattr(cmd_error, 'stderr') and cmd_error.stderr:
                        self.console.print(f"[red]Error output:[/red]")
                        self.console.print(f"[red]{cmd_error.stderr}[/red]")
                    if hasattr(cmd_error, 'stdout') and cmd_error.stdout:
                        self.console.print(f"[yellow]Standard output:[/yellow]")
                        self.console.print(f"[yellow]{cmd_error.stdout}[/yellow]")
                    
                    # Try to execute the command again without capture_output to see the actual error
                    self.console.print(f"[yellow]Executing command again to show full output...[/yellow]")
                    try:
                        self.shell.execute(command, cwd=salesforce_dir, capture_output=False)
                    except Exception as debug_error:
                        self.console.print(f"[red]Full error output:[/red]")
                        self.console.print(f"[red]{debug_error}[/red]")
                    
                    raise SalesforceError(f"Failed to deploy permission sets: {cmd_error}")
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to deploy permission sets: {e}")
    
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
        
        # Validate permission sets directory exists
        permission_sets_dir = salesforce_dir / "force-app" / "main" / "default" / "permissionsets"
        self.validators.validate_directory_path(permission_sets_dir, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Deploy Salesforce permission sets to scratch org"
    
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

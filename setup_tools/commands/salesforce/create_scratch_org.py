"""
Create Salesforce scratch org command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:create-scratch-org")
class CreateScratchOrgCommand(BaseCommand):
    """Create a Salesforce scratch org."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, org_name: Optional[str] = None, duration_days: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Create a Salesforce scratch org.
        
        Args:
            org_name: Name for the scratch org
            duration_days: Duration in days (1-30)
            
        Returns:
            Dictionary with org creation results
            
        Raises:
            SalesforceError: If org creation fails
        """
        # Use config defaults if not provided
        org_name = org_name or self.config.salesforce.org_name
        duration_days = duration_days or self.config.salesforce.duration_days
        
        # Validate inputs
        self.validate_inputs(org_name=org_name, duration_days=duration_days)
        
        self.console.print(f"[bold blue]Creating Salesforce scratch org: {org_name}[/bold blue]")
        
        try:
            # Change to Salesforce directory
            salesforce_dir = self.config.root_dir / "salesforce"
            if not salesforce_dir.exists():
                raise SalesforceError(f"Salesforce directory not found: {salesforce_dir}")
            
            # Check if sf CLI is available
            if not self.shell.check_command_exists("sf"):
                raise SalesforceError("Salesforce CLI (sf) is not installed or not in PATH")
            
            # Check if scratch org definition file exists
            scratch_def_file = self.config.root_dir / self.config.salesforce.project_scratch_def
            if not scratch_def_file.exists():
                raise SalesforceError(f"Scratch org definition file not found: {scratch_def_file}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Creating scratch org...", total=None)
                
                # Create the scratch org
                command = [
                    "sf", "org", "create", "scratch",
                    "--definition-file", str(scratch_def_file),
                    "--alias", org_name,
                    "--set-default",
                    "--duration-days", str(duration_days)
                ]
                
                result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
                
                progress.update(task, description="Scratch org created successfully!")
            
            # Get org information
            org_info = self._get_org_info(salesforce_dir)
            
            self.console.print(f"[green]✅ Scratch org '{org_name}' created successfully![/green]")
            self.console.print(f"[blue]Org ID: {org_info.get('id', 'N/A')}[/blue]")
            self.console.print(f"[blue]Instance URL: {org_info.get('instanceUrl', 'N/A')}[/blue]")
            
            return {
                'success': True,
                'org_name': org_name,
                'duration_days': duration_days,
                'org_info': org_info,
                'command_output': result.stdout
            }
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to create scratch org: {e}")
    
    def validate_inputs(self, org_name: str, duration_days: int, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            org_name: Name for the scratch org
            duration_days: Duration in days
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate org name
        self.validators.validate_org_name(org_name)
        
        # Validate duration
        self.validators.validate_duration_days(duration_days)
        
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
        
        # Validate scratch org definition file exists
        scratch_def_file = self.config.root_dir / self.config.salesforce.project_scratch_def
        self.validators.validate_file_path(scratch_def_file, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Create a Salesforce scratch org with specified name and duration"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'org_name': 'Name for the scratch org (defaults to config)',
            'duration_days': 'Duration in days 1-30 (defaults to config)'
        }
    
    def _get_org_info(self, salesforce_dir: Path) -> Dict[str, str]:
        """
        Get information about the current org.
        
        Args:
            salesforce_dir: Salesforce project directory
            
        Returns:
            Dictionary with org information
        """
        try:
            result = self.shell.execute(
                ["sf", "org", "display", "--json"],
                cwd=salesforce_dir,
                capture_output=True
            )
            
            import json
            org_data = json.loads(result.stdout)
            return org_data.get('result', {})
            
        except Exception as e:
            self.logger.warning(f"Failed to get org info: {e}")
            return {}

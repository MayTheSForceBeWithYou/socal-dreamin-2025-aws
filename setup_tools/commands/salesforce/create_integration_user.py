"""
Create Salesforce integration user command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:create-integration-user")
class CreateIntegrationUserCommand(BaseCommand):
    """Create an integration user in the Salesforce scratch org."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, contact_email: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Create an integration user in the Salesforce scratch org.
        
        Args:
            contact_email: Contact email for the integration user
            
        Returns:
            Dictionary with user creation results
            
        Raises:
            SalesforceError: If user creation fails
        """
        # Use config default if not provided
        contact_email = contact_email or self.config.salesforce.contact_email
        
        self.console.print("[bold blue]Creating Salesforce integration user...[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs(contact_email=contact_email)
            
            # Check if integration user already exists
            if self._integration_user_exists():
                self.console.print("[yellow]⚠️  Integration user already exists, skipping creation[/yellow]")
                user_info = self._get_user_info(self.config.root_dir / "salesforce", "socal-dreamin-2025-aws-integration-user")
                self.console.print(f"[green]✅ Using existing integration user[/green]")
                self.console.print(f"[blue]Username: {user_info.get('username', 'N/A')}[/blue]")
                self.console.print(f"[blue]User ID: {user_info.get('id', 'N/A')}[/blue]")
                
                return {
                    'success': True,
                    'contact_email': contact_email,
                    'instance_url': self._get_org_instance_url(self.config.root_dir / "salesforce"),
                    'user_info': user_info,
                    'command_output': 'User already exists - skipped creation',
                    'skipped': True
                }
            
            # Check if sf CLI is available
            if not self.shell.check_command_exists("sf"):
                raise SalesforceError("Salesforce CLI (sf) is not installed or not in PATH")
            
            # Change to Salesforce directory
            salesforce_dir = self.config.root_dir / "salesforce"
            if not salesforce_dir.exists():
                raise SalesforceError(f"Salesforce directory not found: {salesforce_dir}")
            
            # Update integration user definition file with contact email
            integration_user_file = self.config.root_dir / self.config.salesforce.integration_user_def
            if not integration_user_file.exists():
                raise SalesforceError(f"Integration user definition file not found: {integration_user_file}")
            
            # Read and update the integration user definition
            self._update_integration_user_file(integration_user_file, contact_email)
            
            # Get org instance URL and update the username domain
            instance_url = self._get_org_instance_url(salesforce_dir)
            if instance_url:
                self._update_username_domain(integration_user_file, instance_url)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Creating integration user...", total=None)
                
                # Create the integration user
                command = [
                    "sf", "org", "create", "user",
                    "--definition-file", str(integration_user_file),
                    "--set-alias", "socal-dreamin-2025-aws-integration-user"
                ]
                
                try:
                    result = self.shell.execute(command, cwd=salesforce_dir, capture_output=True)
                    progress.update(task, description="Integration user created successfully!")
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
                        self.console.print(f"[yellow]{cmd_error.stdout}[/yellow]")
                    
                    # Try to execute the command again without capture_output to see the actual error
                    self.console.print(f"[yellow]Executing command again to show full output...[/yellow]")
                    try:
                        self.shell.execute(command, cwd=salesforce_dir, capture_output=False)
                    except Exception as debug_error:
                        self.console.print(f"[red]Full error output:[/red]")
                        self.console.print(f"[red]{debug_error}[/red]")
                    
                    raise SalesforceError(f"Failed to create integration user: {cmd_error}")
            
            # Get the created user information
            user_info = self._get_user_info(salesforce_dir, "socal-dreamin-2025-aws-integration-user")
            
            self.console.print(f"[green]✅ Integration user created successfully![/green]")
            self.console.print(f"[blue]Username: {user_info.get('username', 'N/A')}[/blue]")
            self.console.print(f"[blue]User ID: {user_info.get('id', 'N/A')}[/blue]")
            
            return {
                'success': True,
                'contact_email': contact_email,
                'instance_url': instance_url,
                'user_info': user_info,
                'command_output': result.stdout
            }
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            # This should not happen now since we handle command errors above
            raise SalesforceError(f"Failed to create integration user: {e}")
    
    def validate_inputs(self, contact_email: str, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            contact_email: Contact email for the integration user
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate email
        self.validators.validate_email(contact_email)
        
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
        
        # Validate integration user definition file exists
        integration_user_file = self.config.root_dir / self.config.salesforce.integration_user_def
        self.validators.validate_file_path(integration_user_file, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Create an integration user in the Salesforce scratch org"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'contact_email': 'Contact email for the integration user (defaults to config)'
        }
    
    def _update_integration_user_file(self, file_path: Path, contact_email: str) -> None:
        """
        Update the integration user definition file with contact email.
        
        Args:
            file_path: Path to integration user definition file
            contact_email: Contact email to set
        """
        try:
            import json
            
            # Read the file
            with open(file_path, 'r') as f:
                user_def = json.load(f)
            
            # Update email
            user_def['Email'] = contact_email
            
            # Write back to file
            with open(file_path, 'w') as f:
                json.dump(user_def, f, indent=4)
            
            self.logger.info(f"Updated integration user file with email: {contact_email}")
            
        except Exception as e:
            raise SalesforceError(f"Failed to update integration user file: {e}")
    
    def _get_org_instance_url(self, salesforce_dir: Path) -> Optional[str]:
        """
        Get the current org instance URL.
        
        Args:
            salesforce_dir: Salesforce project directory
            
        Returns:
            Instance URL or None if failed
        """
        try:
            result = self.shell.execute(
                ["sf", "org", "display", "--json"],
                cwd=salesforce_dir,
                capture_output=True
            )
            
            import json
            org_data = json.loads(result.stdout)
            return org_data.get('result', {}).get('instanceUrl')
            
        except Exception as e:
            self.logger.warning(f"Failed to get org instance URL: {e}")
            return None
    
    def _update_username_domain(self, file_path: Path, instance_url: str) -> None:
        """
        Update the username domain in the integration user definition file.
        
        Args:
            file_path: Path to integration user definition file
            instance_url: Instance URL to extract domain from
        """
        try:
            import json
            
            # Extract domain from instance URL
            domain = instance_url.replace('https://', '').replace('http://', '')
            
            # Read the file
            with open(file_path, 'r') as f:
                user_def = json.load(f)
            
            # Update username domain
            current_username = user_def.get('Username', '')
            if '@replace.with.instance.domain' in current_username:
                new_username = current_username.replace('@replace.with.instance.domain', f'@{domain}')
                user_def['Username'] = new_username
            
            # Write back to file
            with open(file_path, 'w') as f:
                json.dump(user_def, f, indent=4)
            
            self.logger.info(f"Updated username domain to: {domain}")
            
        except Exception as e:
            raise SalesforceError(f"Failed to update username domain: {e}")
    
    def _integration_user_exists(self) -> bool:
        """
        Check if the integration user already exists in the org by querying the User object.
        
        Returns:
            True if the integration user exists, False otherwise
        """
        try:
            salesforce_dir = self.config.root_dir / "salesforce"
            
            # Read the integration user definition to get the username
            integration_user_file = self.config.root_dir / self.config.salesforce.integration_user_def
            if not integration_user_file.exists():
                self.logger.debug("Integration user definition file not found")
                return False
            
            import json
            with open(integration_user_file, 'r') as f:
                user_def = json.load(f)
            
            username = user_def.get('Username')
            if not username:
                self.logger.debug("No username found in integration user definition")
                return False
            
            # Query for the User with this username
            soql_query = f"SELECT Id, Username FROM User WHERE Username = '{username}'"
            result = self.shell.execute(
                ["sf", "data", "query", "--query", soql_query, "--json"],
                cwd=salesforce_dir,
                capture_output=True
            )
            
            query_data = json.loads(result.stdout)
            
            # Check if we got any records (user exists)
            records = query_data.get('result', {}).get('records', [])
            return len(records) > 0
            
        except Exception as e:
            # If the command fails, assume the user doesn't exist
            self.logger.debug(f"Integration user existence check failed: {e}")
            return False
    
    def _get_user_info(self, salesforce_dir: Path, alias: str) -> Dict[str, str]:
        """
        Get information about the created user.
        
        Args:
            salesforce_dir: Salesforce project directory
            alias: User alias
            
        Returns:
            Dictionary with user information
        """
        try:
            result = self.shell.execute(
                ["sf", "org", "display", "--target-org", alias, "--json"],
                cwd=salesforce_dir,
                capture_output=True
            )
            
            import json
            user_data = json.loads(result.stdout)
            return user_data.get('result', {})
            
        except Exception as e:
            self.logger.warning(f"Failed to get user info: {e}")
            return {}

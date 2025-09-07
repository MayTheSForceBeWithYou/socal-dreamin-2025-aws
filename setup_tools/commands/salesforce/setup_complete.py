"""
Complete Salesforce setup command.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:setup-complete")
class SetupCompleteSalesforceCommand(BaseCommand):
    """Complete Salesforce setup including scratch org, certificates, Connected App, and integration user."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, contact_email: Optional[str] = None, environment: str = "demo", **kwargs) -> Dict[str, Any]:
        """
        Complete Salesforce setup.
        
        Args:
            contact_email: Contact email for Salesforce components
            environment: Environment name
            
        Returns:
            Dictionary with complete setup results
            
        Raises:
            SalesforceError: If setup fails
        """
        # Use config default if not provided
        contact_email = contact_email or self.config.salesforce.contact_email
        
        self.console.print(Panel(
            f"🚀 Complete Salesforce Setup\n"
            f"Environment: {environment}\n"
            f"Contact Email: {contact_email}",
            title="Salesforce Setup",
            border_style="blue"
        ))
        
        try:
            # Validate inputs
            self.validate_inputs(contact_email=contact_email)
            
            results = {}
            
            # Step 1: Generate certificate
            self.console.print("\n[bold]Step 1: Generating Salesforce certificate...[/bold]")
            cert_command = self.command_factory.create_command(
                'salesforce:generate-certificate',
                self.config,
                dry_run=self.dry_run,
                verbose=self.verbose
            )
            cert_result = cert_command.execute()
            results['certificate'] = cert_result
            
            # Step 2: Create scratch org
            self.console.print("\n[bold]Step 2: Creating Salesforce scratch org...[/bold]")
            org_name = f"socal-dreamin-2025-aws-{environment}"
            org_command = self.command_factory.create_command(
                'salesforce:create-scratch-org',
                self.config,
                dry_run=self.dry_run,
                verbose=self.verbose
            )
            org_result = org_command.execute(org_name=org_name, duration_days=30)
            results['scratch_org'] = org_result
            
            # Step 3: Setup Connected App
            self.console.print("\n[bold]Step 3: Setting up Connected App...[/bold]")
            app_command = self.command_factory.create_command(
                'salesforce:setup-connected-app',
                self.config,
                dry_run=self.dry_run,
                verbose=self.verbose
            )
            app_result = app_command.execute(contact_email=contact_email, environment=environment)
            results['connected_app'] = app_result
            
            # Step 4: Create integration user
            self.console.print("\n[bold]Step 4: Creating integration user...[/bold]")
            user_command = self.command_factory.create_command(
                'salesforce:create-integration-user',
                self.config,
                dry_run=self.dry_run,
                verbose=self.verbose
            )
            user_result = user_command.execute(contact_email=contact_email)
            results['integration_user'] = user_result
            
            # Check if all steps were successful
            all_successful = all(result.get('success', False) for result in results.values())
            
            if all_successful:
                self.console.print(Panel(
                    "✅ Complete Salesforce setup finished successfully!\n\n"
                    f"📧 Contact Email: {contact_email}\n"
                    f"🌐 Instance URL: {org_result.get('org_info', {}).get('instanceUrl', 'N/A')}\n"
                    f"🔑 Consumer Key: {app_result.get('consumer_key', 'N/A')}\n"
                    f"👤 Integration User: {user_result.get('user_info', {}).get('username', 'N/A')}",
                    title="Setup Complete",
                    border_style="green"
                ))
                
                return {
                    'success': True,
                    'contact_email': contact_email,
                    'environment': environment,
                    'results': results
                }
            else:
                failed_steps = [step for step, result in results.items() if not result.get('success', False)]
                raise SalesforceError(f"Setup failed for steps: {', '.join(failed_steps)}")
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            raise SalesforceError(f"Failed to complete Salesforce setup: {e}")
    
    def validate_inputs(self, contact_email: str, **kwargs) -> None:
        """
        Validate command inputs.
        
        Args:
            contact_email: Contact email for Salesforce components
            
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate email
        self.validators.validate_email(contact_email)
        
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Complete Salesforce setup including scratch org, certificates, Connected App, and integration user"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {
            'contact_email': 'Contact email for Salesforce components (defaults to config)',
            'environment': 'Environment name (default: demo)'
        }

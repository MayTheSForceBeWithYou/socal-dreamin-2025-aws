"""
Main CLI entry point for setup tools.
"""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from .core.config import get_config
from .core.logger import get_logger, SetupToolsLogger
from .core.exceptions import SetupToolsError
from .commands.base import CommandFactory
from .commands.salesforce.create_scratch_org import CreateScratchOrgCommand
from .commands.salesforce.generate_certificate import GenerateSalesforceCertificateCommand
from .commands.salesforce.query_login_history import QueryLoginHistoryCommand
from .commands.salesforce.create_integration_user import CreateIntegrationUserCommand
from .commands.salesforce.setup_complete import SetupCompleteSalesforceCommand
from .commands.salesforce.setup_connected_app import SetupConnectedAppCommand
from .commands.aws.generate_certificate import GenerateAWSCertificateCommand
from .commands.infrastructure.deploy_complete_lab import deploy_complete_lab
from .commands.infrastructure.setup_terraform_vars import setup_terraform_vars
from .commands.services.start_dashboard_proxy import start_dashboard_proxy
from .commands.services.access_dashboards import access_dashboards
from .commands.validation.validate_lab import validate_lab
from .commands.validation.generate_test_data import generate_test_data
from .commands.opensearch.post_terraform_setup import OpenSearchValidator

# Initialize console
console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--dry-run', is_flag=True, help='Preview operations without executing')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              default='INFO', help='Set logging level')
@click.pass_context
def cli(ctx, config, dry_run, verbose, log_level):
    """Setup Tools - Professional Python Architecture for Salesforce/AWS Demo Project."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Set up logging
    logger = SetupToolsLogger()
    logger.set_level(log_level)
    
    # Load configuration
    try:
        config_obj = get_config(config)
        
        # Override config with CLI options
        if dry_run:
            config_obj.dry_run = True
        if verbose:
            config_obj.verbose = True
            
        ctx.obj['config'] = config_obj
        ctx.obj['dry_run'] = dry_run
        ctx.obj['verbose'] = verbose
        
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise click.Abort()


@cli.group()
@click.pass_context
def salesforce(ctx):
    """Salesforce operations."""
    pass


@cli.group()
@click.pass_context
def aws(ctx):
    """AWS operations."""
    pass


@cli.group()
@click.pass_context
def infrastructure(ctx):
    """Infrastructure operations."""
    pass


@cli.group()
@click.pass_context
def services(ctx):
    """Service operations."""
    pass


@cli.group()
@click.pass_context
def validation(ctx):
    """Validation operations."""
    pass


@cli.group()
@click.pass_context
def opensearch(ctx):
    """OpenSearch operations."""
    pass


@cli.command()
@click.pass_context
def list_commands(ctx):
    """List all available commands."""
    commands = CommandFactory.list_commands()
    
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    for name, description in commands.items():
        table.add_row(name, description)
    
    console.print(table)


@cli.command()
@click.argument('command_name')
@click.pass_context
def command_info(ctx, command_name):
    """Get detailed information about a specific command."""
    try:
        info = CommandFactory.get_command_info(command_name)
        
        console.print(f"[bold blue]Command: {info['name']}[/bold blue]")
        console.print(f"[bold]Description:[/bold] {info['description']}")
        
        if info['required_args']:
            console.print("[bold]Required Arguments:[/bold]")
            for arg in info['required_args']:
                console.print(f"  • {arg}")
        
        if info['optional_args']:
            console.print("[bold]Optional Arguments:[/bold]")
            for arg, desc in info['optional_args'].items():
                console.print(f"  • {arg}: {desc}")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# Salesforce Commands
@salesforce.command('create-scratch-org')
@click.option('--org-name', help='Name for the scratch org')
@click.option('--duration-days', type=int, help='Duration in days (1-30)')
@click.pass_context
def salesforce_create_scratch_org(ctx, org_name, duration_days):
    """Create a Salesforce scratch org."""
    try:
        command = CommandFactory.create_command(
            'salesforce:create-scratch-org',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(org_name=org_name, duration_days=duration_days)
        
        if result['success']:
            console.print("[green]✅ Scratch org created successfully![/green]")
        else:
            console.print("[red]❌ Failed to create scratch org[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('generate-certificate')
@click.pass_context
def salesforce_generate_certificate(ctx):
    """Generate digital certificate for Salesforce integration."""
    try:
        command = CommandFactory.create_command(
            'salesforce:generate-certificate',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute()
        
        if result['success']:
            console.print("[green]✅ Certificate generated successfully![/green]")
        else:
            console.print("[red]❌ Failed to generate certificate[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('create-integration-user')
@click.option('--contact-email', help='Contact email for the integration user')
@click.pass_context
def salesforce_create_integration_user(ctx, contact_email):
    """Create an integration user in the Salesforce scratch org."""
    try:
        command = CommandFactory.create_command(
            'salesforce:create-integration-user',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(contact_email=contact_email)
        
        if result['success']:
            console.print("[green]✅ Integration user created successfully![/green]")
        else:
            console.print("[red]❌ Failed to create integration user[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('setup-connected-app')
@click.option('--contact-email', help='Contact email for the Connected App')
@click.option('--environment', default='demo', help='Environment name for org targeting')
@click.pass_context
def salesforce_setup_connected_app(ctx, contact_email, environment):
    """Set up Salesforce Connected App and retrieve Consumer Key."""
    try:
        command = CommandFactory.create_command(
            'salesforce:setup-connected-app',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(contact_email=contact_email, environment=environment)
        
        if result['success']:
            console.print("[green]✅ Connected App setup completed successfully![/green]")
        else:
            console.print("[red]❌ Failed to setup Connected App[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('setup-complete')
@click.option('--contact-email', help='Contact email for Salesforce components')
@click.option('--environment', default='demo', help='Environment name')
@click.pass_context
def salesforce_setup_complete(ctx, contact_email, environment):
    """Complete Salesforce setup including scratch org, certificates, Connected App, and integration user."""
    try:
        command = CommandFactory.create_command(
            'salesforce:setup-complete',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(contact_email=contact_email, environment=environment)
        
        if result['success']:
            console.print("[green]✅ Complete Salesforce setup finished successfully![/green]")
        else:
            console.print("[red]❌ Failed to complete Salesforce setup[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('deploy-permission-sets')
@click.option('--environment', default='demo', help='Environment name')
@click.pass_context
def salesforce_deploy_permission_sets(ctx, environment):
    """Deploy Salesforce permission sets to scratch org."""
    try:
        command = CommandFactory.create_command(
            'salesforce:deploy-permission-sets',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(environment=environment)
        
        if result['success']:
            console.print("[green]✅ Salesforce permission sets deployed successfully![/green]")
        else:
            console.print("[red]❌ Failed to deploy Salesforce permission sets[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('deploy-project')
@click.option('--environment', default='demo', help='Environment name')
@click.pass_context
def salesforce_deploy_project(ctx, environment):
    """Deploy Salesforce project to scratch org."""
    try:
        command = CommandFactory.create_command(
            'salesforce:deploy-project',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(environment=environment)
        
        if result['success']:
            console.print("[green]✅ Salesforce project deployed successfully![/green]")
        else:
            console.print("[red]❌ Failed to deploy Salesforce project[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@salesforce.command('query-login-history')
@click.pass_context
def salesforce_query_login_history(ctx):
    """Query Salesforce login history and export to CSV files."""
    try:
        command = CommandFactory.create_command(
            'salesforce:query-login-history',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute()
        
        if result['success']:
            console.print("[green]✅ Login history queries completed successfully![/green]")
        else:
            console.print("[red]❌ Failed to query login history[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# AWS Commands
@aws.command('generate-certificate')
@click.option('--key-name', help='Name for the SSH key')
@click.pass_context
def aws_generate_certificate(ctx, key_name):
    """Generate SSH keypair for AWS EC2 instances."""
    try:
        command = CommandFactory.create_command(
            'aws:generate-certificate',
            ctx.obj['config'],
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose']
        )
        
        result = command.execute(key_name=key_name)
        
        if result['success']:
            console.print("[green]✅ SSH keypair generated successfully![/green]")
        else:
            console.print("[red]❌ Failed to generate SSH keypair[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# Infrastructure Commands
@infrastructure.command('deploy-complete-lab')
@click.option('--environment', default='demo', help='Environment name')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--dry-run', is_flag=True, help='Preview operations without executing')
@click.option('--validate', is_flag=True, help='Run validation after deployment')
@click.option('--skip-prereqs', is_flag=True, help='Skip prerequisite validation')
@click.pass_context
def infrastructure_deploy_complete_lab(ctx, environment, config, dry_run, validate, skip_prereqs):
    """Deploy complete lab infrastructure and application."""
    deploy_complete_lab.callback(environment, config, dry_run, validate, skip_prereqs)


@infrastructure.command('setup-terraform-vars')
@click.option('--environment', default='demo', help='Environment name')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def infrastructure_setup_terraform_vars(ctx, environment, config):
    """Set up Terraform variables file from template."""
    setup_terraform_vars.callback(environment, config)


# Services Commands
@services.command('start-dashboard-proxy')
@click.option('--port', default=8080, help='Port for the proxy server')
@click.option('--endpoint', help='OpenSearch endpoint (auto-detected if not provided)')
@click.option('--username', default='os_admin', help='OpenSearch username')
@click.option('--password', help='OpenSearch password (auto-detected if not provided)')
@click.pass_context
def services_start_dashboard_proxy(ctx, port, endpoint, username, password):
    """Start OpenSearch Dashboard proxy server."""
    start_dashboard_proxy.callback(port, endpoint, username, password)


@services.command('access-dashboards')
@click.option('--open-browser', is_flag=True, help='Open browser automatically')
@click.option('--create-guide', is_flag=True, help='Create access guide script')
@click.pass_context
def services_access_dashboards(ctx, open_browser, create_guide):
    """Access OpenSearch Dashboards with multiple methods."""
    access_dashboards.callback(open_browser, create_guide)


# Validation Commands
@validation.command('validate-lab')
@click.option('--comprehensive', is_flag=True, help='Run comprehensive validation suite')
@click.option('--component', help='Validate specific component (terraform, ec2, opensearch, salesforce, pipeline, dashboard)')
@click.pass_context
def validation_validate_lab(ctx, comprehensive, component):
    """Validate lab infrastructure and functionality."""
    validate_lab.callback(comprehensive, component)


@validation.command('generate-test-data')
@click.option('--count', default=100, help='Number of events to generate')
@click.option('--create-template', is_flag=True, help='Create index template')
@click.pass_context
def validation_generate_test_data(ctx, count, create_template):
    """Generate test data for Salesforce login events."""
    generate_test_data.callback(count, create_template)


# OpenSearch Commands
@opensearch.command('validate-iam-auth')
@click.option('--region', default='us-west-1', help='AWS region')
@click.pass_context
def opensearch_validate_iam_auth(ctx, region):
    """Validate OpenSearch IAM authentication and connectivity."""
    try:
        validator = OpenSearchValidator(region)
        success = validator.run_validation()
        
        if success:
            console.print("[green]✅ OpenSearch IAM authentication validated successfully![/green]")
        else:
            console.print("[red]❌ OpenSearch IAM authentication validation failed[/red]")
            raise click.Abort()
            
    except Exception as e:
        console.print(f"[red]❌ OpenSearch validation failed: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option('--environment', default='default', help='Environment to run')
@click.pass_context
def run_all(ctx, environment):
    """Run all setup operations in sequence."""
    console.print(f"[bold blue]Running all setup operations for environment: {environment}[/bold blue]")
    
    operations = [
        ('salesforce:generate-certificate', 'Generate Salesforce certificate'),
        ('aws:generate-certificate', 'Generate AWS SSH keypair'),
        ('salesforce:create-scratch-org', 'Create Salesforce scratch org'),
        ('salesforce:create-integration-user', 'Create integration user'),
        ('salesforce:query-login-history', 'Query login history')
    ]
    
    results = []
    
    for command_name, description in operations:
        try:
            console.print(f"[yellow]🔄 {description}...[/yellow]")
            
            command = CommandFactory.create_command(
                command_name,
                ctx.obj['config'],
                dry_run=ctx.obj['dry_run'],
                verbose=ctx.obj['verbose']
            )
            
            result = command.execute()
            results.append((command_name, description, result['success']))
            
            if result['success']:
                console.print(f"[green]✅ {description} completed[/green]")
            else:
                console.print(f"[red]❌ {description} failed[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ {description} failed: {e}[/red]")
            results.append((command_name, description, False))
    
    # Summary
    console.print("\n[bold]Summary:[/bold]")
    success_count = sum(1 for _, _, success in results if success)
    total_count = len(results)
    
    for command_name, description, success in results:
        status = "✅" if success else "❌"
        console.print(f"{status} {description}")
    
    console.print(f"\n[bold]Completed: {success_count}/{total_count} operations[/bold]")


if __name__ == '__main__':
    cli()

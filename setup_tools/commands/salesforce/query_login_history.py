"""
Query Salesforce login history command.
"""

from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ...commands.base import BaseCommand, register_command
from ...core.exceptions import SalesforceError, ValidationError
from ...utils.validators import Validators


@register_command("salesforce:query-login-history")
class QueryLoginHistoryCommand(BaseCommand):
    """Query Salesforce login history and export to CSV files."""
    
    def __init__(self, config, dry_run: bool = False, verbose: bool = False):
        super().__init__(config, dry_run, verbose)
        self.console = Console()
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Query Salesforce login history and export to CSV files.
        
        Returns:
            Dictionary with query results
            
        Raises:
            SalesforceError: If query execution fails
        """
        self.console.print("[bold blue]Querying Salesforce login history...[/bold blue]")
        
        try:
            # Validate inputs
            self.validate_inputs()
            
            # Check if sf CLI is available
            if not self.shell.check_command_exists("sf"):
                raise SalesforceError("Salesforce CLI (sf) is not installed or not in PATH")
            
            # Ensure data directory exists
            data_dir = self.config.root_dir / "salesforce" / "data"
            self.file_ops.ensure_directory(data_dir)
            
            # Define SOQL queries and their output files
            queries = [
                {
                    'file': 'salesforce/scripts/soql/LoginHistory.soql',
                    'output': 'salesforce/data/LoginHistory.csv',
                    'description': 'Login History'
                },
                {
                    'file': 'salesforce/scripts/soql/LoginIp.soql',
                    'output': 'salesforce/data/LoginIp.csv',
                    'description': 'Login IP'
                },
                {
                    'file': 'salesforce/scripts/soql/LoginGeo.soql',
                    'output': 'salesforce/data/LoginGeo.csv',
                    'description': 'Login Geography'
                },
                {
                    'file': 'salesforce/scripts/soql/User.soql',
                    'output': 'salesforce/data/User.csv',
                    'description': 'User Data'
                }
            ]
            
            results = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                
                total_tasks = len(queries)
                main_task = progress.add_task("Executing queries...", total=total_tasks)
                
                for i, query_info in enumerate(queries):
                    query_file = self.config.root_dir / query_info['file']
                    output_file = self.config.root_dir / query_info['output']
                    
                    # Update progress description
                    progress.update(main_task, description=f"Querying {query_info['description']}...")
                    
                    # Check if SOQL file exists
                    if not query_file.exists():
                        self.logger.warning(f"SOQL file not found: {query_file}")
                        continue
                    
                    # Execute query
                    command = [
                        "sf", "data", "query",
                        "--file", str(query_file),
                        "--result-format", "csv"
                    ]
                    
                    try:
                        result = self.shell.execute(command, capture_output=True)
                        
                        # Write output to CSV file
                        self.file_ops.write_file(output_file, result.stdout)
                        
                        results.append({
                            'query_file': str(query_file),
                            'output_file': str(output_file),
                            'description': query_info['description'],
                            'success': True
                        })
                        
                    except Exception as cmd_error:
                        # Display the command output for debugging
                        self.console.print(f"[red]❌ Query failed: {' '.join(command)}[/red]")
                        if hasattr(cmd_error, 'stderr') and cmd_error.stderr:
                            self.console.print(f"[red]Error output:[/red]")
                            self.console.print(f"[red]{cmd_error.stderr}[/red]")
                        if hasattr(cmd_error, 'stdout') and cmd_error.stdout:
                            self.console.print(f"[yellow]Standard output:[/yellow]")
                            self.console.print(f"[yellow]{cmd_error.stdout}[/yellow]")
                        raise SalesforceError(f"Failed to execute query {query_info['description']}: {cmd_error}")
                    
                    # Update progress
                    progress.update(main_task, advance=1)
                
                progress.update(main_task, description="All queries completed!")
            
            self.console.print(f"[green]✅ Successfully executed {len(results)} queries![/green]")
            
            # Display results
            for result in results:
                self.console.print(f"[blue]📄 {result['description']}: {result['output_file']}[/blue]")
            
            return {
                'success': True,
                'queries_executed': len(results),
                'results': results,
                'data_directory': str(data_dir)
            }
            
        except Exception as e:
            if isinstance(e, SalesforceError):
                raise
            # This should not happen now since we handle command errors above
            raise SalesforceError(f"Failed to query login history: {e}")
    
    def validate_inputs(self, **kwargs) -> None:
        """
        Validate command inputs.
        
        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate Salesforce directory exists
        salesforce_dir = self.config.root_dir / "salesforce"
        self.validators.validate_directory_path(salesforce_dir, must_exist=True)
        
        # Validate SOQL scripts directory exists
        soql_dir = salesforce_dir / "scripts" / "soql"
        self.validators.validate_directory_path(soql_dir, must_exist=True)
    
    def get_description(self) -> str:
        """Get command description."""
        return "Query Salesforce login history and export to CSV files"
    
    def get_required_args(self) -> list:
        """Get list of required arguments."""
        return []
    
    def get_optional_args(self) -> dict:
        """Get dictionary of optional arguments with defaults."""
        return {}

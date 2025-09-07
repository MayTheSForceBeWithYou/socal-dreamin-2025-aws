#!/usr/bin/env python3
"""
Test Data Generator for Salesforce Login Events
Generates sample data for demonstration purposes
"""

import os
import sys
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import click
import requests
import base64
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()


class TestDataGenerator:
    """Generates test data for Salesforce login events."""
    
    def __init__(self):
        self.project_root = project_root
        self.terraform_dir = self.project_root / "aws" / "terraform"
        
    def get_opensearch_credentials(self) -> tuple[str, str]:
        """Get OpenSearch credentials from Terraform outputs."""
        try:
            os.chdir(self.terraform_dir)
            
            result = subprocess.run(
                ["terraform", "output", "-json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                console.print("[red]❌ Failed to get Terraform outputs[/red]")
                return None, None
            
            outputs = json.loads(result.stdout)
            endpoint = outputs.get("opensearch_endpoint", {}).get("value")
            password = outputs.get("opensearch_master_password", {}).get("value")
            
            return endpoint, password
            
        except Exception as e:
            console.print(f"[red]❌ Error getting credentials: {e}[/red]")
            return None, None
        finally:
            os.chdir(self.project_root)
    
    def generate_login_events(self, count: int = 100) -> List[Dict]:
        """Generate sample Salesforce login events."""
        
        # Sample data templates
        users = [
            "john.doe@company.com",
            "jane.smith@company.com", 
            "bob.wilson@company.com",
            "alice.brown@company.com",
            "charlie.davis@company.com",
            "diana.miller@company.com",
            "eve.jones@company.com",
            "frank.garcia@company.com"
        ]
        
        browsers = [
            "Chrome/120.0.0.0",
            "Firefox/121.0",
            "Safari/17.2",
            "Edge/120.0.0.0"
        ]
        
        platforms = [
            "Windows 10",
            "Windows 11", 
            "macOS 14.2",
            "Ubuntu 22.04",
            "iOS 17.2",
            "Android 14"
        ]
        
        applications = [
            "Salesforce Classic",
            "Lightning Experience",
            "Salesforce Mobile",
            "Salesforce API"
        ]
        
        login_types = [
            "Web",
            "Mobile",
            "API",
            "Desktop"
        ]
        
        statuses = ["Success", "Failed", "Success", "Success", "Success"]  # Mostly successful
        
        # Generate events
        events = []
        base_time = datetime.now() - timedelta(days=7)  # Last 7 days
        
        for i in range(count):
            # Random timestamp within last 7 days
            random_minutes = random.randint(0, 7 * 24 * 60)
            event_time = base_time + timedelta(minutes=random_minutes)
            
            # Random IP address
            ip_parts = [random.randint(1, 255) for _ in range(4)]
            source_ip = ".".join(map(str, ip_parts))
            
            # Random location (simplified)
            locations = [
                {"city": "San Francisco", "state": "CA", "country": "US"},
                {"city": "New York", "state": "NY", "country": "US"},
                {"city": "Los Angeles", "state": "CA", "country": "US"},
                {"city": "Chicago", "state": "IL", "country": "US"},
                {"city": "Austin", "state": "TX", "country": "US"},
                {"city": "Seattle", "state": "WA", "country": "US"},
                {"city": "Boston", "state": "MA", "country": "US"},
                {"city": "Denver", "state": "CO", "country": "US"}
            ]
            
            event = {
                "@timestamp": event_time.isoformat() + "Z",
                "user_id": random.choice(users),
                "login_time": event_time.isoformat() + "Z",
                "login_type": random.choice(login_types),
                "login_url": "https://company.lightning.force.com/",
                "source_ip": source_ip,
                "status": random.choice(statuses),
                "browser": random.choice(browsers),
                "platform": random.choice(platforms),
                "application": random.choice(applications),
                "location": random.choice(locations),
                "session_id": f"session_{random.randint(100000, 999999)}",
                "user_agent": f"Mozilla/5.0 ({random.choice(platforms)}) {random.choice(browsers)}",
                "event_type": "login_attempt"
            }
            
            events.append(event)
        
        return events
    
    def index_events_to_opensearch(self, events: List[Dict], endpoint: str, password: str) -> bool:
        """Index events to OpenSearch."""
        try:
            credentials = f"admin:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            # Prepare bulk index request
            bulk_data = []
            for event in events:
                # Index action
                bulk_data.append(json.dumps({
                    "index": {
                        "_index": "salesforce-login-events",
                        "_type": "_doc"
                    }
                }))
                # Document
                bulk_data.append(json.dumps(event))
            
            bulk_body = "\n".join(bulk_data) + "\n"
            
            # Send bulk request
            response = requests.post(
                f"https://{endpoint}/_bulk",
                headers=headers,
                data=bulk_body,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errors"):
                    console.print("[yellow]⚠️  Some documents failed to index[/yellow]")
                    return False
                else:
                    console.print(f"[green]✅ Successfully indexed {len(events)} events[/green]")
                    return True
            else:
                console.print(f"[red]❌ Failed to index events: {response.status_code}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error indexing events: {e}[/red]")
            return False
    
    def create_index_template(self, endpoint: str, password: str) -> bool:
        """Create index template for Salesforce login events."""
        try:
            credentials = f"admin:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            template = {
                "index_patterns": ["salesforce-login-events*"],
                "template": {
                    "mappings": {
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "user_id": {"type": "keyword"},
                            "login_time": {"type": "date"},
                            "login_type": {"type": "keyword"},
                            "login_url": {"type": "keyword"},
                            "source_ip": {"type": "ip"},
                            "status": {"type": "keyword"},
                            "browser": {"type": "text"},
                            "platform": {"type": "keyword"},
                            "application": {"type": "keyword"},
                            "location": {
                                "properties": {
                                    "city": {"type": "keyword"},
                                    "state": {"type": "keyword"},
                                    "country": {"type": "keyword"}
                                }
                            },
                            "session_id": {"type": "keyword"},
                            "user_agent": {"type": "text"},
                            "event_type": {"type": "keyword"}
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                }
            }
            
            response = requests.put(
                f"https://{endpoint}/_index_template/salesforce-login-events-template",
                headers=headers,
                data=json.dumps(template),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                console.print("[green]✅ Index template created successfully[/green]")
                return True
            else:
                console.print(f"[yellow]⚠️  Index template creation returned: {response.status_code}[/yellow]")
                return True  # Not critical for demo
                
        except Exception as e:
            console.print(f"[yellow]⚠️  Index template creation failed: {e}[/yellow]")
            return True  # Not critical for demo


@click.command()
@click.option('--count', default=100, help='Number of events to generate')
@click.option('--create-template', is_flag=True, help='Create index template')
def generate_test_data(count: int, create_template: bool):
    """Generate test data for Salesforce login events."""
    
    console.print(Panel(
        f"📊 Test Data Generator\n"
        f"Generating {count} Salesforce login events",
        title="Test Data",
        border_style="blue"
    ))
    
    generator = TestDataGenerator()
    
    # Get OpenSearch credentials
    console.print("[yellow]🔍 Getting OpenSearch credentials...[/yellow]")
    endpoint, password = generator.get_opensearch_credentials()
    
    if not endpoint or not password:
        console.print("[red]❌ Could not get OpenSearch credentials[/red]")
        return
    
    console.print(f"[green]✅ Got credentials for {endpoint}[/green]")
    
    # Create index template if requested
    if create_template:
        console.print("[yellow]📝 Creating index template...[/yellow]")
        generator.create_index_template(endpoint, password)
    
    # Generate events
    console.print(f"[yellow]🔄 Generating {count} login events...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Generating events...", total=count)
        
        events = generator.generate_login_events(count)
        progress.update(task, completed=count, description="✅ Events generated")
    
    # Index events
    console.print("[yellow]📤 Indexing events to OpenSearch...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Indexing events...", total=1)
        
        success = generator.index_events_to_opensearch(events, endpoint, password)
        
        if success:
            progress.update(task, completed=1, description="✅ Events indexed")
        else:
            progress.update(task, completed=1, description="❌ Indexing failed")
    
    if success:
        console.print(Panel(
            f"🎉 Test data generation completed!\n"
            f"Generated: {count} login events\n"
            f"Index: salesforce-login-events\n"
            f"Dashboard: https://{endpoint}/_dashboards/\n"
            f"Username: admin\n"
            f"Password: {password}",
            title="✅ Success",
            border_style="green"
        ))
        
        console.print("[blue]📊 Next Steps:[/blue]")
        console.print("1. Access OpenSearch Dashboards")
        console.print("2. Create index pattern for 'salesforce-login-events*'")
        console.print("3. Explore the data in the Discover tab")
        console.print("4. Create visualizations and dashboards")
        
    else:
        console.print("[red]❌ Test data generation failed[/red]")


if __name__ == "__main__":
    generate_test_data()

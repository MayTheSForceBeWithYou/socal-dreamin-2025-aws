#!/usr/bin/env python3
"""
Salesforce to OpenSearch Lab Environment Deployment Script

This script automates the deployment of the Salesforce streaming application
to AWS EC2 infrastructure using Terraform.
"""

import subprocess
import sys
import time
import os
from pathlib import Path
from typing import Optional


class DeploymentError(Exception):
    """Custom exception for deployment errors."""
    pass


def run_command(command: str, cwd: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.
    
    Args:
        command: The command to run
        cwd: Working directory for the command
        check: Whether to raise an exception on non-zero exit code
        
    Returns:
        CompletedProcess object with stdout, stderr, and returncode
        
    Raises:
        DeploymentError: If command fails and check=True
    """
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        raise DeploymentError(f"Command failed: {command}")


def get_ec2_ip() -> str:
    """
    Get the EC2 instance public IP from Terraform output.
    
    Returns:
        The public IP address of the EC2 instance
        
    Raises:
        DeploymentError: If unable to get IP from Terraform
    """
    try:
        result = run_command("terraform output -raw ec2_public_ip", cwd="aws/terraform")
        ip = result.stdout.strip()
        if not ip:
            raise DeploymentError("No IP address returned from Terraform")
        return ip
    except Exception as e:
        raise DeploymentError(f"Failed to get EC2 IP: {e}")


def deploy_infrastructure():
    """Deploy AWS infrastructure using Terraform."""
    print("Deploying infrastructure...")
    
    terraform_dir = "aws/terraform"
    
    # Initialize Terraform
    run_command("terraform init", cwd=terraform_dir)
    
    # Plan deployment
    run_command("terraform plan -var-file='terraform.tfvars'", cwd=terraform_dir)
    
    # Apply deployment
    run_command("terraform apply -var-file='terraform.tfvars'", cwd=terraform_dir)


def deploy_application(ec2_ip: str):
    """
    Deploy application code to EC2 instance.
    
    Args:
        ec2_ip: The public IP address of the EC2 instance
    """
    print("Deploying application code to EC2...")
    
    # Check if SSH key exists
    ssh_key = os.path.expanduser("../aws/certs/aws-ec2")
    if not os.path.exists(ssh_key):
        raise DeploymentError(f"SSH key not found at {ssh_key}")
    
    # Copy application files
    scp_command = (
        f"scp -i {ssh_key} -o StrictHostKeyChecking=no "
        f"../aws/ec2-app/* ec2-user@{ec2_ip}:/tmp/"
    )
    run_command(scp_command)


def install_and_start_service(ec2_ip: str):
    """
    Install dependencies and start the service on EC2.
    
    Args:
        ec2_ip: The public IP address of the EC2 instance
    """
    print("Installing dependencies and starting service...")
    
    ssh_key = os.path.expanduser("../aws/certs/aws-ec2")
    
    # SSH commands to run on the remote instance
    ssh_commands = [
        "sudo cp /tmp/*.py /opt/salesforce-streamer/",
        "sudo cp /tmp/requirements.txt /opt/salesforce-streamer/",
        "sudo chown -R salesforce-streamer:salesforce-streamer /opt/salesforce-streamer/",
        "cd /opt/salesforce-streamer",
        "sudo pip3 install -r requirements.txt",
        "sudo systemctl start salesforce-streamer",
        "sudo systemctl status salesforce-streamer"
    ]
    
    # Combine commands with && for proper error handling
    combined_command = " && ".join(ssh_commands)
    
    ssh_command = (
        f"ssh -i {ssh_key} -o StrictHostKeyChecking=no "
        f"ec2-user@{ec2_ip} '{combined_command}'"
    )
    
    run_command(ssh_command)


def main():
    """Main deployment function."""
    try:
        print("Deploying Salesforce to OpenSearch Lab Environment...")
        
        # Change to project root directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        os.chdir(project_root)
        
        # Deploy infrastructure
        deploy_infrastructure()
        
        # Get EC2 instance IP
        ec2_ip = get_ec2_ip()
        print(f"EC2 Instance IP: {ec2_ip}")
        
        # Wait for instance to be ready
        print("Waiting for EC2 instance to be ready...")
        time.sleep(60)
        
        # Deploy application code
        deploy_application(ec2_ip)
        
        # Install and start the service
        install_and_start_service(ec2_ip)
        
        print("Deployment completed!")
        print(f"SSH to instance: ssh -i ../aws/certs/aws-ec2 ec2-user@{ec2_ip}")
        print("Check logs: sudo journalctl -u salesforce-streamer -f")
        
    except DeploymentError as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDeployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

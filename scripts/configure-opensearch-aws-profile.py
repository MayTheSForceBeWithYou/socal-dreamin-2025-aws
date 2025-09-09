#!/usr/bin/env python3
"""
AWS OpenSearch Access Configuration Tool

This script automates the setup of AWS IAM permissions and profiles for OpenSearch access.
It reads configuration from Terraform outputs and configures the local AWS CLI environment.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional

def run_command(cmd: list, capture_output: bool = True, check: bool = True, cwd: Optional[Path] = None, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"🔧 Running: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        check=False,
        cwd=cwd,
        env=env
    )
    
    if check and result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    return result

def get_terraform_output(output_name: str, terraform_dir: Path) -> str:
    """Get a specific Terraform output value."""
    cmd = ["terraform", "output", "-raw", output_name]
    result = run_command(cmd, cwd=terraform_dir)
    return result.stdout.strip()

def get_aws_identity() -> Dict[str, str]:
    """Get current AWS identity information."""
    cmd = ["aws", "sts", "get-caller-identity"]
    result = run_command(cmd)
    identity = json.loads(result.stdout)
    return identity

def extract_role_info(master_user_arn: str) -> Dict[str, str]:
    """Extract role information from the master user ARN."""
    # ARN format: arn:aws:iam::ACCOUNT_ID:role/PROJECT_NAME-ec2-role
    parts = master_user_arn.split(":")
    account_id = parts[4]
    role_name = parts[5].split("/")[1]
    project_name = role_name.replace("-ec2-role", "")
    
    return {
        "account_id": account_id,
        "role_name": role_name,
        "project_name": project_name
    }

def get_region_from_endpoint(endpoint: str) -> str:
    """Extract region from OpenSearch endpoint."""
    # Format: https://search-PROJECT-os-RANDOM.REGION.es.amazonaws.com
    parts = endpoint.split(".")
    if len(parts) >= 2:
        return parts[1]
    return "us-west-1"  # fallback

def add_assume_role_policy(user_name: str, role_arn: str) -> None:
    """Add assume role policy to the specified user."""
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": role_arn
            }
        ]
    }
    
    cmd = [
        "aws", "iam", "put-user-policy",
        "--user-name", user_name,
        "--policy-name", "AllowAssumeOpenSearchRole",
        "--policy-document", json.dumps(policy_document)
    ]
    
    run_command(cmd)
    print(f"✅ Added assume role policy for user: {user_name}")

def add_aws_profile(account_id: str, project_name: str, region: str) -> None:
    """Add AWS profile configuration to ~/.aws/config."""
    aws_config_path = Path.home() / ".aws" / "config"
    aws_config_path.parent.mkdir(exist_ok=True)
    
    profile_name = "sf-opensearch-role"
    role_arn = f"arn:aws:iam::{account_id}:role/{project_name}-ec2-role"
    
    profile_config = f"""
[profile {profile_name}]
role_arn = {role_arn}
source_profile = default
region = {region}
"""
    
    # Check if profile already exists
    if aws_config_path.exists():
        with open(aws_config_path, 'r') as f:
            content = f.read()
        
        if f"[profile {profile_name}]" in content:
            print(f"⚠️  Profile '{profile_name}' already exists in {aws_config_path}")
            return
    
    # Append to config file
    with open(aws_config_path, 'a') as f:
        f.write(profile_config)
    
    print(f"✅ Added profile '{profile_name}' to {aws_config_path}")

def test_aws_profile() -> bool:
    """Test the AWS profile configuration."""
    env = os.environ.copy()
    env["AWS_PROFILE"] = "sf-opensearch-role"
    
    cmd = ["aws", "sts", "get-caller-identity"]
    result = run_command(cmd, check=False, env=env)
    
    if result.returncode == 0:
        identity = json.loads(result.stdout)
        print(f"✅ AWS profile test successful!")
        print(f"   Assumed role: {identity['Arn']}")
        return True
    else:
        print(f"❌ AWS profile test failed: {result.stderr}")
        return False

def test_opensearch_validation(project_root: Path) -> bool:
    """Test OpenSearch validation with the new profile."""
    env = os.environ.copy()
    env["AWS_PROFILE"] = "sf-opensearch-role"
    
    cmd = ["python3", "-m", "setup_tools", "opensearch", "validate-iam-auth"]
    result = run_command(cmd, check=False, cwd=project_root, env=env)
    
    if result.returncode == 0:
        print("✅ OpenSearch IAM authentication validation successful!")
        return True
    else:
        print("❌ OpenSearch validation failed")
        print(f"Error output: {result.stderr}")
        return False

def main():
    """Main configuration function."""
    print("🔧 Configuring OpenSearch IAM Authentication...")
    print()
    
    # Check if we're in the right directory
    project_root = Path.cwd()
    terraform_dir = project_root / "aws" / "terraform"
    
    if not terraform_dir.exists():
        print("❌ Error: aws/terraform directory not found.")
        print("   Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check Terraform state
    if not (terraform_dir / "terraform.tfstate").exists():
        print("❌ Error: Terraform state not found.")
        print("   Please run 'terraform apply' in aws/terraform first.")
        sys.exit(1)
    
    try:
        # Get configuration from Terraform
        print("📋 Getting configuration from Terraform outputs...")
        master_user_arn = get_terraform_output("opensearch_master_user_arn", terraform_dir)
        opensearch_endpoint = get_terraform_output("opensearch_endpoint", terraform_dir)
        
        # Extract role information
        role_info = extract_role_info(master_user_arn)
        region = get_region_from_endpoint(opensearch_endpoint)
        
        # Get current AWS user
        identity = get_aws_identity()
        user_name = identity["Arn"].split("/")[-1]
        
        print("📋 Configuration:")
        print(f"  Account ID: {role_info['account_id']}")
        print(f"  Project Name: {role_info['project_name']}")
        print(f"  Region: {region}")
        print(f"  User Name: {user_name}")
        print(f"  Role ARN: {master_user_arn}")
        print()
        
        # Step 1: Add assume role policy
        print("🔐 Adding assume role policy...")
        add_assume_role_policy(user_name, master_user_arn)
        print()
        
        # Step 2: Configure AWS profile
        print("⚙️  Configuring AWS profile...")
        add_aws_profile(role_info["account_id"], role_info["project_name"], region)
        print()
        
        # Step 3: Test configuration
        print("🧪 Testing configuration...")
        
        if test_aws_profile():
            print()
            
            # Test OpenSearch validation
            print("🔍 Testing OpenSearch validation...")
            if test_opensearch_validation(project_root):
                print()
                print("🎉 OpenSearch IAM authentication configured successfully!")
                print()
                print("📝 Usage Examples:")
                print("  # Test OpenSearch validation")
                print("  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth")
                print()
                print("  # Run comprehensive lab validation")
                print("  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools validation validate-lab --comprehensive")
                print()
                print("  # Test AWS CLI with the profile")
                print("  AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity")
                print()
                print("  # Check OpenSearch domain status")
                print(f"  AWS_PROFILE=sf-opensearch-role aws es describe-elasticsearch-domain --domain-name {role_info['project_name']}-os")
            else:
                print()
                print("❌ OpenSearch validation failed. Check the error messages above.")
                print()
                print("🔧 Troubleshooting:")
                print(f"  1. Verify the EC2 role exists: aws iam get-role --role-name {role_info['role_name']}")
                print(f"  2. Check your user policies: aws iam list-user-policies --user-name {user_name}")
                print(f"  3. Verify the OpenSearch domain: aws es describe-elasticsearch-domain --domain-name {role_info['project_name']}-os")
        else:
            print()
            print("❌ AWS profile configuration failed.")
            print()
            print("🔧 Troubleshooting:")
            print("  1. Check your AWS credentials: aws sts get-caller-identity")
            print(f"  2. Verify the assume role policy was created: aws iam list-user-policies --user-name {user_name}")
            print(f"  3. Check the role exists: aws iam get-role --role-name {role_info['role_name']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print()
    print("📚 For more information, see OPENSEARCH_IAM_AUTHENTICATION.md")

if __name__ == "__main__":
    main()

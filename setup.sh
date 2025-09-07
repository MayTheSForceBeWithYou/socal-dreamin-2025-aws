#!/bin/bash
# Quick Setup Script for Salesforce → AWS → OpenSearch Lab
# This script helps users set up the prerequisites quickly

set -e

echo "🚀 Salesforce → AWS → OpenSearch Lab Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "setup_tools" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Expected files: README.md, setup_tools/"
    exit 1
fi

echo "✅ Found project files"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9+ required, found Python $python_version"
    exit 1
fi

echo "✅ Python version check passed"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt
echo "✅ Requirements installed"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "⚠️  Warning: AWS CLI not found. Please install and configure it:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    echo "   Then run: aws configure"
else
    echo "✅ AWS CLI found"
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "⚠️  Warning: Terraform not found. Please install it:"
    echo "   https://developer.hashicorp.com/terraform/downloads"
else
    echo "✅ Terraform found"
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo ""
echo "1. Set up prerequisites:"
echo "   python -m setup_tools.main aws generate-certificate --key-name aws-ec2"
echo "   python -m setup_tools.main salesforce generate-certificate"
echo "   python -m setup_tools.main infrastructure setup-terraform-vars --environment demo"
echo ""
echo "2. Configure Salesforce credentials:"
echo "   cp aws/sfdc-auth-secrets.json.example aws/sfdc-auth-secrets.json"
echo "   # Edit aws/sfdc-auth-secrets.json with your Salesforce credentials"
echo ""
echo "3. Deploy the complete lab:"
echo "   python -m setup_tools.main infrastructure deploy-complete-lab --environment demo --validate"
echo ""
echo "📚 For detailed instructions, see README.md"

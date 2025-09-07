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
echo "✅ Virtual environment activated"

read -p "Press Enter to continue"

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
echo "🚀 RECOMMENDED: One-Command Complete Setup"
echo "=========================================="
echo "1. Complete Salesforce setup (one command):"
echo "   python -m setup_tools.main salesforce setup-complete --contact-email your-email@example.com --environment demo"
echo ""
echo "2. Set up Terraform variables:"
echo "   python -m setup_tools.main infrastructure setup-terraform-vars --environment demo"
echo ""
echo "3. Configure Salesforce credentials:"
echo "   cp aws/sfdc-auth-secrets.json.example aws/sfdc-auth-secrets.json"
echo "   # Edit aws/sfdc-auth-secrets.json with your Salesforce credentials"
echo ""
echo "4. Deploy the complete lab:"
echo "   python -m setup_tools.main infrastructure deploy-complete-lab --environment demo --validate"
echo ""
echo "📊 Access OpenSearch Dashboards"
echo "==============================="
echo "• Direct access: python -m setup_tools.main services access-dashboards --open-browser"
echo "• Proxy server: python -m setup_tools.main services start-dashboard-proxy"
echo "• SSH tunnel: ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@<EC2_IP>"
echo ""
echo "🔍 Validation & Testing"
echo "======================="
echo "• Comprehensive validation: python -m setup_tools.main validation validate-lab --comprehensive"
echo "• Generate test data: python -m setup_tools.main validation generate-test-data --count 100"
echo "• Check specific components: python -m setup_tools.main validation validate-lab --component opensearch"
echo ""
echo "🛠️ Individual Commands (if needed)"
echo "=================================="
echo "• AWS certificate: python -m setup_tools.main aws generate-certificate --key-name aws-ec2"
echo "• Salesforce certificate: python -m setup_tools.main salesforce generate-certificate"
echo "• Create scratch org: python -m setup_tools.main salesforce create-scratch-org --org-name demo --duration-days 30"
echo "• Setup Connected App: python -m setup_tools.main salesforce setup-connected-app --contact-email your-email@example.com"
echo "• Create integration user: python -m setup_tools.main salesforce create-integration-user --contact-email your-email@example.com"
echo "• Query login history: python -m setup_tools.main salesforce query-login-history"
echo ""
echo "📚 Documentation & Help"
echo "======================"
echo "• README.md - Complete project overview"
echo "• SETUP.md - Detailed setup guide"
echo "• TROUBLESHOOTING.md - Comprehensive troubleshooting"
echo "• DEMO_SCRIPT.md - Demo walkthrough guide"
echo "• List all commands: python -m setup_tools.main list-commands"
echo "• Command help: python -m setup_tools.main command-info <command-name>"
echo ""
echo "🎯 Key Features Available:"
echo "• One-command deployment with validation"
echo "• Multiple dashboard access methods"
echo "• Comprehensive validation suite"
echo "• Test data generation for demos"
echo "• Professional error handling and logging"

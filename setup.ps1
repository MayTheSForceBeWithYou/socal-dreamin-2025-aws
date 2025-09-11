# Salesforce -> AWS -> OpenSearch Lab Setup (Windows PowerShell)
# This script helps users set up the prerequisites quickly on Windows

param(
    [switch]$SkipChecks = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Salesforce → AWS → OpenSearch Lab Setup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "README.md") -or -not (Test-Path "setup_tools" -PathType Container)) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "   Expected files: README.md, setup_tools/" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found project files" -ForegroundColor Green

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 5) {
    Write-Host "❌ Error: PowerShell 5.0+ required, found PowerShell $($psVersion)" -ForegroundColor Red
    exit 1
}

Write-Host "✅ PowerShell version check passed" -ForegroundColor Green

# Check Python version
try {
    $pythonOutput = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    $pythonVersion = ($pythonOutput -split " ")[1]
    $versionParts = $pythonVersion -split "\."
    $majorMinor = "$($versionParts[0]).$($versionParts[1])"
    
    if ([version]$majorMinor -lt [version]"3.9") {
        Write-Host "❌ Error: Python 3.9+ required, found Python $pythonVersion" -ForegroundColor Red
        Write-Host "   Download Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Python version check passed" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: Python not found or not accessible" -ForegroundColor Red
    Write-Host "   Please install Python 3.9+ from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "   Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv" -PathType Container)) {
    Write-Host "📦 Creating Python virtual environment..." -ForegroundColor Blue
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Blue
& ".\.venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "   You may need to enable script execution with:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Install requirements
Write-Host "📥 Installing requirements..." -ForegroundColor Blue
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Failed to install requirements" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Requirements installed" -ForegroundColor Green

if (-not $SkipChecks) {
    # Check Salesforce CLI
    try {
        $sfVersion = sf --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Salesforce CLI not found"
        }
        Write-Host "✅ Salesforce CLI found" -ForegroundColor Green
        
        # Check if there is a default devhub org
        try {
            $orgList = sf org list --json | ConvertFrom-Json
            $hasDevHub = $false
            foreach ($org in $orgList.result.nonScratchOrgs + $orgList.result.sandboxes + $orgList.result.other) {
                if ($org.isDefaultDevHubUsername -eq $true) {
                    $hasDevHub = $true
                    break
                }
            }
            
            if (-not $hasDevHub) {
                Write-Host "⚠️  Warning: No default devhub org found." -ForegroundColor Yellow
                Write-Host "   Please ensure you have a Developer Edition or Trailhead Playground org with Dev Hub enabled." -ForegroundColor Yellow
                Write-Host "   Then run: sf org login web --alias <devhub-alias> --set-default-dev-hub" -ForegroundColor Yellow
            } else {
                Write-Host "✅ Default devhub org found" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "⚠️  Warning: Could not check devhub org status" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "⚠️  Warning: Salesforce CLI not found. Please install and configure it:" -ForegroundColor Yellow
        Write-Host "   Download from: https://developer.salesforce.com/tools/salesforcecli" -ForegroundColor Yellow
        Write-Host "   or run: npm install -g @salesforce/cli" -ForegroundColor Yellow
        Write-Host "   Then run: sf login" -ForegroundColor Yellow
    }

    # Check AWS CLI
    try {
        $awsVersion = aws --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "AWS CLI not found"
        }
        Write-Host "✅ AWS CLI found" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Warning: AWS CLI not found. Please install and configure it:" -ForegroundColor Yellow
        Write-Host "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" -ForegroundColor Yellow
        Write-Host "   or install with: winget install Amazon.AWSCLI" -ForegroundColor Yellow
        Write-Host "   Then run: aws configure" -ForegroundColor Yellow
    }

    # Check Terraform
    try {
        $terraformVersion = terraform --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform not found"
        }
        Write-Host "✅ Terraform found" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Warning: Terraform not found. Please install it:" -ForegroundColor Yellow
        Write-Host "   https://developer.hashicorp.com/terraform/downloads" -ForegroundColor Yellow
        Write-Host "   or install with: winget install Hashicorp.Terraform" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "🎉 Setup complete! Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 RECOMMENDED: One-Command Complete Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "1. Complete Salesforce setup (one command):" -ForegroundColor White
Write-Host "   python -m setup_tools salesforce setup-complete --contact-email your-email@example.com --environment demo" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Set up Terraform variables:" -ForegroundColor White
Write-Host "   python -m setup_tools infrastructure setup-terraform-vars --environment demo" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Configure Salesforce credentials:" -ForegroundColor White
Write-Host "   Copy-Item aws\sfdc-auth-secrets.json.example aws\sfdc-auth-secrets.json" -ForegroundColor Gray
Write-Host "   # Edit aws\sfdc-auth-secrets.json with your Salesforce credentials" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Deploy the complete lab:" -ForegroundColor White
Write-Host "   python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Access OpenSearch Dashboards" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "• Direct access: python -m setup_tools services access-dashboards --open-browser" -ForegroundColor White
Write-Host "• Proxy server: python -m setup_tools services start-dashboard-proxy" -ForegroundColor White
Write-Host "• SSH tunnel: ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@<EC2_IP>" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Validation & Testing" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan
Write-Host "• Comprehensive validation: python -m setup_tools validation validate-lab --comprehensive" -ForegroundColor White
Write-Host "• Generate test data: python -m setup_tools validation generate-test-data --count 100" -ForegroundColor White
Write-Host "• Check specific components: python -m setup_tools validation validate-lab --component opensearch" -ForegroundColor White
Write-Host ""
Write-Host "🛠️ Individual Commands (if needed)" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "• AWS certificate: python -m setup_tools aws generate-certificate --key-name aws-ec2" -ForegroundColor White
Write-Host "• Salesforce certificate: python -m setup_tools salesforce generate-certificate" -ForegroundColor White
Write-Host "• Create scratch org: python -m setup_tools salesforce create-scratch-org --org-name demo --duration-days 30" -ForegroundColor White
Write-Host "• Setup Connected App: python -m setup_tools salesforce setup-connected-app --contact-email your-email@example.com" -ForegroundColor White
Write-Host "• Create integration user: python -m setup_tools salesforce create-integration-user --contact-email your-email@example.com" -ForegroundColor White
Write-Host "• Query login history: python -m setup_tools salesforce query-login-history" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation & Help" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan
Write-Host "• README.md - Complete project overview" -ForegroundColor White
Write-Host "• SETUP.md - Detailed setup guide" -ForegroundColor White
Write-Host "• TROUBLESHOOTING.md - Comprehensive troubleshooting" -ForegroundColor White
Write-Host "• DEMO_SCRIPT.md - Demo walkthrough guide" -ForegroundColor White
Write-Host "• List all commands: python -m setup_tools list-commands" -ForegroundColor White
Write-Host "• Command help: python -m setup_tools command-info <command-name>" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Key Features Available:" -ForegroundColor Cyan
Write-Host "• One-command deployment with validation" -ForegroundColor White
Write-Host "• Multiple dashboard access methods" -ForegroundColor White
Write-Host "• Comprehensive validation suite" -ForegroundColor White
Write-Host "• Test data generation for demos" -ForegroundColor White
Write-Host "• Professional error handling and logging" -ForegroundColor White
Write-Host ""
Write-Host "💡 Windows-specific notes:" -ForegroundColor Yellow
Write-Host "• Use PowerShell (not Command Prompt) for best compatibility" -ForegroundColor White
Write-Host "• If you see execution policy errors, run:" -ForegroundColor White
Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
Write-Host "• For SSH commands, consider using Windows Subsystem for Linux (WSL)" -ForegroundColor White
Write-Host "  or install OpenSSH: winget install Microsoft.OpenSSH.Beta" -ForegroundColor Gray
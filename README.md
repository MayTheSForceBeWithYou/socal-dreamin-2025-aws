# Salesforce → AWS → OpenSearch Security Lab

This repository contains workshop materials for **SoCal Dreamin'** on
building a free-tier, real-time monitoring pipeline for Salesforce login
activity using AWS and OpenSearch.

## Overview

We will set up a lab environment where Salesforce activity logs (e.g.,
`LoginHistory`) are ingested into AWS, streamed through **Kinesis Data
Firehose**, and indexed in **Amazon OpenSearch Service** for
visualization, anomaly detection, and security alerting.

**Architecture Flow:**

    Salesforce (LoginHistory / API)
          ↓
    Python Script / Lambda (middleware)
          ↓
    Kinesis Data Firehose → S3 backup
          ↓
    Amazon OpenSearch Service
          ↓
    OpenSearch Dashboards (alerts, anomaly detection, visualizations)

## Prerequisites

### Required Software
-   **Python 3.9+** with pip
-   **AWS CLI** configured (`aws configure`)
-   **Terraform** (latest version)
-   **Git** (for cloning the repository)

### Required Accounts
-   **AWS Account** (free tier eligible)
-   **Salesforce Developer Edition** OR Trailhead Playground OR Scratch Org

### Required Knowledge
-   Basic knowledge of Salesforce & AWS
-   Understanding of SSH keys and certificates
-   Familiarity with command line tools

### Prerequisites Validation
The setup tools will automatically validate these prerequisites:
- ✅ AWS CLI configuration
- ✅ Terraform installation
- ✅ SSH keypair generation
- ✅ Salesforce configuration
- ✅ Terraform variables setup

## Manual Walkthrough (Summary)

1.  **Salesforce Setup**
    -   Create a Developer Org, Trailhead Playground, or Scratch Org.
    -   Collect `LoginHistory` events via Salesforce APIs.
    -   Generate a digital certificate for API access.
2.  **AWS Setup**
    -   Create an **Amazon OpenSearch Service** domain
        (`t3.small.search`, free tier).
    -   Create an **EC2 instance** with a Python app to poll
        Salesforce and populate OpenSearch index.
4.  **Visualize in OpenSearch**
    -   Create index template (`sfdc-logins*`).
    -   Build dashboards to monitor:
        -   Failed logins by time
        -   Top source IPs (failures)
        -   Suspicious login geolocations
    -   (Optional) Enable Anomaly Detection & Alerting.
5.  **Optional EC2 Instance**
    -   Launch an EC2 instance in a **non-US region** with Salesforce
        CLI installed.
    -   Use it to log in to Salesforce to simulate foreign logins →
        validate anomaly detection.

## 🚀 Complete Lab Infrastructure

This lab now features a **comprehensive, bulletproof setup system** with:

- **One-command deployment**: Deploy everything with a single command
- **Professional Python architecture**: Modular, extensible setup tools
- **Multiple dashboard access methods**: Direct, proxy, SSH tunnel, AWS console
- **Comprehensive validation**: End-to-end testing and validation
- **Production-ready**: Error handling, monitoring, and troubleshooting

### Quick Setup (Recommended)

**Option 1: Automated Setup Script**
```bash
# Clone the repository
git clone <repository-url>
cd socal-dreamin-2025-aws

# Run the automated setup script
./setup.sh
```

**Option 2: Manual Setup**

1. **Navigate to project root and create virtual environment:**
   ```bash
   cd /path/to/socal-dreamin-2025-aws
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Complete Salesforce setup (one command):**
   ```bash
   # This will create scratch org, certificates, Connected App, and integration user
   python -m setup_tools.main salesforce setup-complete --contact-email your-email@example.com --environment demo
   ```

4. **Set up Terraform variables:**
   ```bash
   # This will prompt for AWS configuration and populate terraform.tfvars
   python -m setup_tools.main infrastructure setup-terraform-vars --environment demo
   ```

5. **Configure Salesforce credentials:**
   - Copy `aws/sfdc-auth-secrets.json.example` to `aws/sfdc-auth-secrets.json`
   - Edit the file with your Salesforce Connected App credentials

### 🎯 Master Setup Command

```bash
# Deploy complete lab with validation
python -m setup_tools.main infrastructure deploy-complete-lab --environment demo --validate
```

This single command will:
- ✅ Validate all prerequisites
- 🏗️ Deploy Terraform infrastructure  
- 📦 Deploy application to EC2
- 📊 Set up dashboard access
- ✅ Validate complete deployment
- 📋 Provide access credentials and next steps

### 🔧 Available Commands

```bash
# Infrastructure Management
python -m setup_tools infrastructure deploy-complete-lab --validate

# Dashboard Access
python -m setup_tools services access-dashboards --open-browser
python -m setup_tools services start-dashboard-proxy

# Validation & Testing
python -m setup_tools validation validate-lab --comprehensive
python -m setup_tools validation generate-test-data --count 200

# Salesforce Operations (Complete Setup)
python -m setup_tools salesforce setup-complete --contact-email your-email@example.com

# Salesforce Operations (Individual)
python -m setup_tools salesforce create-scratch-org --org-name demo --duration-days 30
python -m setup_tools salesforce generate-certificate
python -m setup_tools salesforce setup-connected-app --contact-email your-email@example.com
python -m setup_tools salesforce create-integration-user --contact-email your-email@example.com

# Infrastructure Management
python -m setup_tools infrastructure setup-terraform-vars --environment demo
python -m setup_tools infrastructure deploy-complete-lab --validate
```

### 📊 Dashboard Access Methods

1. **Direct Browser Access** (Recommended):
   ```bash
   python -m setup_tools services access-dashboards --open-browser
   ```

2. **Python Proxy Server**:
   ```bash
   python -m setup_tools services start-dashboard-proxy
   # Access: http://localhost:8080/_dashboards/
   ```

3. **SSH Tunnel**:
   ```bash
   ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@<EC2_IP>
   # Access: https://localhost:9200/_dashboards/
   ```

4. **AWS Console**: Direct access via AWS web console

### 📚 Documentation

- **[SETUP.md](./SETUP.md)**: Complete setup guide
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**: Comprehensive troubleshooting
- **[DEMO_SCRIPT.md](./DEMO_SCRIPT.md)**: Demo walkthrough guide
- **[OPENSEARCH_DASHBOARDS_ACCESS.md](./OPENSEARCH_DASHBOARDS_ACCESS.md)**: Dashboard access details

### 🔍 Quick Validation

```bash
# Validate everything is working
python -m setup_tools validation validate-lab --comprehensive

# Generate test data for demonstration
python -m setup_tools validation generate-test-data --count 100

# Check specific components
python -m setup_tools validation validate-lab --component opensearch
python -m setup_tools validation validate-lab --component pipeline
```

### 🛠️ Troubleshooting

```bash
# Get comprehensive help
python -m setup_tools validation validate-lab --comprehensive

# Access dashboards with multiple methods
python -m setup_tools services access-dashboards --create-guide

# Check individual components
python -m setup_tools validation validate-lab --component <component>
```

**Common Issues & Solutions:**

1. **Prerequisites Validation Failures**:
   - **SSH Key Missing**: Run `python -m setup_tools.main aws generate-certificate --key-name aws-ec2`
   - **Salesforce Config Missing**: Copy `aws/sfdc-auth-secrets.json.example` to `aws/sfdc-auth-secrets.json` and configure
   - **Terraform Variables Missing**: Run `python -m setup_tools.main infrastructure setup-terraform-vars --environment demo`
   - **AWS CLI Not Configured**: Run `aws configure` with your credentials
   - **Salesforce CLI Not Found**: Install Salesforce CLI from https://developer.salesforce.com/tools/sfdxcli
   - **Salesforce Certificate Missing**: Run `python -m setup_tools.main salesforce generate-certificate` first

2. **OpenSearch Authentication**: Use the Python proxy server method
3. **EC2 Connection**: Check SSH key permissions and security groups  
4. **Salesforce Integration**: Verify Connected App configuration
5. **Data Pipeline**: Generate test data if no real data is flowing

### 🎉 Key Features

- **One-Command Deployment**: Complete lab setup in minutes
- **Multiple Access Methods**: Reliable dashboard access
- **Comprehensive Validation**: End-to-end testing
- **Professional Architecture**: Modular, extensible Python tools
- **Production-Ready**: Error handling, monitoring, logging
- **Demo-Ready**: Test data generation and validation

## Future Work

We will continue evolving this lab with:
- **Salesforce Scratch Org** setup automation
- **Lambda-based ingestion** instead of EC2
- **Advanced anomaly detection** with OpenSearch ML
- **Multi-region deployment** options

## Workshop Goals

-   Show Salesforce professionals how to extend org security monitoring
    using **cloud-native and open-source tools**.
-   Provide a free-tier, hands-on SIEM-like experience without requiring
    Splunk licenses.
-   Teach reusable patterns for integrating Salesforce into enterprise
    security ecosystems.

## License

MIT License

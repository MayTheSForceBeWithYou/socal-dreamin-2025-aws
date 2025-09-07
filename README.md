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

-   Salesforce Developer Edition OR Trailhead Playground OR Scratch Org
-   AWS account (free tier eligible)
-   Python 3.9+
-   AWS CLI configured (`aws configure`)
-   Basic knowledge of Salesforce & AWS

## Manual Walkthrough (Summary)

1.  **Salesforce Setup**
    -   Create a Developer Org, Trailhead Playground, or Scratch Org.
    -   Collect `LoginHistory` events via Salesforce APIs.
    -   Generate a Security Token for API access.
2.  **AWS Setup**
    -   Create S3 bucket (backup destination).
    -   Create an **Amazon OpenSearch Service** domain
        (`t3.small.search`, free tier).
    -   Create a **Kinesis Firehose** delivery stream → OpenSearch (+ S3
        backup).
3.  **Local Ingestion Script**
    -   Use Python + `simple-salesforce` + `boto3` to pull LoginHistory
        from Salesforce and push to Firehose.
    -   Example script included in `/scripts/ingest_login_history.py`.
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

## 🚀 Complete Lab Infrastructure (NEW!)

This lab now features a **comprehensive, bulletproof setup system** with:

- **One-command deployment**: Deploy everything with a single command
- **Professional Python architecture**: Modular, extensible setup tools
- **Multiple dashboard access methods**: Direct, proxy, SSH tunnel, AWS console
- **Comprehensive validation**: End-to-end testing and validation
- **Production-ready**: Error handling, monitoring, and troubleshooting

### 🎯 Master Setup Command

```bash
# Deploy complete lab with validation
python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate
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

# Salesforce Operations
python -m setup_tools salesforce create-scratch-org
python -m setup_tools salesforce generate-certificate
python -m setup_tools salesforce create-integration-user
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

1. **OpenSearch Authentication**: Use the Python proxy server method
2. **EC2 Connection**: Check SSH key permissions and security groups  
3. **Salesforce Integration**: Verify Connected App configuration
4. **Data Pipeline**: Generate test data if no real data is flowing

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

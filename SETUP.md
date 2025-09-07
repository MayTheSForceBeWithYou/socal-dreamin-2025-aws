# Complete Lab Setup Guide

This guide provides step-by-step instructions for setting up the complete Salesforce-to-AWS data pipeline lab.

## Prerequisites

Before starting, ensure you have:

- **AWS CLI** configured with appropriate permissions
- **Terraform** installed (>= 1.0)
- **Python 3.8+** with pip
- **SSH keypair** for EC2 access
- **Salesforce** scratch org with Connected App configured

## Quick Start

### 1. Deploy Complete Lab

```bash
# Deploy everything with one command
python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate
```

This command will:
- ✅ Validate prerequisites
- 🏗️ Deploy Terraform infrastructure
- 📦 Deploy application to EC2
- 📊 Set up dashboard access
- ✅ Validate complete deployment

### 2. Access OpenSearch Dashboards

```bash
# Get dashboard access information
python -m setup_tools services access-dashboards --create-guide

# Or start proxy server for local access
python -m setup_tools services start-dashboard-proxy
```

### 3. Generate Test Data

```bash
# Generate sample login events for demonstration
python -m setup_tools validation generate-test-data --count 200 --create-template
```

### 4. Validate Everything

```bash
# Run comprehensive validation
python -m setup_tools validation validate-lab --comprehensive
```

## Detailed Setup Instructions

### Step 1: Environment Preparation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd socal-dreamin-2025-aws
   ```

2. **Set up Python environment**:
   ```bash
   cd setup_tools
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure AWS CLI**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, and region
   ```

4. **Verify prerequisites**:
   ```bash
   python -m setup_tools infrastructure deploy-complete-lab --dry-run --skip-prereqs
   ```

### Step 2: Salesforce Configuration

1. **Create scratch org** (if not already done):
   ```bash
   python -m setup_tools salesforce create-scratch-org --org-name "demo-org" --duration-days 30
   ```

2. **Generate certificates**:
   ```bash
   python -m setup_tools salesforce generate-certificate
   ```

3. **Create integration user**:
   ```bash
   python -m setup_tools salesforce create-integration-user --contact-email "your-email@example.com"
   ```

4. **Update Terraform variables**:
   Edit `aws/terraform/terraform.tfvars` with your Salesforce configuration:
   ```hcl
   salesforce_instance_url = "https://your-org.scratch.my.salesforce.com"
   salesforce_client_id = "your-connected-app-consumer-key"
   salesforce_username = "integration-user@your-org.scratch.my.salesforce.com"
   salesforce_private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
   ```

### Step 3: Infrastructure Deployment

1. **Deploy infrastructure**:
   ```bash
   python -m setup_tools infrastructure deploy-complete-lab --environment demo
   ```

2. **Monitor deployment**:
   The script will show progress and provide status updates. Wait for completion.

3. **Note the outputs**:
   Save the following information:
   - EC2 Public IP
   - OpenSearch Endpoint
   - OpenSearch Master Password
   - SSH Command

### Step 4: Application Deployment

The application deployment is handled automatically by the deploy script, but you can also run it separately:

```bash
bash scripts/deploy-application.sh
```

### Step 5: Dashboard Access Setup

1. **Test direct access**:
   ```bash
   python -m setup_tools services access-dashboards
   ```

2. **If direct access fails, use proxy**:
   ```bash
   python -m setup_tools services start-dashboard-proxy
   # Access: http://localhost:8080/_dashboards/
   ```

3. **Create access guide**:
   ```bash
   python -m setup_tools services access-dashboards --create-guide
   ```

### Step 6: Data Pipeline Validation

1. **Generate test data**:
   ```bash
   python -m setup_tools validation generate-test-data --count 100
   ```

2. **Validate pipeline**:
   ```bash
   python -m setup_tools validation validate-lab --component pipeline
   ```

3. **Check application logs**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   sudo journalctl -u salesforce-streamer -f
   ```

## Access Methods

### Method 1: Direct Browser Access (Recommended)

1. Open browser
2. Go to: `https://<opensearch-endpoint>/_dashboards/`
3. Login with:
   - Username: `admin`
   - Password: `<opensearch-master-password>`

### Method 2: Python Proxy Server

1. Start proxy:
   ```bash
   python -m setup_tools services start-dashboard-proxy
   ```

2. Access: `http://localhost:8080/_dashboards/`

### Method 3: SSH Tunnel

1. Start tunnel:
   ```bash
   ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@<EC2_IP>
   ```

2. Access: `https://localhost:9200/_dashboards/`

### Method 4: AWS Console

1. Go to AWS Console → OpenSearch
2. Find domain: `salesforce-opensearch-lab-os`
3. Click "OpenSearch Dashboards URL"

## Dashboard Usage

### 1. Create Index Pattern

1. Go to Stack Management → Index Patterns
2. Create pattern: `salesforce-login-events*`
3. Select `@timestamp` as time field

### 2. Explore Data

1. Go to Discover tab
2. Select your index pattern
3. View login events data

### 3. Create Visualizations

1. Go to Visualize tab
2. Create visualizations:
   - Login attempts over time
   - Success/failure rates
   - Top users by login count
   - Geographic distribution

### 4. Build Dashboard

1. Go to Dashboard tab
2. Create new dashboard
3. Add your visualizations
4. Save and share

## Troubleshooting

### Common Issues

1. **Terraform deployment fails**:
   - Check AWS credentials
   - Verify region settings
   - Check for resource limits

2. **EC2 connection fails**:
   - Verify SSH key permissions
   - Check security groups
   - Wait for instance to be ready

3. **OpenSearch access fails**:
   - Check domain status in AWS Console
   - Verify credentials
   - Try proxy server method

4. **Application not running**:
   - SSH to EC2 and check logs
   - Verify Secrets Manager access
   - Check Salesforce connectivity

### Useful Commands

```bash
# Check EC2 status
aws ec2 describe-instances --instance-ids <instance-id>

# Check OpenSearch domain
aws es describe-elasticsearch-domain --domain-name salesforce-opensearch-lab-os

# SSH to EC2
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>

# Check application logs
sudo journalctl -u salesforce-streamer -f

# Test OpenSearch connection
curl -u admin:<password> https://<endpoint>/

# Validate specific component
python -m setup_tools validation validate-lab --component <component>
```

## Cleanup

To tear down the infrastructure:

```bash
cd aws/terraform
terraform destroy -auto-approve
```

## Support

For additional help:

1. Run comprehensive validation:
   ```bash
   python -m setup_tools validation validate-lab --comprehensive
   ```

2. Check the troubleshooting guide in `TROUBLESHOOTING.md`

3. Review logs and error messages

4. Contact the development team

## Next Steps

After successful setup:

1. **Explore the data** in OpenSearch Dashboards
2. **Create visualizations** for your use case
3. **Set up monitoring** and alerts
4. **Customize the application** for your needs
5. **Scale the infrastructure** as required

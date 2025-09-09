# Demo Script for Salesforce-to-AWS Data Pipeline

This script provides a step-by-step walkthrough for demonstrating the complete Salesforce-to-AWS data pipeline lab.

## Pre-Demo Setup

### 1. Verify Prerequisites

```bash
# Check AWS CLI
aws sts get-caller-identity

# Check Terraform
terraform version

# Check Python environment
python --version
pip list | grep -E "(click|rich|requests|boto3)"
```

### 2. Deploy Complete Lab

```bash
# Deploy everything with validation
python -m setup_tools infrastructure deploy-complete-lab --environment demo --validate
```

**Expected Output**:
- ✅ Prerequisites validated
- 🏗️ Infrastructure deployed
- 📦 Application deployed
- 📊 Dashboard access configured
- ✅ All validations passed

### 3. Generate Test Data

```bash
# Generate sample data for demonstration
python -m setup_tools validation generate-test-data --count 200 --create-template
```

## Demo Walkthrough

### Part 1: Infrastructure Overview (5 minutes)

**Objective**: Show the complete AWS infrastructure

**Script**:
```bash
# Show infrastructure components
echo "🏗️ AWS Infrastructure Components:"
echo "1. VPC with public/private subnets"
echo "2. EC2 instance running Python application"
echo "3. OpenSearch domain for data storage"
echo "4. IAM roles and policies for security"
echo "5. Secrets Manager for Salesforce credentials"

# Display infrastructure summary
python -m setup_tools infrastructure deploy-complete-lab --dry-run
```

**Key Points**:
- Infrastructure as Code with Terraform
- Secure networking with VPC
- Managed OpenSearch for analytics
- Automated deployment process

### Part 2: Data Pipeline Demonstration (10 minutes)

**Objective**: Show real-time data flow from Salesforce to AWS

**Script**:
```bash
# Show application status
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo systemctl status salesforce-streamer"

# Show recent logs
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo journalctl -u salesforce-streamer --since '10 minutes ago' --no-pager"

# Show data in OpenSearch
curl -u os_admin:<password> https://<endpoint>/salesforce-login-events/_count
```

**Key Points**:
- Python application polls Salesforce every 60 seconds
- JWT authentication with Salesforce
- Data indexed to OpenSearch in real-time
- Error handling and logging

### Part 3: OpenSearch Dashboards (15 minutes)

**Objective**: Demonstrate data visualization and analytics

**Setup**:
```bash
# Access dashboards
python -m setup_tools services access-dashboards --open-browser
```

**Demo Steps**:

1. **Login to Dashboards**
   - URL: `https://<opensearch-endpoint>/_dashboards/`
   - Username: `os_admin`
   - Password: `<opensearch-master-password>`

2. **Create Index Pattern**
   - Go to Stack Management → Index Patterns
   - Create pattern: `salesforce-login-events*`
   - Select `@timestamp` as time field

3. **Explore Data**
   - Go to Discover tab
   - Show login events data
   - Demonstrate filtering and searching

4. **Create Visualizations**
   - Go to Visualize tab
   - Create "Login Attempts Over Time" (Line chart)
   - Create "Login Status Distribution" (Pie chart)
   - Create "Top Users by Login Count" (Data table)

5. **Build Dashboard**
   - Go to Dashboard tab
   - Create new dashboard
   - Add visualizations
   - Save and share

**Key Points**:
- Real-time data visualization
- Interactive dashboards
- Search and analytics capabilities
- Business insights from login data

### Part 4: Advanced Features (10 minutes)

**Objective**: Show advanced capabilities and monitoring

**Script**:
```bash
# Show cluster health
curl -u os_admin:<password> https://<endpoint>/_cluster/health

# Show index statistics
curl -u os_admin:<password> https://<endpoint>/salesforce-login-events/_stats

# Show application metrics
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo systemctl show salesforce-streamer --property=ActiveState,SubState"
```

**Demo Features**:

1. **Monitoring and Alerts**
   - Show cluster health status
   - Demonstrate monitoring capabilities
   - Explain alerting possibilities

2. **Data Management**
   - Show index management
   - Demonstrate data retention policies
   - Explain scaling options

3. **Security Features**
   - Show IAM-based access control
   - Demonstrate encryption at rest
   - Explain network security

**Key Points**:
- Production-ready monitoring
- Scalable architecture
- Security best practices
- Operational excellence

### Part 5: Troubleshooting and Validation (5 minutes)

**Objective**: Show operational capabilities

**Script**:
```bash
# Run comprehensive validation
python -m setup_tools validation validate-lab --comprehensive

# Show troubleshooting capabilities
python -m setup_tools services access-dashboards --create-guide
```

**Key Points**:
- Automated validation
- Comprehensive troubleshooting
- Operational readiness
- Support capabilities

## Demo Scripts

### Quick Demo (5 minutes)

```bash
#!/bin/bash
# Quick demo script

echo "🚀 Salesforce-to-AWS Data Pipeline Demo"
echo "======================================"

# Show infrastructure
echo "1. Infrastructure deployed with Terraform"
python -m setup_tools infrastructure deploy-complete-lab --dry-run

# Show data
echo "2. Data pipeline active"
curl -u os_admin:<password> https://<endpoint>/salesforce-login-events/_count

# Show dashboards
echo "3. OpenSearch Dashboards available"
python -m setup_tools services access-dashboards

echo "✅ Demo complete!"
```

### Full Demo (30 minutes)

```bash
#!/bin/bash
# Full demo script

echo "🚀 Complete Salesforce-to-AWS Data Pipeline Demo"
echo "================================================"

# Part 1: Infrastructure
echo "Part 1: Infrastructure Overview"
python -m setup_tools infrastructure deploy-complete-lab --dry-run

# Part 2: Data Pipeline
echo "Part 2: Data Pipeline"
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo journalctl -u salesforce-streamer --since '5 minutes ago' --no-pager"

# Part 3: Dashboards
echo "Part 3: OpenSearch Dashboards"
python -m setup_tools services access-dashboards --open-browser

# Part 4: Validation
echo "Part 4: System Validation"
python -m setup_tools validation validate-lab --comprehensive

echo "✅ Full demo complete!"
```

## Demo Tips

### Before the Demo

1. **Test everything**:
   ```bash
   python -m setup_tools validation validate-lab --comprehensive
   ```

2. **Prepare backup plans**:
   - Have proxy server ready
   - Prepare screenshots
   - Have test data ready

3. **Check timing**:
   - Ensure data is flowing
   - Verify dashboards are accessible
   - Test all commands

### During the Demo

1. **Start with the big picture**
2. **Show the data flow**
3. **Demonstrate real-time capabilities**
4. **Highlight business value**
5. **Address questions confidently**

### After the Demo

1. **Provide access information**
2. **Share documentation**
3. **Offer hands-on time**
4. **Collect feedback**

## Common Demo Questions

### Q: How does the authentication work?
**A**: We use JWT (JSON Web Tokens) with Salesforce Connected Apps. The private key is stored securely in AWS Secrets Manager, and the application authenticates using the JWT flow.

### Q: How do you handle errors?
**A**: The application has comprehensive error handling, logging, and retry mechanisms. All errors are logged and can be monitored through CloudWatch or application logs.

### Q: Can this scale to production?
**A**: Yes, this architecture is production-ready. You can scale the OpenSearch cluster, use multiple EC2 instances, and implement additional monitoring and alerting.

### Q: What about security?
**A**: We implement multiple security layers: VPC isolation, IAM roles, encryption at rest and in transit, and network security groups.

### Q: How do you monitor the system?
**A**: We use OpenSearch for application monitoring, CloudWatch for infrastructure monitoring, and custom dashboards for business metrics.

## Demo Environment Setup

### Required Information

Before starting the demo, have ready:
- EC2 Public IP
- OpenSearch Endpoint
- OpenSearch Master Password
- SSH Command
- Dashboard URLs

### Backup Plans

1. **If direct dashboard access fails**:
   ```bash
   python -m setup_tools services start-dashboard-proxy
   ```

2. **If data is not flowing**:
   ```bash
   python -m setup_tools validation generate-test-data --count 100
   ```

3. **If validation fails**:
   ```bash
   python -m setup_tools validation validate-lab --component <component>
   ```

## Success Metrics

### Demo Success Indicators

- ✅ Infrastructure deployed successfully
- ✅ Data flowing from Salesforce to OpenSearch
- ✅ Dashboards accessible and functional
- ✅ Visualizations created and working
- ✅ All validations passing
- ✅ Audience engaged and asking questions

### Follow-up Actions

After a successful demo:
1. **Provide access credentials**
2. **Share documentation links**
3. **Schedule follow-up sessions**
4. **Collect contact information**
5. **Offer additional resources**

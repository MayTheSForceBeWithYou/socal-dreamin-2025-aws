# Troubleshooting Guide

This guide helps you resolve common issues with the Salesforce-to-AWS data pipeline lab.

## Prerequisites Issues

### AWS CLI Not Configured

**Error**: `AWS CLI not configured`

**Solution**:
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, region, and output format
```

**Verification**:
```bash
aws sts get-caller-identity
```

### Terraform Not Installed

**Error**: `terraform: command not found`

**Solution**:
```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Windows
# Download from https://www.terraform.io/downloads.html
```

**Verification**:
```bash
terraform version
```

### SSH Key Not Found

**Error**: `SSH key not found`

**Solution**:
```bash
# Generate SSH keypair
python -m setup_tools aws generate-certificate --key-name aws-ec2
```

**Verification**:
```bash
ls -la aws/certs/aws-ec2*
```

## Infrastructure Deployment Issues

### Terraform State Lock

**Error**: `Error acquiring the state lock`

**Solution**:
```bash
cd aws/terraform
terraform force-unlock <lock-id>
```

### Resource Already Exists

**Error**: `Resource already exists`

**Solution**:
```bash
# Check existing resources
aws ec2 describe-instances --filters "Name=tag:Project,Values=salesforce-opensearch-lab"
aws es describe-elasticsearch-domain --domain-name salesforce-opensearch-lab-os

# Destroy and recreate if needed
terraform destroy -auto-approve
terraform apply -auto-approve
```

### Insufficient Permissions

**Error**: `Access Denied` or `Insufficient permissions`

**Solution**:
1. Check IAM permissions for your AWS user/role
2. Ensure you have permissions for:
   - EC2 (instances, security groups, key pairs)
   - OpenSearch (domains, access policies)
   - IAM (roles, policies)
   - Secrets Manager (secrets, versions)

**Required Permissions**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "es:*",
                "iam:*",
                "secretsmanager:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## EC2 Instance Issues

### SSH Connection Failed

**Error**: `Connection refused` or `Permission denied`

**Solutions**:

1. **Check instance status**:
   ```bash
   aws ec2 describe-instances --instance-ids <instance-id>
   ```

2. **Verify security group**:
   ```bash
   aws ec2 describe-security-groups --group-ids <security-group-id>
   ```

3. **Check SSH key permissions**:
   ```bash
   chmod 600 aws/certs/aws-ec2
   ```

4. **Wait for instance to be ready**:
   ```bash
   # Wait 2-3 minutes after instance launch
   aws ec2 wait instance-running --instance-ids <instance-id>
   ```

### Application Service Not Running

**Error**: `salesforce-streamer service not active`

**Solutions**:

1. **SSH to instance and check status**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   sudo systemctl status salesforce-streamer
   ```

2. **Check logs**:
   ```bash
   sudo journalctl -u salesforce-streamer -f
   ```

3. **Restart service**:
   ```bash
   sudo systemctl restart salesforce-streamer
   sudo systemctl enable salesforce-streamer
   ```

4. **Check environment variables**:
   ```bash
   sudo cat /opt/salesforce-streamer/.env
   ```

### Application Dependencies Missing

**Error**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
cd /opt/salesforce-streamer
sudo pip3 install -r requirements.txt
```

## OpenSearch Issues

### Domain Not Accessible

**Error**: `Connection refused` or `Timeout`

**Solutions**:

1. **Check domain status**:
   ```bash
   aws es describe-elasticsearch-domain --domain-name salesforce-opensearch-lab-os
   ```

2. **Verify security groups**:
   ```bash
   aws ec2 describe-security-groups --group-ids <opensearch-security-group-id>
   ```

3. **Check access policies**:
   ```bash
   aws es describe-elasticsearch-domain --domain-name salesforce-opensearch-lab-os --query 'DomainStatus.AccessPolicies'
   ```

### Authentication Failed

**Error**: `401 Unauthorized` or `Authentication failed`

**Solutions**:

1. **Verify credentials**:
   ```bash
   terraform output opensearch_master_password
   ```

2. **Test connection**:
   ```bash
   curl -u admin:<password> https://<endpoint>/
   ```

3. **Check advanced security settings**:
   ```bash
   aws es describe-elasticsearch-domain --domain-name salesforce-opensearch-lab-os --query 'DomainStatus.AdvancedSecurityOptions'
   ```

### Dashboard Access Issues

**Error**: `User: anonymous is not authorized`

**Solutions**:

1. **Use Python proxy server**:
   ```bash
   python -m setup_tools services start-dashboard-proxy
   ```

2. **Try SSH tunnel**:
   ```bash
   ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@<EC2_IP>
   ```

3. **Check AWS Console access**:
   - Go to AWS Console → OpenSearch
   - Find your domain
   - Click "OpenSearch Dashboards URL"

## Salesforce Integration Issues

### Authentication Failed

**Error**: `Salesforce authentication failed: 400 Bad Request`

**Solutions**:

1. **Check Connected App configuration**:
   - Verify Consumer Key
   - Check OAuth settings
   - Ensure JWT is enabled

2. **Verify private key**:
   ```bash
   # Check if private key is correctly formatted
   cat aws/terraform/terraform.tfvars | grep salesforce_private_key
   ```

3. **Test Salesforce connection**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   sudo journalctl -u salesforce-streamer | grep -i salesforce
   ```

### SOQL Query Issues

**Error**: `sObject type 'LoginEventStream' is not supported`

**Solution**:
The application uses `LoginHistory` instead of `LoginEventStream`. This is correct behavior.

### No Data Retrieved

**Error**: No login events in OpenSearch

**Solutions**:

1. **Check Salesforce data**:
   ```bash
   python -m setup_tools salesforce query-login-history
   ```

2. **Generate test data**:
   ```bash
   python -m setup_tools validation generate-test-data --count 100
   ```

3. **Check application logs**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   sudo journalctl -u salesforce-streamer -f
   ```

## Data Pipeline Issues

### No Documents in Index

**Error**: `No documents found in the index`

**Solutions**:

1. **Check if index exists**:
   ```bash
   curl -u admin:<password> https://<endpoint>/salesforce-login-events
   ```

2. **Verify data flow**:
   ```bash
   python -m setup_tools validation validate-lab --component pipeline
   ```

3. **Generate test data**:
   ```bash
   python -m setup_tools validation generate-test-data --count 50
   ```

### Index Pattern Issues

**Error**: `Unable to fetch mapping` in Dashboards

**Solutions**:

1. **Create index template**:
   ```bash
   python -m setup_tools validation generate-test-data --create-template
   ```

2. **Manually create index**:
   ```bash
   curl -X PUT -u admin:<password> https://<endpoint>/salesforce-login-events
   ```

## Network Issues

### Security Group Problems

**Error**: `Connection timeout` or `Connection refused`

**Solutions**:

1. **Check security group rules**:
   ```bash
   aws ec2 describe-security-groups --group-ids <security-group-id>
   ```

2. **Verify VPC configuration**:
   ```bash
   aws ec2 describe-vpcs --vpc-ids <vpc-id>
   ```

3. **Check route tables**:
   ```bash
   aws ec2 describe-route-tables --filters "Name=vpc-id,Values=<vpc-id>"
   ```

### DNS Resolution Issues

**Error**: `Name resolution failed`

**Solutions**:

1. **Check DNS settings**:
   ```bash
   nslookup <opensearch-endpoint>
   ```

2. **Try IP address instead**:
   ```bash
   # Get IP address
   dig <opensearch-endpoint>
   ```

## Performance Issues

### Slow OpenSearch Queries

**Solutions**:

1. **Check cluster health**:
   ```bash
   curl -u admin:<password> https://<endpoint>/_cluster/health
   ```

2. **Monitor resource usage**:
   ```bash
   curl -u admin:<password> https://<endpoint>/_nodes/stats
   ```

3. **Scale up instance**:
   ```bash
   # Update terraform.tfvars
   opensearch_instance_type = "t3.medium.search"
   terraform apply -auto-approve
   ```

### EC2 Performance Issues

**Solutions**:

1. **Check instance metrics**:
   ```bash
   aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=<instance-id>
   ```

2. **Scale up instance**:
   ```bash
   # Update terraform.tfvars
   ec2_instance_type = "t3.small"
   terraform apply -auto-approve
   ```

## Validation Issues

### Validation Failures

**Error**: `Some validations failed`

**Solutions**:

1. **Run specific component validation**:
   ```bash
   python -m setup_tools validation validate-lab --component <component>
   ```

2. **Check individual components**:
   ```bash
   # Check Terraform
   cd aws/terraform && terraform plan
   
   # Check EC2
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   
   # Check OpenSearch
   curl -u admin:<password> https://<endpoint>/
   ```

3. **Review logs**:
   ```bash
   # Application logs
   ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP>
   sudo journalctl -u salesforce-streamer
   
   # System logs
   sudo journalctl -xe
   ```

## Getting Help

### Debug Information

Collect debug information:

```bash
# System information
python -m setup_tools validation validate-lab --comprehensive > debug.log

# Infrastructure status
cd aws/terraform && terraform output -json >> debug.log

# Application logs
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo journalctl -u salesforce-streamer" >> debug.log
```

### Common Commands

```bash
# Check everything
python -m setup_tools validation validate-lab --comprehensive

# Restart application
ssh -i aws/certs/aws-ec2 ec2-user@<EC2_IP> "sudo systemctl restart salesforce-streamer"

# Test OpenSearch
curl -u admin:<password> https://<endpoint>/

# Generate test data
python -m setup_tools validation generate-test-data --count 100

# Access dashboards
python -m setup_tools services access-dashboards
```

### Contact Support

If you continue to experience issues:

1. **Collect debug information** (see above)
2. **Document the exact error messages**
3. **Note your environment** (OS, Python version, AWS region)
4. **Contact the development team** with this information

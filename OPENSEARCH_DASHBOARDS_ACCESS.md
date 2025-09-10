# OpenSearch Dashboards Access Guide

This guide explains how to access your OpenSearch Dashboards for the Salesforce Streamer project using the new **IP Gateway (Bastion Host)** approach.

## 🚀 Quick Start

The **easiest way** to access OpenSearch Dashboards is through the new IP Gateway:

1. Deploy infrastructure with bastion host: `terraform apply`
2. Get bastion IP: `terraform output bastion_public_ip`
3. Open browser: `https://BASTION_IP/_dashboards/`
4. You'll be authenticated automatically through AWS IAM

**Alternative**: Use AWS Console for AWS IAM authentication:
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **OpenSearch** service
3. Find your domain: `sf-opensearch-lab-os`
4. Click **"OpenSearch Dashboards URL"**

## 📋 Prerequisites

- AWS CLI configured with valid credentials
- Terraform deployed with bastion host
- Your public IP configured in `allowed_cidr_blocks` (for security)

## 🔧 Access Methods

### Method 1: IP Gateway (Recommended - New Approach)

**Pros:** Direct HTTPS access, secure, no SSH tunneling needed, works from any browser
**Cons:** Requires bastion host deployment

1. **Deploy the infrastructure** (if not already done):
   ```bash
   cd aws/terraform
   terraform apply
   ```

2. **Get the bastion host IP**:
   ```bash
   terraform output bastion_public_ip
   ```

3. **Open browser** and go to: `https://BASTION_IP/_dashboards/`

4. **You're authenticated!** The bastion host acts as a secure proxy to OpenSearch

### Method 2: AWS Console (Alternative)

**Pros:** Easiest, automatic authentication, no setup required
**Cons:** Requires AWS Console access

1. Open [AWS Console](https://console.aws.amazon.com/)
2. Search for "OpenSearch" in the services
3. Click on your domain: `sf-opensearch-lab-os`
4. Click the **"OpenSearch Dashboards URL"** button
5. You'll be redirected to Dashboards with full access

### Method 3: SSH to Bastion + Local Proxy (For Advanced Users)

**Pros:** Full control, good for development
**Cons:** Requires SSH access and local proxy setup

1. **SSH into bastion host**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@$(cd aws/terraform && terraform output -raw bastion_public_ip)
   ```

2. **Check nginx status**:
   ```bash
   sudo systemctl status nginx
   ```

3. **View logs**:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

### Method 4: CLI Access (For Testing)

**Pros:** Good for testing connectivity and API calls
**Cons:** Command-line only, not for Dashboards UI

1. **SSH into bastion**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@$(cd aws/terraform && terraform output -raw bastion_public_ip)
   ```

2. **Test basic connectivity**:
   ```bash
   curl -X GET 'https://localhost/_dashboards/'
   ```

3. **Test OpenSearch API**:
   ```bash
   curl -X GET 'https://localhost/'
   ```

## 🔍 Troubleshooting

### "Connection refused" on bastion IP
- **Cause**: Bastion host not running or nginx not started
- **Solution**: Check bastion instance status and SSH in to restart nginx

### "SSL certificate error" in browser
- **Cause**: Self-signed certificate on bastion
- **Solution**: Click "Advanced" → "Proceed to bastion IP" (it's safe)

### "User: anonymous is not authorized"
- **Cause**: Browser can't authenticate with AWS IAM through proxy
- **Solution**: Use AWS Console method instead, or configure proper authentication

### Bastion host not accessible
- **Cause**: Security group not allowing your IP
- **Solution**: Check `allowed_cidr_blocks` in terraform.tfvars and update with your public IP

### OpenSearch domain not found
- **Cause**: Domain might be in different region
- **Solution**: Check AWS region in terraform configuration

## 🔐 Security Features

- **IP Restriction**: Only your IP can access the bastion host
- **HTTPS Encryption**: All traffic encrypted between you and bastion
- **VPC Security**: Bastion can only access OpenSearch within the VPC
- **IAM Authentication**: OpenSearch uses AWS IAM for authentication
- **Self-signed Certificates**: Bastion uses self-signed certs for local proxy

## 📊 What You Can Do in Dashboards

Once you have access, you can:

1. **View Indexed Data**: Browse the `salesforce-login-events` index
2. **Create Visualizations**: Build charts and graphs from your data
3. **Set Up Dashboards**: Create custom dashboards for monitoring
4. **Search Data**: Use the Discover tab to search and filter events
5. **Manage Index Patterns**: Configure how data is displayed

## 🆘 Getting Help

If you encounter issues:

1. Check bastion instance status: `aws ec2 describe-instances --filters "Name=tag:Type,Values=opensearch-gateway"`
2. Verify OpenSearch domain status in AWS Console
3. Check bastion logs: `ssh -i aws/certs/aws-ec2 ec2-user@BASTION_IP 'sudo journalctl -u nginx -f'`
4. Test connectivity from bastion: `curl -X GET 'https://localhost/'`

## 🔄 Migration from SSH Tunneling

If you were previously using SSH tunneling:

1. **Old method**: `ssh -L 9200:localhost:9200 ec2-user@EC2_IP`
2. **New method**: Direct access via `https://BASTION_IP/_dashboards/`

The new IP gateway approach is more secure and easier to use!

---

**Recommendation**: Use Method 1 (IP Gateway) for the easiest and most secure access to OpenSearch Dashboards.



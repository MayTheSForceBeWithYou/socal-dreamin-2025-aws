# OpenSearch Dashboards Access Guide

This guide explains how to access your OpenSearch Dashboards for the Salesforce Streamer project.

## 🚀 Quick Start

The **easiest way** to access OpenSearch Dashboards with proper authentication is using the User Proxy:

1. Run: `./scripts/start-user-proxy.sh`
2. Open browser: `http://localhost:8080/_dashboards/`
3. You'll be authenticated as the OpenSearch user (os_admin/password)

**Alternative**: Use AWS Console for AWS IAM authentication:
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **OpenSearch** service
3. Find your domain: `sf-opensearch-lab-os`
4. Click **"OpenSearch Dashboards URL"**

## 📋 Prerequisites

- AWS CLI configured with valid credentials
- SSH key file: `aws/certs/aws-ec2`
- EC2 instance running (check with `terraform output`)

## 🔧 Access Methods

### Method 1: User Proxy (Recommended for Browser Access)

**Pros:** Proper OpenSearch user authentication, works in any browser, no AWS Console needed
**Cons:** Requires running a local proxy

1. **Start the user proxy**:
   ```bash
   cd /Users/nate/dev/socal-dreamin-2025-aws
   ./scripts/start-user-proxy.sh
   ```

2. **Keep the proxy terminal open** (don't close it)

3. **Open browser** and go to: `http://localhost:8080/_dashboards/`

4. **You're authenticated!** The proxy handles OpenSearch user authentication automatically

### Method 2: AWS Console (Alternative)

**Pros:** Easiest, automatic authentication, no setup required
**Cons:** Requires AWS Console access

1. Open [AWS Console](https://console.aws.amazon.com/)
2. Search for "OpenSearch" in the services
3. Click on your domain: `sf-opensearch-lab-os`
4. Click the **"OpenSearch Dashboards URL"** button
5. You'll be redirected to Dashboards with full access

### Method 3: SSH Tunnel + Browser

**Pros:** Direct access, good for development
**Cons:** Requires SSH tunnel setup, browser authentication issues

1. **Start SSH tunnel** (run this in a separate terminal):
   ```bash
   cd /Users/nate/dev/socal-dreamin-2025-aws
   ssh -i aws/certs/aws-ec2 -L 9200:localhost:9200 ec2-user@$(cd aws/terraform && terraform output -raw ec2_public_ip)
   ```

2. **Keep the SSH tunnel terminal open** (don't close it)

3. **Open browser** and go to: `https://localhost:9200/_dashboards/`

4. **Handle security warning**: Click "Advanced" → "Proceed to localhost"

5. **Authentication issue**: You'll see "User: anonymous is not authorized" - this is expected because browsers can't authenticate with AWS IAM directly

### Method 4: CLI Access (For Testing)

**Pros:** Good for testing connectivity and API calls
**Cons:** Command-line only, not for Dashboards UI

1. **SSH into EC2**:
   ```bash
   ssh -i aws/certs/aws-ec2 ec2-user@$(cd aws/terraform && terraform output -raw ec2_public_ip)
   ```

2. **Test basic connectivity**:
   ```bash
   curl -X GET 'https://localhost:9200/'
   ```

3. **Test IAM authentication**:
   ```bash
   python3 /opt/salesforce-streamer/test-opensearch-iam.py
   ```

### Method 5: Programmatic Access

**Pros:** Full API access, good for automation
**Cons:** Requires Python/curl knowledge

Use the test script we created:
```bash
ssh -i aws/certs/aws-ec2 ec2-user@$(cd aws/terraform && terraform output -raw ec2_public_ip)
python3 /opt/salesforce-streamer/test-opensearch-iam.py
```

## 🔍 Troubleshooting

### "User: anonymous is not authorized"
- **Cause**: Browser can't authenticate with AWS IAM
- **Solution**: Use AWS Console method instead

### "Connection refused" on localhost:9200
- **Cause**: SSH tunnel not established
- **Solution**: Make sure SSH tunnel is running and EC2 is accessible

### "TargetNotConnected" SSM error
- **Cause**: EC2 instance not connected to SSM
- **Solution**: Check EC2 instance status and SSM agent

### OpenSearch domain not found
- **Cause**: Domain might be in different region
- **Solution**: Check AWS region in terraform configuration

## 📊 What You Can Do in Dashboards

Once you have access, you can:

1. **View Indexed Data**: Browse the `salesforce-login-events` index
2. **Create Visualizations**: Build charts and graphs from your data
3. **Set Up Dashboards**: Create custom dashboards for monitoring
4. **Search Data**: Use the Discover tab to search and filter events
5. **Manage Index Patterns**: Configure how data is displayed

## 🔐 Security Notes

- OpenSearch is configured with IAM authentication
- Only authorized AWS users/roles can access the domain
- The EC2 instance has the necessary permissions to write data
- SSH access is secured with key-based authentication

## 📝 Next Steps

1. **Access Dashboards** using Method 1 (AWS Console)
2. **Explore the data** in the Discover tab
3. **Create visualizations** for login patterns
4. **Set up monitoring** dashboards
5. **Configure alerts** for unusual activity

## 🆘 Getting Help

If you encounter issues:

1. Check EC2 instance status: `aws ec2 describe-instances`
2. Verify OpenSearch domain status in AWS Console
3. Check application logs: `ssh -i key.pem ec2-user@ip 'sudo journalctl -u salesforce-streamer -f'`
4. Test connectivity from EC2: `curl -X GET 'https://localhost:9200/'`

---

**Recommendation**: Start with Method 1 (User Proxy) for the easiest browser access with proper OpenSearch user authentication.



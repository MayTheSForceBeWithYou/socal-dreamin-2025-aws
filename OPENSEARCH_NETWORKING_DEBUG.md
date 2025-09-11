# OpenSearch Networking Debug & Fix Guide

This guide provides comprehensive tools and strategies for debugging and fixing OpenSearch "Pending VPC access" issues.

## 🔍 Quick Diagnosis

Start here to understand your current OpenSearch networking configuration:

```bash
# Diagnose current OpenSearch networking issues
python -m setup_tools diagnose-opensearch-networking

# Test connectivity from local environment
python -m setup_tools test-opensearch-connectivity

# Test connectivity from EC2 (if you have instances running)
python -m setup_tools test-opensearch-connectivity --from-ec2
```

## 🔧 Available Fix Strategies

### 1. Permissive VPC Mode (Recommended for Labs)
Opens up all necessary network access within VPC:

```bash
# Analyze and fix with maximum VPC permissions
python -m setup_tools fix-opensearch-networking --mode permissive

# Dry run to see what would be changed
python -m setup_tools fix-opensearch-networking --mode permissive --dry-run
```

### 2. Public Access Mode (Fallback Option)
Switches domain to public access if VPC issues persist:

```bash
# Switch to public access with IP restrictions
python -m setup_tools fix-opensearch-networking --mode public --ip-restrict "1.2.3.4,5.6.7.8"

# Public access without IP restrictions (less secure)
python -m setup_tools fix-opensearch-networking --mode public
```

### 3. Hybrid Mode
Applies VPC fixes first, provides guidance for adding public access:

```bash
python -m setup_tools fix-opensearch-networking --mode hybrid
```

## 🔒 Security Group Analysis

Analyze and create permissive security groups for different services:

```bash
# Analyze OpenSearch security groups
python -m setup_tools analyze-security-groups --service opensearch

# Create maximally permissive security group for OpenSearch
python -m setup_tools analyze-security-groups --service opensearch --create-permissive

# Analyze other services
python -m setup_tools analyze-security-groups --service ec2
python -m setup_tools analyze-security-groups --service bastion
```

## 🏗️ Terraform Infrastructure Fixes

The following Terraform changes have been applied to fix common networking issues:

### Fixed Issues:
1. **Added NAT Gateway and Routes**: Private subnets now have internet access via NAT Gateway
2. **Fixed Circular Security Group Reference**: Removed circular dependency in bastion security group
3. **Added Comprehensive OpenSearch Ports**: Including 5601 (Dashboard), 9200 (API), 80, 443
4. **Permissive Lab Rules**: Added wide-open VPC access for demo/lab environments

### Apply Terraform Changes:
```bash
cd aws/terraform
terraform plan
terraform apply
```

**⚠️ Important**: After applying Terraform changes, wait 15-30 minutes for AWS to process the domain updates.

## 🎯 Step-by-Step Troubleshooting

### Step 1: Run Diagnostics
```bash
python -m setup_tools diagnose-opensearch-networking
```

Look for these common issues:
- ❌ Subnet has no internet access (no IGW or NAT Gateway route)
- ❌ Security group missing HTTPS (443) access
- ❌ Security group missing OpenSearch API (9200) access

### Step 2: Apply Terraform Fixes
```bash
cd aws/terraform
terraform apply
```

### Step 3: Apply Permissive Fixes
```bash
python -m setup_tools fix-opensearch-networking --mode permissive
```

### Step 4: Test Connectivity
```bash
python -m setup_tools test-opensearch-connectivity
```

### Step 5: If Still Failing, Try Public Mode
```bash
python -m setup_tools fix-opensearch-networking --mode public --ip-restrict "YOUR_IP_ADDRESS"
```

## 📊 Understanding the Diagnostic Output

### Domain Status Indicators:
- ✅ **Active**: Domain is ready and accessible
- ⚠️ **Processing**: Domain is updating (wait 15-30 minutes)
- ❌ **Pending**: Domain configuration issues need attention

### Network Analysis:
- **VPC Configuration**: Shows which VPC, subnets, and security groups are used
- **Subnet Analysis**: Identifies if subnets are public/private and have internet access
- **Routing Analysis**: Shows if route tables have IGW or NAT Gateway routes
- **Security Group Analysis**: Lists all ingress/egress rules and identifies missing ports

### Connectivity Test Results:
- **DNS Resolution**: Can resolve OpenSearch endpoint hostname
- **Port Connectivity**: Can reach ports 443 and 9200
- **HTTPS Connectivity**: Can establish HTTPS connections
- **OpenSearch API**: Can access cluster health endpoint

## 🚨 Common Issues and Solutions

### Issue: "Pending VPC access" in Dashboard
**Root Cause**: OpenSearch Dashboard service cannot reach your VPC-based domain

**Solutions**:
1. **Private Subnets Missing NAT Gateway**: Apply Terraform fixes to add NAT Gateway
2. **Security Groups Too Restrictive**: Use `--mode permissive` to open up access
3. **Wrong Subnet Type**: Consider moving to public subnets for simpler access
4. **Network Routing Issues**: Check route table associations

### Issue: Connection Timeouts
**Root Cause**: Network path blocked or misconfigured

**Solutions**:
1. Check security group ingress rules for ports 80, 443, 9200, 5601
2. Verify subnets have internet routes (IGW for public, NAT for private)
3. Ensure no NACLs blocking traffic
4. Test from different source locations (EC2 vs local)

### Issue: Authentication Errors (401/403)
**Root Cause**: Domain access policy or authentication settings

**Solutions**:
1. This is actually **GOOD** - it means networking is working!
2. 401/403 errors indicate the service is reachable but requires authentication
3. Configure proper IAM roles and policies for access
4. For testing, use public mode with open access policies

## 🔧 Manual Verification Commands

If you want to manually verify the fixes:

```bash
# Check OpenSearch domain status
aws opensearch describe-domain --domain-name YOUR_DOMAIN_NAME

# Test DNS resolution
nslookup YOUR_OPENSEARCH_ENDPOINT

# Test port connectivity
nc -zv YOUR_OPENSEARCH_ENDPOINT 443
nc -zv YOUR_OPENSEARCH_ENDPOINT 9200

# Test HTTPS endpoint
curl -I https://YOUR_OPENSEARCH_ENDPOINT

# Test OpenSearch API
curl -X GET https://YOUR_OPENSEARCH_ENDPOINT/_cluster/health
```

## 📋 Troubleshooting Checklist

### Before Running Fixes:
- [ ] AWS credentials configured (`aws sts get-caller-identity`)
- [ ] In correct region
- [ ] Have necessary IAM permissions (EC2, OpenSearch, VPC)
- [ ] OpenSearch domain exists and is identifiable

### After Running Terraform Changes:
- [ ] `terraform apply` completed successfully
- [ ] No Terraform errors or circular dependencies
- [ ] NAT Gateway and Elastic IP created
- [ ] Route table associations updated

### After Running Permissive Fixes:
- [ ] Domain status shows "Processing" or "Active" (not "Failed")
- [ ] Security groups have required ingress rules
- [ ] Wait 15-30 minutes for AWS propagation

### Testing Phase:
- [ ] DNS resolution works
- [ ] Port connectivity succeeds for 443 and 9200
- [ ] HTTPS requests return responses (even 401/403 is OK)
- [ ] OpenSearch Dashboards accessible via browser

## 🎉 Success Criteria

You'll know the fix worked when:

1. **Domain Status**: Shows "Active" in AWS Console
2. **Dashboard Access**: OpenSearch Dashboards loads (even if requiring login)
3. **API Access**: Can reach `https://YOUR_ENDPOINT/_cluster/health`
4. **No "Pending VPC access"**: Message disappears from Dashboard UI

## 🆘 Emergency Fallback

If nothing else works, use this emergency public access configuration:

```bash
# Last resort: fully public access (INSECURE - LAB USE ONLY)
python -m setup_tools fix-opensearch-networking --mode public --force

# Then restrict by IP immediately
python -m setup_tools fix-opensearch-networking --mode public --ip-restrict "$(curl -s ifconfig.me)" --force
```

**⚠️ Security Warning**: Public mode makes your OpenSearch cluster accessible from the internet. Only use for labs/demos and always add IP restrictions!

---

## 📞 Support

If you continue having issues after following this guide:

1. Run the diagnostic tool and save the output
2. Check the AWS CloudTrail logs for API errors
3. Review the OpenSearch domain's processing status in AWS Console
4. Consider recreating the domain with a simpler configuration

The tools in this guide are designed to handle 90% of common OpenSearch networking issues. For complex enterprise configurations, additional manual troubleshooting may be required.
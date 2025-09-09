# OpenSearch IAM Authentication Guide

This guide helps you configure and troubleshoot OpenSearch IAM authentication for local access to the validation tools.

## Overview

The OpenSearch domain is configured to use IAM role-based authentication. By default, only the EC2 instance with the `sf-opensearch-lab-ec2-role` can access OpenSearch. To run validation tools from your local machine, you need to configure proper AWS authentication.

## Current Setup

**✅ Working on EC2**: The application runs successfully on the EC2 instance because it uses the proper IAM role.

**❌ Local Access**: Validation tools fail when run locally because your AWS user doesn't have OpenSearch permissions.

## Solution Options

### Option 1: Add OpenSearch Permissions to Your Admin User (Recommended)

This is the simplest approach if you're using the `admin` user as your AWS CLI default profile.

```bash
# Add OpenSearch full access to your admin user
aws iam attach-user-policy --user-name admin --policy-arn arn:aws:iam::aws:policy/AmazonOpenSearchServiceFullAccess

# Verify the policy was attached
aws iam list-attached-user-policies --user-name admin
```

**Test the fix:**
```bash
# Test the validation command (should now work)
python3 -m setup_tools opensearch validate-iam-auth

# Should show success instead of 403 errors
```

### Option 2: Update OpenSearch Access Policy via Terraform

Modify the Terraform configuration to include your admin user in the OpenSearch access policy.

**Edit `aws/terraform/modules/opensearch/main.tf`:**

Replace the access_policies block:
```hcl
# Access policy for IAM role-based authentication
access_policies = jsonencode({
  Version = "2012-10-17"
  Statement = [
    {
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ec2-role",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/admin"
        ]
      }
      Action = "es:*"
      Resource = "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-os/*"
    }
  ]
})
```

**Apply the changes:**
```bash
cd aws/terraform
terraform plan
terraform apply -auto-approve
```

### Option 3: Configure AWS Profile for Role Assumption (Lab-Ready)

This approach uses AWS profiles to assume the EC2 role, making it easy for lab attendees to configure.

#### Step 1: Add Assume Role Policy to Your User

First, add a policy that allows your user to assume the EC2 role:

```bash
# Get your AWS account ID and project name from Terraform outputs
ACCOUNT_ID=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d: -f5)
PROJECT_NAME=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d/ -f2 | sed 's/-ec2-role$//')
USER_NAME=$(aws sts get-caller-identity --query User.UserName --output text)

# Create the assume role policy
aws iam put-user-policy \
  --user-name $USER_NAME \
  --policy-name AllowAssumeOpenSearchRole \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": \"sts:AssumeRole\",
        \"Resource\": \"arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role\"
      }
    ]
  }"
```

#### Step 2: Configure AWS Profile

Add this configuration to your `~/.aws/config` file:

```bash
# Get configuration values from Terraform
ACCOUNT_ID=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d: -f5)
PROJECT_NAME=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d/ -f2 | sed 's/-ec2-role$//')
REGION=$(cd aws/terraform && terraform output -raw opensearch_endpoint | cut -d. -f2)

# Add profile to ~/.aws/config
cat >> ~/.aws/config << EOF

[profile sf-opensearch-role]
role_arn = arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role
source_profile = default
region = ${REGION}
EOF
```

#### Step 3: Test the Configuration

```bash
# Test the profile configuration
AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity

# Run validation with the profile
AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth
```

### Option 4: Use AssumeRole for Temporary Testing

You can temporarily assume the EC2 role for testing:

```bash
# Assume the EC2 role
aws sts assume-role --role-arn arn:aws:iam::881811711506:role/sf-opensearch-lab-ec2-role --role-session-name test-opensearch

# Use the returned credentials to test
export AWS_ACCESS_KEY_ID=<returned-access-key>
export AWS_SECRET_ACCESS_KEY=<returned-secret-key>
export AWS_SESSION_TOKEN=<returned-session-token>

# Then run the validation
python3 -m setup_tools opensearch validate-iam-auth

# Clean up when done
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

## Helper Scripts for Lab Attendees

### Automated Configuration Script

Create a script that automatically configures everything for lab attendees:

```bash
#!/bin/bash
# configure-opensearch-access.sh

set -e

echo "🔧 Configuring OpenSearch IAM Authentication..."

# Get configuration values from Terraform
if [ ! -d "aws/terraform" ]; then
    echo "❌ Error: aws/terraform directory not found. Run this from the project root."
    exit 1
fi

cd aws/terraform

# Get values from Terraform outputs
ACCOUNT_ID=$(terraform output -raw opensearch_master_user_arn | cut -d: -f5)
PROJECT_NAME=$(terraform output -raw opensearch_master_user_arn | cut -d/ -f2 | sed 's/-ec2-role$//')
REGION=$(terraform output -raw opensearch_endpoint | cut -d. -f2)
USER_NAME=$(aws sts get-caller-identity --query User.UserName --output text)

echo "📋 Configuration:"
echo "  Account ID: $ACCOUNT_ID"
echo "  Project Name: $PROJECT_NAME"
echo "  Region: $REGION"
echo "  User Name: $USER_NAME"

# Step 1: Add assume role policy
echo "🔐 Adding assume role policy to user $USER_NAME..."
aws iam put-user-policy \
  --user-name "$USER_NAME" \
  --policy-name AllowAssumeOpenSearchRole \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": \"sts:AssumeRole\",
        \"Resource\": \"arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role\"
      }
    ]
  }"

# Step 2: Configure AWS profile
echo "⚙️  Configuring AWS profile..."
PROFILE_CONFIG="
[profile sf-opensearch-role]
role_arn = arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role
source_profile = default
region = ${REGION}"

# Check if profile already exists
if grep -q "\[profile sf-opensearch-role\]" ~/.aws/config; then
    echo "⚠️  Profile sf-opensearch-role already exists in ~/.aws/config"
else
    echo "$PROFILE_CONFIG" >> ~/.aws/config
    echo "✅ Added sf-opensearch-role profile to ~/.aws/config"
fi

# Step 3: Test configuration
echo "🧪 Testing configuration..."
if AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS profile configuration successful!"
    
    # Test OpenSearch validation
    cd ../..
    if AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth; then
        echo "🎉 OpenSearch IAM authentication configured successfully!"
        echo ""
        echo "📝 Usage:"
        echo "  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth"
        echo "  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools validation validate-lab --comprehensive"
    else
        echo "❌ OpenSearch validation failed. Check the error messages above."
    fi
else
    echo "❌ AWS profile configuration failed. Check your AWS credentials."
fi
```

### Manual Configuration Commands

If you prefer to run the commands manually:

```bash
# 1. Get configuration values
ACCOUNT_ID=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d: -f5)
PROJECT_NAME=$(cd aws/terraform && terraform output -raw opensearch_master_user_arn | cut -d/ -f2 | sed 's/-ec2-role$//')
REGION=$(cd aws/terraform && terraform output -raw opensearch_endpoint | cut -d. -f2)
USER_NAME=$(aws sts get-caller-identity --query User.UserName --output text)

# 2. Add assume role policy
aws iam put-user-policy \
  --user-name $USER_NAME \
  --policy-name AllowAssumeOpenSearchRole \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": \"sts:AssumeRole\",
        \"Resource\": \"arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role\"
      }
    ]
  }"

# 3. Add AWS profile to ~/.aws/config
cat >> ~/.aws/config << EOF

[profile sf-opensearch-role]
role_arn = arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role
source_profile = default
region = ${REGION}
EOF

# 4. Test the configuration
AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity
AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth
```

## Troubleshooting

### Error: "no permissions for [cluster:monitor/health]"

**Cause**: Your AWS user doesn't have OpenSearch permissions.

**Solution**: Use Option 1, 2, or 3 above.

### Error: "Access Denied" when attaching policy

**Cause**: Your AWS user doesn't have IAM permissions.

**Solution**: 
```bash
# Check your current user
aws sts get-caller-identity

# If you're not using an admin user, ask someone with admin access to attach the policy
```

### Error: "User does not exist"

**Cause**: The username doesn't match your actual IAM user.

**Solution**:
```bash
# List all IAM users to find the correct name
aws iam list-users

# Use the correct username in the commands above
```

### Error: "The role cannot be assumed"

**Cause**: The assume role policy wasn't created correctly or the role ARN is wrong.

**Solution**:
```bash
# Verify the role exists
aws iam get-role --role-name sf-opensearch-lab-ec2-role

# Check your user's policies
aws iam list-user-policies --user-name $(aws sts get-caller-identity --query User.UserName --output text)
```

## Validation Commands

After configuring access, test with these commands:

```bash
# Test OpenSearch IAM authentication
python3 -m setup_tools opensearch validate-iam-auth

# Run comprehensive lab validation
python3 -m setup_tools validation validate-lab --comprehensive

# Test direct OpenSearch connection
aws es describe-elasticsearch-domain --domain-name sf-opensearch-lab-os
```

## Security Best Practices

1. **Principle of Least Privilege**: Only grant the minimum required permissions
2. **Use IAM Roles**: Prefer roles over user credentials when possible
3. **Regular Review**: Periodically review and remove unused permissions
4. **Audit Access**: Monitor OpenSearch access logs for unusual activity

## FAQ

**Q: Why doesn't the validation work from my local machine?**
A: The OpenSearch domain is configured to only allow the EC2 IAM role. This is correct security behavior.

**Q: Is it safe to add my user to the OpenSearch policy?**
A: Yes, if you're using this for development/learning. For production, use more restrictive policies.

**Q: Can I use a different AWS profile?**
A: Yes, configure the profile with OpenSearch permissions and use `aws configure set profile <profile-name>`.

**Q: How do I know which user my AWS CLI is using?**
A: Run `aws sts get-caller-identity` to see your current identity.

**Q: What's the difference between the options?**
A: 
- Option 1: Direct permissions (simplest)
- Option 2: Terraform-based (infrastructure as code)
- Option 3: Role assumption (most secure, lab-ready)
- Option 4: Temporary testing only

---

*This guide was created as part of the OpenSearch IAM authentication troubleshooting process.*
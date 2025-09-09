#!/bin/bash
# configure-opensearch-access.sh
# 
# This script automatically configures OpenSearch IAM authentication for lab attendees.
# It creates the necessary IAM policies and AWS profile configuration.

set -e

echo "🔧 Configuring OpenSearch IAM Authentication..."

# Check if we're in the right directory
if [ ! -d "aws/terraform" ]; then
    echo "❌ Error: aws/terraform directory not found. Run this from the project root."
    exit 1
fi

# Check if Terraform has been applied
if [ ! -f "aws/terraform/terraform.tfstate" ]; then
    echo "❌ Error: Terraform state not found. Please run 'terraform apply' first."
    exit 1
fi

cd aws/terraform

# Get values from Terraform outputs
echo "📋 Getting configuration from Terraform outputs..."
ACCOUNT_ID=$(terraform output -raw opensearch_master_user_arn | cut -d: -f5)
PROJECT_NAME=$(terraform output -raw opensearch_master_user_arn | cut -d/ -f2 | sed 's/-ec2-role$//')
REGION=$(terraform output -raw opensearch_endpoint | cut -d. -f2)
USER_NAME=$(aws sts get-caller-identity --query User.UserName --output text)

echo "📋 Configuration:"
echo "  Account ID: $ACCOUNT_ID"
echo "  Project Name: $PROJECT_NAME"
echo "  Region: $REGION"
echo "  User Name: $USER_NAME"
echo ""

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

echo "✅ Assume role policy added successfully!"
echo ""

# Step 2: Configure AWS profile
echo "⚙️  Configuring AWS profile..."

# Create ~/.aws directory if it doesn't exist
mkdir -p ~/.aws

# Create config file if it doesn't exist
if [ ! -f ~/.aws/config ]; then
    touch ~/.aws/config
fi

PROFILE_CONFIG="
[profile sf-opensearch-role]
role_arn = arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-ec2-role
source_profile = default
region = ${REGION}"

# Check if profile already exists
if grep -q "\[profile sf-opensearch-role\]" ~/.aws/config; then
    echo "⚠️  Profile sf-opensearch-role already exists in ~/.aws/config"
    echo "   Skipping profile configuration..."
else
    echo "$PROFILE_CONFIG" >> ~/.aws/config
    echo "✅ Added sf-opensearch-role profile to ~/.aws/config"
fi

echo ""

# Step 3: Test configuration
echo "🧪 Testing configuration..."

# Test AWS profile
if AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS profile configuration successful!"
    
    # Get the assumed role identity
    ASSUMED_ROLE=$(AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity --query Arn --output text)
    echo "   Assumed role: $ASSUMED_ROLE"
    echo ""
    
    # Test OpenSearch validation
    echo "🔍 Testing OpenSearch validation..."
    cd ../..
    
    if AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth; then
        echo ""
        echo "🎉 OpenSearch IAM authentication configured successfully!"
        echo ""
        echo "📝 Usage Examples:"
        echo "  # Test OpenSearch validation"
        echo "  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools opensearch validate-iam-auth"
        echo ""
        echo "  # Run comprehensive lab validation"
        echo "  AWS_PROFILE=sf-opensearch-role python3 -m setup_tools validation validate-lab --comprehensive"
        echo ""
        echo "  # Test AWS CLI with the profile"
        echo "  AWS_PROFILE=sf-opensearch-role aws sts get-caller-identity"
        echo ""
        echo "  # Check OpenSearch domain status"
        echo "  AWS_PROFILE=sf-opensearch-role aws es describe-elasticsearch-domain --domain-name ${PROJECT_NAME}-os"
    else
        echo "❌ OpenSearch validation failed. Check the error messages above."
        echo ""
        echo "🔧 Troubleshooting:"
        echo "  1. Verify the EC2 role exists: aws iam get-role --role-name ${PROJECT_NAME}-ec2-role"
        echo "  2. Check your user policies: aws iam list-user-policies --user-name $USER_NAME"
        echo "  3. Verify the OpenSearch domain: aws es describe-elasticsearch-domain --domain-name ${PROJECT_NAME}-os"
    fi
else
    echo "❌ AWS profile configuration failed."
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  1. Check your AWS credentials: aws sts get-caller-identity"
    echo "  2. Verify the assume role policy was created: aws iam list-user-policies --user-name $USER_NAME"
    echo "  3. Check the role exists: aws iam get-role --role-name ${PROJECT_NAME}-ec2-role"
fi

echo ""
echo "📚 For more information, see OPENSEARCH_IAM_AUTHENTICATION.md"

#!/bin/bash

# OpenSearch SSH Tunnel Test Script
# This script sets up the tunnel, tests connectivity, and provides troubleshooting

set -e

# Use the same configuration from opensearch-tunnel.sh
EC2_USER="ec2-user"
EC2_HOST="54.219.71.255"
KEY_PATH="aws/certs/aws-ec2"
OPENSEARCH_ENDPOINT="vpc-sf-opensearch-lab-os-4lubcnrajwordhojyr2uhhorwi.us-west-1.es.amazonaws.com"
LOCAL_PORT="9200"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== OpenSearch SSH Tunnel Connection Test ===${NC}"
echo ""

# Step 1: Validate prerequisites
echo -e "${YELLOW}Step 1: Validating prerequisites...${NC}"

if [[ ! -f "$KEY_PATH" ]]; then
    echo -e "${RED}ERROR: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Check if port is available
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Port $LOCAL_PORT is in use. Attempting to kill existing process...${NC}"
    lsof -ti:$LOCAL_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# Step 2: Test basic SSH connectivity
echo -e "${YELLOW}Step 2: Testing SSH connectivity to EC2...${NC}"

if ! ssh -i "$KEY_PATH" -o ConnectTimeout=10 -o BatchMode=yes "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${RED}ERROR: Cannot SSH to EC2 instance${NC}"
    echo "Please check:"
    echo "- EC2 instance is running"
    echo "- Security group allows SSH (port 22)"
    echo "- Key file permissions (should be 600)"
    echo "- Correct hostname/IP: $EC2_HOST"
    exit 1
fi

echo -e "${GREEN}SSH connectivity OK${NC}"
echo ""

# Step 3: Start SSH tunnel in background
echo -e "${YELLOW}Step 3: Starting SSH tunnel...${NC}"

# Start tunnel in background and capture PID
ssh -f -N \
    -L $LOCAL_PORT:$OPENSEARCH_ENDPOINT:443 \
    -i "$KEY_PATH" \
    "$EC2_USER@$EC2_HOST"

TUNNEL_PID=$!
echo "Tunnel started with PID: $TUNNEL_PID"

# Wait a moment for tunnel to establish
sleep 3

# Function to cleanup tunnel
cleanup() {
    echo -e "\n${YELLOW}Cleaning up SSH tunnel...${NC}"
    pkill -f "ssh.*$LOCAL_PORT:$OPENSEARCH_ENDPOINT" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}SSH tunnel established${NC}"
echo ""

# Step 4: Test OpenSearch connectivity
echo -e "${YELLOW}Step 4: Testing OpenSearch connectivity...${NC}"

# Test basic connectivity
echo "Testing connection to https://localhost:$LOCAL_PORT..."

# First test - basic connectivity
CURL_OUTPUT=$(curl -s -k -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}\n" \
    https://localhost:$LOCAL_PORT 2>&1 || echo "CURL_FAILED")

HTTP_CODE=$(echo "$CURL_OUTPUT" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$CURL_OUTPUT" | sed '/HTTP_CODE:/,$d')

echo ""
echo -e "${BLUE}=== Connection Test Results ===${NC}"
echo "HTTP Status Code: $HTTP_CODE"
echo ""
echo "Response Body:"
echo "$RESPONSE_BODY"
echo ""

# Step 5: Analyze results and provide troubleshooting
echo -e "${YELLOW}Step 5: Analysis and Troubleshooting...${NC}"

case "$HTTP_CODE" in
    "200")
        echo -e "${GREEN}✅ SUCCESS: OpenSearch is accessible!${NC}"
        echo "You can now access the dashboard at: https://localhost:$LOCAL_PORT/_dashboards"
        ;;
    "401"|"403")
        echo -e "${RED}❌ AUTHENTICATION/AUTHORIZATION ERROR${NC}"
        echo ""
        echo "The tunnel is working, but there's an authentication issue."
        echo ""
        echo -e "${YELLOW}Troubleshooting steps:${NC}"
        echo "1. Check if the EC2 instance has the correct IAM role attached"
        echo "2. Verify the IAM role has the required OpenSearch permissions"
        echo "3. Check the OpenSearch domain access policy"
        echo ""
        
        # Test what the EC2 instance can see
        echo "Testing from EC2 instance directly..."
        EC2_TEST=$(ssh -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" \
            "curl -s -k https://$OPENSEARCH_ENDPOINT 2>&1 | head -20" || echo "EC2_TEST_FAILED")
        
        echo "EC2 direct test result:"
        echo "$EC2_TEST"
        
        if [[ "$EC2_TEST" == *"User: anonymous"* ]]; then
            echo ""
            echo -e "${RED}ISSUE: EC2 instance is not using IAM role authentication${NC}"
            echo ""
            echo "Required fixes:"
            echo "1. Attach an IAM role to your EC2 instance with OpenSearch permissions"
            echo "2. Or configure AWS credentials on the EC2 instance"
            echo "3. Ensure the OpenSearch domain access policy allows the IAM role"
        fi
        ;;
    "404")
        echo -e "${RED}❌ NOT FOUND ERROR${NC}"
        echo "The OpenSearch endpoint might be incorrect or the domain doesn't exist"
        echo "Current endpoint: $OPENSEARCH_ENDPOINT"
        ;;
    "000"|"CURL_FAILED")
        echo -e "${RED}❌ CONNECTION FAILED${NC}"
        echo "Cannot connect through the tunnel. Possible issues:"
        echo "1. OpenSearch domain is in a different VPC than the EC2 instance"
        echo "2. Security group doesn't allow EC2 to reach OpenSearch (port 443)"
        echo "3. Network ACLs blocking traffic"
        echo "4. OpenSearch domain is not accessible from the subnet"
        ;;
    *)
        echo -e "${YELLOW}⚠️  UNEXPECTED RESPONSE${NC}"
        echo "HTTP Code: $HTTP_CODE"
        echo "This might indicate a configuration issue or service problem"
        ;;
esac

echo ""
echo -e "${BLUE}=== Dashboard Access URLs ===${NC}"
echo "OpenSearch Dashboards: https://localhost:$LOCAL_PORT/_dashboards"
echo "OpenSearch API: https://localhost:$LOCAL_PORT"
echo ""
echo "Press Ctrl+C to stop the tunnel and exit"

# Keep tunnel running
while true; do
    sleep 10
    # Check if tunnel is still alive
    if ! pgrep -f "ssh.*$LOCAL_PORT:$OPENSEARCH_ENDPOINT" > /dev/null; then
        echo -e "${RED}SSH tunnel died unexpectedly${NC}"
        exit 1
    fi
done
#!/bin/bash

# OpenSearch SSH Tunnel Setup Script
# This script creates an SSH tunnel through an EC2 instance to access OpenSearch dashboard

set -e

# Configuration - Update these values for your setup
EC2_USER="ec2-user"          # or "ubuntu" depending on your AMI
EC2_HOST="54.219.71.255"     # Your EC2 instance public IP or hostname
KEY_PATH="aws/certs/aws-ec2" # Path to your EC2 key pair file
# Your OpenSearch domain endpoint (without https://)
OPENSEARCH_ENDPOINT="vpc-sf-opensearch-lab-os-4lubcnrajwordhojyr2uhhorwi.us-west-1.es.amazonaws.com"
LOCAL_PORT="9200"            # Local port to forward to

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -h, --host EC2_HOST        EC2 instance hostname or IP"
    echo "  -k, --key KEY_PATH         Path to EC2 key pair file"
    echo "  -e, --endpoint ENDPOINT    OpenSearch domain endpoint"
    echo "  -u, --user EC2_USER        EC2 username (default: ec2-user)"
    echo "  -p, --port LOCAL_PORT      Local port to forward (default: 9200)"
    echo "  --help                     Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -h ec2-12-34-56-78.compute-1.amazonaws.com -k ~/.ssh/my-key.pem -e search-mydomain-abc123.us-east-1.es.amazonaws.com"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            EC2_HOST="$2"
            shift 2
            ;;
        -k|--key)
            KEY_PATH="$2"
            shift 2
            ;;
        -e|--endpoint)
            OPENSEARCH_ENDPOINT="$2"
            shift 2
            ;;
        -u|--user)
            EC2_USER="$2"
            shift 2
            ;;
        -p|--port)
            LOCAL_PORT="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$EC2_HOST" ]]; then
    echo -e "${RED}Error: EC2 host is required${NC}"
    print_usage
    exit 1
fi

if [[ -z "$KEY_PATH" ]]; then
    echo -e "${RED}Error: Key path is required${NC}"
    print_usage
    exit 1
fi

if [[ -z "$OPENSEARCH_ENDPOINT" ]]; then
    echo -e "${RED}Error: OpenSearch endpoint is required${NC}"
    print_usage
    exit 1
fi

# Validate key file exists
if [[ ! -f "$KEY_PATH" ]]; then
    echo -e "${RED}Error: Key file not found at $KEY_PATH${NC}"
    exit 1
fi

# Check if local port is already in use
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port $LOCAL_PORT is already in use${NC}"
    echo "You may need to stop the existing process or choose a different port"
    exit 1
fi

echo -e "${GREEN}Setting up SSH tunnel to OpenSearch...${NC}"
echo "EC2 Instance: $EC2_USER@$EC2_HOST"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "Local Port: $LOCAL_PORT"
echo ""

# Clean up function
cleanup() {
    echo -e "\n${YELLOW}Shutting down SSH tunnel...${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting SSH tunnel...${NC}"
echo "Press Ctrl+C to stop the tunnel"
echo ""
echo -e "${GREEN}Once connected, access OpenSearch at: http://localhost:$LOCAL_PORT/_dashboards${NC}"
echo ""

# Start SSH tunnel
# -N: Don't execute remote commands
# -L: Local port forwarding
# -i: Identity file (key)
ssh -N \
    -L $LOCAL_PORT:$OPENSEARCH_ENDPOINT:443 \
    -i "$KEY_PATH" \
    "$EC2_USER@$EC2_HOST"
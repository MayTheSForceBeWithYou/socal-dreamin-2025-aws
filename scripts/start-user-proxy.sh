#!/bin/bash
# Start OpenSearch User Proxy

set -e

PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
PORT=${1:-8080}

echo "🚀 Starting OpenSearch User Proxy..."
echo "===================================="
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Port: $PORT"
echo ""

# Check if Terraform has been applied
if [ ! -d "$PROJECT_ROOT/aws/terraform" ]; then
    echo "❌ Terraform directory not found"
    echo "Please run the infrastructure setup first"
    exit 1
fi

# Check if Terraform outputs exist
cd "$PROJECT_ROOT/aws/terraform"
if ! terraform output opensearch_endpoint >/dev/null 2>&1; then
    echo "❌ Terraform outputs not found"
    echo "Please run 'terraform apply' first"
    exit 1
fi

echo "✅ Terraform outputs found"
echo ""

# Start the proxy
echo "Starting proxy on port $PORT..."
echo "Browser URL: http://localhost:$PORT/_dashboards/"
echo ""
echo "Press Ctrl+C to stop the proxy"
echo ""

python3 "$PROJECT_ROOT/scripts/opensearch-user-proxy.py" "$PORT"

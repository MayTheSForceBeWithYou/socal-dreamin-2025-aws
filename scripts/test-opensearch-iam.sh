#!/bin/bash
# Test OpenSearch IAM Authentication Script

echo "Testing OpenSearch IAM Authentication..."

# Get OpenSearch endpoint
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"

# Test basic connectivity with IAM authentication
echo ""
echo "Testing basic connectivity with IAM authentication..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  "https://$OPENSEARCH_ENDPOINT/"

echo ""
echo "Testing cluster health with IAM authentication..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  "https://$OPENSEARCH_ENDPOINT/_cluster/health"

echo ""
echo "Testing indices listing with IAM authentication..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  "https://$OPENSEARCH_ENDPOINT/_cat/indices?v"

echo ""
echo "Testing Dashboards access with IAM authentication..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  "https://$OPENSEARCH_ENDPOINT/_dashboards/"


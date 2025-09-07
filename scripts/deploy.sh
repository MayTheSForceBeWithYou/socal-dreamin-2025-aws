#!/bin/bash
set -e

# Set project root
PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "PROJECT_ROOT: $PROJECT_ROOT"

echo "Deploying Salesforce to OpenSearch Lab Environment..."
echo "This script will deploy both infrastructure and application."
echo ""

# Check if user wants to deploy infrastructure or just application
if [ "$1" = "--app-only" ]; then
    echo "Deploying application only..."
    bash $PROJECT_ROOT/scripts/deploy-application.sh
else
    echo "Deploying infrastructure and application..."
    bash $PROJECT_ROOT/scripts/deploy-infrastructure.sh
    echo ""
    echo "Waiting 30 seconds before deploying application..."
    sleep 30
    bash $PROJECT_ROOT/scripts/deploy-application.sh
fi

echo ""
echo "Full deployment completed!"
echo ""
echo "Usage:"
echo "  bash scripts/deploy.sh              # Deploy infrastructure + application"
echo "  bash scripts/deploy.sh --app-only   # Deploy application only"
echo "  bash scripts/deploy-infrastructure.sh  # Deploy infrastructure only"
echo "  bash scripts/deploy-application.sh     # Deploy application only"

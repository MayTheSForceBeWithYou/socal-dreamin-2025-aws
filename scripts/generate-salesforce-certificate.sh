#!/bin/bash

# Ensure script exits on error
set -e

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "ROOT_DIR: $ROOT_DIR"

# Generate the digital certificate
echo "🔧 Generating digital certificate..."
openssl genrsa -out $ROOT_DIR/salesforce/certs/aws-to-sf-cert.key 2048
openssl req -new -x509 -key $ROOT_DIR/salesforce/certs/aws-to-sf-cert.key -out $ROOT_DIR/salesforce/certs/aws-to-sf-cert.crt -days 365
echo "✅ Digital certificate generated successfully"
echo "📄 Certificate saved in $ROOT_DIR/salesforce/certs directory"
echo "🔑 Key saved in $ROOT_DIR/salesforce/certs directory"
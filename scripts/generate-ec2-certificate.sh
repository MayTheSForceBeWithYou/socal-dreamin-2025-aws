#!/bin/bash

# Exit on error
set -e

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT_DIR/aws/certs"

mkdir -p "$CERT_DIR"

# Filenames
KEY_NAME="aws-ec2"
PRIVATE_KEY_FILE="$CERT_DIR/$KEY_NAME"
PUBLIC_KEY_FILE="$CERT_DIR/$KEY_NAME.pub"

echo "🔧 Generating EC2 SSH keypair..."
ssh-keygen -t rsa -b 4096 -f "$PRIVATE_KEY_FILE" -N ""

echo "✅ SSH keypair generated"
echo "🔑 Private key: $PRIVATE_KEY_FILE"
echo "📄 Public key:  $PUBLIC_KEY_FILE"

# Optional: Show fingerprint
echo "🔍 Fingerprint:"
ssh-keygen -lf "$PUBLIC_KEY_FILE"

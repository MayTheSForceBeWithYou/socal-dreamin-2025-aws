#!/bin/bash
# SSM Session Manager Plugin Installation Script
# This script installs the AWS Session Manager plugin for macOS

echo "Installing AWS Session Manager Plugin..."

# Download the plugin
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"

# Extract the plugin
unzip sessionmanager-bundle.zip

# Install the plugin
sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin

# Clean up
rm -rf sessionmanager-bundle.zip sessionmanager-bundle

echo "Session Manager Plugin installed successfully!"
echo ""
echo "You can now use: aws ssm start-session --target i-0c2603edb17f98d1d"


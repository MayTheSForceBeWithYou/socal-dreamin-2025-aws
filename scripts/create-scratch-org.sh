#!/bin/bash

# Ensure script exits on error
set -e

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "ROOT_DIR: $ROOT_DIR"

# Change to the Salesforce directory
cd $ROOT_DIR/salesforce
# Create the scratch org
sf org create scratch --definition-file config/project-scratch-def.json --alias socal-dreamin-2025-aws --set-default
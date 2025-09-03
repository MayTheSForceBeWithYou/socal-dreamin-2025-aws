#!/bin/bash

# Ensure script exits on error
set -e

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
echo "ROOT_DIR: $ROOT_DIR"
sf data query --file $ROOT_DIR/salesforce/scripts/soql/LoginHistory.soql --result-format csv > $ROOT_DIR/salesforce/data/LoginHistory.csv
sf data query --file $ROOT_DIR/salesforce/scripts/soql/LoginIp.soql --result-format csv > $ROOT_DIR/salesforce/data/LoginIp.csv
sf data query --file $ROOT_DIR/salesforce/scripts/soql/LoginGeo.soql --result-format csv > $ROOT_DIR/salesforce/data/LoginGeo.csv
sf data query --file $ROOT_DIR/salesforce/scripts/soql/User.soql --result-format csv > $ROOT_DIR/salesforce/data/User.csv
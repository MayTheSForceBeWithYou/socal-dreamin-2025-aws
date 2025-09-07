#!/bin/bash

# Ensure script exits on error
set -e

# Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
echo "ROOT_DIR: $ROOT_DIR"
CONNECTED_APP_XML_FILE="$ROOT_DIR/salesforce/force-app/main/default/connectedApps/AWS_Lambda_PubSub_App.connectedApp-meta.xml"

# Check if the XML file exists
if [[ ! -f "$CONNECTED_APP_XML_FILE" ]]; then
  echo "❌ XML file not found at: $CONNECTED_APP_XML_FILE"
  exit 1
fi

# Prompt for email
read -rp "Enter your contact email for the Connected App: " CONTACT_EMAIL

# Validate email format (basic regex)
if [[ ! "$CONTACT_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
  echo "❌ Invalid email format. Exiting."
  exit 1
fi

# Backup the XML file
cp $CONNECTED_APP_XML_FILE ${CONNECTED_APP_XML_FILE}.bak

# Update the <contactEmail> value
echo "🔧 Updating <contactEmail> in XML..."
echo "CONTACT_EMAIL: $CONTACT_EMAIL"

# Use sed to replace the line in the original XML file
if [[ "$OSTYPE" == "darwin"* ]]; then
  SED_INPLACE="sed -i ''"
else
  SED_INPLACE="sed -i"
fi
$SED_INPLACE "s|<contactEmail>.*</contactEmail>|<contactEmail>${CONTACT_EMAIL}</contactEmail>|" "$CONNECTED_APP_XML_FILE"

echo "✅ Updated <contactEmail> to: $CONTACT_EMAIL"

# Use sed to replace the email in the config/integration-user-def.json file
$SED_INPLACE "s|replace@with.your.email|${CONTACT_EMAIL}|" $ROOT_DIR/salesforce/config/integration-user-def.json

echo "✅ Updated email in config/integration-user-def.json to: $CONTACT_EMAIL"

# Run the generate-salesforce-certificate.sh script
source "$ROOT_DIR/salesforce/scripts/shell/generate-salesforce-certificate.sh"

CERT_FILE="$ROOT_DIR/salesforce/certs/aws-to-sf-cert.crt"
# Strip header/footer and line breaks from certificate body
CERT_BODY=$(awk 'BEGIN { ORS="" } /-----BEGIN CERTIFICATE-----/ { next } /-----END CERTIFICATE-----/ { next } { print }' "$CERT_FILE")

# Use sed to replace the commented-out <certificate> tag with the actual certificate contents
$SED_INPLACE "s|<!--certificate>.*</certificate-->|<certificate>${CERT_BODY}</certificate>|" "$CONNECTED_APP_XML_FILE"

echo "✅ Embedded certificate into Connected App XML"

echo "📄 Backup saved as: ${CONNECTED_APP_XML_FILE}.bak"

# Navigate to the Salesforce directory
cd $ROOT_DIR/salesforce

# Run the create-scratch-org.sh script
source "$ROOT_DIR/salesforce/scripts/shell/create-scratch-org.sh"

# Retrieve the org instanceUrl and update the config/integration-user-def.json file's username domain with the instanceUrl
INSTANCE_URL=$(sf org display --json | jq -r '.result.instanceUrl')
echo "INSTANCE_URL: $INSTANCE_URL"
# Strip the https:// from the instanceUrl
INSTANCE_DOMAIN=$(echo $INSTANCE_URL | sed 's|^https://||')
echo "INSTANCE_DOMAIN: $INSTANCE_DOMAIN"

# Update the config/integration-user-def.json file with the instanceUrl
$SED_INPLACE "s|@replace.with.instance.domain|@$INSTANCE_DOMAIN|" $ROOT_DIR/salesforce/config/integration-user-def.json

# Deploy the Salesforce project
sf project deploy start --source-dir force-app

# Create the integration user
sf org create user --definition-file $ROOT_DIR/salesforce/config/integration-user-def.json --set-alias socal-dreamin-2025-aws-integration-user

# Retrieve the connected app with the Client Key
sf project retrieve start --metadata ConnectedApp:AWS_Lambda_PubSub_App

# Read the connected app's consumerKey from the xml file and store in a variable
CLIENT_KEY=$(awk '/<consumerKey>.*<\/consumerKey>/ {print $1}' "$CONNECTED_APP_XML_FILE" | sed -e 's/<consumerKey>//' -e 's/<\/consumerKey>//')
echo "CLIENT_KEY: $CLIENT_KEY"

# Retrieve the integration user's username
INTEGRATION_USER_USERNAME=$(jq -r '.Username' $ROOT_DIR/salesforce/config/integration-user-def.json)
echo "INTEGRATION_USER_USERNAME: $INTEGRATION_USER_USERNAME"

PRIVATE_KEY_FILE="salesforce/certs/aws-to-sf-cert.key"

# Write Salesforce Auth Secrets to aws/terraform/terraform.tfvars file
echo "🔧 Creating sfdc-auth-secrets.json file..."
# Use EOF to write the file
cat << EOF > $ROOT_DIR/aws/terraform/terraform.tfvars
{
  "clientId": "$CLIENT_KEY",
  "username": "$INTEGRATION_USER_USERNAME",
  "loginUrl": "$INSTANCE_URL",
  "privateKey": "$(awk '{printf "%s\\n", $0}' "$PRIVATE_KEY_FILE")"
}
EOF
echo "✅ terraform.tfvars file updated"

# Read the salesforce/certs/aws-to-sf-cert.key file and use heredoc to write the private key to the aws/terraform/terraform.tfvars file
# Example:
# Replace this
# salesforce_private_key = REPLACE_WITH_YOUR_PRIVATE_KEY
# With this:
# salesforce_private_key = <<-EOT
# -----BEGIN PRIVATE KEY-----
# M3MASDHKLJALSHDLKASDHLAKSHDL
# KASHDKLASHDKLASHDKLASHDKLASH
# -----END PRIVATE KEY-----
# EOT
# Using sed to replace the line in the aws/terraform/terraform.tfvars file
$SED_INPLACE "s|REPLACE_WITH_YOUR_PRIVATE_KEY|$(awk '{printf "%s\\n", $0}' "$PRIVATE_KEY_FILE")|" $ROOT_DIR/aws/terraform/terraform.tfvars
echo "✅ Private key added to aws/terraform/terraform.tfvars file"
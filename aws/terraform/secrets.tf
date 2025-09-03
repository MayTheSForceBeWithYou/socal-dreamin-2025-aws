resource "aws_secretsmanager_secret" "sfdc_auth" {
  name        = "sfdc/auth-${random_id.bucket.hex}"
  description = "Salesforce JWT auth credentials for AWS Lambda"
}

resource "aws_secretsmanager_secret_version" "sfdc_auth_value" {
  secret_id     = aws_secretsmanager_secret.sfdc_auth.id
  secret_string = file("${path.module}/../sfdc-auth-secrets.json")
}

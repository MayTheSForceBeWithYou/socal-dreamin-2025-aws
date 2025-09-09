output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "EC2 public IP"
  value       = module.ec2.public_ip
}

output "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  value       = module.opensearch.endpoint
}

output "opensearch_kibana_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = module.opensearch.kibana_endpoint
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i aws/certs/aws-ec2 ec2-user@${module.ec2.public_ip}"
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Salesforce credentials"
  value       = aws_secretsmanager_secret.salesforce_creds.arn
}

output "salesforce_instance_url" {
  description = "Salesforce instance URL"
  value       = var.salesforce_instance_url
}

output "opensearch_master_user_arn" {
  description = "OpenSearch master user ARN (IAM role)"
  value       = module.opensearch.master_user_arn
}

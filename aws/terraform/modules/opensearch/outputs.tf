output "endpoint" {
  description = "OpenSearch endpoint"
  value       = aws_opensearch_domain.main.endpoint
}

output "kibana_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = aws_opensearch_domain.main.dashboard_endpoint
}

output "domain_arn" {
  description = "OpenSearch domain ARN"
  value       = aws_opensearch_domain.main.arn
}

output "master_user_arn" {
  description = "OpenSearch master user ARN (IAM role)"
  value       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ec2-role"
}

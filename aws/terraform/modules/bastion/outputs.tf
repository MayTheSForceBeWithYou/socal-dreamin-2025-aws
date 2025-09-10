output "bastion_instance_id" {
  description = "ID of the bastion instance"
  value       = aws_instance.bastion.id
}

output "bastion_public_ip" {
  description = "Public IP address of the bastion host"
  value       = aws_eip.bastion.public_ip
}

output "bastion_public_dns" {
  description = "Public DNS name of the bastion host"
  value       = aws_eip.bastion.public_dns
}

output "opensearch_proxy_url" {
  description = "URL to access OpenSearch through the bastion proxy"
  value       = "https://${aws_eip.bastion.public_ip}/_dashboards/"
}

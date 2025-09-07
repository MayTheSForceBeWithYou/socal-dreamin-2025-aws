variable "project_name" {
  description = "Project name"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "key_pair_name" {
  description = "Name of the key pair for SSH access"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the EC2 instance"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs for the EC2 instance"
  type        = list(string)
}

variable "iam_instance_profile" {
  description = "IAM instance profile name"
  type        = string
}

variable "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  type        = string
}

variable "salesforce_instance_url" {
  description = "Salesforce instance URL"
  type        = string
}

variable "secrets_manager_secret_arn" {
  description = "Secrets Manager secret ARN for Salesforce credentials"
  type        = string
}

variable "poll_interval_seconds" {
  description = "Polling interval for Salesforce events"
  type        = number
}

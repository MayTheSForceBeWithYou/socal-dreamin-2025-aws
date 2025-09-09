variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "sf-opensearch-lab"
}

variable "owner" {
  description = "Owner tag"
  type        = string
  default     = "lab-user"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}

# OpenSearch
variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 1
}

variable "opensearch_ebs_volume_size" {
  description = "OpenSearch EBS volume size (GB)"
  type        = number
  default     = 20
}

# EC2
variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "poll_interval_seconds" {
  description = "Polling interval for Salesforce events"
  type        = number
  default     = 60
}

# Salesforce JWT
variable "salesforce_instance_url" {
  description = "Salesforce instance URL"
  type        = string
}

variable "salesforce_client_id" {
  description = "Salesforce Connected App Consumer Key"
  type        = string
  sensitive   = true
}

variable "salesforce_username" {
  description = "Salesforce username for JWT"
  type        = string
  sensitive   = true
}

variable "salesforce_private_key" {
  description = "Private key for JWT (PEM format)"
  type        = string
  sensitive   = true
}

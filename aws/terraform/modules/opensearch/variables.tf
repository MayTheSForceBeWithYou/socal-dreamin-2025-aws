variable "project_name" {
  description = "Project name"
  type        = string
}

variable "instance_type" {
  description = "OpenSearch instance type"
  type        = string
}

variable "instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
}

variable "ebs_volume_size" {
  description = "OpenSearch EBS volume size (GB)"
  type        = number
}

variable "subnet_ids" {
  description = "List of subnet IDs for OpenSearch"
  type        = list(string)
}

variable "security_groups" {
  description = "List of security group IDs for OpenSearch"
  type        = list(string)
}

variable "terraform_user_arn" {
  description = "ARN of the terraform IAM user"
  type        = string
}

variable "ec2_role_arn" {
  description = "ARN of the EC2 IAM role for OpenSearch master user"
  type        = string
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# OpenSearch Domain
resource "aws_opensearch_domain" "main" {
  domain_name    = "${var.project_name}-os"
  engine_version = "OpenSearch_2.11"
  
  cluster_config {
    instance_type            = var.instance_type
    instance_count          = var.instance_count
    zone_awareness_enabled  = var.instance_count > 1
    
    dynamic "zone_awareness_config" {
      for_each = var.instance_count > 1 ? [1] : []
      content {
        availability_zone_count = var.instance_count
      }
    }
  }
  
  ebs_options {
    ebs_enabled = true
    volume_size = var.ebs_volume_size
    volume_type = "gp3"
  }
  
  # Commented out VPC options to enable public access
  # vpc_options {
  #   subnet_ids         = var.subnet_ids
  #   security_group_ids = var.security_groups
  # }
  
  encrypt_at_rest {
    enabled = true
  }
  
  node_to_node_encryption {
    enabled = true
  }
  
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }
  
  # Configure for reliable dashboard access with internal user database
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = "os_admin"
      master_user_password = random_password.opensearch_password.result
    }
  }
  
  # Single access policy that allows both IAM and public access
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ec2-role",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
          ]
        }
        Action = [
          "es:*"
        ]
        Resource = [
          "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-os",
          "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-os/*"
        ]
      },
      {
        Effect = "Allow"
        Principal = "*"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = [
          "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-os",
          "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-os/*"
        ]
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-opensearch"
  }
}

# Random password for OpenSearch admin user
resource "random_password" "opensearch_password" {
  length  = 32
  special = true
}
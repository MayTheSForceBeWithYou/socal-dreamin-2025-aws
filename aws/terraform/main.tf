terraform {
  required_version = ">= 1.0"
  
  # Using local state storage for workshop simplicity
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "salesforce-opensearch/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
      Owner     = var.owner
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# IAM User for Terraform
resource "aws_iam_user" "terraform_user" {
  name = "terraform"
  
  tags = {
    Name = "terraform-user"
  }
}

# Random string for unique names
resource "random_string" "random" {
  length  = 8
  special = false
}

# Key Pair for EC2 SSH access
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-keypair"
  public_key = var.ssh_public_key
  
  tags = {
    Name = "${var.project_name}-keypair"
  }
}

# Networking
module "networking" {
  source = "./modules/networking"
  
  project_name         = var.project_name
  vpc_cidr            = var.vpc_cidr
  availability_zones  = data.aws_availability_zones.available.names
  allowed_cidr_blocks = var.allowed_cidr_blocks
}

# IAM Roles
module "iam" {
  source = "./modules/iam"
  
  project_name = var.project_name
}

# OpenSearch Domain
module "opensearch" {
  source = "./modules/opensearch"
  
  project_name    = var.project_name
  subnet_ids      = [module.networking.private_subnet_ids[0]]  # Use only one subnet for single instance
  security_groups = [module.networking.opensearch_security_group_id]
  
  instance_type   = var.opensearch_instance_type
  instance_count  = var.opensearch_instance_count
  ebs_volume_size = var.opensearch_ebs_volume_size
  
  terraform_user_arn = aws_iam_user.terraform_user.arn
  ec2_role_arn       = module.iam.ec2_role_arn
  
  depends_on = [module.iam]
}

# EC2 Instance
module "ec2" {
  source = "./modules/ec2"
  
  project_name           = var.project_name
  subnet_id              = module.networking.public_subnet_ids[0]  # Use public subnet for easy access
  security_group_ids     = [module.networking.ec2_security_group_id]
  key_pair_name          = aws_key_pair.main.key_name
  iam_instance_profile   = module.iam.ec2_instance_profile_name
  
  instance_type          = var.ec2_instance_type
  opensearch_endpoint    = module.opensearch.endpoint
  salesforce_instance_url = var.salesforce_instance_url
  secrets_manager_secret_arn = aws_secretsmanager_secret.salesforce_creds.arn
  poll_interval_seconds  = var.poll_interval_seconds
}

# Bastion Host for OpenSearch Access
module "bastion" {
  source = "./modules/bastion"
  
  project_name           = var.project_name
  vpc_id                 = module.networking.vpc_id
  subnet_id              = module.networking.public_subnet_ids[0]  # Use public subnet
  security_group_id      = module.networking.bastion_security_group_id
  key_pair_name          = aws_key_pair.main.key_name
  iam_instance_profile   = module.iam.ec2_instance_profile_name
  
  instance_type          = var.bastion_instance_type
  opensearch_endpoint    = module.opensearch.endpoint
  allowed_cidr_blocks    = var.allowed_cidr_blocks
}

# Secrets Manager for Salesforce credentials
resource "aws_secretsmanager_secret" "salesforce_creds" {
  name        = "${var.project_name}-salesforce-creds-${random_string.random.result}"
  description = "Salesforce JWT credentials for login event streaming"
  
  tags = {
    Name = "${var.project_name}-salesforce-credentials-${random_string.random.result}"
  }
}

resource "aws_secretsmanager_secret_version" "salesforce_creds" {
  secret_id = aws_secretsmanager_secret.salesforce_creds.id
  secret_string = jsonencode({
    client_id    = var.salesforce_client_id
    username     = var.salesforce_username
    private_key  = var.salesforce_private_key
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

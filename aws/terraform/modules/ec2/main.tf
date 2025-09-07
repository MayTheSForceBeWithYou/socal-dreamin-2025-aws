data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# User data script for EC2 initialization
locals {
  user_data = templatefile("${path.module}/../../user-data.sh", {
    opensearch_endpoint        = var.opensearch_endpoint
    salesforce_instance_url    = var.salesforce_instance_url
    secrets_manager_secret_arn = var.secrets_manager_secret_arn
    poll_interval_seconds      = var.poll_interval_seconds
    aws_region                 = data.aws_region.current.name
  })
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  subnet_id             = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile   = var.iam_instance_profile
  
  user_data = base64encode(local.user_data)
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  tags = {
    Name = "${var.project_name}-streamer"
    Type = "salesforce-opensearch-streamer"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for consistent access
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"
  
  tags = {
    Name = "${var.project_name}-eip"
  }
}

data "aws_region" "current" {}

# Bastion Host for OpenSearch Access
# This module creates a secure bastion host that acts as a gateway to access OpenSearch

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

# Security Group for Bastion Host
resource "aws_security_group" "bastion" {
  name_prefix = "${var.project_name}-bastion-"
  vpc_id      = var.vpc_id
  description = "Security group for bastion host"
  
  # SSH access - restricted to your IP only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access from allowed IPs"
  }
  
  # HTTPS access for OpenSearch proxy - restricted to your IP only
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTPS access for OpenSearch proxy"
  }
  
  # HTTP access for OpenSearch proxy - restricted to your IP only
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTP access for OpenSearch proxy"
  }
  
  # Outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}

# User data script for bastion initialization
locals {
  user_data = templatefile("${path.module}/user-data.sh", {
    opensearch_endpoint = var.opensearch_endpoint
    aws_region         = data.aws_region.current.name
  })
}

# Bastion Host Instance
resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  subnet_id             = var.subnet_id
  vpc_security_group_ids = [aws_security_group.bastion.id]
  iam_instance_profile   = var.iam_instance_profile
  
  user_data = base64encode(local.user_data)
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  tags = {
    Name = "${var.project_name}-bastion"
    Type = "opensearch-gateway"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for consistent access
resource "aws_eip" "bastion" {
  instance = aws_instance.bastion.id
  domain   = "vpc"
  
  tags = {
    Name = "${var.project_name}-bastion-eip"
  }
}

data "aws_region" "current" {}

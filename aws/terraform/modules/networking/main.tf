# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]
  
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]
  
  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Route Table Association for Public Subnets
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Group for EC2
resource "aws_security_group" "ec2" {
  name_prefix = "${var.project_name}-ec2-"
  vpc_id      = aws_vpc.main.id
  
  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

# Security Group for OpenSearch
resource "aws_security_group" "opensearch" {
  name_prefix = "${var.project_name}-opensearch-"
  vpc_id      = aws_vpc.main.id
  
  # OpenSearch HTTPS from EC2
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description     = "HTTPS access from EC2 instance"
  }
  
  # OpenSearch HTTP from EC2 (if needed)
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    cidr_blocks = [var.vpc_cidr]  # Allow from entire VPC
    # security_groups = [aws_security_group.ec2.id]
    description     = "HTTP access from EC2 instance"
  }
  
  # OpenSearch HTTPS from Bastion Host
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks = [var.vpc_cidr]  # Allow from entire VPC
    # security_groups = [aws_security_group.bastion.id]
    description     = "HTTPS access from bastion host"
  }
  
  # OpenSearch port 9200 HTTPS
  ingress {
    from_port       = 9200
    to_port         = 9200
    protocol        = "tcp"
    cidr_blocks = [var.vpc_cidr]  # Allow from entire VPC
    # security_groups = [aws_security_group.bastion.id]
    description     = "HTTPS access"
  }
  
  # OpenSearch HTTP from Bastion Host (if needed)
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
    description     = "HTTP access from bastion host"
  }
  
  # Outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-opensearch-sg"
  }
}

# Security Group for Bastion Host
resource "aws_security_group" "bastion" {
  name_prefix = "${var.project_name}-bastion-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for bastion host"
  
  # SSH access - restricted to allowed CIDR blocks
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access from allowed IPs"
  }
  
  # HTTPS access for OpenSearch proxy - restricted to allowed CIDR blocks
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTPS access for OpenSearch proxy"
  }
  
  # HTTP access for OpenSearch proxy - restricted to allowed CIDR blocks
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

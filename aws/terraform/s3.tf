terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.region
}

# Small random suffix ensures global uniqueness even if two people collide
resource "random_id" "bucket" {
  byte_length = 3 # 6 hex chars (e.g., a1b2c3)
}

# S3 bucket for login history data
resource "aws_s3_bucket" "login_history_data" {
  bucket = lower(
    replace(
      format(
        "%s-%s-%s-%s",
        var.bucket_prefix,     # e.g., socal-dreamin-2025-aws-login-history-data
        var.environment,       # e.g., lab
        var.owner_suffix,      # e.g., flastname
        random_id.bucket.hex   # e.g., a1b2c3
      ),
      "_",
      "-"
    )
  )

  # Helpful during workshop teardown so non-empty buckets don't block destroy
  force_destroy = true
}

# Block all public access (safest default)
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.login_history_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  value = aws_s3_bucket.login_history_data.bucket
}

# S3 bucket for login history data
resource "aws_s3_bucket" "login_history_data" {
  bucket = "socal-dreamin-2025-aws-login-history-data"
}
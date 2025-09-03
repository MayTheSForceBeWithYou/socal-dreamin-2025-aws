# Lambda function to listen to Salesforce LoginEventStream and forward to AWS EventBridge
# Lambda function script located at aws/lambda/LoginEventStream-handler.js
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/LoginEventStream-handler.js"
  output_path = "${path.module}/../lambda/LoginEventStream-handler.zip"
}

resource "aws_lambda_function" "login_event_stream_handler" {
  function_name = "LoginEventStreamHandler"
  handler = "LoginEventStream-handler.handler"
  runtime = "nodejs20.x"
  role = aws_iam_role.lambda_role.arn
  filename = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

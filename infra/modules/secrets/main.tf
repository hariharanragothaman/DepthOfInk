resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.app_name}/openai-api-key"
  description             = "OpenAI API key for ${var.app_name}"
  recovery_window_in_days = 7

  tags = { Name = "${var.app_name}-openai-key" }
}

resource "aws_secretsmanager_secret_version" "openai_api_key_placeholder" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = jsonencode({ OPENAI_API_KEY = "REPLACE_ME" })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

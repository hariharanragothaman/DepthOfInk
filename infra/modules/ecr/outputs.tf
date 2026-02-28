output "repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "repository_arn" {
  value = aws_ecr_repository.backend.arn
}

output "registry_id" {
  value = aws_ecr_repository.backend.registry_id
}

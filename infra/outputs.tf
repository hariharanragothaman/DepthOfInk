output "backend_url" {
  description = "Backend ALB URL (API base)"
  value       = "http://${module.ecs.alb_dns_name}"
}

output "frontend_url" {
  description = "Frontend CloudFront URL"
  value       = "https://${module.frontend.cloudfront_domain_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for docker push"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

output "frontend_s3_bucket" {
  description = "S3 bucket for frontend static files"
  value       = module.frontend.s3_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = module.frontend.cloudfront_distribution_id
}

output "secret_name" {
  description = "Secrets Manager secret name (set your OpenAI key here)"
  value       = module.secrets.secret_name
}

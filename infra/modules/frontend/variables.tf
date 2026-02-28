variable "app_name" {
  type = string
}

variable "alb_dns_name" {
  type        = string
  description = "Backend ALB DNS name, used for CORS origin allowlisting."
}

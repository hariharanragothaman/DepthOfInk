variable "app_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "ecs_security_group_id" {
  type = string
}

variable "efs_security_group_id" {
  type = string
}

variable "ecr_repository_url" {
  type = string
}

variable "secret_arn" {
  type = string
}

variable "container_image_tag" {
  type    = string
  default = "latest"
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "max_count" {
  type    = number
  default = 3
}

variable "container_port" {
  type    = number
  default = 8000
}

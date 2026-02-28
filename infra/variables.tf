variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "app_name" {
  type    = string
  default = "depthofink"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "az_count" {
  type    = number
  default = 2
}

variable "fargate_cpu" {
  type    = number
  default = 256
}

variable "fargate_memory" {
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

variable "container_image_tag" {
  type    = string
  default = "latest"
}

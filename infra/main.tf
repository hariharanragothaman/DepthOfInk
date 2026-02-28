terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use S3 remote state:
  # backend "s3" {
  #   bucket         = "depthofink-terraform-state"
  #   key            = "infra/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "depthofink-tf-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.app_name
      ManagedBy = "terraform"
    }
  }
}

# --- Modules ---

module "networking" {
  source   = "./modules/networking"
  app_name = var.app_name
  vpc_cidr = var.vpc_cidr
  az_count = var.az_count
}

module "ecr" {
  source   = "./modules/ecr"
  app_name = var.app_name
}

module "secrets" {
  source   = "./modules/secrets"
  app_name = var.app_name
}

module "ecs" {
  source = "./modules/ecs"

  app_name              = var.app_name
  aws_region            = var.aws_region
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  ecs_security_group_id = module.networking.ecs_security_group_id
  efs_security_group_id = module.networking.efs_security_group_id
  ecr_repository_url    = module.ecr.repository_url
  secret_arn            = module.secrets.secret_arn
  container_image_tag   = var.container_image_tag
  cpu                   = var.fargate_cpu
  memory                = var.fargate_memory
  desired_count         = var.desired_count
  max_count             = var.max_count
}

module "frontend" {
  source       = "./modules/frontend"
  app_name     = var.app_name
  alb_dns_name = module.ecs.alb_dns_name
}

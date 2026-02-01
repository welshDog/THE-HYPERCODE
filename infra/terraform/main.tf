terraform {
  required_version = ">= 1.5.0"
}

variable "environment" { type = string }
variable "registry" { type = string }
variable "image_name" { type = string }
variable "image_tag" { type = string }

module "network" { source = "./modules/network" environment = var.environment }
module "compute" { source = "./modules/compute" environment = var.environment }
module "storage" { source = "./modules/storage" environment = var.environment }

output "endpoint" { value = module.compute.endpoint }

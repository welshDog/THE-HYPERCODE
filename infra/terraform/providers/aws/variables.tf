variable "environment" { type = string }
variable "region" { type = string }
variable "az" { type = string }
variable "vpc_cidr" { type = string }
variable "public_subnet_cidr" { type = string }
variable "route53_zone_id" { type = string }
variable "domain" { type = string }
variable "acm_certificate_arn" { type = string }

variable "tags" {
  type = map(string)
  default = {
    ManagedBy   = "terraform"
    Project     = "hypercode"
  }
}

variable "target_type" {
  type    = string
  default = "ip"
  validation {
    condition     = contains(["ip", "instance", "lambda"], var.target_type)
    error_message = "target_type must be one of ip, instance, lambda"
  }
}

variable "target_ip" {
  type    = string
  default = ""
}

variable "target_instance_ids" {
  type    = list(string)
  default = []
}

variable "target_port" {
  type    = number
  default = 80
}

variable "health_check_enabled" {
  type    = bool
  default = true
}

variable "health_check_protocol" {
  type    = string
  default = "HTTP"
}

variable "health_check_port" {
  type    = number
  default = 80
}

variable "health_check_path" {
  type    = string
  default = "/ready"
}

variable "health_check_interval" {
  type    = number
  default = 10
}

variable "health_check_timeout" {
  type    = number
  default = 5
}

variable "health_check_healthy_threshold" {
  type    = number
  default = 3
}

variable "health_check_unhealthy_threshold" {
  type    = number
  default = 3
}

variable "health_check_matcher" {
  type    = string
  default = "200-399"
}

variable "asg_name" {
  type    = string
  default = ""
}

variable "enable_asg_attachment" {
  type    = bool
  default = false
}

variable "enable_ecs_integration" {
  type    = bool
  default = false
}

variable "ecs_target_type" {
  type    = string
  default = "ip"
}

variable "ecs_container_port" {
  type    = number
  default = 80
}

variable "lambda_function_arn" {
  type    = string
  default = ""
}

variable "enable_lambda_integration" {
  type    = bool
  default = false
}

variable "_validate_targets" {
  type    = bool
  default = true
  validation {
    condition = (
      (var.target_type != "ip" || length(var.target_ip) > 0) &&
      (var.target_type != "instance" || length(var.target_instance_ids) > 0) &&
      (var.target_type != "lambda" || length(var.lambda_function_arn) > 0)
    )
    error_message = "Provide targets for the selected target_type"
  }
}

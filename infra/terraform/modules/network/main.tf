variable "environment" { type = string }
output "subnet_id" { value = "subnet-${var.environment}" }

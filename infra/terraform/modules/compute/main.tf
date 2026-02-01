variable "environment" { type = string }
output "endpoint" { value = "vm-${var.environment}.local" }

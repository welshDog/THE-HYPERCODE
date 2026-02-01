variable "environment" { type = string }
output "bucket" { value = "bucket-${var.environment}" }

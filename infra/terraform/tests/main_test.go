package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestAwsNetworking(t *testing.T) {
    t.Parallel()
    terraformOptions := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/aws",
        Vars: map[string]interface{}{
            "environment": "dev",
            "region": "us-east-1",
            "az": "us-east-1a",
            "vpc_cidr": "10.0.0.0/16",
            "public_subnet_cidr": "10.0.1.0/24",
            "route53_zone_id": "Z123456",
            "domain": "example.com",
        },
    }
    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndPlan(t, terraformOptions)
}

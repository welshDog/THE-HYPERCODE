package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestGcpNetworking(t *testing.T) {
    t.Parallel()
    terraformOptions := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/gcp",
        Vars: map[string]interface{}{
            "environment": "dev",
            "project": "hypercode-dev",
            "region": "us-central1",
            "subnet_cidr": "10.4.1.0/24",
        },
    }
    terraform.InitAndPlan(t, terraformOptions)
}

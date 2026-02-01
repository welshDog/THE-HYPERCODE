package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestAzureNetworking(t *testing.T) {
    t.Parallel()
    terraformOptions := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/azure",
        Vars: map[string]interface{}{
            "environment": "dev",
            "location": "eastus",
            "address_space": "10.3.0.0/16",
            "subnet_cidr": "10.3.1.0/24",
        },
    }
    terraform.InitAndPlan(t, terraformOptions)
}

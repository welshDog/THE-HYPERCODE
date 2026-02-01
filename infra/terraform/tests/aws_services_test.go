package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
)

func TestAwsAlbWithLambdaIntegrationPlan(t *testing.T) {
    t.Parallel()
    tf := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/aws",
        Vars: map[string]interface{}{
            "target_type": "lambda",
            "enable_lambda_integration": true,
            "lambda_function_arn": "arn:aws:lambda:us-east-1:123456789012:function:demo",
        },
    }
    terraform.InitAndPlan(t, tf)
}

func TestAwsAlbWithAsgAttachmentPlan(t *testing.T) {
    t.Parallel()
    tf := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/aws",
        Vars: map[string]interface{}{
            "target_type": "instance",
            "enable_asg_attachment": true,
            "asg_name": "example-asg",
        },
    }
    terraform.InitAndPlan(t, tf)
}

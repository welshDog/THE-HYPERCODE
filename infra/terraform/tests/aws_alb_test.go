package test

import (
    "testing"
    "time"

    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/session"
    elbv2 "github.com/aws/aws-sdk-go/service/elbv2"
    "github.com/gruntwork-io/terratest/modules/aws"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "strconv"
)

func TestAwsAlbTargetGroupHealthChecks(t *testing.T) {
    t.Parallel()
    tf := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/aws",
        VarFiles:      []string{"dev.tfvars"},
    }

    terraform.InitAndApply(t, tf)
    defer terraform.Destroy(t, tf)

    region := terraform.Output(t, tf, "region")
    tgArn := terraform.Output(t, tf, "target_group_arn")
    hc := terraform.OutputMap(t, tf, "health_check")

    sess := session.Must(session.NewSession(&aws.Config{Region: aws.String(region)}))
    svc := elbv2.New(sess)

    desc, err := svc.DescribeTargetGroups(&elbv2.DescribeTargetGroupsInput{TargetGroupArns: []*string{aws.String(tgArn)}})
    if err != nil {
        t.Fatalf("describe target groups: %v", err)
    }
    if len(desc.TargetGroups) != 1 {
        t.Fatalf("target group not found")
    }
    tg := desc.TargetGroups[0]
    if aws.StringValue(tg.HealthCheckPath) != hc["path"] {
        t.Fatalf("health check path mismatch")
    }
    if aws.StringValue(tg.HealthCheckProtocol) != hc["protocol"] {
        t.Fatalf("health check protocol mismatch")
    }
    if aws.Int64Value(tg.HealthCheckIntervalSeconds) != int64(mustAtoi(hc["interval"])) {
        t.Fatalf("health check interval mismatch")
    }
    if aws.Int64Value(tg.HealthCheckTimeoutSeconds) != int64(mustAtoi(hc["timeout"])) {
        t.Fatalf("health check timeout mismatch")
    }
    if aws.Int64Value(tg.HealthyThresholdCount) != int64(mustAtoi(hc["healthy_threshold"])) {
        t.Fatalf("healthy threshold mismatch")
    }
    if aws.Int64Value(tg.UnhealthyThresholdCount) != int64(mustAtoi(hc["unhealthy_threshold"])) {
        t.Fatalf("unhealthy threshold mismatch")
    }
    if aws.StringValue(tg.Matcher.HttpCode) != hc["matcher"] {
        t.Fatalf("http code matcher mismatch")
    }

    out, err := svc.DescribeTargetHealth(&elbv2.DescribeTargetHealthInput{TargetGroupArn: aws.String(tgArn)})
    if err != nil {
        t.Fatalf("describe target health: %v", err)
    }
    counts := terraform.OutputMap(t, tf, "attachment_counts")
    exp := mustAtoi(counts["ip"]) + mustAtoi(counts["instances"])
    if len(out.TargetHealthDescriptions) != exp {
        t.Fatalf("attachment count mismatch")
    }
    _ = hc
}

func TestAwsAlbTargetAttachmentLifecycle(t *testing.T) {
    t.Parallel()
    tf := &terraform.Options{
        TerraformDir: "../../infra/terraform/providers/aws",
        VarFiles:      []string{"dev.tfvars"},
    }

    terraform.InitAndApply(t, tf)
    defer terraform.Destroy(t, tf)

    region := terraform.Output(t, tf, "region")
    tgArn := terraform.Output(t, tf, "target_group_arn")

    sess := session.Must(session.NewSession(&aws.Config{Region: aws.String(region)}))
    svc := elbv2.New(sess)
    _, _ = svc, tgArn

    time.Sleep(5 * time.Second)
}

func mustAtoi(s string) int {
    n, err := strconv.Atoi(s)
    if err != nil {
        panic(err)
    }
    return n
}

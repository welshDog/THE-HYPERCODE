terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = merge(var.tags, { Name = "hypercode-${var.environment}-vpc", Environment = var.environment })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = var.az
  tags = merge(var.tags, { Name = "hypercode-${var.environment}-public", Environment = var.environment })
}

resource "aws_security_group" "app" {
  name        = "hypercode-${var.environment}-sg"
  description = "App security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "app" {
  name               = "hypercode-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.public.id]
  tags               = merge(var.tags, { Name = "hypercode-${var.environment}-alb", Environment = var.environment })
}

resource "aws_lb_target_group" "app" {
  name        = "hypercode-${var.environment}-tg"
  port        = var.target_port
  protocol    = var.health_check_protocol
  vpc_id      = aws_vpc.main.id
  target_type = var.target_type
  dynamic "health_check" {
    for_each = var.health_check_enabled && var.target_type != "lambda" ? [1] : []
    content {
      protocol            = var.health_check_protocol
      port                = var.health_check_port
      path                = var.health_check_path
      interval            = var.health_check_interval
      timeout             = var.health_check_timeout
      healthy_threshold   = var.health_check_healthy_threshold
      unhealthy_threshold = var.health_check_unhealthy_threshold
      matcher             = var.health_check_matcher
    }
  }
  tags = merge(var.tags, { Name = "hypercode-${var.environment}-tg", Environment = var.environment })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.acm_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lambda_permission" "alb_invoke" {
  count               = var.enable_lambda_integration && length(var.lambda_function_arn) > 0 ? 1 : 0
  statement_id        = "AllowALBInvoke"
  action              = "lambda:InvokeFunction"
  function_name       = var.lambda_function_arn
  principal           = "elasticloadbalancing.amazonaws.com"
  source_arn          = aws_lb_target_group.app.arn
}

resource "aws_lb_target_group_attachment" "ip" {
  count             = var.target_type == "ip" && length(var.target_ip) > 0 ? 1 : 0
  target_group_arn  = aws_lb_target_group.app.arn
  target_id         = var.target_ip
  port              = var.target_port
}

resource "aws_lb_target_group_attachment" "instances" {
  count             = var.target_type == "instance" ? length(var.target_instance_ids) : 0
  target_group_arn  = aws_lb_target_group.app.arn
  target_id         = var.target_instance_ids[count.index]
  port              = var.target_port
}

resource "aws_autoscaling_attachment" "asg_tg" {
  count                  = var.enable_asg_attachment && length(var.asg_name) > 0 ? 1 : 0
  autoscaling_group_name = var.asg_name
  lb_target_group_arn    = aws_lb_target_group.app.arn
}

resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.domain
  type    = "A"
  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

output "endpoint" {
  value = "http://${aws_route53_record.app.name}"
}
output "security_group_id" {
  value = aws_security_group.app.id
}
output "vpc_id" {
  value = aws_vpc.main.id
}
output "region" {
  value = var.region
}
output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}
output "health_check" {
  value = {
    protocol            = var.health_check_protocol
    port                = var.health_check_port
    path                = var.health_check_path
    interval            = var.health_check_interval
    timeout             = var.health_check_timeout
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
    matcher             = var.health_check_matcher
  }
}
output "attachment_counts" {
  value = {
    ip        = var.target_type == "ip" && length(var.target_ip) > 0 ? 1 : 0
    instances = var.target_type == "instance" ? length(var.target_instance_ids) : 0
  }
}

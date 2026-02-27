terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name            = "${var.project_name}-${var.environment}"
  container_name  = "${var.project_name}-cli"
  log_group_name  = "/ecs/${local.name}"
  merged_env_vars = merge(
    {
      LOG_LEVEL = var.log_level,
    },
    var.extra_env,
  )
}

resource "aws_ecr_repository" "this" {
  count                = var.create_ecr_repository ? 1 : 0
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_in_days
}

resource "aws_ecs_cluster" "this" {
  name = local.name
}

resource "aws_iam_role" "task_execution" {
  name = "${local.name}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "execution_policy" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "${local.name}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  inline_policy {
    name = "allow-parameter-store"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect   = "Allow"
          Action   = ["ssm:GetParameters", "ssm:GetParameter", "secretsmanager:GetSecretValue"]
          Resource = "*"
        }
      ]
    })
  }
}

resource "aws_ecs_task_definition" "email" {
  family                   = local.name
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = local.container_name
      image     = var.container_image
      essential = true
      command   = var.task_command
      environment = [
        for k, v in local.merged_env_vars : {
          name  = k
          value = v
        }
      ]
      secrets = [
        for secret in var.secret_env : {
          name      = secret.name
          valueFrom = secret.value_from
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.log_group_name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_iam_role" "events" {
  name = "${local.name}-events-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  inline_policy {
    name = "allow-ecs-run"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = ["ecs:RunTask", "ecs:DescribeTasks"]
          Resource = [aws_ecs_task_definition.email.arn]
          Condition = {
            ArnLike = {
              "ecs:cluster" = aws_ecs_cluster.this.arn
            }
          }
        },
        {
          Effect = "Allow"
          Action = ["iam:PassRole"]
          Resource = [aws_iam_role.task_execution.arn, aws_iam_role.task.arn]
        }
      ]
    })
  }
}

resource "aws_events_rule" "scheduler" {
  name                = "${local.name}-rule"
  schedule_expression = var.schedule_expression
  description         = "Invoke the email assistant container on a schedule"
}

resource "aws_events_target" "scheduler" {
  rule      = aws_events_rule.scheduler.name
  target_id = "${local.name}-target"
  arn       = aws_ecs_cluster.this.arn
  role_arn  = aws_iam_role.events.arn

  ecs_target {
    launch_type = "FARGATE"
    task_count  = var.task_count
    task_definition_arn = aws_ecs_task_definition.email.arn
    network_configuration {
      subnets         = var.subnet_ids
      security_groups = var.security_group_ids
      assign_public_ip = var.assign_public_ip
    }
  }
}
# Terraform Deployment (AWS ECS)

This module provisions the infrastructure required to run the email assistant container on a recurring schedule using EventBridge + ECS Fargate.

## Prerequisites
- Terraform >= 1.6
- AWS account + credentials
- Existing VPC subnets and security groups with outbound internet access (for Gmail API)
- Container image pushed to ECR (or any public registry)
- Gmail OAuth credentials + refresh token stored as Secrets Manager parameters (base64 recommended)

## Inputs Overview
| Variable | Description |
| --- | --- |
| `project_name` | Base name for all resources |
| `environment` | Suffix (prod/stage/dev) |
| `container_image` | Fully-qualified image URI |
| `task_command` | CLI args (default labels 50 messages) |
| `schedule_expression` | EventBridge schedule (e.g., `rate(15 minutes)`) |
| `subnet_ids` / `security_group_ids` | Networking for the Fargate task |
| `extra_env` | Plain env vars (LOG_LEVEL, account names, etc.) |
| `secret_env` | Secrets from SSM/Secrets Manager following the ECS format |

See [variables.tf](variables.tf) for the complete list.

## Example Usage
```hcl
module "email_assistant" {
  source = "./terraform"

  project_name   = "email-assistant"
  environment    = "prod"
  aws_region     = "us-east-1"
  container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/email-assistant:latest"
  subnet_ids        = ["subnet-abc123", "subnet-def456"]
  security_group_ids = ["sg-0123456789abcdef0"]
  schedule_expression = "rate(10 minutes)"

  extra_env = {
    GMAIL_USER_ID = "me"
    LOG_LEVEL     = "INFO"
  }

  secret_env = [
    {
      name       = "GOOGLE_CLIENT_SECRETS_B64"
      value_from = "arn:aws:ssm:us-east-1:123456789012:parameter/email-assistant/credentials-b64"
    },
    {
      name       = "GOOGLE_TOKEN_B64"
      value_from = "arn:aws:secretsmanager:us-east-1:123456789012:secret:email-assistant/token"
    }
  ]
}
```

After applying, CloudWatch Logs will capture the CLI output, and EventBridge will trigger the task on the configured schedule.

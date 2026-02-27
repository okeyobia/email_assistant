variable "project_name" {
  type        = string
  description = "Base name for all provisioned resources"
  default     = "email-assistant"
}

variable "environment" {
  type        = string
  description = "Environment suffix (e.g. prod, staging)"
  default     = "prod"
}

variable "aws_region" {
  type        = string
  description = "AWS region for all resources"
  default     = "us-east-1"
}

variable "container_image" {
  type        = string
  description = "Fully-qualified image URI (e.g., account.dkr.ecr.../email-assistant:latest)"
}

variable "task_command" {
  type        = list(string)
  description = "Override the default CLI arguments passed to the container"
  default     = ["label", "--max-results", "50"]
}

variable "task_cpu" {
  type        = number
  description = "ECS task CPU units"
  default     = 512
}

variable "task_memory" {
  type        = number
  description = "ECS task memory (MiB)"
  default     = 1024
}

variable "task_count" {
  type        = number
  description = "Number of tasks to launch per schedule trigger"
  default     = 1
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule expression (e.g., rate(15 minutes))"
  default     = "rate(15 minutes)"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the Fargate task"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups applied to the task ENIs"
}

variable "assign_public_ip" {
  type        = bool
  description = "Assign a public IP to the Fargate task"
  default     = false
}

variable "log_retention_in_days" {
  type        = number
  description = "Retention for CloudWatch log group"
  default     = 30
}

variable "create_ecr_repository" {
  type        = bool
  description = "Whether to create an ECR repository for the container image"
  default     = true
}

variable "log_level" {
  type        = string
  description = "LOG_LEVEL environment variable"
  default     = "INFO"
}

variable "extra_env" {
  type        = map(string)
  description = "Additional plain-text environment variables for the task"
  default     = {}
}

variable "secret_env" {
  description = "Secrets injected via AWS Secrets Manager / SSM Parameter Store"
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []
}
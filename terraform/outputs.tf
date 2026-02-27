output "cluster_name" {
  value       = aws_ecs_cluster.this.name
  description = "Name of the ECS cluster running the assistant"
}

output "task_definition_arn" {
  value       = aws_ecs_task_definition.email.arn
  description = "ARN of the ECS task definition"
}

output "event_rule_name" {
  value       = aws_events_rule.scheduler.name
  description = "EventBridge rule that triggers the task"
}

output "log_group_name" {
  value       = aws_cloudwatch_log_group.this.name
  description = "CloudWatch Logs group storing task output"
}

output "ecr_repository_url" {
  value       = var.create_ecr_repository ? aws_ecr_repository.this[0].repository_url : null
  description = "Optional ECR repository for the container image"
}

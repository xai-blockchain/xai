# ============================================================================
# VPC Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# ============================================================================
# Load Balancer Outputs
# ============================================================================

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "api_target_group_arn" {
  description = "ARN of API target group"
  value       = aws_lb_target_group.api.arn
}

output "explorer_target_group_arn" {
  description = "ARN of Block Explorer target group"
  value       = aws_lb_target_group.explorer.arn
}

# ============================================================================
# ECS Cluster Outputs
# ============================================================================

output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

# ============================================================================
# RDS Outputs
# ============================================================================

output "rds_cluster_endpoint" {
  description = "RDS cluster endpoint"
  value       = aws_rds_cluster.main.endpoint
}

output "rds_reader_endpoint" {
  description = "RDS cluster reader endpoint"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "rds_cluster_id" {
  description = "RDS cluster identifier"
  value       = aws_rds_cluster.main.cluster_identifier
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_rds_cluster.main.database_name
}

output "rds_master_username" {
  description = "RDS master username"
  value       = aws_rds_cluster.main.master_username
  sensitive   = true
}

output "rds_port" {
  description = "RDS port"
  value       = aws_rds_cluster.main.port
}

# ============================================================================
# Redis Outputs
# ============================================================================

output "redis_endpoint" {
  description = "Redis replication group endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_cluster_id" {
  description = "Redis replication group ID"
  value       = aws_elasticache_replication_group.main.id
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "redis_auth_token" {
  description = "Redis authentication token"
  value       = random_password.redis_auth_token.result
  sensitive   = true
}

# ============================================================================
# S3 Outputs
# ============================================================================

output "backups_bucket_name" {
  description = "S3 bucket name for backups"
  value       = aws_s3_bucket.backups.id
}

output "backups_bucket_arn" {
  description = "S3 bucket ARN for backups"
  value       = aws_s3_bucket.backups.arn
}

# ============================================================================
# Security Groups
# ============================================================================

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = aws_security_group.ecs_cluster.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "elasticache_security_group_id" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.elasticache.id
}

# ============================================================================
# IAM Roles
# ============================================================================

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task_role.arn
}

# ============================================================================
# CloudWatch
# ============================================================================

output "ecs_log_group_name" {
  description = "CloudWatch log group name for ECS"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "sns_alerts_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

# ============================================================================
# Connection Information
# ============================================================================

output "connection_info" {
  description = "Summary of connection information"
  value = {
    api_endpoint           = "https://${aws_lb.main.dns_name}/api"
    explorer_endpoint      = "https://${aws_lb.main.dns_name}/explorer"
    postgres_endpoint      = aws_rds_cluster.main.endpoint
    postgres_reader_endpoint = aws_rds_cluster.main.reader_endpoint
    redis_endpoint         = aws_elasticache_replication_group.main.primary_endpoint_address
    postgres_database      = aws_rds_cluster.main.database_name
    postgres_port          = aws_rds_cluster.main.port
    redis_port             = aws_elasticache_replication_group.main.port
    region                 = var.aws_region
  }
  sensitive = true
}

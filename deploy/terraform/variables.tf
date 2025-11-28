# ============================================================================
# AWS Provider Variables
# ============================================================================

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# ============================================================================
# Project Configuration
# ============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "xai-blockchain"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens only."
  }
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# ============================================================================
# VPC and Networking
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required."
  }
}

# ============================================================================
# Database Configuration
# ============================================================================

variable "postgres_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.3"
}

variable "postgres_db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "xai_blockchain"
  validation {
    condition     = can(regex("^[a-z0-9_]+$", var.postgres_db_name))
    error_message = "Database name must be lowercase alphanumeric with underscores only."
  }
}

variable "postgres_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "xaiadmin"
  sensitive   = true
  validation {
    condition     = length(var.postgres_username) >= 4
    error_message = "PostgreSQL username must be at least 4 characters."
  }
}

variable "postgres_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.postgres_password) >= 16
    error_message = "PostgreSQL password must be at least 16 characters."
  }
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.xlarge"
}

variable "rds_instance_count" {
  description = "Number of RDS instances in cluster"
  type        = number
  default     = 2
  validation {
    condition     = var.rds_instance_count >= 1 && var.rds_instance_count <= 10
    error_message = "RDS instance count must be between 1 and 10."
  }
}

# ============================================================================
# Redis Configuration
# ============================================================================

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r6g.xlarge"
}

variable "redis_cluster_size" {
  description = "Number of Redis nodes"
  type        = number
  default     = 3
  validation {
    condition     = var.redis_cluster_size >= 1 && var.redis_cluster_size <= 500
    error_message = "Redis cluster size must be between 1 and 500."
  }
}

# ============================================================================
# SSL/TLS Configuration
# ============================================================================

variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for ALB"
  type        = string
  sensitive   = true
}

# ============================================================================
# Monitoring and Alerts
# ============================================================================

variable "alert_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Alert email must be a valid email address."
  }
}

# ============================================================================
# Tagging
# ============================================================================

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

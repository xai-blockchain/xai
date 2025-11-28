# XAI Blockchain Testnet - Terraform Variables

variable "primary_region" {
  description = "Primary AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for blockchain nodes"
  type        = string
  default     = "t3.small"  # Bypassing Free Tier restrictions
}

variable "ssh_allowed_ips" {
  description = "List of IP addresses allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # CHANGE THIS IN PRODUCTION
}

variable "node_count_primary" {
  description = "Number of nodes in primary region"
  type        = number
  default     = 2
}

variable "node_count_eu" {
  description = "Number of nodes in EU region"
  type        = number
  default     = 1
}

variable "node_count_asia" {
  description = "Number of nodes in Asia region"
  type        = number
  default     = 1
}

variable "blockchain_p2p_port" {
  description = "P2P communication port for blockchain"
  type        = number
  default     = 8333
}

variable "blockchain_api_port" {
  description = "API port for blockchain nodes"
  type        = number
  default     = 5000
}

variable "enable_monitoring" {
  description = "Enable Prometheus/Grafana monitoring stack"
  type        = bool
  default     = true
}

variable "enable_spot_instances" {
  description = "Use spot instances for cost savings"
  type        = bool
  default     = false  # Using on-demand for reliability
}

variable "spot_price" {
  description = "Maximum spot price (if spot instances enabled)"
  type        = string
  default     = "0.10"  # Increased to ensure availability
}

variable "ebs_volume_size" {
  description = "Size of EBS volume for blockchain data (GB)"
  type        = number
  default     = 50
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for nodes"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default = {
    Terraform   = "true"
    Project     = "XAI-Blockchain"
    Environment = "testnet"
  }
}

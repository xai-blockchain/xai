# XAI Blockchain Testnet - Terraform Outputs

output "api_load_balancer_dns" {
  description = "DNS name of the API load balancer"
  value       = aws_lb.api.dns_name
}

output "api_endpoint" {
  description = "Full API endpoint URL"
  value       = "http://${aws_lb.api.dns_name}"
}

output "vpc_ids" {
  description = "VPC IDs for all regions"
  value = {
    primary = module.vpc_primary.vpc_id
    eu      = module.vpc_eu.vpc_id
    asia    = module.vpc_asia.vpc_id
  }
}

output "public_subnets" {
  description = "Public subnet IDs"
  value = {
    primary = module.vpc_primary.public_subnets
    eu      = module.vpc_eu.public_subnets
    asia    = module.vpc_asia.public_subnets
  }
}

output "security_group_id" {
  description = "Security group ID for blockchain nodes"
  value       = aws_security_group.blockchain_node.id
}

output "instance_profile_name" {
  description = "IAM instance profile name"
  value       = aws_iam_instance_profile.blockchain_node.name
}

output "asg_name_primary" {
  description = "Auto Scaling Group name for primary region"
  value       = aws_autoscaling_group.blockchain_nodes_primary.name
}

output "launch_template_id" {
  description = "Launch template ID for blockchain nodes"
  value       = aws_launch_template.blockchain_node.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for node logs"
  value       = "/aws/ec2/xai-testnet"
}

output "deployment_info" {
  description = "Testnet deployment information"
  value = {
    api_endpoint         = "http://${aws_lb.api.dns_name}"
    explorer_url         = "http://${aws_lb.api.dns_name}/explorer"
    faucet_url           = "http://${aws_lb.api.dns_name}/faucet"
    metrics_url          = "http://${aws_lb.api.dns_name}/metrics"
    regions              = ["us-east-1", "eu-west-1", "ap-southeast-1"]
    total_nodes          = var.node_count_primary + var.node_count_eu + var.node_count_asia
    network              = "testnet"
  }
}

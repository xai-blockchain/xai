# XAI Blockchain Testnet - AWS Infrastructure
# Terraform configuration for multi-region testnet deployment

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Store state in S3
  # backend "s3" {
  #   bucket = "xai-terraform-state"
  #   key    = "testnet/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Primary region provider
provider "aws" {
  region = var.primary_region

  default_tags {
    tags = {
      Project     = "XAI-Blockchain"
      Environment = "testnet"
      ManagedBy   = "Terraform"
    }
  }
}

# Secondary regions for multi-region deployment
provider "aws" {
  alias  = "eu"
  region = "eu-west-1"

  default_tags {
    tags = {
      Project     = "XAI-Blockchain"
      Environment = "testnet"
      ManagedBy   = "Terraform"
    }
  }
}

provider "aws" {
  alias  = "asia"
  region = "ap-southeast-1"

  default_tags {
    tags = {
      Project     = "XAI-Blockchain"
      Environment = "testnet"
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Configuration for primary region
module "vpc_primary" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "xai-testnet-vpc-primary"
  cidr = "10.0.0.0/16"

  azs             = ["${var.primary_region}a", "${var.primary_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true  # Cost optimization for testnet
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "xai-testnet-vpc-primary"
  }
}

# VPC for EU region
module "vpc_eu" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  providers = {
    aws = aws.eu
  }

  name = "xai-testnet-vpc-eu"
  cidr = "10.1.0.0/16"

  azs             = ["eu-west-1a", "eu-west-1b"]
  private_subnets = ["10.1.1.0/24", "10.1.2.0/24"]
  public_subnets  = ["10.1.101.0/24", "10.1.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "xai-testnet-vpc-eu"
  }
}

# VPC for Asia region
module "vpc_asia" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  providers = {
    aws = aws.asia
  }

  name = "xai-testnet-vpc-asia"
  cidr = "10.2.0.0/16"

  azs             = ["ap-southeast-1a", "ap-southeast-1b"]
  private_subnets = ["10.2.1.0/24", "10.2.2.0/24"]
  public_subnets  = ["10.2.101.0/24", "10.2.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "xai-testnet-vpc-asia"
  }
}

# Security Group for blockchain nodes
resource "aws_security_group" "blockchain_node" {
  name        = "xai-blockchain-node-sg"
  description = "Security group for XAI blockchain nodes"
  vpc_id      = module.vpc_primary.vpc_id

  # P2P networking
  ingress {
    from_port   = 8333
    to_port     = 8333
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "P2P blockchain communication"
  }

  # API endpoint
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "REST API"
  }

  # Prometheus metrics
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [module.vpc_primary.vpc_cidr_block]
    description = "Prometheus metrics"
  }

  # SSH access (restrict to your IP in production)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_ips
    description = "SSH access"
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "xai-blockchain-node-sg"
  }
}

# Launch template for blockchain nodes
resource "aws_launch_template" "blockchain_node" {
  name_prefix   = "xai-node-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  # Security groups moved to network_interfaces block (DEFECT-008)

  iam_instance_profile {
    name = aws_iam_instance_profile.blockchain_node.name
  }

  # Enable spot instances for cost savings
  instance_market_options {
    market_type = var.enable_spot_instances ? "spot" : null

    dynamic "spot_options" {
      for_each = var.enable_spot_instances ? [1] : []
      content {
        max_price = var.spot_price
      }
    }
  }

  # DEFECT-008 FIX: Enable public IP for SSM access
  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination      = true
    device_index               = 0
    security_groups            = [aws_security_group.blockchain_node.id]
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    node_name = "primary-node"
    region    = var.primary_region
  }))

  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size           = 50
      volume_type           = "gp3"
      delete_on_termination = false  # Preserve blockchain data
      encrypted             = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name = "xai-blockchain-node"
    }
  }
}

# Auto Scaling Group for nodes in primary region
resource "aws_autoscaling_group" "blockchain_nodes_primary" {
  name                = "xai-nodes-primary-asg"
  vpc_zone_identifier = module.vpc_primary.public_subnets
  desired_capacity    = 2
  min_size            = 2
  max_size            = 4

  launch_template {
    id      = aws_launch_template.blockchain_node.id
    version = "$Latest"
  }

  # FIX DEFECT-001: Register instances with load balancer target group
  target_group_arns = [aws_lb_target_group.api.arn]

  # FIX DEFECT-001: Use ELB health checks instead of EC2
  health_check_type         = "ELB"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "xai-node-primary"
    propagate_at_launch = true
  }

  tag {
    key                 = "NodeType"
    value               = "blockchain"
    propagate_at_launch = true
  }
}

# Application Load Balancer for API traffic
resource "aws_lb" "api" {
  name               = "xai-api-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc_primary.public_subnets

  enable_deletion_protection = false

  tags = {
    Name = "xai-api-lb"
  }
}

resource "aws_lb_target_group" "api" {
  name     = "xai-api-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = module.vpc_primary.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "xai-api-tg"
  }
}

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# Security group for ALB
resource "aws_security_group" "alb" {
  name_prefix = "xai-alb-sg-"
  vpc_id      = module.vpc_primary.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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

# IAM role for EC2 instances
resource "aws_iam_role" "blockchain_node" {
  name = "xai-blockchain-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_instance_profile" "blockchain_node" {
  name = "xai-blockchain-node-profile"
  role = aws_iam_role.blockchain_node.name
}

# Attach policies for CloudWatch, SSM, and S3
resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.blockchain_node.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.blockchain_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# FIX DEFECT-002: Add S3 access for deployment artifacts
resource "aws_iam_role_policy" "s3_deployment_access" {
  name = "xai-s3-deployment-access"
  role = aws_iam_role.blockchain_node.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::xai-testnet-deploy-artifacts-*",
          "arn:aws:s3:::xai-testnet-deploy-artifacts-*/*"
        ]
      }
    ]
  })
}

# Data source for latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# CloudWatch Billing Alarm
resource "aws_cloudwatch_metric_alarm" "billing_alarm" {
  alarm_name          = "xai-testnet-billing-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "21600"  # 6 hours
  statistic           = "Maximum"
  threshold           = "100"
  alarm_description   = "Alert when AWS charges exceed $100"
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name = "xai-testnet-billing-alarm"
  }
}

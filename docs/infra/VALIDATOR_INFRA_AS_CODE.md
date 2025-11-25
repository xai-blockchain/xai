# Validator Infrastructure-as-Code Samples

These IaC snippets show how to provision hardened validator nodes with Terraform (AWS / Azure / GCP variants) and then wire in configuration via Ansible or shell scripts. They map back to the governance and monitoring controls documented in `docs/architecture/CONSENSUS_NETWORK_SPEC.md`, `docs/runbooks/MULTI_NODE_HARNESS.md`, and `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`.

## Terraform sample (AWS)

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "validator_count" {
  type    = number
  default = 3
}

locals {
  validator_names = [
    for idx in range(var.validator_count) :
    format("xai-validator-%02d", idx + 1)
  ]
}

resource "aws_instance" "validators" {
  for_each = toset(local.validator_names)
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.medium"
  key_name      = var.ssh_key
  tags = {
    Name        = each.value
    Environment = var.environment
    Role        = "validator"
  }
  user_data = templatefile("${path.module}/bootstrap.sh.tpl", {
    node_name   = each.value
    data_dir    = "/var/lib/xai/${each.value}"
    github_ref  = "main"
    api_keys    = fileexists("bootstrap-api-keys.json") ? file("bootstrap-api-keys.json") : ""
  })
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_security_group" "validator_sg" {
  name        = "xai-validator-sg"
  description = "Allow HTTP/8545, P2P/30303, Prometheus/9100"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 30303
    to_port     = 30303
    protocol    = "tcp"
    cidr_blocks = var.p2p_cidrs
  }

  ingress {
    from_port   = 8545
    to_port     = 8545
    protocol    = "tcp"
    cidr_blocks = var.api_cidrs
  }

  ingress {
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    cidr_blocks = var.monitoring_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

Include `/bootstrap.sh.tpl` to install dependencies, clone the repo, configure `APIKeyStore`, and register each node with the downloader script described in `docs/runbooks/MULTI_NODE_HARNESS.md`.

## Ansible/CLI configuration tip

After instances launch, run an Ansible playbook (`ansible/playbooks/validator.yml` or similar) that:

- copies `config/*.yaml` from the repo
- populates `/etc/systemd/system/xai-node.service`
- enables Prometheus/Node Exporter (see `monitoring/README.md`)
- registers `/admin/api-keys` via `scripts/tools/manage_api_keys.py`

The Ansible inventory can be generated from the Terraform output (`terraform output validators`). Use `ansible.cfg` to push the same API key rotation/playbooks referenced in `SECURITY_AUDIT_CHECKLIST.md`.

## Verification

- Run `scripts/tools/verify_monitoring.py` after deployment to ensure Grafana dashboards and Prometheus scrape targets exist.
- Use `scripts/tools/multi_node_harness.py` to confirm peer propagation and faucet claims across the provisioned nodes.
- Capture a state snapshot right after deployment with `scripts/tools/state_snapshot.py` per `docs/runbooks/STATE_SNAPSHOT_RUNBOOK.md`.

## References

- `docs/architecture/CONSENSUS_NETWORK_SPEC.md`
- `docs/runbooks/MULTI_NODE_HARNESS.md`
- `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`

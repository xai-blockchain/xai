terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = "Droplet size"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "volume_size" {
  description = "Block storage volume size in GB"
  type        = number
  default     = 100
}

variable "network_mode" {
  description = "XAI network mode (testnet or mainnet)"
  type        = string
  default     = "testnet"
}

variable "ssh_keys" {
  description = "List of SSH key fingerprints"
  type        = list(string)
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_droplet" "xai_node" {
  name     = "xai-blockchain-node"
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-22-04-x64"
  ssh_keys = var.ssh_keys

  user_data = <<-EOF
              #!/bin/bash
              set -e

              # Update system
              apt-get update
              apt-get upgrade -y

              # Install Docker
              curl -fsSL https://get.docker.com -o get-docker.sh
              sh get-docker.sh
              systemctl enable docker
              systemctl start docker

              # Install Docker Compose
              curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              chmod +x /usr/local/bin/docker-compose

              # Clone XAI
              apt-get install -y git
              mkdir -p /opt/xai
              cd /opt/xai
              git clone https://github.com/xai-blockchain/xai.git .

              # Wait for volume mount
              sleep 10

              # Configure data directory on volume
              if [ -d /mnt/xai_data ]; then
                mkdir -p /mnt/xai_data/{data,logs}
                ln -s /mnt/xai_data/data /opt/xai/data
                ln -s /mnt/xai_data/logs /opt/xai/logs
              fi

              # Configure environment
              cat > /opt/xai/.env <<ENVEOF
              XAI_NETWORK=${var.network_mode}
              XAI_ENV=production
              XAI_API_PORT=8080
              XAI_NODE_PORT=8333
              XAI_METRICS_PORT=9090
              XAI_DATA_DIR=/opt/xai/data
              XAI_LOG_DIR=/opt/xai/logs
              POSTGRES_PASSWORD=$(openssl rand -hex 32)
              ENVEOF

              # Start node
              cd /opt/xai/docker/testnet
              docker-compose -f docker-compose.one-node.yml up -d

              # Setup systemd service
              cat > /etc/systemd/system/xai-node.service <<SERVICEEOF
              [Unit]
              Description=XAI Blockchain Node
              After=docker.service
              Requires=docker.service

              [Service]
              Type=oneshot
              RemainAfterExit=yes
              WorkingDirectory=/opt/xai/docker/testnet
              ExecStart=/usr/local/bin/docker-compose -f docker-compose.one-node.yml up -d
              ExecStop=/usr/local/bin/docker-compose -f docker-compose.one-node.yml down

              [Install]
              WantedBy=multi-user.target
              SERVICEEOF

              systemctl daemon-reload
              systemctl enable xai-node

              # Configure firewall
              ufw allow 22/tcp
              ufw allow 8080/tcp
              ufw allow 8333/tcp
              ufw allow 9090/tcp
              ufw allow 3000/tcp
              ufw --force enable

              echo "XAI Node deployed successfully"
              EOF

  tags = ["xai-node", "blockchain"]
}

resource "digitalocean_volume" "xai_data" {
  region                  = var.region
  name                    = "xai-node-data"
  size                    = var.volume_size
  initial_filesystem_type = "ext4"
  description             = "XAI blockchain data volume"
}

resource "digitalocean_volume_attachment" "xai_data_attachment" {
  droplet_id = digitalocean_droplet.xai_node.id
  volume_id  = digitalocean_volume.xai_data.id
}

resource "digitalocean_firewall" "xai_node" {
  name = "xai-node-firewall"

  droplet_ids = [digitalocean_droplet.xai_node.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8333"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "9090"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "3000"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

output "droplet_id" {
  value       = digitalocean_droplet.xai_node.id
  description = "Droplet ID"
}

output "droplet_ip" {
  value       = digitalocean_droplet.xai_node.ipv4_address
  description = "Droplet public IP address"
}

output "api_url" {
  value       = "http://${digitalocean_droplet.xai_node.ipv4_address}:8080"
  description = "XAI API endpoint"
}

output "explorer_url" {
  value       = "http://${digitalocean_droplet.xai_node.ipv4_address}:3000"
  description = "Block Explorer URL"
}

output "ssh_command" {
  value       = "ssh root@${digitalocean_droplet.xai_node.ipv4_address}"
  description = "SSH command to connect"
}

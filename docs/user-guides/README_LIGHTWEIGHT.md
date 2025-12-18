# XAI Lightweight Node Documentation

Comprehensive documentation for running XAI nodes on resource-constrained devices.

## Documentation Index

### Main Guides

1. **[Lightweight Node Guide](LIGHTWEIGHT_NODE_GUIDE.md)** - Complete guide for all lightweight node modes
   - Light client, pruned node, and full node configurations
   - Platform-specific setup (Raspberry Pi, VPS, NAS, mobile)
   - Performance tuning and optimization
   - Monitoring and troubleshooting

2. **[Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md)** - Step-by-step Raspberry Pi installation
   - Hardware requirements and recommendations
   - OS installation and system configuration
   - XAI node installation and setup
   - Systemd service configuration
   - Performance optimization and monitoring

3. **[Quick Reference Card](LIGHTWEIGHT_NODE_QUICK_REFERENCE.md)** - Commands and configurations at a glance
   - Quick start commands for each mode
   - Essential environment variables
   - Common operations and troubleshooting
   - Monitoring commands

## Quick Navigation

### By Hardware

- **Raspberry Pi** → [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)
- **VPS/Cloud** → [LIGHTWEIGHT_NODE_GUIDE.md](LIGHTWEIGHT_NODE_GUIDE.md#low-memory-vps-1gb-ram)
- **NAS/Docker** → [LIGHTWEIGHT_NODE_GUIDE.md](LIGHTWEIGHT_NODE_GUIDE.md#docker-on-synologyqnab-nas)
- **Mobile** → [LIGHTWEIGHT_NODE_GUIDE.md](LIGHTWEIGHT_NODE_GUIDE.md#light-client-mode-minimal-resources)

### By Resource Availability

- **256MB RAM** → Light Client Mode
- **512MB-1GB RAM** → Pruned Node Mode
- **2GB+ RAM** → Full Node Mode

### By Use Case

- **Mobile Wallet** → Light Client
- **Payment Verification** → Light Client or Pruned Node
- **Home Node** → Pruned Node on Raspberry Pi
- **Validator** → Full Node
- **Exchange** → Full Node

## Getting Started

1. **Determine your hardware** and choose the appropriate node mode
2. **Follow the platform-specific guide** (Raspberry Pi or general lightweight guide)
3. **Keep the quick reference** handy for common operations
4. **Monitor your node** using the provided monitoring commands

## Node Mode Selection Guide

```
Have < 512MB RAM? → Light Client
Have 512MB-2GB RAM? → Pruned Node
Have 2GB+ RAM? → Full Node

Using Raspberry Pi? → See RASPBERRY_PI_SETUP.md
Using VPS/Cloud? → See LIGHTWEIGHT_NODE_GUIDE.md
Using Docker/NAS? → See LIGHTWEIGHT_NODE_GUIDE.md
```

## Support

- General documentation: [../index.md](../index.md)
- Troubleshooting: [troubleshooting.md](troubleshooting.md)
- API documentation: [../api/README.md](../api/README.md)

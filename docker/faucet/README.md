# XAI Testnet Faucet - Docker Setup

Web-based interface for requesting testnet XAI tokens.

## Quick Start

```bash
# Navigate to faucet directory
cd /home/hudson/blockchain-projects/xai/docker/faucet

# (Optional) Copy and customize environment variables
cp .env.example .env

# Start the faucet
docker-compose up -d

# Access at http://localhost:8086
```

## Prerequisites

- Docker and Docker Compose installed
- XAI testnet node running (or access to remote node)
- Port 8086 available

## Configuration

Edit `.env` file or set environment variables:

```bash
# XAI Node API URL (default: http://host.docker.internal:18545)
XAI_API_URL=http://your-node-url:18545

# Faucet web UI port (default: 8086)
FAUCET_PORT=8086

# Amount per request (default: 100 XAI)
FAUCET_AMOUNT=100

# Cooldown in seconds (default: 3600 = 1 hour)
FAUCET_COOLDOWN=3600
```

## Usage

### Start Faucet

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop Faucet

```bash
docker-compose down
```

### Rebuild Container

```bash
docker-compose up -d --build
```

## Accessing the Faucet

Once running, open your browser to:

**http://localhost:8086**

Enter a TXAI address and click "Request Tokens" to receive 100 testnet XAI.

## Troubleshooting

### "Cannot connect to XAI node"

- Ensure your XAI node is running
- Check `XAI_API_URL` points to correct node
- For local node, use `http://host.docker.internal:18545`

### Port already in use

Change `FAUCET_PORT` in `.env`:

```bash
FAUCET_PORT=8087
```

Then restart: `docker-compose down && docker-compose up -d`

### Rate limit errors

Default cooldown is 1 hour. You can adjust in `.env`:

```bash
FAUCET_COOLDOWN=1800  # 30 minutes
```

## Network Configuration

The faucet connects to the `xai-testnet` Docker network. If this network doesn't exist, create it:

```bash
docker network create xai-testnet
```

Or remove the `external: true` line from `docker-compose.yml`.

## Health Check

```bash
curl http://localhost:8086/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T12:34:56.789Z"
}
```

## Related Documentation

- [Complete Faucet Guide](../../docs/user-guides/TESTNET_FAUCET.md)
- [Testnet Guide](../../docs/user-guides/TESTNET_GUIDE.md)
- [Quick Start](../../docs/QUICK_START.md)

# XAI Blockchain - Network Configuration

**IMPORTANT:** All network settings are fully configurable. No hardcoded defaults in production code.

---

## Configuration Methods

### Method 1: Environment Variables (Recommended for Production)

```bash
# Linux/Mac
export XAI_HOST="0.0.0.0"
export XAI_PORT="8545"
python core/node.py

# Windows
set XAI_HOST=0.0.0.0
set XAI_PORT=8545
python core/node.py
```

### Method 2: Command Line Arguments

```bash
python core/node.py --host 0.0.0.0 --port 8545
```

### Method 3: Configuration File

```bash
# Copy example config
cp config.example.json config.json

# Edit config.json with your settings
# Then load in your application
```

---

## Default Behavior

If no configuration is provided:
- **Host:** `0.0.0.0` (binds to all interfaces)
- **Port:** `8545`

**Note:** These are industry-standard blockchain defaults and do not reveal identifying information.

---

## Anonymity & Security Recommendations

### For Maximum Anonymity:

1. **Run Behind Tor Hidden Service**
   ```bash
   # /etc/tor/torrc
   HiddenServiceDir /var/lib/tor/xai/
   HiddenServicePort 80 127.0.0.1:8545
   ```

2. **Bind to Localhost Only (if not using Tor)**
   ```bash
   export XAI_HOST="127.0.0.1"
   python core/node.py
   ```

3. **Use Non-Standard Port**
   ```bash
   export XAI_PORT="9876"  # Custom port
   python core/node.py
   ```

4. **Firewall Rules**
   ```bash
   # Linux: Restrict access
   iptables -A INPUT -p tcp --dport 8545 -s 127.0.0.1 -j ACCEPT
   iptables -A INPUT -p tcp --dport 8545 -j DROP
   ```

---

## Production Deployment Examples

### Example 1: Public Node (Community Infrastructure)

```bash
# Accessible to other nodes
export XAI_HOST="0.0.0.0"
export XAI_PORT="8545"
export XAI_MINER="XAI1a2b3c..."
python core/node.py
```

### Example 2: Private Node (Local Development)

```bash
# Only accessible locally
export XAI_HOST="127.0.0.1"
export XAI_PORT="8545"
python core/node.py
```

### Example 3: Tor Hidden Service Node (Maximum Anonymity)

```bash
# Bind to localhost, accessible via Tor
export XAI_HOST="127.0.0.1"
export XAI_PORT="8545"

# Tor configuration (/etc/tor/torrc):
# HiddenServiceDir /var/lib/tor/xai/
# HiddenServicePort 80 127.0.0.1:8545

python core/node.py
```

### Example 4: Docker Container

```dockerfile
# Dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Environment variables
ENV XAI_HOST=0.0.0.0
ENV XAI_PORT=8545

CMD ["python", "core/node.py"]
```

```bash
# Run container
docker run -e XAI_HOST=0.0.0.0 -e XAI_PORT=8545 -p 8545:8545 xai-blockchain
```

---

## Network Topology Options

### 1. Standalone Node (No Peers)

```bash
python core/node.py
# No peer connections
```

### 2. Connected Node (With Peers)

```bash
python core/node.py --peers http://peer1:8545 http://peer2:8545
```

### 3. Mining Node

```bash
python core/node.py --miner XAI1a2b3c...
```

### 4. Full Node (Mining + Peers)

```bash
python core/node.py \
  --host 0.0.0.0 \
  --port 8545 \
  --miner XAI1a2b3c... \
  --peers http://peer1:8545 http://peer2:8545
```

---

## Understanding Network Settings

### Host Configuration

| Value | Meaning | Use Case |
|-------|---------|----------|
| `0.0.0.0` | Bind to all interfaces | Public node, accessible from network |
| `127.0.0.1` | Localhost only | Private node, local development |
| `192.168.x.x` | Specific network interface | LAN-only access |

### Port Configuration

| Port | Standard | Notes |
|------|----------|-------|
| `8545` | Ethereum standard | Common default, may be scanned |
| `30303` | Alternative | Less common, more private |
| `1024-65535` | Any custom port | Best for anonymity |

---

## Security Considerations

### ⚠️ Public Node Risks

If you run `0.0.0.0:8545`:
- Node is accessible from internet
- Port may be scanned
- IP address is visible to peers
- **Recommendation:** Use Tor hidden service

### ✅ Private Node Benefits

If you run `127.0.0.1:8545`:
- Only accessible locally
- Not exposed to internet
- Can still connect to peers via Tor
- **Recommendation:** Best for anonymity

### 🔒 Tor Hidden Service (Maximum Anonymity)

```
Your Node (127.0.0.1:8545)
    ↓
Tor Network
    ↓
.onion Address
    ↓
Other Tor-Connected Nodes
```

**Benefits:**
- IP address never revealed
- Geographic location hidden
- Censorship resistant
- End-to-end encrypted

---

## Troubleshooting

### "Address already in use"

```bash
# Port 8545 is busy
# Solution: Use different port
export XAI_PORT="9545"
python core/node.py
```

### "Permission denied" (Port < 1024)

```bash
# Ports below 1024 require root
# Solution 1: Use sudo (not recommended)
sudo python core/node.py --port 80

# Solution 2: Use higher port
python core/node.py --port 8545
```

### Can't connect to peers

```bash
# Check firewall
# Linux:
sudo iptables -L

# Mac:
sudo pfctl -s rules

# Windows:
netsh advfirewall firewall show rule name=all
```

---

## Integration with Personal AI

When using Personal AI features:

```python
from integrate_ai_systems import IntegratedXAINode

# Custom network configuration
node = IntegratedXAINode(
    host="127.0.0.1",  # Localhost only
    port=9876          # Custom port
)

node.run()
```

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_HOST` | `0.0.0.0` | Network interface to bind |
| `XAI_PORT` | `8545` | Port to listen on |

**Example `.env` file:**
```bash
XAI_HOST=127.0.0.1
XAI_PORT=8545
```

---

## Best Practices

### For Node Operators

1. ✅ Use environment variables in production
2. ✅ Run behind Tor for anonymity
3. ✅ Use firewall rules
4. ✅ Change default port if public
5. ✅ Monitor connection logs

### For Developers

1. ✅ Never hardcode IP addresses in code
2. ✅ Always use environment variables
3. ✅ Provide config.example.json
4. ✅ Document all network settings
5. ✅ Test with different configurations

---

## Summary

- **No hardcoded IPs:** All network settings are configurable
- **Environment variables:** Recommended for production
- **Tor support:** Maximum anonymity configuration
- **Flexible deployment:** Local, public, or hidden service
- **No identifying information:** Standard blockchain defaults

**For anonymous operation, always use Tor hidden service configuration.**

---

**See also:**
- `config.example.json` - Configuration template
- `ANONYMITY_COMPLIANCE_AUDIT.md` - Security guidelines
- `GITHUB_UPLOAD_GUIDE.md` - Anonymous deployment

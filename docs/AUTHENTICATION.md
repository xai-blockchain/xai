# XAI Blockchain API Authentication Guide

Complete guide for authenticating with the XAI Blockchain API.

## Table of Contents

- [Authentication Methods](#authentication-methods)
- [API Keys](#api-keys)
- [JWT Tokens](#jwt-tokens)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Authentication Methods

The XAI Blockchain API supports two authentication methods:

### 1. API Key Authentication

**Method**: Header-based authentication using API key

**Header Name**: `X-API-Key`

**Example:**
```bash
curl -H "X-API-Key: your-api-key" \
  https://api.xai-blockchain.io/wallet/balance
```

**Python SDK:**
```python
from xai_sdk import XAIClient

client = XAIClient(api_key="your-api-key")
```

### 2. JWT Bearer Token

**Method**: Bearer token authentication using JWT

**Header Name**: `Authorization`

**Format**: `Bearer <token>`

**Example:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  https://api.xai-blockchain.io/wallet/balance
```

**Python SDK:**
```python
import requests

headers = {
    "Authorization": "Bearer your-jwt-token"
}

response = requests.get(
    "https://api.xai-blockchain.io/wallet/balance",
    headers=headers
)
```

---

## API Keys

### Obtaining an API Key

1. **Create Account**
   - Visit https://xai-blockchain.io
   - Sign up for an account

2. **Navigate to API Settings**
   - Log in to your account
   - Go to Settings > API Keys

3. **Generate API Key**
   - Click "Generate New Key"
   - Choose key permissions:
     - Read (wallet, transaction, blockchain data)
     - Write (send transactions, create proposals)
     - Admin (manage API keys, settings)
   - Click "Create"

4. **Copy and Store**
   - Copy the API key immediately
   - Store it securely (never commit to version control)

### API Key Permissions

| Permission | Endpoints | Description |
|---|---|---|
| read | GET endpoints | Read-only access to blockchain data |
| write | POST endpoints | Ability to send transactions, create proposals |
| admin | Settings endpoints | Manage API keys and account settings |

### API Key Best Practices

```python
import os
from xai_sdk import XAIClient

# Load API key from environment variable
api_key = os.environ.get("XAI_API_KEY")

if not api_key:
    raise ValueError("XAI_API_KEY environment variable not set")

# Initialize client
client = XAIClient(api_key=api_key)
```

### Environment Variable Setup

**Linux/macOS:**
```bash
export XAI_API_KEY="your-api-key"
```

**Windows (PowerShell):**
```powershell
$env:XAI_API_KEY="your-api-key"
```

**Windows (Command Prompt):**
```cmd
set XAI_API_KEY=your-api-key
```

**.env File:**
```
XAI_API_KEY=your-api-key
```

**Python (.env file loader):**
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("XAI_API_KEY")
```

### API Key Rotation

**Rotate your API key periodically:**

1. Generate a new API key
2. Update applications to use the new key
3. Wait 24 hours for propagation
4. Deactivate the old key
5. Delete after 30 days

---

## JWT Tokens

### Obtaining a JWT Token

**Endpoint**: `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.org",
  "password": "your-password"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Python Example:**
```python
import requests

response = requests.post(
    "https://api.xai-blockchain.io/auth/login",
    json={
        "email": "user@example.org",
        "password": "your-password"
    }
)

data = response.json()
access_token = data["token"]
expires_in = data["expires_in"]
refresh_token = data["refresh_token"]

print(f"Token expires in {expires_in} seconds")
```

### Using JWT Token

```python
from xai_sdk import XAIClient
import requests

# Get token first
login_response = requests.post(
    "https://api.xai-blockchain.io/auth/login",
    json={
        "email": "user@example.org",
        "password": "your-password"
    }
)

token = login_response.json()["token"]

# Create client with Authorization header
headers = {"Authorization": f"Bearer {token}"}

# Or use directly with requests
response = requests.get(
    "https://api.xai-blockchain.io/wallet/balance",
    headers=headers
)
```

### Token Refresh

**Endpoint**: `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "your-refresh-token"
}
```

**Python Example:**
```python
def refresh_token(refresh_token):
    response = requests.post(
        "https://api.xai-blockchain.io/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    return response.json()["token"]

# Use refresh token before expiration
new_token = refresh_token(refresh_token)
```

### Token Expiration Handling

```python
import requests
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None
        self.expires_at = None
    
    def get_token(self):
        """Get valid token, refreshing if necessary."""
        # Check if token is expired or about to expire
        if self.token and self.expires_at and datetime.now() < self.expires_at:
            return self.token
        
        # Refresh or login
        if self.refresh_token:
            self._refresh()
        else:
            self._login()
        
        return self.token
    
    def _login(self):
        """Authenticate and get new token."""
        response = requests.post(
            "https://api.xai-blockchain.io/auth/login",
            json={
                "email": self.email,
                "password": self.password
            }
        )
        data = response.json()
        self.token = data["token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
    
    def _refresh(self):
        """Refresh token using refresh token."""
        response = requests.post(
            "https://api.xai-blockchain.io/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        data = response.json()
        self.token = data["token"]
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])

# Usage
token_mgr = TokenManager("user@example.org", "password")
token = token_mgr.get_token()  # Auto-refreshes if needed
```

---

## Security Best Practices

### 1. Never Commit Credentials

**Bad:**
```python
# DON'T DO THIS
client = XAIClient(api_key="sk_live_abc123def456")
```

**Good:**
```python
import os
api_key = os.environ.get("XAI_API_KEY")
client = XAIClient(api_key=api_key)
```

### 2. Use Environment Variables

**Setup:**
```bash
# .env
XAI_API_KEY=sk_live_abc123def456
```

**Load:**
```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ.get("XAI_API_KEY")
```

### 3. Rotate API Keys Regularly

```python
# Rotate keys every 90 days
rotation_interval = 90  # days

# Check last rotation date
import datetime
last_rotation = datetime.datetime(2024, 1, 15)
days_since_rotation = (datetime.datetime.now() - last_rotation).days

if days_since_rotation > rotation_interval:
    print("API key should be rotated")
```

### 4. Use HTTPS Only

```python
# Always use HTTPS in production
client = XAIClient(
    base_url="https://api.xai-blockchain.io",  # Not http://
    api_key=api_key
)
```

### 5. Restrict Key Scope

- Create separate keys for different environments
- Use least privilege principle
- Only enable required permissions

### 6. Monitor API Usage

```python
# Log all API requests
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("xai_sdk")

# This will log all requests
client = XAIClient(api_key=api_key)
```

### 7. Secure Token Storage

```python
import keyring

# Store token securely
def store_token(service, username, token):
    keyring.set_password(service, username, token)

# Retrieve token
def get_token(service, username):
    return keyring.get_password(service, username)

# Usage
store_token("xai_blockchain", "user@example.org", token)
token = get_token("xai_blockchain", "user@example.org")
```

### 8. Rate Limiting

```python
from xai_sdk import RateLimitError
import time

def call_api_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or 60
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

# Usage
def get_balance():
    return client.wallet.get_balance("0x...")

balance = call_api_with_retry(get_balance)
```

---

## Troubleshooting

### Invalid API Key

**Error:**
```
AuthenticationError: [401] Invalid API key
```

**Solutions:**
1. Verify API key is correct
2. Check environment variable is set
3. Ensure API key hasn't been revoked
4. Generate a new API key

### Token Expired

**Error:**
```
AuthenticationError: [401] Token expired
```

**Solutions:**
1. Refresh the token using refresh token
2. Re-authenticate to get new token
3. Implement automatic token refresh

### Missing Authorization Header

**Error:**
```
AuthenticationError: [401] Missing authorization header
```

**Solutions:**
```python
# Ensure header is being sent
headers = {
    "X-API-Key": "your-api-key",  # or
    "Authorization": "Bearer your-token"
}

response = requests.get(
    "https://api.xai-blockchain.io/wallet/balance",
    headers=headers
)
```

### Rate Limited

**Error:**
```
RateLimitError: [429] Rate limit exceeded
```

**Solutions:**
1. Wait for `Retry-After` seconds
2. Upgrade to higher tier API plan
3. Implement exponential backoff

### Authentication Timeout

**Error:**
```
TimeoutError: Request timeout after 30s
```

**Solutions:**
```python
# Increase timeout
client = XAIClient(
    api_key=api_key,
    timeout=60  # 60 seconds instead of 30
)
```

### CORS Issues (Browser)

**Error:**
```
CORS policy: No 'Access-Control-Allow-Origin'
```

**Solutions:**
- Use backend server to proxy API requests
- Server-side code doesn't have CORS restrictions
- Use HTTPS in production

```python
# Server-side proxy example (Flask)
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/api/balance/<address>')
def get_balance(address):
    response = requests.get(
        f"https://api.xai-blockchain.io/wallet/{address}/balance",
        headers={"X-API-Key": os.environ["XAI_API_KEY"]}
    )
    return response.json()
```

---

## Support

For authentication issues:
- **Email**: support@xai-blockchain.io
- **Discord**: https://discord.gg/xai-blockchain
- **Documentation**: https://docs.xai-blockchain.io

#!/usr/bin/env python3
"""
XAI Testnet Faucet
Provides free testnet tokens for development purposes
"""

import os
import time
import logging
import re
import ipaddress
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
from collections import defaultdict
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
XAI_API_URL = os.getenv('XAI_API_URL', 'http://xai-testnet-bootstrap:8080')
XAI_API_KEY = os.getenv('XAI_API_KEY', '').strip()
XAI_FAUCET_PATH = os.getenv('XAI_FAUCET_PATH', '/api/faucet')
XAI_TRANSFER_PATH = os.getenv('XAI_TRANSFER_PATH', '/transfer')
FAUCET_SENDER = os.getenv('FAUCET_SENDER', '').strip()
FAUCET_PORT = int(os.getenv('FAUCET_PORT', '8086'))
FAUCET_AMOUNT = float(os.getenv('FAUCET_AMOUNT', '100'))
FAUCET_COOLDOWN = int(os.getenv('FAUCET_COOLDOWN', '3600'))  # 1 hour in seconds
FAUCET_ENV = os.getenv('FAUCET_ENV', 'development').strip().lower()
XAI_NETWORK = os.getenv('XAI_NETWORK', 'testnet').strip().lower()
FAUCET_ALLOW_MAINNET = os.getenv('FAUCET_ALLOW_MAINNET', '0') == '1'
REQUIRE_CAPTCHA_IN_PROD = os.getenv('REQUIRE_CAPTCHA_IN_PROD', '1') == '1'

# IP rate limiting (additional anti-abuse)
FAUCET_IP_COOLDOWN = int(os.getenv('FAUCET_IP_COOLDOWN', '600'))  # 10 minutes
FAUCET_IP_MAX_PER_WINDOW = int(os.getenv('FAUCET_IP_MAX_PER_WINDOW', '5'))
FAUCET_IP_WINDOW = int(os.getenv('FAUCET_IP_WINDOW', '3600'))  # 1 hour

# Access control configuration (devnet-friendly)
FAUCET_MAX_BALANCE = float(os.getenv('FAUCET_MAX_BALANCE', '0') or 0)
FAUCET_ALLOWED_ADDRESSES = [
    entry.strip() for entry in os.getenv('FAUCET_ALLOWED_ADDRESSES', '').split(',')
    if entry.strip()
]
FAUCET_ALLOWED_IPS = [
    entry.strip() for entry in os.getenv('FAUCET_ALLOWED_IPS', '').split(',')
    if entry.strip()
]

_captcha_override = os.getenv('FAUCET_REQUIRE_CAPTCHA', '').strip().lower()
if _captcha_override:
    CAPTCHA_REQUIRED = _captcha_override in ('1', 'true', 'yes', 'y', 'on')
else:
    CAPTCHA_REQUIRED = FAUCET_ENV == 'production' and REQUIRE_CAPTCHA_IN_PROD

# Address prefix validation
ALLOWED_PREFIXES = os.getenv(
    'FAUCET_ALLOWED_PREFIXES',
    'TXAI' if XAI_NETWORK != 'mainnet' else 'XAI'
).split(',')
ALLOWED_PREFIXES = [prefix.strip().upper() for prefix in ALLOWED_PREFIXES if prefix.strip()]
if not ALLOWED_PREFIXES:
    ALLOWED_PREFIXES = ['TXAI']
ADDRESS_REGEX = re.compile(r'^(' + '|'.join(ALLOWED_PREFIXES) + r')[0-9a-fA-F]{40}$')

# hCaptcha configuration (optional)
HCAPTCHA_SITE_KEY = os.getenv('HCAPTCHA_SITE_KEY', '')
HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY', '')
HCAPTCHA_ENABLED = bool(HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET_KEY)

# Redis configuration (optional)
REDIS_URL = os.getenv('REDIS_URL', '')

# Storage backends
redis_client = None
request_history = {}  # Fallback in-memory storage
ip_history = {}  # IP cooldown tracking
ip_window_history = {}  # IP window tracking (start_ts, count)
stats = {
    'total_requests': 0,
    'unique_addresses': set(),
    'start_time': time.time()
}

# Initialize Redis if available
if REDIS_URL:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
    except ImportError:
        logger.warning("Redis URL provided but redis package not installed. Install with: pip install redis")
        redis_client = None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory storage.")
        redis_client = None
else:
    logger.info("Redis URL not configured. Using in-memory storage for rate limits.")

# HTML template
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>XAI Testnet Faucet</title>
    {% if hcaptcha_enabled %}
    <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
    {% endif %}
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #45a049; }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .h-captcha { margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>XAI Testnet Faucet</h1>
        <div class="info message">
            <p>Get {{ amount }} testnet XAI tokens for development.</p>
            <p>Cooldown: {{ cooldown }} seconds between requests.</p>
            <p>IP limit: max {{ ip_max_per_window }} requests per {{ ip_window }} seconds (cooldown {{ ip_cooldown }}s).</p>
            {% if max_balance and max_balance > 0 %}
            <p>Eligibility: balances below {{ max_balance }} XAI.</p>
            {% endif %}
            <p>Testnet only. Do not reuse mainnet keys. Balances may reset.</p>
        </div>
        <form id="faucetForm">
            <input type="text" id="address" placeholder="Enter your XAI address" required>
            {% if hcaptcha_enabled %}
            <div class="h-captcha" data-sitekey="{{ hcaptcha_sitekey }}"></div>
            {% endif %}
            <button type="submit">Request Tokens</button>
        </form>
        <div id="result"></div>
    </div>
    <script>
        document.getElementById('faucetForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const address = document.getElementById('address').value;
            const resultDiv = document.getElementById('result');

            // Get hCaptcha response if enabled
            let captchaResponse = '';
            {% if hcaptcha_enabled %}
            captchaResponse = hcaptcha.getResponse();
            if (!captchaResponse) {
                resultDiv.innerHTML = '<div class="error message">Please complete the CAPTCHA</div>';
                return;
            }
            {% endif %}

            resultDiv.innerHTML = '<div class="info message">Processing...</div>';

            try {
                const response = await fetch('/api/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ address, captcha: captchaResponse })
                });

                const data = await response.json();

                if (data.success) {
                    resultDiv.innerHTML = `<div class="success message">${data.message}</div>`;
                    {% if hcaptcha_enabled %}
                    hcaptcha.reset();
                    {% endif %}
                } else {
                    resultDiv.innerHTML = `<div class="error message">${data.error}</div>`;
                    {% if hcaptcha_enabled %}
                    hcaptcha.reset();
                    {% endif %}
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error message">Network error: ${error.message}</div>`;
            }
        });
    </script>
</body>
</html>
"""


def verify_hcaptcha(token: str) -> bool:
    """Verify hCaptcha token with hCaptcha API"""
    if not HCAPTCHA_ENABLED:
        return True

    if not token:
        return False

    try:
        response = requests.post(
            'https://hcaptcha.com/siteverify',
            data={
                'secret': HCAPTCHA_SECRET_KEY,
                'response': token
            },
            timeout=10
        )
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"hCaptcha verification failed: {e}")
        return False


def get_client_ip() -> str:
    """Resolve client IP with proxy headers."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    real_ip = request.headers.get('X-Real-IP', '').strip()
    if real_ip:
        return real_ip
    return request.remote_addr or ''


def address_allowed(address: str) -> bool:
    """Check address allowlist when configured."""
    if not FAUCET_ALLOWED_ADDRESSES:
        return True
    return address in FAUCET_ALLOWED_ADDRESSES


def ip_allowed(ip: str) -> bool:
    """Check IP allowlist (supports CIDR ranges) when configured."""
    if not FAUCET_ALLOWED_IPS:
        return True
    try:
        client_ip = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for allowed in FAUCET_ALLOWED_IPS:
        if '/' in allowed:
            try:
                network = ipaddress.ip_network(allowed, strict=False)
            except ValueError:
                continue
            if client_ip in network:
                return True
        elif allowed == ip:
            return True
    return False


def get_address_balance(address: str) -> float:
    """Fetch address balance from XAI API."""
    url = f"{XAI_API_URL.rstrip('/')}/balance/{address}"
    headers = {}
    if XAI_API_KEY:
        headers["X-API-Key"] = XAI_API_KEY
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data.get('balance', 0))


def check_ip_limit(ip: str) -> tuple[bool, int, str]:
    """Check IP cooldown and window rate limit. Returns (allowed, remaining, reason)."""
    if not ip:
        return True, 0, ''

    now = time.time()

    if redis_client:
        try:
            cooldown_key = f"faucet:cooldown:ip:{ip}"
            last_request_str = redis_client.get(cooldown_key)
            if last_request_str is not None:
                last_request = float(last_request_str)
                elapsed = now - last_request
                remaining = FAUCET_IP_COOLDOWN - elapsed
                if remaining > 0:
                    return False, int(remaining), 'ip_cooldown'

            window_key = f"faucet:window:ip:{ip}"
            window_count = int(redis_client.get(window_key) or 0)
            if window_count >= FAUCET_IP_MAX_PER_WINDOW:
                ttl = redis_client.ttl(window_key)
                remaining = ttl if ttl and ttl > 0 else FAUCET_IP_WINDOW
                return False, int(remaining), 'ip_rate'
        except Exception as e:
            logger.warning(f"Redis IP check failed, falling back to memory: {e}")

    # In-memory fallback
    last_request = ip_history.get(ip)
    if last_request is not None:
        elapsed = now - last_request
        remaining = FAUCET_IP_COOLDOWN - elapsed
        if remaining > 0:
            return False, int(remaining), 'ip_cooldown'

    window_start, count = ip_window_history.get(ip, (now, 0))
    if now - window_start > FAUCET_IP_WINDOW:
        window_start, count = now, 0
    if count >= FAUCET_IP_MAX_PER_WINDOW:
        remaining = FAUCET_IP_WINDOW - int(now - window_start)
        return False, max(remaining, 0), 'ip_rate'

    return True, 0, ''


def record_ip_request(ip: str) -> None:
    """Record IP request for cooldown and window limits."""
    if not ip:
        return

    now = time.time()
    ip_history[ip] = now

    if redis_client:
        try:
            cooldown_key = f"faucet:cooldown:ip:{ip}"
            redis_client.setex(cooldown_key, FAUCET_IP_COOLDOWN, str(now))

            window_key = f"faucet:window:ip:{ip}"
            count = redis_client.incr(window_key)
            if count == 1:
                redis_client.expire(window_key, FAUCET_IP_WINDOW)
        except Exception as e:
            logger.warning(f"Redis IP record failed: {e}")
        return

    window_start, count = ip_window_history.get(ip, (now, 0))
    if now - window_start > FAUCET_IP_WINDOW:
        window_start, count = now, 0
    ip_window_history[ip] = (window_start, count + 1)


def check_cooldown(address: str) -> tuple[bool, int]:
    """Check if address is in cooldown period. Uses Redis if available."""
    # Try Redis first
    if redis_client:
        try:
            key = f"faucet:cooldown:{address}"
            last_request_str = redis_client.get(key)
            if last_request_str is None:
                return True, 0

            last_request = float(last_request_str)
            elapsed = time.time() - last_request
            remaining = FAUCET_COOLDOWN - elapsed

            if remaining <= 0:
                return True, 0
            return False, int(remaining)
        except Exception as e:
            logger.warning(f"Redis check failed, falling back to memory: {e}")

    # Fallback to in-memory
    if address not in request_history:
        return True, 0

    last_request = request_history[address]
    elapsed = time.time() - last_request
    remaining = FAUCET_COOLDOWN - elapsed

    if remaining <= 0:
        return True, 0

    return False, int(remaining)


def is_valid_address(address: str) -> bool:
    """Validate address against allowed prefixes and length."""
    return bool(ADDRESS_REGEX.match(address))


def record_request(address: str) -> None:
    """Record a faucet request. Uses Redis if available."""
    current_time = time.time()

    # Always update in-memory for stats
    request_history[address] = current_time
    stats['total_requests'] += 1
    stats['unique_addresses'].add(address)

    # Also persist to Redis if available
    if redis_client:
        try:
            key = f"faucet:cooldown:{address}"
            redis_client.setex(key, FAUCET_COOLDOWN, str(current_time))

            # Update stats in Redis
            redis_client.incr("faucet:stats:total_requests")
            redis_client.sadd("faucet:stats:unique_addresses", address)
        except Exception as e:
            logger.warning(f"Redis write failed: {e}")


def send_tokens(address: str, amount: float) -> dict:
    """Send tokens to the specified address via XAI API."""
    faucet_url = f"{XAI_API_URL}{XAI_FAUCET_PATH}"
    transfer_url = f"{XAI_API_URL}{XAI_TRANSFER_PATH}"
    headers = {}
    if XAI_API_KEY:
        headers["X-API-Key"] = XAI_API_KEY
    payload = {"address": address}
    if not XAI_FAUCET_PATH.rstrip("/").endswith("/faucet/claim"):
        payload["amount"] = amount

    try:
        response = requests.post(
            faucet_url,
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code not in (404, 405):
            return {"success": False, "error": f"Faucet API error: {response.text}"}
    except Exception as e:
        logger.warning(f"Primary faucet API failed: {e}")

    if not FAUCET_SENDER:
        return {"success": False, "error": "Faucet sender not configured for transfer fallback"}

    try:
        response = requests.post(
            transfer_url,
            headers=headers,
            json={"from": FAUCET_SENDER, "to": address, "amount": amount},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return {"success": False, "error": f"Transfer API error: {response.text}"}
    except Exception as e:
        logger.error(f"Transfer fallback failed: {e}")
        return {"success": False, "error": str(e)}


@app.route('/')
def index():
    """Render faucet interface"""
    return render_template_string(
        TEMPLATE,
        amount=FAUCET_AMOUNT,
        cooldown=FAUCET_COOLDOWN,
        ip_max_per_window=FAUCET_IP_MAX_PER_WINDOW,
        ip_window=FAUCET_IP_WINDOW,
        ip_cooldown=FAUCET_IP_COOLDOWN,
        max_balance=FAUCET_MAX_BALANCE,
        hcaptcha_enabled=HCAPTCHA_ENABLED,
        hcaptcha_sitekey=HCAPTCHA_SITE_KEY
    )


@app.route('/api/request', methods=['POST'])
def request_tokens():
    """Handle token request"""
    data = request.get_json()

    if not data or 'address' not in data:
        return jsonify({'success': False, 'error': 'Address is required'}), 400

    address = data['address']
    client_ip = get_client_ip()

    # Validate address is a string (security: prevent type confusion attacks)
    if not isinstance(address, str):
        return jsonify({'success': False, 'error': 'Address must be a string'}), 400

    # Block faucet on mainnet unless explicitly allowed
    if XAI_NETWORK == 'mainnet' and not FAUCET_ALLOW_MAINNET:
        return jsonify({'success': False, 'error': 'Faucet is disabled on mainnet'}), 403

    # Enforce captcha when required
    if CAPTCHA_REQUIRED and not HCAPTCHA_ENABLED:
        return jsonify({'success': False, 'error': 'Captcha is required but not configured'}), 503

    # Verify hCaptcha if enabled
    if HCAPTCHA_ENABLED:
        captcha_token = data.get('captcha', '')
        if not verify_hcaptcha(captcha_token):
            return jsonify({'success': False, 'error': 'CAPTCHA verification failed'}), 400

    # Validate address format (basic check)
    if not is_valid_address(address):
        return jsonify({
            'success': False,
            'error': f"Invalid XAI address. Expected prefixes: {', '.join(ALLOWED_PREFIXES)}"
        }), 400

    # Enforce allowlists when configured (devnet access control)
    if not address_allowed(address):
        return jsonify({'success': False, 'error': 'Address is not allowed to use this faucet'}), 403
    if not ip_allowed(client_ip):
        return jsonify({'success': False, 'error': 'IP is not allowed to use this faucet'}), 403

    # Check IP rate limits
    ip_ok, ip_remaining, ip_reason = check_ip_limit(client_ip)
    if not ip_ok:
        if ip_reason == 'ip_rate':
            msg = f'Too many requests from this IP. Try again in {ip_remaining} seconds.'
        else:
            msg = f'Please wait {ip_remaining} seconds before requesting again from this IP.'
        return jsonify({'success': False, 'error': msg}), 429

    # Check cooldown
    can_request, remaining = check_cooldown(address)
    if not can_request:
        return jsonify({
            'success': False,
            'error': f'Please wait {remaining} seconds before requesting again'
        }), 429

    # Check recipient balance cap
    if FAUCET_MAX_BALANCE > 0:
        try:
            balance = get_address_balance(address)
        except Exception as exc:
            logger.warning(f"Failed to check recipient balance: {exc}")
            return jsonify({'success': False, 'error': 'Unable to verify recipient balance at this time'}), 503

        if balance >= FAUCET_MAX_BALANCE:
            return jsonify({
                'success': False,
                'error': 'Address balance is above faucet eligibility threshold'
            }), 429

    # Send tokens
    result = send_tokens(address, FAUCET_AMOUNT)

    if result.get('success'):
        record_ip_request(client_ip)
        record_request(address)
        return jsonify({
            'success': True,
            'message': f'Successfully sent {FAUCET_AMOUNT} XAI to {address}',
            'txid': result.get('txid', 'N/A')
        })
    else:
        record_ip_request(client_ip)
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error occurred')
        }), 500


@app.route('/faucet/claim', methods=['POST'])
def faucet_claim():
    """Alias endpoint for hosted faucet UI."""
    return request_tokens()


@app.route('/claim', methods=['POST'])
def claim():
    """Legacy claim endpoint alias."""
    return request_tokens()


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/stats')
def get_stats():
    """Get faucet statistics"""
    uptime = time.time() - stats['start_time']

    # Try Redis for persistent stats
    if redis_client:
        try:
            total_requests = int(redis_client.get("faucet:stats:total_requests") or 0)
            unique_addresses = redis_client.scard("faucet:stats:unique_addresses") or 0
        except Exception:
            total_requests = stats['total_requests']
            unique_addresses = len(stats['unique_addresses'])
    else:
        total_requests = stats['total_requests']
        unique_addresses = len(stats['unique_addresses'])

    return jsonify({
        'total_requests': total_requests,
        'unique_addresses': unique_addresses,
        'uptime_seconds': int(uptime),
        'faucet_amount': FAUCET_AMOUNT,
        'max_recipient_balance': FAUCET_MAX_BALANCE,
        'cooldown_seconds': FAUCET_COOLDOWN,
        'ip_cooldown_seconds': FAUCET_IP_COOLDOWN,
        'ip_max_per_window': FAUCET_IP_MAX_PER_WINDOW,
        'ip_window_seconds': FAUCET_IP_WINDOW,
        'hcaptcha_enabled': HCAPTCHA_ENABLED,
        'redis_enabled': redis_client is not None,
        'allowed_prefixes': ALLOWED_PREFIXES,
        'network': XAI_NETWORK
    })


if __name__ == '__main__':
    logger.info(f"Starting XAI Testnet Faucet on port {FAUCET_PORT}")
    logger.info(f"Faucet amount: {FAUCET_AMOUNT} XAI")
    logger.info(f"Cooldown period: {FAUCET_COOLDOWN} seconds")
    logger.info(f"XAI API URL: {XAI_API_URL}")
    logger.info(f"hCaptcha: {'enabled' if HCAPTCHA_ENABLED else 'disabled'}")
    logger.info(f"Redis: {'connected' if redis_client else 'disabled (in-memory mode)'}")
    logger.info(f"Allowed prefixes: {', '.join(ALLOWED_PREFIXES)}")
    logger.info(f"IP limits: cooldown={FAUCET_IP_COOLDOWN}s window={FAUCET_IP_WINDOW}s max={FAUCET_IP_MAX_PER_WINDOW}")

    app.run(host='0.0.0.0', port=FAUCET_PORT, debug=False)

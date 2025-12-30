#!/usr/bin/env python3
"""
XAI Testnet Faucet
Provides free testnet tokens for development purposes
"""

import os
import time
import logging
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
FAUCET_PORT = int(os.getenv('FAUCET_PORT', '8086'))
FAUCET_AMOUNT = float(os.getenv('FAUCET_AMOUNT', '100'))
FAUCET_COOLDOWN = int(os.getenv('FAUCET_COOLDOWN', '3600'))  # 1 hour in seconds

# hCaptcha configuration (optional)
HCAPTCHA_SITE_KEY = os.getenv('HCAPTCHA_SITE_KEY', '')
HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY', '')
HCAPTCHA_ENABLED = bool(HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET_KEY)

# Redis configuration (optional)
REDIS_URL = os.getenv('REDIS_URL', '')

# Storage backends
redis_client = None
request_history = {}  # Fallback in-memory storage
ip_history = {}  # IP-based rate limiting
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
    """Send tokens to the specified address via XAI API"""
    try:
        response = requests.post(
            f"{XAI_API_URL}/api/faucet",
            json={"address": address, "amount": amount},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending tokens: {e}")
        return {"success": False, "error": str(e)}


@app.route('/')
def index():
    """Render faucet interface"""
    return render_template_string(
        TEMPLATE,
        amount=FAUCET_AMOUNT,
        cooldown=FAUCET_COOLDOWN,
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

    # Verify hCaptcha if enabled
    if HCAPTCHA_ENABLED:
        captcha_token = data.get('captcha', '')
        if not verify_hcaptcha(captcha_token):
            return jsonify({'success': False, 'error': 'CAPTCHA verification failed'}), 400

    # Validate address format (basic check)
    if not address.startswith('AXN') or len(address) < 40:
        return jsonify({'success': False, 'error': 'Invalid XAI address'}), 400

    # Check cooldown
    can_request, remaining = check_cooldown(address)
    if not can_request:
        return jsonify({
            'success': False,
            'error': f'Please wait {remaining} seconds before requesting again'
        }), 429

    # Send tokens
    result = send_tokens(address, FAUCET_AMOUNT)

    if result.get('success'):
        record_request(address)
        return jsonify({
            'success': True,
            'message': f'Successfully sent {FAUCET_AMOUNT} XAI to {address}',
            'txid': result.get('txid', 'N/A')
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error occurred')
        }), 500


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
        'cooldown_seconds': FAUCET_COOLDOWN,
        'hcaptcha_enabled': HCAPTCHA_ENABLED,
        'redis_enabled': redis_client is not None
    })


if __name__ == '__main__':
    logger.info(f"Starting XAI Testnet Faucet on port {FAUCET_PORT}")
    logger.info(f"Faucet amount: {FAUCET_AMOUNT} XAI")
    logger.info(f"Cooldown period: {FAUCET_COOLDOWN} seconds")
    logger.info(f"XAI API URL: {XAI_API_URL}")
    logger.info(f"hCaptcha: {'enabled' if HCAPTCHA_ENABLED else 'disabled'}")
    logger.info(f"Redis: {'connected' if redis_client else 'disabled (in-memory mode)'}")

    app.run(host='0.0.0.0', port=FAUCET_PORT, debug=False)

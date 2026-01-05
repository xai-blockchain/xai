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
from flask import Flask, request, jsonify, send_from_directory, send_file
from datetime import datetime, timedelta
from collections import defaultdict
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Frontend directory for static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')

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
FAUCET_IP_WINDOW = int(os.getenv('FAUCET_IP_WINDOW', '86400'))  # 24 hours

# Wallet visit limiting (per-wallet requests per 24hr window)
FAUCET_WALLET_MAX_PER_DAY = int(os.getenv('FAUCET_WALLET_MAX_PER_DAY', '2'))

# Global daily limit (total XAI dispensed per 24hr, resets at midnight EST)
FAUCET_DAILY_LIMIT = float(os.getenv('FAUCET_DAILY_LIMIT', '40000'))
FAUCET_DAILY_RESET_HOUR_UTC = int(os.getenv('FAUCET_DAILY_RESET_HOUR_UTC', '5'))  # 5 UTC = midnight EST

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
    'xaitest1' if XAI_NETWORK != 'mainnet' else 'xai1'
).split(',')
ALLOWED_PREFIXES = [prefix.strip() for prefix in ALLOWED_PREFIXES if prefix.strip()]
if not ALLOWED_PREFIXES:
    ALLOWED_PREFIXES = ['xaitest1']
# Build regex pattern for address validation (supports both hex and bech32-style addresses)
ADDRESS_REGEX = re.compile(r'^(' + '|'.join(re.escape(p) for p in ALLOWED_PREFIXES) + r')[0-9a-zA-Z]{38,42}$')

# Turnstile configuration (optional)
TURNSTILE_SITE_KEY = os.getenv('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY', '')
TURNSTILE_ENABLED = bool(TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY)

# Redis configuration (optional)
REDIS_URL = os.getenv('REDIS_URL', '')

# Storage backends
redis_client = None
request_history = {}  # Fallback in-memory storage
ip_history = {}  # IP cooldown tracking
ip_window_history = {}  # IP window tracking (start_ts, count)
wallet_daily_history = {}  # Wallet daily visit tracking (reset_day, count)
daily_dispensed = {'reset_day': 0, 'amount': 0.0}  # Global daily limit tracking
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



def verify_turnstile(token: str) -> bool:
    """Verify Turnstile token with Turnstile API"""
    if not TURNSTILE_ENABLED:
        return True

    if not token:
        return False

    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_SECRET_KEY,
                'response': token
            },
            timeout=10
        )
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Turnstile verification failed: {e}")
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


def get_daily_reset_day() -> int:
    """Get the current 'day' number for daily limit tracking (resets at FAUCET_DAILY_RESET_HOUR_UTC)."""
    now = datetime.utcnow()
    # If before reset hour, count as previous day
    if now.hour < FAUCET_DAILY_RESET_HOUR_UTC:
        now = now - timedelta(days=1)
    return now.toordinal()


def check_daily_limit() -> tuple[bool, float]:
    """Check if global daily faucet limit has been reached. Returns (allowed, remaining_amount)."""
    if FAUCET_DAILY_LIMIT <= 0:
        return True, float('inf')

    current_day = get_daily_reset_day()

    if redis_client:
        try:
            day_key = f"faucet:daily:{current_day}"
            dispensed_str = redis_client.get(day_key)
            dispensed = float(dispensed_str) if dispensed_str else 0.0
            remaining = FAUCET_DAILY_LIMIT - dispensed
            return remaining >= FAUCET_AMOUNT, remaining
        except Exception as e:
            logger.warning(f"Redis daily check failed: {e}")

    # In-memory fallback
    if daily_dispensed['reset_day'] != current_day:
        daily_dispensed['reset_day'] = current_day
        daily_dispensed['amount'] = 0.0

    remaining = FAUCET_DAILY_LIMIT - daily_dispensed['amount']
    return remaining >= FAUCET_AMOUNT, remaining


def record_daily_dispensed(amount: float) -> None:
    """Record amount dispensed for daily limit tracking."""
    if FAUCET_DAILY_LIMIT <= 0:
        return

    current_day = get_daily_reset_day()

    if redis_client:
        try:
            day_key = f"faucet:daily:{current_day}"
            redis_client.incrbyfloat(day_key, amount)
            # Set expiry for 48 hours to auto-cleanup
            redis_client.expire(day_key, 172800)
        except Exception as e:
            logger.warning(f"Redis daily record failed: {e}")

    # Always update in-memory
    if daily_dispensed['reset_day'] != current_day:
        daily_dispensed['reset_day'] = current_day
        daily_dispensed['amount'] = 0.0
    daily_dispensed['amount'] += amount


def check_wallet_daily_limit(address: str) -> tuple[bool, int]:
    """Check if wallet has exceeded daily visit limit. Returns (allowed, visits_remaining)."""
    if FAUCET_WALLET_MAX_PER_DAY <= 0:
        return True, 999

    current_day = get_daily_reset_day()

    if redis_client:
        try:
            day_key = f"faucet:wallet_daily:{address}:{current_day}"
            visits = int(redis_client.get(day_key) or 0)
            if visits >= FAUCET_WALLET_MAX_PER_DAY:
                return False, 0
            return True, FAUCET_WALLET_MAX_PER_DAY - visits
        except Exception as e:
            logger.warning(f"Redis wallet daily check failed: {e}")

    # In-memory fallback
    reset_day, count = wallet_daily_history.get(address, (0, 0))
    if reset_day != current_day:
        count = 0

    if count >= FAUCET_WALLET_MAX_PER_DAY:
        return False, 0
    return True, FAUCET_WALLET_MAX_PER_DAY - count


def record_wallet_daily_visit(address: str) -> None:
    """Record wallet visit for daily limit tracking."""
    if FAUCET_WALLET_MAX_PER_DAY <= 0:
        return

    current_day = get_daily_reset_day()

    if redis_client:
        try:
            day_key = f"faucet:wallet_daily:{address}:{current_day}"
            redis_client.incr(day_key)
            redis_client.expire(day_key, 172800)  # 48hr expiry
        except Exception as e:
            logger.warning(f"Redis wallet daily record failed: {e}")

    # Always update in-memory
    reset_day, count = wallet_daily_history.get(address, (0, 0))
    if reset_day != current_day:
        count = 0
    wallet_daily_history[address] = (current_day, count + 1)


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
        if response.status_code not in (404, 405, 429, 503):
            return {"success": False, "error": f"Faucet API error: {response.text}"}
        logger.warning(f"Primary faucet API returned {response.status_code}: {response.text}")
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
    """Serve faucet frontend"""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/wallet.html')
def wallet_page():
    """Serve wallet generation page"""
    return send_from_directory(FRONTEND_DIR, 'wallet.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, etc.)"""
    return send_from_directory(FRONTEND_DIR, filename)


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
    if CAPTCHA_REQUIRED and not TURNSTILE_ENABLED:
        return jsonify({'success': False, 'error': 'Captcha is required but not configured'}), 503

    # Verify Turnstile if enabled
    if TURNSTILE_ENABLED:
        captcha_token = data.get('captcha', '')
        if not verify_turnstile(captcha_token):
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

    # Check wallet daily visit limit (2 visits per 24hr)
    wallet_ok, wallet_visits_left = check_wallet_daily_limit(address)
    if not wallet_ok:
        return jsonify({
            'success': False,
            'error': 'Wallet has reached daily visit limit (2 per 24 hours). Resets at midnight EST.'
        }), 429

    # Check global daily faucet limit (40,000 XAI per 24hr)
    daily_ok, daily_remaining = check_daily_limit()
    if not daily_ok:
        return jsonify({
            'success': False,
            'error': f'Daily faucet limit reached ({FAUCET_DAILY_LIMIT:.0f} XAI). Resets at midnight EST.'
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
        record_wallet_daily_visit(address)
        record_daily_dispensed(FAUCET_AMOUNT)
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

    # Get daily dispensed amount
    _, daily_remaining = check_daily_limit()
    daily_dispensed_today = FAUCET_DAILY_LIMIT - daily_remaining if FAUCET_DAILY_LIMIT > 0 else 0

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
        'wallet_max_per_day': FAUCET_WALLET_MAX_PER_DAY,
        'daily_limit': FAUCET_DAILY_LIMIT,
        'daily_dispensed': daily_dispensed_today,
        'daily_remaining': daily_remaining if FAUCET_DAILY_LIMIT > 0 else None,
        'daily_reset_hour_utc': FAUCET_DAILY_RESET_HOUR_UTC,
        'turnstile_enabled': TURNSTILE_ENABLED,
        'redis_enabled': redis_client is not None,
        'allowed_prefixes': ALLOWED_PREFIXES,
        'network': XAI_NETWORK
    })


if __name__ == '__main__':
    logger.info(f"Starting XAI Testnet Faucet on port {FAUCET_PORT}")
    logger.info(f"Faucet amount: {FAUCET_AMOUNT} XAI")
    logger.info(f"Cooldown period: {FAUCET_COOLDOWN} seconds")
    logger.info(f"XAI API URL: {XAI_API_URL}")
    logger.info(f"Turnstile: {'enabled' if TURNSTILE_ENABLED else 'disabled'}")
    logger.info(f"Redis: {'connected' if redis_client else 'disabled (in-memory mode)'}")
    logger.info(f"Allowed prefixes: {', '.join(ALLOWED_PREFIXES)}")
    logger.info(f"IP limits: cooldown={FAUCET_IP_COOLDOWN}s window={FAUCET_IP_WINDOW}s max={FAUCET_IP_MAX_PER_WINDOW}")

    app.run(host='0.0.0.0', port=FAUCET_PORT, debug=False)

"""
XAI Block Explorer - Web Interface
Local testing interface for blockchain features
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from threading import Lock

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from xai.core.security.flask_secret_manager import get_flask_secret_key
from xai.core.security.process_sandbox import maybe_enable_process_sandbox

app = Flask(__name__)
# Use persistent secret key manager to prevent session invalidation on restart
app.secret_key = get_flask_secret_key(data_dir=os.path.expanduser("~/.xai"))
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 60  # requests per window
rate_limit_data: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "reset_time": 0})
rate_limit_lock = Lock()


def generate_csrf_token():
    """Generate a CSRF token for the session"""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(token):
    """Validate CSRF token"""
    if "csrf_token" not in session:
        return False
    return hmac.compare_digest(session["csrf_token"], token)


def csrf_required(f):
    """Decorator to require CSRF token for POST requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "POST":
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or not validate_csrf_token(token):
                return jsonify({"error": "Invalid or missing CSRF token"}), 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(max_requests=RATE_LIMIT_MAX_REQUESTS, window=RATE_LIMIT_WINDOW):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP address)
            client_ip = request.remote_addr or "unknown"

            current_time = time.time()

            with rate_limit_lock:
                client_data = rate_limit_data[client_ip]

                # Reset counter if window has passed
                if current_time > client_data["reset_time"]:
                    client_data["count"] = 0
                    client_data["reset_time"] = current_time + window

                # Check rate limit
                if client_data["count"] >= max_requests:
                    return jsonify({
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": int(client_data["reset_time"] - current_time)
                    }), 429

                # Increment counter
                client_data["count"] += 1

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Make CSRF token available to all templates
app.jinja_env.globals["csrf_token"] = generate_csrf_token

# Configure secure session cookies
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Only send cookie over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour session lifetime
)

# Setup security middleware
from xai.core.security.security_middleware import SecurityConfig, setup_security_middleware

security_config = SecurityConfig()
security_config.CORS_ORIGINS = [
    "http://localhost:12080",
    "http://localhost:12080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
    "https://127.0.0.1:3443",
    "https://localhost:3443",
]
security_middleware = setup_security_middleware(app, config=security_config, enable_cors=True)

# Node API endpoint
NODE_URL = os.getenv("XAI_API_URL", "http://localhost:12080")
PUBLIC_NODE_URL = os.getenv("XAI_PUBLIC_NODE_URL", NODE_URL)
PUBLIC_DASHBOARD_ORIGIN = os.getenv("XAI_PUBLIC_DASHBOARD_ORIGIN", "http://127.0.0.1:3000")


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


app.jinja_env.globals.update(format_timestamp=format_timestamp)


def get_node_stats():
    """Get blockchain stats from node"""
    try:
        response = requests.get(f"{NODE_URL}/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # Log the specific error for debugging
        import logging
        logging.warning(f"Failed to fetch node stats: {e}")
        return None
    except (ValueError, KeyError) as e:
        logging.warning(f"Invalid response format from node stats: {e}")
        return None


def get_recent_blocks(limit=10):
    """Fetch recent blocks from node"""
    try:
        response = requests.get(f"{NODE_URL}/blocks?limit={limit}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("blocks", [])
    except requests.RequestException as e:
        import logging
        logging.warning(f"Failed to fetch recent blocks: {e}")
        return []
    except (ValueError, KeyError) as e:
        logging.warning(f"Invalid response format from blocks endpoint: {e}")
        return []


@app.route("/health")
@rate_limit(max_requests=120, window=60)  # Health checks can be more frequent
def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        # Try to connect to the node
        response = requests.get(f"{NODE_URL}/stats", timeout=10)
        node_accessible = response.status_code == 200

        return jsonify(
            {
                "status": "healthy" if node_accessible else "degraded",
                "timestamp": time.time(),
                "services": {
                    "web_interface": "running",
                    "node_connection": "connected" if node_accessible else "disconnected",
                    "node_url": NODE_URL,
                },
            }
        ), (200 if node_accessible else 503)
    except requests.RequestException as e:
        logger.warning(
            "Health check degraded - node unreachable: %s",
            e,
            extra={"event": "explorer.health_check_failed"},
        )
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time(),
                    "services": {"web_interface": "running", "node_connection": "failed"},
                }
            ),
            503,
        )
    except (ValueError, KeyError, TypeError) as e:
        logger.exception(
            "Health check encountered unexpected error",
            extra={"event": "explorer.health_check_unexpected"},
        )
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time(),
                    "services": {"web_interface": "running", "node_connection": "failed"},
                }
            ),
            503,
        )


@app.route("/")
def index():
    """Home page with stats and recent blocks"""
    stats = get_node_stats()
    recent_blocks = get_recent_blocks(5)
    return render_template("index.html", stats=stats, recent_blocks=recent_blocks)


@app.route("/blocks")
def blocks():
    """Block list page"""
    page = request.args.get("page", 1, type=int)
    limit = 50
    offset = (page - 1) * limit

    try:
        response = requests.get(f"{NODE_URL}/blocks?limit={limit}&offset={offset}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return render_template(
            "blocks.html",
            blocks=data.get("blocks", []),
            total=data.get("total", 0),
            page=page,
            limit=limit,
        )
    except requests.RequestException as e:
        import logging
        logging.error(f"Failed to fetch blocks page: {e}")
    except (ValueError, KeyError) as e:
        logging.error(f"Invalid response format from blocks endpoint: {e}")

    return render_template("blocks.html", blocks=[], total=0, page=1, limit=limit)


@app.route("/block/<int:index>")
def block_detail(index):
    """Block detail page"""
    try:
        response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=10)
        response.raise_for_status()
        block = response.json()
        return render_template("block.html", block=block)
    except requests.RequestException as e:
        import logging
        logging.warning(f"Failed to fetch block {index}: {e}")
    except (ValueError, KeyError) as e:
        logging.error(f"Invalid response format for block {index}: {e}")

    return "Block not found", 404


@app.route("/transaction/<txid>")
def transaction_detail(txid):
    """Transaction detail page"""
    # Validate transaction ID format (should be 64 hex characters)
    if not txid or len(txid) != 64 or not all(c in '0123456789abcdefABCDEF' for c in txid):
        return "Invalid transaction ID format", 400

    try:
        response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=10)
        response.raise_for_status()
        tx_data = response.json()
        return render_template("transaction.html", tx=tx_data)
    except requests.RequestException as e:
        import logging
        logging.warning(f"Failed to fetch transaction {txid}: {e}")
    except (ValueError, KeyError) as e:
        logging.error(f"Invalid response format for transaction {txid}: {e}")

    return "Transaction not found", 404


@app.route("/address/<address>")
def address_detail(address):
    """Address detail page"""
    # Validate address format (bech32-style: xai1, xaitest1, or legacy: XAI, TXAI)
    if not address or not address.startswith(("xai1", "xaitest1", "XAI", "TXAI")):
        return "Invalid address format", 400

    # Additional length validation
    if len(address) < 10 or len(address) > 100:
        return "Invalid address length", 400

    balance = 0
    history = []

    try:
        # Get balance
        response = requests.get(f"{NODE_URL}/balance/{address}", timeout=10)
        response.raise_for_status()
        balance = response.json().get("balance", 0)
    except requests.RequestException as e:
        import logging
        logging.warning(f"Failed to fetch balance for {address}: {e}")
    except (ValueError, KeyError) as e:
        logging.error(f"Invalid balance response format: {e}")

    try:
        # Get history
        response = requests.get(f"{NODE_URL}/history/{address}", timeout=10)
        response.raise_for_status()
        history = response.json().get("transactions", [])
    except requests.RequestException as e:
        import logging
        logging.warning(f"Failed to fetch history for {address}: {e}")
    except (ValueError, KeyError) as e:
        logging.error(f"Invalid history response format: {e}")

    return render_template("address.html", address=address, balance=balance, history=history)


@app.route("/search", methods=["GET", "POST"])
@rate_limit(max_requests=30, window=60)  # 30 searches per minute
@csrf_required
def search():
    """Search for block, transaction, or address"""
    if request.method == "POST":
        query = request.form.get("query", "").strip()

        # Validate query input
        if not query:
            return render_template("search.html", error="Please enter a search term")

        # Limit query length to prevent DOS
        if len(query) > 200:
            return render_template("search.html", error="Search query too long (max 200 characters)")

        # Sanitize query - remove any potentially dangerous characters
        import re
        if not re.match(r'^[a-zA-Z0-9]+$', query):
            return render_template("search.html",
                                 error="Invalid characters in search query. Use only letters and numbers.")

        # Try as block number (must be all digits and reasonable range)
        if query.isdigit():
            block_num = int(query)
            if block_num < 0 or block_num > 10000000:  # Reasonable max block number
                return render_template("search.html", error="Block number out of valid range")
            return redirect(url_for("block_detail", index=block_num))

        # Try as transaction ID (must be exactly 64 hex characters)
        if len(query) == 64 and all(c in '0123456789abcdefABCDEF' for c in query):
            return redirect(url_for("transaction_detail", txid=query))

        # Try as address (bech32-style: xai1, xaitest1, or legacy: XAI, TXAI)
        if query.startswith(("xai1", "xaitest1", "XAI", "TXAI")) and 10 <= len(query) <= 100:
            return redirect(url_for("address_detail", address=query))

        return render_template("search.html", error="Invalid search query format")

    return render_template("search.html")


@app.route("/dashboard")
def dashboard():
    """Interactive testing dashboard"""
    stats = get_node_stats() or {}
    recent_blocks = get_recent_blocks(6)
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_blocks=recent_blocks,
        public_node_url=PUBLIC_NODE_URL,
    )


@app.route("/api/stats")
@rate_limit(max_requests=60, window=60)
def api_stats():
    """API endpoint for stats (for auto-refresh)"""
    stats = get_node_stats()
    if stats:
        return jsonify(stats)
    return jsonify({"error": "Node unavailable"}), 503


@app.route("/api/dashboard")
@rate_limit(max_requests=60, window=60)
def api_dashboard():
    """Combined stats + recent blocks for the dashboard"""
    stats = get_node_stats() or {}
    recent_blocks = get_recent_blocks(6)
    return jsonify(
        {
            "stats": stats,
            "recent_blocks": recent_blocks,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )


@app.route("/mobile")
def mobile_view():
    """Simplified mobile page for scanners and QR navigation"""
    stats = get_node_stats() or {}
    return render_template("mobile.html", stats=stats, public_node_url=PUBLIC_NODE_URL)


if __name__ == "__main__":
    maybe_enable_process_sandbox()
    port = int(os.getenv("EXPLORER_PORT", 8082))
    print("=" * 60)
    print("XAI BLOCK EXPLORER")
    print("=" * 60)
    print(f"Explorer: http://localhost:{port}")
    print(f"Node API: {NODE_URL}")
    print("=" * 60)

    # Use debug mode only if explicitly enabled via environment variable
    import os

    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    # Security fix: Use environment variable with secure default (127.0.0.1)
    host = os.getenv("EXPLORER_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=debug_mode)

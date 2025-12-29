from __future__ import annotations

"""
XAI Block Explorer - Local Testing Interface

Simple web interface for exploring the XAI blockchain locally.
NOT for production - only for local testing and debugging!

Usage:
    python block_explorer.py

Then visit: http://localhost:8080
"""

import logging
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import requests
import yaml
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = int(os.getenv("XAI_CACHE_TTL", "60"))  # seconds
CACHE_SIZE = int(os.getenv("XAI_CACHE_SIZE", "128"))  # max cached items

class SimpleCache:
    """
    Simple time-based cache for API responses.

    Stores responses with timestamps and evicts entries older than TTL.
    """

    def __init__(self, ttl: int = CACHE_TTL, max_size: int = CACHE_SIZE):
        """
        Initialize the cache.

        Args:
            ttl: Time-to-live in seconds for cached entries
            max_size: Maximum number of entries to cache

        Raises:
            ValueError: If ttl or max_size are invalid
        """
        if ttl <= 0:
            raise ValueError(f"TTL must be positive, got {ttl}")
        if max_size <= 0:
            raise ValueError(f"Max size must be positive, got {max_size}")
        if max_size > 10000:
            raise ValueError(f"Max size too large (max 10000), got {max_size}")

        self.ttl = ttl
        self.max_size = max_size
        self.cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        """
        Get a cached value if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired

        Raises:
            ValueError: If key is empty or invalid
        """
        if not key or not isinstance(key, str):
            raise ValueError("Cache key must be a non-empty string")

        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now().timestamp() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove it
                del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set a cache value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache

        Raises:
            ValueError: If key is empty or invalid, or value is None
        """
        if not key or not isinstance(key, str):
            raise ValueError("Cache key must be a non-empty string")
        if value is None:
            raise ValueError("Cannot cache None value")

        # Simple eviction: if at max size, remove oldest
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (value, datetime.now().timestamp())

# Global cache instance
response_cache = SimpleCache()

@lru_cache(maxsize=1)
def get_allowed_origins() -> list[str]:
    """
    Get allowed origins from config file (cached).

    Returns:
        List of allowed CORS origins

    Note:
        This function is cached to avoid repeated file I/O operations.
    """
    cors_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cors.yaml")
    if os.path.exists(cors_config_path):
        with open(cors_config_path, "r") as f:
            cors_config = yaml.safe_load(f)
            return cors_config.get("origins", [])
    return []

app = Flask(__name__)
allowed_origins = get_allowed_origins()
CORS(app, origins=allowed_origins)

# Configuration
NODE_URL = os.getenv("XAI_NODE_URL", "http://localhost:12001")

def get_from_node(endpoint: str, use_cache: bool = True) -> dict[str, Any] | None:
    """
    Fetch data from XAI node with optional caching.

    Args:
        endpoint: API endpoint path
        use_cache: Whether to use cached response if available

    Returns:
        JSON response as dictionary or None on error

    Note:
        Caching reduces load on the node and improves response times.
        Cache TTL is configurable via XAI_CACHE_TTL environment variable.
    """
    # Check cache first
    if use_cache:
        cached = response_cache.get(endpoint)
        if cached is not None:
            logger.debug(f"Cache hit for {endpoint}")
            return cached

    try:
        response = requests.get(f"{NODE_URL}{endpoint}", timeout=15)
        response.raise_for_status()
        data = response.json()

        # Cache successful response
        if use_cache and data is not None:
            response_cache.set(endpoint, data)

        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {endpoint} from node")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching {endpoint} - is the node running?")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching {endpoint}: {e.response.status_code}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON response from {endpoint}: {e}")
        return None
    except (RuntimeError, TypeError, KeyError, ValueError) as e:
        logger.error(
            "Unexpected error fetching %s: %s",
            endpoint,
            e,
            exc_info=True,
        )
        return None

def post_to_node(endpoint: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Post data to XAI node.

    Args:
        endpoint: API endpoint path
        data: Data to post as JSON

    Returns:
        JSON response as dictionary or None on error
    """
    try:
        response = requests.post(f"{NODE_URL}{endpoint}", json=data, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout posting to {endpoint}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error posting to {endpoint} - is the node running?")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error posting to {endpoint}: {e.response.status_code}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON response from {endpoint}: {e}")
        return None
    except (RuntimeError, TypeError, KeyError, ValueError) as e:
        logger.error(
            "Unexpected error posting to %s: %s",
            endpoint,
            e,
            exc_info=True,
        )
        return None

def format_timestamp(timestamp: float | None) -> str:
    """
    Convert timestamp to readable UTC format.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted timestamp string
    """
    if timestamp:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return "N/A"

def format_amount(amount: float | None) -> str:
    """
    Format XAI amount.

    Args:
        amount: Amount to format

    Returns:
        Formatted amount string with 4 decimal places
    """
    return f"{amount:,.4f}" if amount else "0.0000"

@app.route("/")
def index():
    """Homepage - Blockchain overview"""
    stats = get_from_node("/stats")

    # Get recent blocks
    blocks_data = get_from_node("/blocks?limit=10")
    recent_blocks = blocks_data.get("blocks", [])[-10:] if blocks_data else []
    recent_blocks.reverse()  # Show newest first

    return render_template(
        "index.html",
        stats=stats,
        recent_blocks=recent_blocks,
        format_timestamp=format_timestamp,
        format_amount=format_amount,
    )

@app.route("/blocks")
def blocks():
    """View all blocks"""
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    blocks_data = get_from_node(f"/blocks?limit={limit}&offset={offset}")
    blocks_list = blocks_data.get("blocks", []) if blocks_data else []
    blocks_list.reverse()  # Show newest first

    return render_template(
        "blocks.html",
        blocks=blocks_list,
        limit=limit,
        offset=offset,
        format_timestamp=format_timestamp,
    )

@app.route("/block/<int:index>")
def block_detail(index):
    """View specific block"""
    block = get_from_node(f"/blocks/{index}")

    return render_template(
        "block.html", block=block, format_timestamp=format_timestamp, format_amount=format_amount
    )

@app.route("/transaction/<txid>")
def transaction_detail(txid):
    """View specific transaction"""
    tx = get_from_node(f"/transaction/{txid}")

    return render_template(
        "transaction.html", tx=tx, format_timestamp=format_timestamp, format_amount=format_amount
    )

@app.route("/address/<address>")
def address_detail(address):
    """View address balance and history"""
    balance_data = get_from_node(f"/balance/{address}")
    history_data = get_from_node(f"/history/{address}")

    balance = balance_data.get("balance", 0) if balance_data else 0
    history = history_data.get("history", []) if history_data else []
    history.reverse()  # Show newest first

    return render_template(
        "address.html",
        address=address,
        balance=balance,
        history=history,
        format_timestamp=format_timestamp,
        format_amount=format_amount,
    )

@app.route("/search", methods=["POST"])
def search():
    """Search for block, transaction, or address"""
    query = request.form.get("query", "").strip()

    if not query:
        return render_template("search.html", error="Please enter a search query")

    # Try to interpret the query
    # Check if it's a number (block index)
    if query.isdigit():
        return render_template("search.html", redirect=f"/block/{query}")

    # Check if it's an address (starts with XAI or TXAI)
    if query.startswith("XAI") or query.startswith("TXAI"):
        return render_template("search.html", redirect=f"/address/{query}")

    # Assume it's a transaction ID
    return render_template("search.html", redirect=f"/transaction/{query}")

@app.route("/api/stats")
def api_stats():
    """API endpoint for stats (for auto-refresh)"""
    stats = get_from_node("/stats")
    return jsonify(stats) if stats else jsonify({"error": "Could not fetch stats"})

if __name__ == "__main__":
    # User-facing startup banner (CLI output - keep print)
    print("=" * 60)
    print("XAI BLOCK EXPLORER")
    print("=" * 60)
    print(f"Connected to node: {NODE_URL}")
    print(f"Explorer running at: http://localhost:8080")
    print("=" * 60)
    print("\nNOTE: This is for LOCAL TESTING ONLY!")
    print("      Not intended for production use.\n")

    # Log startup for monitoring
    logger.info("Block explorer starting", node_url=NODE_URL, cache_ttl=CACHE_TTL, cache_size=CACHE_SIZE)

    # Use debug mode only if explicitly enabled via environment variable
    import os

    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    # Security fix: Use environment variable with secure default (127.0.0.1)
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "8080"))

    logger.info("Starting Flask server", host=host, port=port, debug=debug_mode)
    app.run(host=host, port=port, debug=debug_mode)

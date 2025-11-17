"""
XAI Block Explorer - Web Interface
Local testing interface for blockchain features
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
from datetime import datetime
import os
import time

app = Flask(__name__)

# Node API endpoint
NODE_URL = os.getenv("AIXN_API_URL", "http://localhost:5000")


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


app.jinja_env.globals.update(format_timestamp=format_timestamp)


def get_node_stats():
    """Get blockchain stats from node"""
    try:
        response = requests.get(f"{NODE_URL}/stats", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_recent_blocks(limit=10):
    """Fetch recent blocks from node"""
    try:
        response = requests.get(f"{NODE_URL}/blocks?limit={limit}", timeout=2)
        if response.status_code == 200:
            return response.json().get("blocks", [])
    except:
        pass
    return []


@app.route("/health")
def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        # Try to connect to the node
        response = requests.get(f"{NODE_URL}/stats", timeout=2)
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
    except Exception as e:
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
        response = requests.get(f"{NODE_URL}/blocks?limit={limit}&offset={offset}", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return render_template(
                "blocks.html",
                blocks=data.get("blocks", []),
                total=data.get("total", 0),
                page=page,
                limit=limit,
            )
    except:
        pass

    return render_template("blocks.html", blocks=[], total=0, page=1, limit=limit)


@app.route("/block/<int:index>")
def block_detail(index):
    """Block detail page"""
    try:
        response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=2)
        if response.status_code == 200:
            block = response.json()
            return render_template("block.html", block=block)
    except:
        pass

    return "Block not found", 404


@app.route("/transaction/<txid>")
def transaction_detail(txid):
    """Transaction detail page"""
    try:
        response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=2)
        if response.status_code == 200:
            tx_data = response.json()
            return render_template("transaction.html", tx=tx_data)
    except:
        pass

    return "Transaction not found", 404


@app.route("/address/<address>")
def address_detail(address):
    """Address detail page"""
    balance = 0
    history = []

    try:
        # Get balance
        response = requests.get(f"{NODE_URL}/balance/{address}", timeout=2)
        if response.status_code == 200:
            balance = response.json().get("balance", 0)

        # Get history
        response = requests.get(f"{NODE_URL}/history/{address}", timeout=2)
        if response.status_code == 200:
            history = response.json().get("transactions", [])
    except:
        pass

    return render_template("address.html", address=address, balance=balance, history=history)


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search for block, transaction, or address"""
    if request.method == "POST":
        query = request.form.get("query", "").strip()

        if not query:
            return render_template("search.html", error="Please enter a search term")

        # Try as block number
        if query.isdigit():
            return redirect(url_for("block_detail", index=int(query)))

        # Try as transaction ID
        if len(query) == 64:
            return redirect(url_for("transaction_detail", txid=query))

        # Try as address
        if query.startswith("AIXN") or query.startswith("TXAI"):
            return redirect(url_for("address_detail", address=query))

        return render_template("search.html", error="Invalid search query")

    return render_template("search.html")


@app.route("/dashboard")
def dashboard():
    """Interactive testing dashboard"""
    stats = get_node_stats() or {}
    recent_blocks = get_recent_blocks(6)
    return render_template(
        "dashboard.html", stats=stats, recent_blocks=recent_blocks, node_url=NODE_URL
    )


@app.route("/api/stats")
def api_stats():
    """API endpoint for stats (for auto-refresh)"""
    stats = get_node_stats()
    if stats:
        return jsonify(stats)
    return jsonify({"error": "Node unavailable"}), 503


@app.route("/api/dashboard")
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
    return render_template("mobile.html", stats=stats, node_url=NODE_URL)


if __name__ == "__main__":
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
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

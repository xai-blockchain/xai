#!/usr/bin/env python3
"""XAI Testnet Explorer API - lightweight proxy for node stats and blocks."""

import os
import time
import logging
from typing import Any, Dict, Tuple

import requests
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - optional dependency
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xai-explorer")

app = Flask(__name__)
CORS(app)

NODE_URL = os.getenv("XAI_NODE_URL", "http://localhost:8545").rstrip("/")
CHAIN_NAME = os.getenv("XAI_CHAIN_NAME", "xai-testnet")
EXPLORER_VERSION = os.getenv("XAI_EXPLORER_VERSION", "2.0.0")


def fetch_json(path: str, params=None) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        response = requests.get(f"{NODE_URL}{path}", params=params, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:
        logger.error("Node request failed: %s %s (%s)", path, params, exc)
        return None, str(exc)


@app.route("/health")
def health():
    data, error = fetch_json("/stats")
    healthy = data is not None
    status = "healthy" if healthy else "degraded"
    return jsonify({
        "chain": CHAIN_NAME,
        "node": {"reachable": healthy, "url": NODE_URL},
        "status": status,
        "timestamp": time.time(),
        "version": EXPLORER_VERSION,
        "error": error if not healthy else None
    }), (200 if healthy else 503)


@app.route("/api/stats")
def api_stats():
    data, error = fetch_json("/stats")
    if data is None:
        return jsonify({"error": error or "Node unreachable"}), 503
    return jsonify(data)


@app.route("/api/blocks")
@app.route("/api/blocks/<block_id>")
def api_blocks(block_id: str | None = None):
    path = f"/blocks/{block_id}" if block_id is not None else "/blocks"
    data, error = fetch_json(path, params=request.args or None)
    if data is None:
        return jsonify({"error": error or "Node unreachable"}), 503
    return jsonify(data)


@app.route("/api/transactions")
def api_transactions():
    data, error = fetch_json("/transactions", params=request.args or None)
    if data is None:
        return jsonify({"error": error or "Node unreachable"}), 503
    return jsonify(data)


@app.route("/api/transaction/<txid>")
def api_transaction(txid: str):
    data, error = fetch_json(f"/transaction/{txid}")
    if data is None:
        return jsonify({"error": error or "Node unreachable"}), 503
    return jsonify(data)


@app.route("/metrics")
def metrics():
    if generate_latest is None:
        return Response("# metrics unavailable\n", mimetype=CONTENT_TYPE_LATEST)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ============================================================================
# HIGH PRIORITY ENDPOINTS
# ============================================================================

@app.route("/api/address/<address>")
def api_address(address: str):
    """Get address/account details including balance and transaction count."""
    balance_data, balance_err = fetch_json(f"/balance/{address}")
    history_data, history_err = fetch_json(f"/history/{address}", params={"limit": 1})

    if balance_data is None:
        return jsonify({"error": balance_err or "Failed to fetch address data"}), 503

    result = {
        "address": address,
        "balance": balance_data.get("balance", 0),
        "transaction_count": 0,
        "first_seen": None,
        "last_seen": None,
    }

    if history_data and "transactions" in history_data:
        result["transaction_count"] = history_data.get("transaction_count", 0)
        txs = history_data.get("transactions", [])
        if txs:
            result["last_seen"] = txs[0].get("timestamp")

    return jsonify(result)


@app.route("/api/address/<address>/transactions")
def api_address_transactions(address: str):
    """Get transaction history for an address with pagination."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    limit = min(limit, 100)  # Cap at 100
    offset = (page - 1) * limit

    data, error = fetch_json(f"/history/{address}", params={"limit": limit, "offset": offset})
    if data is None:
        return jsonify({"error": error or "Failed to fetch transactions"}), 503

    transactions = []
    for tx in data.get("transactions", []):
        transactions.append({
            "txid": tx.get("txid"),
            "block": tx.get("block_index"),
            "timestamp": tx.get("timestamp"),
            "type": tx.get("tx_type"),
            "amount": tx.get("amount", 0),
            "fee": tx.get("fee", 0),
            "sender": tx.get("sender"),
            "recipient": tx.get("recipient"),
            "status": "confirmed" if tx.get("block_index") else "pending",
        })

    return jsonify({
        "address": address,
        "transactions": transactions,
        "page": page,
        "limit": limit,
        "total": data.get("transaction_count", len(transactions)),
    })


@app.route("/api/search", methods=["GET", "POST"])
def api_search():
    """Universal search - detect and route to block, transaction, or address."""
    if request.method == "POST":
        query = request.json.get("q", "") if request.is_json else request.form.get("q", "")
    else:
        query = request.args.get("q", "")

    query = query.strip()
    if not query:
        return jsonify({"error": "Search query required", "type": None, "result": None}), 400

    # Detect search type
    # Block number: purely numeric
    if query.isdigit():
        block_data, err = fetch_json(f"/blocks/{query}")
        if block_data:
            return jsonify({
                "type": "block",
                "query": query,
                "result": block_data,
            })
        return jsonify({"type": "block", "query": query, "result": None, "error": "Block not found"}), 404

    # Transaction hash: 64 hex characters (SHA256)
    if len(query) == 64 and all(c in "0123456789abcdefABCDEF" for c in query):
        tx_data, err = fetch_json(f"/transaction/{query}")
        if tx_data and "error" not in tx_data:
            return jsonify({
                "type": "transaction",
                "query": query,
                "result": tx_data,
            })
        return jsonify({"type": "transaction", "query": query, "result": None, "error": "Transaction not found"}), 404

    # Address: starts with TXAI or standard format
    if query.startswith("TXAI") or (len(query) >= 26 and len(query) <= 64):
        balance_data, err = fetch_json(f"/balance/{query}")
        if balance_data and "error" not in balance_data:
            history_data, _ = fetch_json(f"/history/{query}", params={"limit": 5})
            result = {
                "address": query,
                "balance": balance_data.get("balance", 0),
                "transaction_count": history_data.get("transaction_count", 0) if history_data else 0,
                "recent_transactions": history_data.get("transactions", [])[:5] if history_data else [],
            }
            return jsonify({
                "type": "address",
                "query": query,
                "result": result,
            })
        return jsonify({"type": "address", "query": query, "result": None, "error": "Address not found"}), 404

    return jsonify({"type": "unknown", "query": query, "result": None, "error": "Could not identify search type"}), 400


# ============================================================================
# MEDIUM PRIORITY ENDPOINTS
# ============================================================================

@app.route("/api/richlist")
def api_richlist():
    """Get top token holders sorted by balance."""
    # XAI node doesn't have a native richlist endpoint, so we build from stats and known addresses
    stats_data, _ = fetch_json("/stats")
    total_supply = stats_data.get("total_circulating_supply", 0) if stats_data else 0

    # Get miner address from stats as it's the only known rich address
    miner_addr = stats_data.get("miner_address", "") if stats_data else ""

    richlist = []
    if miner_addr:
        balance_data, _ = fetch_json(f"/balance/{miner_addr}")
        if balance_data:
            balance = balance_data.get("balance", 0)
            richlist.append({
                "rank": 1,
                "address": miner_addr,
                "balance": balance,
                "percentage_of_supply": round((balance / total_supply * 100) if total_supply > 0 else 0, 4),
            })

    return jsonify({
        "richlist": richlist,
        "total_supply": total_supply,
        "count": len(richlist),
        "note": "Richlist is limited to known active addresses",
    })


@app.route("/api/mempool")
def api_mempool():
    """Get pending/unconfirmed transactions from mempool."""
    data, error = fetch_json("/transactions")
    stats_data, _ = fetch_json("/stats")

    if data is None:
        return jsonify({"error": error or "Failed to fetch mempool"}), 503

    mempool_stats = {}
    if stats_data:
        mempool_stats = {
            "size_bytes": stats_data.get("mempool_size_bytes", 0),
            "evicted_low_fee_total": stats_data.get("mempool_evicted_low_fee_total", 0),
            "rejected_invalid_total": stats_data.get("mempool_rejected_invalid_total", 0),
            "rejected_low_fee_total": stats_data.get("mempool_rejected_low_fee_total", 0),
            "active_bans": stats_data.get("mempool_active_bans", 0),
        }

    return jsonify({
        "pending_count": data.get("count", 0),
        "transactions": data.get("transactions", []),
        "mempool_stats": mempool_stats,
    })


@app.route("/api/supply")
def api_supply():
    """Get token supply information."""
    stats_data, error = fetch_json("/stats")
    if stats_data is None:
        return jsonify({"error": error or "Failed to fetch supply data"}), 503

    return jsonify({
        "total_supply": stats_data.get("total_circulating_supply", 0),
        "circulating_supply": stats_data.get("total_circulating_supply", 0),
        "burned": 0,  # XAI doesn't track burns separately
        "chain_height": stats_data.get("chain_height", 0),
    })


@app.route("/api/network")
def api_network():
    """Get network statistics including peers and mining info."""
    stats_data, stats_err = fetch_json("/stats")
    peers_data, _ = fetch_json("/peers")

    if stats_data is None:
        return jsonify({"error": stats_err or "Failed to fetch network data"}), 503

    return jsonify({
        "peer_count": stats_data.get("peers", 0),
        "peers": peers_data.get("peers", []) if peers_data else [],
        "node_version": "2.0.0",
        "chain_height": stats_data.get("chain_height", 0),
        "difficulty": stats_data.get("difficulty", 0),
        "is_mining": stats_data.get("is_mining", False),
        "node_uptime": stats_data.get("node_uptime", 0),
        "latest_block_hash": stats_data.get("latest_block_hash", ""),
        "orphan_blocks_count": stats_data.get("orphan_blocks_count", 0),
        "orphan_transactions_count": stats_data.get("orphan_transactions_count", 0),
    })


# ============================================================================
# XAI-SPECIFIC AI ENDPOINTS
# ============================================================================

@app.route("/api/ai/tasks")
def api_ai_tasks():
    """Get AI computation task listings (XAI-specific feature)."""
    # Check if algorithmic features are enabled
    algo_status, _ = fetch_json("/algo/status")
    if not algo_status or not algo_status.get("enabled", False):
        return jsonify({
            "enabled": False,
            "tasks": [],
            "total": 0,
            "message": "AI task features not enabled on this network",
        })

    # If enabled, would query the node for AI tasks
    return jsonify({
        "enabled": True,
        "tasks": [],
        "total": 0,
        "features": algo_status.get("features", []),
    })


@app.route("/api/ai/models")
def api_ai_models():
    """Get AI model registry (XAI-specific feature)."""
    algo_status, _ = fetch_json("/algo/status")
    if not algo_status or not algo_status.get("enabled", False):
        return jsonify({
            "enabled": False,
            "models": [],
            "total": 0,
            "message": "AI model registry not enabled on this network",
        })

    return jsonify({
        "enabled": True,
        "models": [],
        "total": 0,
        "features": algo_status.get("features", []),
    })


@app.route("/api/providers")
def api_providers():
    """Get AI compute providers (XAI-specific feature)."""
    algo_status, _ = fetch_json("/algo/status")

    # Get mining stats for known providers
    stats_data, _ = fetch_json("/stats")

    providers = []
    if stats_data and stats_data.get("miner_address"):
        # The active miner is a compute provider
        miner_addr = stats_data["miner_address"]
        providers.append({
            "address": miner_addr,
            "capacity": "active",
            "tasks_completed": stats_data.get("chain_height", 0),  # Blocks mined as proxy
            "reputation": 100,
            "is_mining": stats_data.get("is_mining", False),
        })

    return jsonify({
        "providers": providers,
        "total": len(providers),
        "ai_features_enabled": algo_status.get("enabled", False) if algo_status else False,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)

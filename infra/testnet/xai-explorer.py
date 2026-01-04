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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)

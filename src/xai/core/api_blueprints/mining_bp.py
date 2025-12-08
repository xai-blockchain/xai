"""
Mining API Blueprint

Handles mining-related endpoints: mine, auto-mine start/stop, peers, sync.
Extracted from node_api.py as part of god class refactoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request

from xai.core.api_blueprints.base import (
    build_peer_snapshot,
    error_response,
    get_blockchain,
    get_node,
    require_api_auth,
    success_response,
)

logger = logging.getLogger(__name__)

mining_bp = Blueprint("mining", __name__)


@mining_bp.route("/mine", methods=["POST"])
def mine_block() -> Tuple[Dict[str, Any], int]:
    """Mine pending transactions."""
    node = get_node()
    blockchain = get_blockchain()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    # Rate limit mining endpoint - fail closed when limiter unavailable
    try:
        from xai.core.advanced_rate_limiter import get_rate_limiter as get_advanced_rate_limiter

        limiter = get_advanced_rate_limiter()
        allowed, rate_error = limiter.check_rate_limit("/mine")
        if not allowed:
            return error_response(
                rate_error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
            )
    except Exception as exc:
        logger.error(
            "Rate limiter unavailable for /mine: %s",
            type(exc).__name__,
            extra={
                "event": "api.rate_limiter_error",
                "endpoint": "/mine",
                "client": request.remote_addr or "unknown",
            },
            exc_info=True,
        )
        return error_response(
            "Rate limiting unavailable. Please retry later.",
            status=503,
            code="rate_limiter_unavailable",
        )

    if not blockchain.pending_transactions:
        return jsonify({"error": "No pending transactions to mine"}), 400

    try:
        block = blockchain.mine_pending_transactions(node.miner_address)

        # Broadcast new block to peers
        node.broadcast_block(block)

        return (
            jsonify(
                {
                    "success": True,
                    "block": block.to_dict(),
                    "message": f"Block {block.index} mined successfully",
                    "reward": blockchain.block_reward,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mining_bp.route("/auto-mine/start", methods=["POST"])
def start_auto_mining() -> Dict[str, str]:
    """Start automatic mining."""
    node = get_node()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error
    if node.is_mining:
        return jsonify({"message": "Mining already active"})

    node.start_mining()
    return jsonify({"message": "Auto-mining started"})


@mining_bp.route("/auto-mine/stop", methods=["POST"])
def stop_auto_mining() -> Dict[str, str]:
    """Stop automatic mining."""
    node = get_node()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error
    if not node.is_mining:
        return jsonify({"message": "Mining not active"})

    node.stop_mining()
    return jsonify({"message": "Auto-mining stopped"})


@mining_bp.route("/peers", methods=["GET"])
def get_peers() -> Dict[str, Any]:
    """Get connected peers."""
    node = get_node()
    verbose = request.args.get("verbose", "false")
    verbose_requested = str(verbose).lower() in {"1", "true", "yes", "on"}
    payload: Dict[str, Any] = {"count": len(node.peers), "peers": list(node.peers), "verbose": verbose_requested}
    if verbose_requested:
        payload.update(build_peer_snapshot())
    return jsonify(payload)


@mining_bp.route("/peers/add", methods=["POST"])
def add_peer() -> Tuple[Dict[str, str], int]:
    """Add peer node."""
    node = get_node()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    url = payload.get("url")
    if not url or not isinstance(url, str):
        return error_response("Invalid peer URL", status=400, code="invalid_payload")

    node.add_peer(url)
    return success_response({"message": f"Peer {url} added"})


@mining_bp.route("/sync", methods=["POST"])
def sync_blockchain() -> Dict[str, Any]:
    """Synchronize blockchain with peers."""
    node = get_node()
    blockchain = get_blockchain()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error
    synced = node.sync_with_network()
    return jsonify({"synced": synced, "chain_length": len(blockchain.chain)})

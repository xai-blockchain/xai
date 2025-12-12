"""
Blockchain API Blueprint

Handles blockchain query endpoints: blocks, transactions, block receipt.
Extracted from node_api.py as part of god class refactoring.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, make_response, request

from xai.core.api_blueprints.base import (
    PaginationError,
    error_response,
    get_api_context,
    get_blockchain,
    get_node,
    get_pagination_params,
    handle_exception,
    require_api_auth,
    success_response,
)

logger = logging.getLogger(__name__)

blockchain_bp = Blueprint("blockchain", __name__)


@blockchain_bp.route("/blocks", methods=["GET"])
def get_blocks() -> Dict[str, Any]:
    """Get all blocks with pagination."""
    blockchain = get_blockchain()
    try:
        limit, offset = get_pagination_params(default_limit=10, max_limit=200)
    except PaginationError as exc:
        return error_response(
            str(exc),
            status=400,
            code="invalid_pagination",
            event_type="api.invalid_paging",
        )

    blocks = [block.to_dict() for block in blockchain.chain]
    blocks.reverse()  # Most recent first

    return jsonify(
        {
            "total": len(blocks),
            "limit": limit,
            "offset": offset,
            "blocks": blocks[offset : offset + limit],
        }
    )


@blockchain_bp.route("/blocks/<index>", methods=["GET"])
def get_block(index: str) -> Tuple[Dict[str, Any], int]:
    """Get specific block by index with explicit validation (supports negative input)."""
    blockchain = get_blockchain()
    try:
        idx_int = int(index)
    except (TypeError, ValueError):
        return jsonify({"error": "Block index must be integer"}), 400

    chain = getattr(blockchain, "chain", [])
    chain_length = len(chain) if hasattr(chain, "__len__") else 0

    if idx_int < 0 or idx_int >= chain_length:
        return jsonify({"error": "Block not found"}), 404

    fallback_block = None
    try:
        fallback_block = chain[idx_int]
    except IndexError as e:
        logger.debug("Block %d not in chain cache: %s", idx_int, type(e).__name__)
        fallback_block = None

    block_obj = None
    if hasattr(blockchain, "get_block") and callable(
        getattr(blockchain, "get_block", None)
    ):
        try:
            block_obj = blockchain.get_block(idx_int)
        except (LookupError, TypeError, ValueError) as e:
            logger.debug("get_block(%d) failed: %s", idx_int, type(e).__name__)
            block_obj = None

    if block_obj is None or (
        not hasattr(block_obj, "to_dict") and not isinstance(block_obj, dict)
    ):
        block_obj = fallback_block or block_obj
    if block_obj is None:
        return jsonify({"error": "Block not found"}), 404

    payload_source = block_obj
    payload = None
    if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
        payload = payload_source.to_dict()
    else:
        payload = payload_source
    if not isinstance(payload, dict) and fallback_block is not None:
        payload_source = fallback_block
        if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
            payload = payload_source.to_dict()
        else:
            payload = payload_source
    if isinstance(payload, dict) and "index" not in payload:
        header = payload.get("header", {})
        if isinstance(header, dict) and "index" in header:
            payload["index"] = header["index"]
    if not isinstance(payload, dict):
        return jsonify({"error": "Block not available"}), 404

    # ETag-based caching for immutable blocks
    block_hash = None
    if isinstance(payload, dict):
        block_hash = payload.get("hash")
        if not block_hash and "header" in payload and isinstance(payload["header"], dict):
            block_hash = payload["header"].get("hash")
    if not block_hash and hasattr(block_obj, "hash"):
        block_hash = block_obj.hash

    if block_hash:
        etag = f'"{block_hash}"'
        client_etag = request.headers.get("If-None-Match")
        if client_etag == etag:
            return "", 304
        response = make_response(jsonify(payload), 200)
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    return jsonify(payload), 200


@blockchain_bp.route("/block/<block_hash>", methods=["GET"])
def get_block_by_hash(block_hash: str) -> Tuple[Dict[str, Any], int]:
    """Get a block by its hash."""
    blockchain = get_blockchain()
    if not block_hash:
        return jsonify({"error": "Invalid block hash"}), 400
    normalized = block_hash.lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    if not normalized or not re.fullmatch(r"[0-9a-f]{64}", normalized):
        return jsonify({"error": "Invalid block hash"}), 400

    block_obj = None
    lookup = getattr(blockchain, "get_block_by_hash", None)
    if callable(lookup):
        try:
            block_obj = lookup(block_hash)
        except (LookupError, ValueError, TypeError) as exc:
            logger.debug("get_block_by_hash failed: %s", type(exc).__name__)
            block_obj = None

    if block_obj is None:
        chain = getattr(blockchain, "chain", [])
        target = f"0x{normalized}"
        for candidate in chain:
            candidate_hash = getattr(candidate, "hash", None)
            if not candidate_hash and isinstance(candidate, dict):
                candidate_hash = candidate.get("hash") or candidate.get("block_hash")
            if not candidate_hash:
                continue
            cand_norm = candidate_hash.lower()
            if cand_norm.startswith("0x"):
                cand_norm = cand_norm[2:]
            if cand_norm == normalized:
                block_obj = candidate
                break

    if block_obj is None:
        return jsonify({"error": "Block not found"}), 404

    payload_source = block_obj
    if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
        payload = payload_source.to_dict()
    elif isinstance(payload_source, dict):
        payload = payload_source
    else:
        payload = None

    if not isinstance(payload, dict):
        return jsonify({"error": "Block not available"}), 404

    if "hash" not in payload:
        payload["hash"] = getattr(block_obj, "hash", None)

    # ETag-based caching
    final_hash = payload.get("hash") or block_hash
    if final_hash:
        etag = f'"{final_hash}"'
        client_etag = request.headers.get("If-None-Match")
        if client_etag == etag:
            return "", 304
        response = make_response(jsonify(payload), 200)
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    return jsonify(payload), 200


@blockchain_bp.route("/block/receive", methods=["POST"])
def receive_block() -> Tuple[Dict[str, Any], int]:
    """Receive a block from a peer node."""
    blockchain = get_blockchain()
    ctx = get_api_context()
    peer_manager = ctx.get("peer_manager")

    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    # Verify signed peer message
    body_bytes = request.get_data(cache=False, as_text=False) or b""
    try:
        verified = peer_manager.encryption.verify_signed_message(body_bytes)
        if not verified:
            return error_response(
                "Unauthorized P2P message",
                status=401,
                code="p2p_invalid_signature",
            )
        payload = verified.get("payload")
        sender_id = verified.get("sender")
        nonce = verified.get("nonce")
        if not sender_id or not nonce:
            return error_response(
                "Unauthorized P2P message",
                status=401,
                code="p2p_missing_identity",
            )
        if peer_manager.is_nonce_replay(sender_id, nonce, verified.get("timestamp")):
            return error_response(
                "Unauthorized P2P message",
                status=401,
                code="p2p_replay_attack",
            )
        peer_manager.record_nonce(sender_id, nonce, verified.get("timestamp"))
    except (ValueError, RuntimeError) as e:
        return error_response(
            "Unauthorized P2P message",
            status=401,
            code=f"p2p_verification_error",
        )

    if payload is None:
        return error_response(
            "Invalid block payload",
            status=400,
            code="invalid_payload",
        )
    header = payload.get("header") if isinstance(payload, dict) else None
    required_header = ["index", "previous_hash", "merkle_root", "timestamp", "difficulty", "nonce"]
    if not header or any(header.get(f) in (None, "") for f in required_header):
        return error_response(
            "Invalid block payload",
            status=400,
            code="invalid_payload",
            context={"missing_header_fields": [f for f in required_header if not header or header.get(f) in (None, "")]},
        )

    try:
        from xai.core.blockchain import Blockchain
        block = Blockchain.deserialize_block(payload)
    except (ValueError, TypeError, KeyError) as exc:
        return error_response(
            f"Invalid block data: {exc}",
            status=400,
            code="invalid_block",
            context={"error": str(exc)},
        )

    try:
        # P2P metrics: received block
        try:
            from xai.core.monitoring import MetricsCollector
            MetricsCollector.instance().record_p2p_message("received")
        except (ImportError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Failed to record P2P metrics for received block: %s",
                type(exc).__name__,
                extra={
                    "event": "api.metrics.record_failed",
                    "reason": str(exc),
                },
            )
        added = blockchain.add_block(block)
    except (RuntimeError, ValueError) as exc:
        return handle_exception(exc, "receive_block")

    if added:
        return success_response({"height": len(blockchain.chain)})
    return error_response(
        "Block rejected",
        status=400,
        code="block_rejected",
    )


@blockchain_bp.route("/transactions", methods=["GET"])
def get_pending_transactions() -> Dict[str, Any]:
    """Get pending transactions in the mempool."""
    blockchain = get_blockchain()
    return jsonify(
        {
            "pending_transactions": [
                tx.to_dict() for tx in blockchain.pending_transactions
            ]
        }
    )


@blockchain_bp.route("/transaction/<txid>", methods=["GET"])
def get_transaction(txid: str) -> Tuple[Dict[str, Any], int]:
    """Get a specific transaction by ID."""
    blockchain = get_blockchain()
    if not txid:
        return jsonify({"error": "Invalid transaction ID"}), 400

    # Normalize txid
    normalized = txid.lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    if not normalized or not re.fullmatch(r"[0-9a-f]{64}", normalized):
        return jsonify({"error": "Invalid transaction ID format"}), 400

    # Search in pending transactions
    for tx in getattr(blockchain, "pending_transactions", []):
        tx_hash = getattr(tx, "txid", None) or getattr(tx, "hash", None)
        if not tx_hash:
            continue
        tx_norm = tx_hash.lower()
        if tx_norm.startswith("0x"):
            tx_norm = tx_norm[2:]
        if tx_norm == normalized:
            tx_payload = tx.to_dict() if hasattr(tx, "to_dict") else tx_hash
            return jsonify({"transaction": tx_payload, "status": "pending"}), 200

    # Search in confirmed blocks
    for block in getattr(blockchain, "chain", []):
        for tx in getattr(block, "transactions", []):
            tx_hash = getattr(tx, "txid", None) or getattr(tx, "hash", None)
            if not tx_hash:
                continue
            tx_norm = tx_hash.lower()
            if tx_norm.startswith("0x"):
                tx_norm = tx_norm[2:]
            if tx_norm == normalized:
                tx_payload = tx.to_dict() if hasattr(tx, "to_dict") else tx_hash
                return jsonify({
                    "transaction": tx_payload,
                    "status": "confirmed",
                    "block_index": getattr(block, "index", None),
                    "block_hash": getattr(block, "hash", None),
                }), 200

    return jsonify({"error": "Transaction not found"}), 404

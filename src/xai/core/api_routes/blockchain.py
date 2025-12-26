from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any

from flask import jsonify, make_response, request

from xai.core.blockchain import Blockchain
from xai.core.monitoring import MetricsCollector

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)

def register_blockchain_routes(routes: "NodeAPIRoutes") -> None:
    """Register blockchain query/manipulation endpoints."""
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/blocks", methods=["GET"])
    def get_blocks() -> dict[str, Any]:
        """Get all blocks with pagination."""
        try:
            limit, offset = routes._get_pagination_params(default_limit=10, max_limit=200)
        except (ValueError, RuntimeError) as exc:
            return routes._error_response(
                str(exc),
                status=400,
                code="invalid_pagination",
                event_type="api.invalid_paging",
            )

        blocks = [block.to_dict() for block in blockchain.chain]
        blocks.reverse()

        return jsonify(
            {
                "total": len(blocks),
                "limit": limit,
                "offset": offset,
                "blocks": blocks[offset : offset + limit],
            }
        )

    @app.route("/blocks/<index>", methods=["GET"])
    def get_block(index: str) -> tuple[dict[str, Any], int]:
        """Get specific block by index with explicit validation (supports negative input)."""
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
        except IndexError as exc:
            logger.debug("Block %d not in chain cache: %s", idx_int, type(exc).__name__)
            fallback_block = None

        block_obj = None
        block_lookup = getattr(blockchain, "get_block", None)
        if callable(block_lookup):
            try:
                block_obj = block_lookup(idx_int)
            except (LookupError, ValueError, TypeError) as exc:
                logger.debug("get_block(%d) failed: %s", idx_int, type(exc).__name__)
                block_obj = None

        if block_obj is None:
            block_obj = fallback_block
        if block_obj is None:
            return jsonify({"error": "Block not found"}), 404

        payload = _block_to_payload(block_obj, fallback_block)
        if not isinstance(payload, dict):
            return jsonify({"error": "Block not available"}), 404

        block_hash = payload.get("hash")
        if not block_hash and isinstance(payload.get("header"), dict):
            block_hash = payload["header"].get("hash")
        if not block_hash and hasattr(block_obj, "hash"):
            block_hash = getattr(block_obj, "hash")

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

    @app.route("/block/<block_hash>", methods=["GET"])
    def get_block_by_hash(block_hash: str) -> tuple[dict[str, Any], int]:
        """Get a block by its hash."""
        if not block_hash:
            return jsonify({"error": "Invalid block hash"}), 400
        normalized = block_hash.lower()
        if normalized.startswith("0x"):
            normalized = normalized[2:]
        if not normalized or not re.fullmatch(r"[0-9a-f]{64}", normalized):
            return jsonify({"error": "Invalid block hash"}), 400

        block_obj = _lookup_block_by_hash(blockchain, block_hash, normalized)
        if block_obj is None:
            return jsonify({"error": "Block not found"}), 404

        payload = _block_to_payload(block_obj)
        if not isinstance(payload, dict):
            return jsonify({"error": "Block not available"}), 404

        if "hash" not in payload:
            payload["hash"] = getattr(block_obj, "hash", None)

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

    @app.route("/chain/range", methods=["GET"])
    @app.route("/api/v1/chain/range", methods=["GET"])
    def get_chain_range() -> tuple[dict[str, Any], int]:
        """
        Get paginated chain data for incremental sync.

        Provides O(limit) serialization instead of O(n) for the full chain.
        Suitable for large chains where full sync would be prohibitive.

        Query Parameters:
            offset: Starting block height (default: 0)
            limit: Maximum blocks to return (default: 100, max: 500)
            include_pending: Include pending transactions (default: true for offset=0)

        Returns:
            JSON with:
            - chain: List of block objects
            - pagination: {offset, limit, count, total_blocks, has_more, next_offset}
            - difficulty: Current difficulty
            - stats: Chain statistics
            - pending_transactions: (optional) List of pending tx
        """
        try:
            offset = request.args.get("offset", 0, type=int)
            limit = request.args.get("limit", 100, type=int)
            include_pending_param = request.args.get("include_pending", "").lower()
        except (ValueError, TypeError) as exc:
            return routes._error_response(
                f"Invalid query parameters: {exc}",
                status=400,
                code="invalid_params",
            )

        # Validate parameters
        if offset < 0:
            return routes._error_response(
                "offset must be non-negative",
                status=400,
                code="invalid_offset",
            )

        # Cap limit to prevent abuse
        max_limit = 500
        if limit < 1 or limit > max_limit:
            return routes._error_response(
                f"limit must be between 1 and {max_limit}",
                status=400,
                code="invalid_limit",
            )

        # Determine include_pending: default to True only for first page
        if include_pending_param in ("true", "1", "yes"):
            include_pending = True
        elif include_pending_param in ("false", "0", "no"):
            include_pending = False
        else:
            include_pending = (offset == 0)

        try:
            paginated_data = blockchain.to_dict_paginated(
                offset=offset,
                limit=limit,
                include_pending=include_pending,
            )
            return jsonify(paginated_data), 200
        except (ValueError, RuntimeError, AttributeError) as exc:
            return routes._error_response(
                f"Failed to get chain range: {exc}",
                status=500,
                code="chain_range_error",
            )

    @app.route("/block/receive", methods=["POST"])
    def receive_block() -> tuple[dict[str, Any], int]:
        """Receive a block from a peer node."""
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        ok, err, payload = routes._verify_signed_peer_message()
        if not ok:
            return routes._error_response(
                "Unauthorized P2P message",
                status=401,
                code=f"p2p_{err}",
            )

        if payload is None:
            return routes._error_response(
                "Invalid block payload",
                status=400,
                code="invalid_payload",
            )
        # Debug: log payload structure
        logger.info(
            "DEBUG receive_block: payload type=%s, keys=%s, preview=%s",
            type(payload).__name__,
            list(payload.keys()) if isinstance(payload, dict) else "N/A",
            str(payload)[:500],
            extra={"event": "p2p.block_receive_debug"}
        )
        # Support both nested format (with "header" key) and flat format (Block.to_dict())
        header = payload.get("header") if "header" in payload else payload
        required_header = ["index", "previous_hash", "merkle_root", "timestamp", "difficulty", "nonce"]
        if not isinstance(header, dict) or any(header.get(f) in (None, "") for f in required_header):
            return routes._error_response(
                "Invalid block payload",
                status=400,
                code="invalid_payload",
                context={"missing_header_fields": [f for f in required_header if not header or header.get(f) in (None, "")]},
            )

        try:
            block = Blockchain.deserialize_block(payload)
        except (ValueError, TypeError, KeyError) as exc:
            return routes._error_response(
                f"Invalid block data: {exc}",
                status=400,
                code="invalid_block",
                context={"error": str(exc)},
            )

        try:
            try:
                MetricsCollector.instance().record_p2p_message("received")
            except (RuntimeError, ValueError) as exc:  # pragma: no cover - metrics optional
                logger.debug("P2P metrics record failed: %s", type(exc).__name__)
            added = blockchain.add_block(block)
        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "receive_block")

        if added:
            return routes._success_response({"height": len(blockchain.chain)})
        return routes._error_response(
            "Block rejected",
            status=400,
            code="block_rejected",
        )

def _block_to_payload(block_obj: Any, fallback: Any | None = None) -> dict[str, Any] | None:
    """Return a JSON-serializable representation of a block."""
    payload_source = block_obj
    payload: dict[str, Any] | None
    if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
        payload = payload_source.to_dict()
    elif isinstance(payload_source, dict):
        payload = payload_source
    else:
        payload = None

    if not isinstance(payload, dict) and fallback is not None:
        fallback_src = fallback
        if hasattr(fallback_src, "to_dict") and callable(getattr(fallback_src, "to_dict", None)):
            payload = fallback_src.to_dict()
        elif isinstance(fallback_src, dict):
            payload = fallback_src

    if isinstance(payload, dict) and "index" not in payload:
        header = payload.get("header", {})
        if isinstance(header, dict) and "index" in header:
            payload["index"] = header["index"]
    return payload

def _build_block_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Construct a concise summary for a block response."""
    header = payload.get("header") if isinstance(payload.get("header"), dict) else {}

    def _first(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None

    transactions = payload.get("transactions")
    if isinstance(transactions, list):
        tx_count = len(transactions)
    elif isinstance(transactions, int):
        tx_count = max(transactions, 0)
    else:
        tx_count = 0

    return {
        "height": _first(payload.get("index"), header.get("index")),
        "hash": _first(payload.get("hash"), header.get("hash")),
        "timestamp": _first(payload.get("timestamp"), header.get("timestamp")),
        "difficulty": _first(payload.get("difficulty"), header.get("difficulty")),
        "miner": _first(payload.get("miner"), header.get("miner")),
        "transactions": tx_count,
    }

def _lookup_block_by_hash(blockchain: Any, block_hash: str, normalized: str) -> Any | None:
    """Lookup a block by hash via direct and chain iteration fallback."""
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
    return block_obj

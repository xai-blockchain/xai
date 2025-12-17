from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Any

from flask import jsonify, request

from xai.core.input_validation_schemas import NodeTransactionInput
from xai.core.request_validator_middleware import validate_request
from xai.core.monitoring import MetricsCollector

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_transaction_routes(routes: "NodeAPIRoutes") -> None:
    """Setup transaction-related routes."""
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/transactions", methods=["GET"])
    def get_pending_transactions() -> Dict[str, Any]:
        """Get pending transactions."""
        try:
            limit, offset = routes._get_pagination_params(default_limit=50, max_limit=500)
        except (ValueError, RuntimeError) as exc:
            return routes._error_response(
                str(exc),
                status=400,
                code="invalid_pagination",
                event_type="api.invalid_paging",
            )

        pending = list(getattr(blockchain, "pending_transactions", []) or [])
        total = len(pending)
        window = pending[offset : offset + limit]

        return jsonify(
            {
                "count": total,
                "limit": limit,
                "offset": offset,
                "transactions": [tx.to_dict() for tx in window],
            }
        )

    @app.route("/transaction/<txid>", methods=["GET"])
    def get_transaction(txid: str) -> Tuple[Dict[str, Any], int]:
        """Get transaction by ID."""
        chain = getattr(blockchain, "chain", [])
        chain_length = len(chain) if hasattr(chain, "__len__") else 0

        for i in range(chain_length):
            fallback_block = None
            try:
                fallback_block = chain[i]
            except IndexError as exc:
                logger.debug("Block %d not in chain cache: %s", i, type(exc).__name__)
                fallback_block = None

            block = None
            lookup = getattr(blockchain, "get_block", None)
            if callable(lookup):
                try:
                    block = lookup(i)
                except (LookupError, ValueError, TypeError) as exc:
                    logger.debug("get_block(%d) failed: %s", i, type(exc).__name__)
                    block = None
            if block is None and fallback_block is not None:
                block = fallback_block
            if not block:
                continue

            txs = getattr(block, "transactions", None)
            if txs is None and isinstance(block, dict):
                txs = block.get("transactions")
            if not isinstance(txs, (list, tuple)):
                if fallback_block is not None and fallback_block is not block:
                    block = fallback_block
                    txs = getattr(block, "transactions", None)
                    if txs is None and isinstance(block, dict):
                        txs = block.get("transactions")
                if not isinstance(txs, (list, tuple)):
                    continue

            for tx in txs:
                tx_identifier = getattr(tx, "txid", None)
                if tx_identifier is None and isinstance(tx, dict):
                    tx_identifier = tx.get("txid")
                if tx_identifier == txid:
                    tx_payload = tx.to_dict() if hasattr(tx, "to_dict") else tx
                    block_index = getattr(block, "index", i)
                    confirmations = chain_length - block_index
                    if confirmations < 0:
                        confirmations = 0
                    return (
                        jsonify(
                            {
                                "found": True,
                                "block": block_index,
                                "confirmations": confirmations,
                                "transaction": tx_payload,
                            }
                        ),
                        200,
                    )

        for tx in getattr(blockchain, "pending_transactions", []):
            tx_identifier = getattr(tx, "txid", None)
            if tx_identifier == txid:
                tx_payload = tx.to_dict() if hasattr(tx, "to_dict") else tx_identifier
                return (
                    jsonify({"found": True, "status": "pending", "transaction": tx_payload}),
                    200,
                )

        return jsonify({"found": False, "error": "Transaction not found"}), 404

    @app.route("/send", methods=["POST"])
    @validate_request(routes.request_validator, NodeTransactionInput)
    def send_transaction() -> Tuple[Dict[str, Any], int]:
        """Submit new transaction with strict validation and sanitized errors."""
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        paused = routes._reject_if_paused("send_transaction")
        if paused:
            return paused

        try:
            from xai.core.advanced_rate_limiter import get_rate_limiter as get_advanced_rate_limiter

            limiter = get_advanced_rate_limiter()
            allowed, error = limiter.check_rate_limit("/send")
            if not allowed:
                return routes._error_response(
                    error or "Rate limit exceeded",
                    status=429,
                    code="rate_limited",
                )
        except (ImportError, AttributeError, RuntimeError) as exc:
            logger.error(
                "Rate limiter unavailable for /send: %s",
                type(exc).__name__,
                extra={
                    "event": "api.rate_limiter_error",
                    "endpoint": "/send",
                    "client": request.remote_addr or "unknown",
                },
                exc_info=True,
            )
            return routes._error_response(
                "Rate limiting unavailable. Please retry later.",
                status=503,
                code="rate_limiter_unavailable",
            )

        model: Optional[NodeTransactionInput] = getattr(request, "validated_model", None)
        if model is None:
            payload = request.get_json(silent=True) or {}
            return routes._error_response(
                "Invalid transaction payload",
                status=400,
                code="invalid_payload",
                context={"payload": payload},
            )

        try:
            from xai.core.blockchain import Transaction
            from xai.core.config import Config

            tx = Transaction(
                sender=model.sender,
                recipient=model.recipient,
                amount=model.amount,
                fee=model.fee,
                public_key=model.public_key,
                nonce=model.nonce,
            )
            tx.signature = model.signature
            if model.metadata:
                tx.metadata = model.metadata

            now_ts = time.time()
            max_future = float(getattr(Config, "TX_MAX_FUTURE_SKEW_SECONDS", 120))
            max_age = float(getattr(Config, "TX_MAX_AGE_SECONDS", 86400))
            if model.timestamp > now_ts + max_future:
                routes._record_send_rejection("future_timestamp")
                return routes._error_response(
                    "Transaction timestamp too far in the future",
                    status=400,
                    code="future_timestamp",
                    context={"timestamp": model.timestamp, "now": now_ts},
                )
            if model.timestamp < now_ts - max_age:
                routes._record_send_rejection("stale_timestamp")
                return routes._error_response(
                    "Transaction timestamp too old",
                    status=400,
                    code="stale_timestamp",
                    context={"timestamp": model.timestamp, "age_seconds": now_ts - model.timestamp},
                )

            tx.timestamp = float(model.timestamp)
            expected_txid = tx.calculate_hash()
            if model.txid and model.txid != expected_txid:
                routes._record_send_rejection("txid_mismatch")
                return routes._error_response(
                    "Transaction hash mismatch",
                    status=400,
                    code="txid_mismatch",
                    context={"expected": expected_txid, "provided": model.txid},
                )
            tx.txid = expected_txid

            allowed, used, limit = routes.spending_limits.can_spend(model.sender, float(model.amount))
            if not allowed:
                return routes._error_response(
                    "Daily spending limit exceeded",
                    status=403,
                    code="spend_limit_exceeded",
                    context={
                        "sender": model.sender,
                        "used_today": used,
                        "limit": limit,
                        "requested": float(model.amount),
                    },
                )

            # Verify signature - now raises exceptions
            try:
                verification_result = tx.verify_signature()
            except Exception as e:
                # Import signature verification exceptions
                from xai.core.transaction import (
                    SignatureVerificationError,
                    MissingSignatureError,
                    InvalidSignatureError,
                    SignatureCryptoError
                )

                if isinstance(e, MissingSignatureError):
                    return routes._error_response(
                        "Missing signature or public key",
                        status=400,
                        code="missing_signature",
                        context={"sender": model.sender, "error": str(e)}
                    )
                elif isinstance(e, InvalidSignatureError):
                    return routes._error_response(
                        "Invalid signature",
                        status=400,
                        code="invalid_signature",
                        context={"sender": model.sender, "error": str(e)}
                    )
                elif isinstance(e, SignatureCryptoError):
                    return routes._error_response(
                        "Signature verification error",
                        status=500,
                        code="crypto_error",
                        context={"sender": model.sender, "error": str(e)}
                    )
                else:
                    # Unexpected error
                    return routes._error_response(
                        "Unexpected signature verification error",
                        status=500,
                        code="verification_error",
                        context={"sender": model.sender, "error": str(e)}
                    )
            else:
                if verification_result is False:
                    return routes._error_response(
                        "Invalid signature",
                        status=400,
                        code="invalid_signature",
                        context={"sender": model.sender},
                    )

            if blockchain.add_transaction(tx):
                try:
                    routes.spending_limits.record_spend(model.sender, float(model.amount))
                except (ValueError, RuntimeError) as exc:
                    logger.warning(
                        "Failed to record spending limit for transaction",
                        extra={"error": str(exc), "sender": model.sender, "event": "spending_limits.record_failed"},
                    )
                routes.node.broadcast_transaction(tx)
                return routes._success_response(
                    {
                        "txid": tx.txid,
                        "message": "Transaction submitted successfully",
                    }
                )

            return routes._error_response(
                "Transaction validation failed",
                status=400,
                code="transaction_rejected",
                context={"sender": model.sender, "recipient": model.recipient},
            )
        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "send_transaction")

    @app.route("/transaction/receive", methods=["POST"])
    def receive_transaction() -> Tuple[Dict[str, Any], int]:
        """Receive a broadcasted transaction from a peer node."""
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        paused = routes._reject_if_paused("receive_transaction")
        if paused:
            return paused

        ok, err, payload = routes._verify_signed_peer_message()
        if not ok:
            return routes._error_response(
                "Unauthorized P2P message",
                status=401,
                code=f"p2p_{err}",
            )

        if payload is None:
            return routes._error_response(
                "Invalid transaction payload",
                status=400,
                code="invalid_payload",
            )
        required = ["sender", "recipient", "amount", "public_key", "signature", "nonce"]
        missing = [field for field in required if payload.get(field) in (None, "")]
        if missing:
            return routes._error_response(
                "Invalid transaction payload",
                status=400,
                code="invalid_payload",
                context={"missing": missing},
            )

        try:
            from xai.core.blockchain import Transaction

            tx = Transaction(
                sender=payload.get("sender"),
                recipient=payload.get("recipient"),
                amount=payload.get("amount"),
                fee=payload.get("fee"),
                public_key=payload.get("public_key"),
                tx_type=payload.get("tx_type"),
                nonce=payload.get("nonce"),
                inputs=payload.get("inputs"),
                outputs=payload.get("outputs"),
            )
            tx.timestamp = payload.get("timestamp") or time.time()
            tx.signature = payload.get("signature")
            tx.txid = payload.get("txid") or tx.calculate_hash()
            if payload.get("metadata"):
                tx.metadata = payload.get("metadata")
        except (ValueError, TypeError, KeyError) as exc:
            return routes._error_response(
                "Invalid transaction data",
                status=400,
                code="invalid_transaction",
                context={"sender": payload.get("sender"), "error": str(exc)},
            )

        try:
            try:
                MetricsCollector.instance().record_p2p_message("received")
            except (RuntimeError, ValueError) as exc:
                logger.debug("P2P metrics record failed: %s", type(exc).__name__)
            accepted = blockchain.add_transaction(tx)
        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "receive_transaction")

        if accepted:
            return routes._success_response({"txid": tx.txid})
        return routes._error_response(
            "Transaction rejected",
            status=400,
            code="transaction_rejected",
            context={"sender": payload.get("sender"), "txid": tx.txid},
        )

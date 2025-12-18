"""
Wallet API Blueprint

Handles wallet-related endpoints: balance, nonce, history, faucet.
Extracted from node_api.py as part of god class refactoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request

from pydantic import ValidationError as PydanticValidationError

from xai.core.api_blueprints.base import (
    PaginationError,
    error_response,
    get_blockchain,
    get_node,
    get_pagination_params,
    handle_exception,
    require_api_auth,
    success_response,
)
from xai.core.config import Config, NetworkType
from xai.core.rate_limiter import get_rate_limiter
from xai.core.input_validation_schemas import FaucetClaimInput

logger = logging.getLogger(__name__)

wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/balance/<address>", methods=["GET"])
def get_balance(address: str) -> Dict[str, Any]:
    """Get address balance."""
    blockchain = get_blockchain()
    balance = blockchain.get_balance(address)
    return jsonify({"address": address, "balance": balance})


@wallet_bp.route("/address/<address>/nonce", methods=["GET"])
def get_address_nonce(address: str) -> Tuple[Dict[str, Any], int]:
    """Return confirmed and next nonce for an address."""
    blockchain = get_blockchain()
    tracker = getattr(blockchain, "nonce_tracker", None)
    if tracker is None:
        return error_response(
            "Nonce tracker unavailable",
            status=503,
            code="nonce_tracker_unavailable",
        )

    try:
        confirmed = tracker.get_nonce(address)
        next_nonce = tracker.get_next_nonce(address)
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid nonce lookup request: %s",
            str(exc),
            extra={"event": "api.nonce_invalid_request", "address": address},
            exc_info=True,
        )
        return error_response(f"Invalid nonce request: {exc}", status=400, code="invalid_request")
    except (OSError, IOError) as exc:
        logger.error(
            "Storage error during nonce lookup: %s",
            str(exc),
            extra={"event": "api.nonce_storage_error", "address": address},
            exc_info=True,
        )
        return error_response("Storage error", status=500, code="storage_error")
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in get_address_nonce",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "get_address_nonce"
            }
        )
        return handle_exception(exc, "nonce_lookup")

    pending_nonce = next_nonce - 1 if next_nonce - 1 > confirmed else None
    return (
        jsonify(
            {
                "address": address,
                "confirmed_nonce": max(confirmed, -1),
                "next_nonce": next_nonce,
                "pending_nonce": pending_nonce,
            }
        ),
        200,
    )


@wallet_bp.route("/history/<address>", methods=["GET"])
def get_history(address: str) -> Dict[str, Any]:
    """Get transaction history for address."""
    blockchain = get_blockchain()
    try:
        limit, offset = get_pagination_params(default_limit=50, max_limit=500)
    except PaginationError as exc:
        logger.warning(
            "PaginationError in get_history",
            extra={
                "error_type": "PaginationError",
                "error": str(exc),
                "function": "get_history"
            }
        )
        return error_response(
            str(exc),
            status=400,
            code="invalid_pagination",
            event_type="api.invalid_paging",
        )

    try:
        window, total = blockchain.get_transaction_history_window(address, limit, offset)
    except ValueError as exc:
        logger.warning(
            "ValueError in get_history",
            extra={
                "error_type": "ValueError",
                "error": str(exc),
                "function": "get_history"
            }
        )
        return error_response(
            str(exc),
            status=400,
            code="invalid_pagination",
            event_type="api.invalid_paging",
        )

    return jsonify(
        {
            "address": address,
            "transaction_count": total,
            "limit": limit,
            "offset": offset,
            "transactions": window,
        }
    )


def _record_faucet_metric(success: bool) -> None:
    """Update faucet metrics without failing requests if monitoring is unavailable."""
    node = get_node()
    metrics = getattr(node, "metrics_collector", None) if node else None
    if not metrics:
        return

    record = getattr(metrics, "record_faucet_result", None)
    if callable(record):
        record(success)


@wallet_bp.route("/faucet/claim", methods=["POST"])
def claim_faucet() -> Tuple[Dict[str, Any], int]:
    """Queue a faucet transaction for the provided testnet address."""
    node = get_node()

    auth_error = require_api_auth()
    if auth_error:
        return auth_error
    if not getattr(Config, "FAUCET_ENABLED", False):
        _record_faucet_metric(success=False)
        return error_response(
            "Faucet is disabled on this network",
            status=403,
            code="faucet_disabled",
        )

    network = getattr(Config, "NETWORK_TYPE", NetworkType.TESTNET)
    if network != NetworkType.TESTNET:
        _record_faucet_metric(success=False)
        return error_response(
            "Faucet is only available on the testnet",
            status=403,
            code="faucet_unavailable",
        )

    payload = request.get_json(silent=True) or {}
    try:
        model = FaucetClaimInput.parse_obj(payload)
    except PydanticValidationError as exc:
        logger.warning(
            "PydanticValidationError in claim_faucet",
            extra={
                "error_type": "PydanticValidationError",
                "error": str(exc),
                "function": "claim_faucet"
            }
        )
        _record_faucet_metric(success=False)
        return error_response(
            "Invalid faucet request",
            status=400,
            code="invalid_payload",
            context={"errors": exc.errors()},
        )

    address = model.address

    expected_prefix = getattr(Config, "ADDRESS_PREFIX", "")
    if expected_prefix and not address.startswith(expected_prefix):
        _record_faucet_metric(success=False)
        return error_response(
            f"Invalid address for this network. Expected prefix {expected_prefix}.",
            status=400,
            code="invalid_address",
            context={"address": address, "expected_prefix": expected_prefix},
        )

    amount = float(getattr(Config, "FAUCET_AMOUNT", 0.0) or 0.0)
    if amount <= 0:
        _record_faucet_metric(success=False)
        return error_response(
            "Faucet amount is not configured",
            status=503,
            code="faucet_misconfigured",
        )

    limiter = get_rate_limiter()
    identifier = f"{address}:{request.remote_addr or 'unknown'}"
    allowed, rate_error = limiter.check_rate_limit(identifier, "/faucet/claim")
    if not allowed:
        _record_faucet_metric(success=False)
        return error_response(
            rate_error or "Rate limit exceeded",
            status=429,
            code="rate_limited",
            context={"address": address, "identifier": identifier},
        )

    try:
        faucet_tx = node.queue_faucet_transaction(address, amount)
    except ValueError as exc:
        _record_faucet_metric(success=False)
        logger.error(
            "Invalid faucet transaction: %s",
            str(exc),
            extra={"event": "api.faucet_invalid_transaction", "address": address, "amount": amount},
            exc_info=True,
        )
        return error_response(f"Invalid transaction: {exc}", status=400, code="invalid_transaction")
    except (OSError, IOError) as exc:
        _record_faucet_metric(success=False)
        logger.error(
            "Storage error queuing faucet transaction: %s",
            str(exc),
            extra={"event": "api.faucet_storage_error", "address": address, "amount": amount},
            exc_info=True,
        )
        return error_response("Storage error", status=500, code="storage_error")
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in claim_faucet",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "claim_faucet"
            }
        )
        _record_faucet_metric(success=False)
        return handle_exception(exc, "faucet_queue")

    _record_faucet_metric(success=True)
    return success_response(
        {
            "amount": amount,
            "txid": getattr(faucet_tx, "txid", None),
            "message": (
                f"Testnet faucet claim successful! {amount} XAI will be added to your "
                "address after the next block."
            ),
            "note": "This is testnet XAI - it has no real value!",
        }
    )

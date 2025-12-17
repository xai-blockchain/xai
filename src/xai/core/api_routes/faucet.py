from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


from typing import TYPE_CHECKING, Dict, Optional, Tuple, Any

from flask import request, jsonify
from pydantic import ValidationError as PydanticValidationError

from xai.core.input_validation_schemas import FaucetClaimInput
from xai.core.config import Config, NetworkType
if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_faucet_routes(
    routes: "NodeAPIRoutes",
    *,
    simple_rate_limiter_getter,
    advanced_rate_limiter_getter=None,
) -> None:
    app = routes.app

    @app.route("/faucet/claim", methods=["POST"])
    def claim_faucet() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        if not getattr(Config, "FAUCET_ENABLED", False):
            routes._record_faucet_metric(success=False)
            return routes._error_response(
                "Faucet is disabled on this network",
                status=403,
                code="faucet_disabled",
            )

        network = getattr(Config, "NETWORK_TYPE", NetworkType.TESTNET)
        if network != NetworkType.TESTNET:
            routes._record_faucet_metric(success=False)
            return routes._error_response(
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
                    "function": "claim_faucet",
                },
            )
            routes._record_faucet_metric(success=False)
            return routes._error_response(
                "Invalid faucet request",
                status=400,
                code="invalid_payload",
                context={"errors": exc.errors()},
            )

        address = model.address
        expected_prefix = getattr(Config, "ADDRESS_PREFIX", "")
        if expected_prefix and not address.startswith(expected_prefix):
            routes._record_faucet_metric(success=False)
            return routes._error_response(
                f"Invalid address for this network. Expected prefix {expected_prefix}.",
                status=400,
                code="invalid_address",
                context={"address": address, "expected_prefix": expected_prefix},
            )

        amount = float(getattr(Config, "FAUCET_AMOUNT", 0.0) or 0.0)
        if amount <= 0:
            routes._record_faucet_metric(success=False)
            return routes._error_response(
                "Faucet amount is not configured",
                status=503,
                code="faucet_misconfigured",
            )

        identifier = f"{address}:{request.remote_addr or 'unknown'}"
        limiter = simple_rate_limiter_getter()
        if not limiter and callable(advanced_rate_limiter_getter):
            limiter = advanced_rate_limiter_getter()
        allowed, error = (True, None)
        if limiter:
            allowed, error = limiter.check_rate_limit(identifier, "/faucet/claim")
        if not allowed:
            routes._record_faucet_metric(success=False)
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"address": address, "identifier": identifier},
            )

        try:
            faucet_tx = routes.node.queue_faucet_transaction(address, amount)
        except (ValueError, RuntimeError) as exc:
            routes._record_faucet_metric(success=False)
            return routes._handle_exception(exc, "faucet_queue")

        routes._record_faucet_metric(success=True)
        return routes._success_response(
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

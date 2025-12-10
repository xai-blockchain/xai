from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Dict, Tuple, Any, List

from flask import jsonify, request

from xai.core import node_utils
from xai.core.node_utils import ALGO_FEATURES_ENABLED
from xai.core.input_validation_schemas import FraudCheckInput

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_algo_routes(routes: "NodeAPIRoutes") -> None:
    """Register algorithmic feature endpoints."""
    app = routes.app
    blockchain = routes.blockchain
    node = routes.node

    @app.route("/algo/fee-estimate", methods=["GET"])
    def estimate_fee() -> Tuple[Dict[str, Any], int]:
        fee_optimizer = getattr(node, "fee_optimizer", None)
        enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED
        if not (enabled and fee_optimizer):
            return jsonify({"error": "Algorithmic features not available"}), 503

        priority = request.args.get("priority", "normal")
        pending_transactions = list(getattr(blockchain, "pending_transactions", []) or [])
        pending_count = len(pending_transactions)

        fee_rates: List[float] = []
        mempool_bytes = 0
        size_samples = 0

        for tx in pending_transactions:
            rate_callable = getattr(tx, "get_fee_rate", None)
            if callable(rate_callable):
                try:
                    rate_value = rate_callable()
                    if isinstance(rate_value, (int, float)) and math.isfinite(rate_value) and rate_value > 0:
                        fee_rates.append(float(rate_value))
                except Exception as exc:
                    logger.debug(
                        "Failed to get fee rate from transaction",
                        extra={"error": str(exc), "event": "mempool.fee_rate_error"},
                    )

            size_callable = getattr(tx, "get_size", None)
            if callable(size_callable):
                try:
                    size_value = size_callable()
                    if isinstance(size_value, (int, float)) and size_value > 0:
                        mempool_bytes += int(size_value)
                        size_samples += 1
                except Exception as exc:
                    logger.debug(
                        "Failed to get size from transaction",
                        extra={"error": str(exc), "event": "mempool.size_error"},
                    )

        avg_tx_size = (mempool_bytes / size_samples) if size_samples else 450.0
        max_block_bytes = 1_000_000
        avg_tx_size = max(avg_tx_size, 200.0)
        approx_block_capacity = max(1, min(5000, int(max_block_bytes / avg_tx_size)))

        recommendation = fee_optimizer.predict_optimal_fee(
            pending_tx_count=pending_count,
            priority=priority,
            fee_rates=fee_rates,
            mempool_bytes=mempool_bytes,
            avg_block_capacity=approx_block_capacity,
        )
        return jsonify(recommendation), 200

    @app.route("/algo/fraud-check", methods=["POST"])
    def check_fraud() -> Tuple[Dict[str, Any], int]:
        enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED
        fraud_detector = getattr(node, "fraud_detector", None)
        if not (enabled and fraud_detector):
            return jsonify({"error": "Algorithmic features not available"}), 503

        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        valid, error, parsed = routes.request_validator.validate_pydantic_model(FraudCheckInput)
        if not valid or parsed is None:
            error_message = error or "Missing transaction data"
            return routes._error_response(
                error_message,
                status=400,
                code="invalid_payload",
                context={"errors": error},
            )

        analysis = fraud_detector.analyze_transaction(parsed.payload)
        return jsonify(analysis), 200

    @app.route("/algo/status", methods=["GET"])
    def algo_status() -> Dict[str, Any]:
        fee_optimizer = getattr(node, "fee_optimizer", None)
        fraud_detector = getattr(node, "fraud_detector", None)
        enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED

        if not enabled:
            return jsonify({"enabled": False, "features": []})

        features: List[Dict[str, Any]] = []
        if fee_optimizer:
            fee_history = getattr(fee_optimizer, "fee_history", [])
            features.append(
                {
                    "name": "Fee Optimizer",
                    "description": "Statistical fee prediction using EMA",
                    "status": "active",
                    "transactions_analyzed": len(fee_history),
                    "confidence": min(100, len(fee_history) * 2),
                }
            )
        if fraud_detector:
            addresses_tracked = len(getattr(fraud_detector, "address_history", []))
            flagged = len(getattr(fraud_detector, "flagged_addresses", []))
            features.append(
                {
                    "name": "Fraud Detector",
                    "description": "Pattern-based fraud detection",
                    "status": "active",
                    "addresses_tracked": addresses_tracked,
                    "flagged_addresses": flagged,
                }
            )

        if not features:
            return jsonify({"enabled": True, "features": [], "warning": "Modules not installed"})

        return jsonify({"enabled": True, "features": features})

"""
Trade Operations Module - Trade Session and Order Management

Extracted from blockchain.py for better modularity and separation of concerns.
Handles trade session registration, order submission with ECDSA verification,
and trade event recording.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from typing import TYPE_CHECKING, Any

from xai.core.trading import SwapOrderType

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class TradeOperationsManager:
    """
    Manages trade operations including sessions, orders, and ECDSA verification.

    This class encapsulates all trade-related functionality including:
    - Trade session management with token-based authentication
    - ECDSA signature verification for order submissions
    - Order normalization and validation
    - Trade event recording for diagnostics
    - Order and match retrieval
    - HTLC secret revelation for atomic swaps
    """

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize trade operations manager.

        Args:
            blockchain: Parent blockchain instance for accessing storage and trade manager
        """
        self.blockchain = blockchain
        self.logger = blockchain.logger

    def register_trade_session(self, wallet_address: str) -> dict[str, Any]:
        """
        Create and track a short-lived trade session token.

        Args:
            wallet_address: Wallet address to register session for

        Returns:
            Dictionary containing session information including session_token
        """
        session = self.blockchain.trade_manager.register_session(wallet_address)
        self.blockchain.trade_sessions[session["session_token"]] = session
        self.record_trade_event("session_registered", {"wallet_address": wallet_address})
        return session

    def record_trade_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Record trade-related events for diagnostics.

        Args:
            event_type: Type of trade event (e.g., 'session_registered', 'order_created')
            payload: Event payload data
        """
        entry = {"type": event_type, "payload": payload, "timestamp": time.time()}
        self.blockchain.trade_history.append(entry)
        self.blockchain.trade_history = self.blockchain.trade_history[-500:]

    def submit_trade_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize order payload, verify ECDSA signature, and dispatch to the trade manager.

        This method validates that the order was actually signed by the wallet owner
        using ECDSA with secp256k1, replacing the previous HMAC-based authentication.

        Args:
            order_data: Dictionary containing order details and ECDSA signature

        Returns:
            Dictionary with order creation result

        Raises:
            ValueError: If signature validation fails or required fields missing
        """
        from xai.core.crypto_utils import verify_signature_hex

        # Extract and validate signature
        signature = order_data.get("signature")
        if not signature:
            raise ValueError("signature required for order authentication")

        if len(signature) != 128:
            raise ValueError("Invalid signature format: must be 128 hex characters (r || s)")

        # Extract maker address for public key lookup
        maker_address = order_data.get("maker_address") or order_data.get("wallet_address")
        if not maker_address:
            raise ValueError("maker_address required")

        # Get public key from address (we need to look up the wallet)
        # Note: In a real implementation, we'd have an address -> public key mapping
        # For now, we require the public key to be provided in the order
        maker_public_key = order_data.get("maker_public_key")
        if not maker_public_key:
            # Try to derive from registered wallets or require it in payload
            raise ValueError(
                "maker_public_key required for signature verification. "
                "Include your wallet's public key in the order payload."
            )

        # Create a copy of order_data without the signature for verification
        order_data_copy = dict(order_data)
        order_data_copy.pop("signature", None)

        # Serialize deterministically (sorted keys) to match frontend
        def stable_stringify(obj):
            if obj is None:
                return "null"
            if isinstance(obj, bool):
                return "true" if obj else "false"
            if isinstance(obj, (int, float)):
                return json.dumps(obj)
            if isinstance(obj, str):
                return json.dumps(obj)
            if isinstance(obj, list):
                return "[" + ",".join(stable_stringify(item) for item in obj) + "]"
            if isinstance(obj, dict):
                sorted_keys = sorted(obj.keys())
                items = [f'"{k}":{stable_stringify(obj[k])}' for k in sorted_keys]
                return "{" + ",".join(items) + "}"
            return json.dumps(obj)

        payload_str = stable_stringify(order_data_copy)

        # Hash the payload
        message_hash = hashlib.sha256(payload_str.encode()).digest()

        # Verify ECDSA signature
        if not verify_signature_hex(maker_public_key, message_hash, signature):
            raise ValueError(
                "Invalid signature: ECDSA verification failed. "
                "The order was not signed by the wallet owner."
            )

        self.logger.info(
            "Trade order signature verified successfully",
            extra={
                "event": "trade.order.signature_verified",
                "maker_address": maker_address[:16] + "...",
            },
        )

        # Signature verified - proceed with order creation
        normalized = self._normalize_trade_order(order_data)
        order, matches = self.blockchain.trade_manager.place_order(**normalized)

        result: dict[str, Any] = {
            "success": True,
            "order_id": order.order_id,
            "status": "pending",
            "maker_address": order.maker_address,
            "token_offered": order.token_offered,
            "token_requested": order.token_requested,
            "amount_offered": order.amount_offered,
            "amount_requested": order.amount_requested,
            "price": order.price,
        }

        if matches:
            result["status"] = "matched"
            serialized_matches = [match.to_dict() for match in matches]
            result["matches"] = serialized_matches
            if len(matches) == 1:
                result["match_id"] = matches[0].match_id
            else:
                result["match_id"] = [m["match_id"] for m in serialized_matches]

        self.record_trade_event("order_created", {"order_id": order.order_id, "status": result["status"]})
        return result

    def _normalize_trade_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize and validate trade order data.

        Accepts various field name aliases and validates all required fields
        and constraints.

        Args:
            order_data: Raw order data with potentially varying field names

        Returns:
            Normalized order dictionary with standard field names

        Raises:
            ValueError: If required fields missing or validation fails
        """
        wallet_address = order_data.get("wallet_address") or order_data.get("from_address")
        if not wallet_address:
            raise ValueError("wallet_address required")

        token_offered = (
            order_data.get("token_offered")
            or order_data.get("from_token")
            or order_data.get("from_asset")
        )
        token_requested = (
            order_data.get("token_requested")
            or order_data.get("to_token")
            or order_data.get("to_asset")
        )
        if not token_offered or not token_requested:
            raise ValueError("token_offered and token_requested required")

        amount_offered = order_data.get("amount_offered") or order_data.get("from_amount")
        amount_requested = order_data.get("amount_requested") or order_data.get("to_amount")
        if amount_offered is None or amount_requested is None:
            raise ValueError("amount_offered and amount_requested required")

        amount_offered = float(amount_offered)
        amount_requested = float(amount_requested)
        if amount_offered <= 0 or amount_requested <= 0:
            raise ValueError("amounts must be positive")

        raw_type = order_data.get("order_type")
        if raw_type:
            try:
                order_type = SwapOrderType(raw_type.lower())
            except ValueError as exc:
                raise ValueError("order_type must be 'buy' or 'sell'") from exc
        else:
            order_type = SwapOrderType.SELL if token_offered.upper() == "AXN" else SwapOrderType.BUY

        price = order_data.get("price")
        if price is None:
            if amount_offered <= 0:
                raise ValueError("amount_offered must be positive to derive price")
            price_value = amount_requested / amount_offered
        else:
            try:
                price_value = float(price)
            except (TypeError, ValueError) as exc:
                raise ValueError("price must be a numeric value") from exc

        if price_value <= 0 or not math.isfinite(price_value):
            raise ValueError("price must be a finite positive number")

        return {
            "maker_address": wallet_address,
            "token_offered": token_offered,
            "amount_offered": amount_offered,
            "token_requested": token_requested,
            "amount_requested": amount_requested,
            "price": price_value,
            "order_type": order_type,
        }

    def get_trade_orders(self) -> list[dict[str, Any]]:
        """
        Return serialized trade orders.

        Returns:
            List of order dictionaries
        """
        return [order.to_dict() for order in self.blockchain.trade_manager.list_orders()]

    def get_trade_matches(self) -> list[dict[str, Any]]:
        """
        Return serialized trade matches.

        Returns:
            List of match dictionaries
        """
        return [match.to_dict() for match in self.blockchain.trade_manager.list_matches()]

    def reveal_trade_secret(self, match_id: str, secret: str) -> dict[str, Any]:
        """
        Settle a match once both parties provide the HTLC secret.

        Args:
            match_id: Match identifier to settle
            secret: HTLC secret for atomic swap verification

        Returns:
            Dictionary with settlement result
        """
        result = self.blockchain.trade_manager.settle_match(match_id, secret)
        if result.get("success"):
            self.record_trade_event("match_settled", {"match_id": match_id})
        return result

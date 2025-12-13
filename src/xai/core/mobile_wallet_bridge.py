"""
Mobile wallet bridge helpers.

Allows constrained devices to request unsigned transactions, display them
as QR/USB payloads, and later submit signed transactions for broadcasting.

Security Note:
    This bridge facilitates air-gapped signing workflows where the signing
    device never directly connects to the network. Transaction drafts are
    encoded as QR codes or transferred via USB for offline signing.
"""

import base64
import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from xai.core.blockchain import Transaction

logger = logging.getLogger(__name__)

DEFAULT_BLOCK_CAPACITY = 500


class MobileWalletBridge:
    """Draft/commit flow for mobile wallets and air-gapped signers."""

    DEFAULT_EXPIRY_SECONDS = 15 * 60  # 15 minutes

    def __init__(self, blockchain, validator, fee_optimizer=None):
        self.blockchain = blockchain
        self.validator = validator
        self.fee_optimizer = fee_optimizer
        self._drafts: Dict[str, Dict[str, Any]] = {}
        self.expiry_seconds = self.DEFAULT_EXPIRY_SECONDS

    def create_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create an unsigned transaction draft."""
        self._purge_expired()

        sender = payload.get("sender", "").strip()
        recipient = payload.get("recipient", "").strip()
        amount = payload.get("amount")
        priority = (payload.get("priority") or "normal").lower()
        memo = payload.get("memo")
        metadata = payload.get("metadata") or {}
        client_id = payload.get("client_id")
        defer_congestion = payload.get("defer_until_congestion_below")

        if not sender or not recipient:
            raise ValueError("sender and recipient are required")

        try:
            self.validator.validate_address(sender, "sender")
            self.validator.validate_address(recipient, "recipient")
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            raise ValueError(str(exc))

        try:
            amount = self.validator.validate_amount(float(amount), "amount")
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            raise ValueError(str(exc))

        if sender in self._active_drafts_for_sender(sender):
            # Only one outstanding draft per sender (matches nonce sequencing)
            raise ValueError(
                "Existing draft pending for this sender. Commit or cancel it before creating another."
            )

        nonce = self.blockchain.nonce_tracker.get_next_nonce(sender)
        fee_quote = self._get_fee_quote(priority)
        timestamp = time.time()

        unsigned_tx = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "fee": fee_quote["recommended_fee"],
            "nonce": nonce,
            "priority": priority,
            "memo": memo,
            "metadata": metadata,
            "timestamp": timestamp,
            "fee_telemetry": fee_quote.get("telemetry"),
        }

        draft_id = str(uuid.uuid4())
        qr_payload = base64.b64encode(json.dumps(unsigned_tx, sort_keys=True).encode()).decode()

        self._drafts[draft_id] = {
            "unsigned_tx": unsigned_tx,
            "created_at": timestamp,
            "client_id": client_id,
            "fee_quote": fee_quote,
            "defer_until_congestion_below": defer_congestion,
            "status": "draft",
        }

        return {
            "draft_id": draft_id,
            "unsigned_transaction": unsigned_tx,
            "fee_quote": fee_quote,
            "qr_payload": qr_payload,
            "expires_at": timestamp + self.expiry_seconds,
            "defer_until_congestion_below": defer_congestion,
        }

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        self._purge_expired()
        draft = self._drafts.get(draft_id)
        if not draft:
            return None

        remaining = max(0, draft["created_at"] + self.expiry_seconds - time.time())
        return {
            "draft_id": draft_id,
            "unsigned_transaction": draft["unsigned_tx"],
            "fee_quote": draft["fee_quote"],
            "status": draft["status"],
            "expires_in": remaining,
        }

    def commit_draft(self, draft_id: str, signature: str, public_key: str) -> Transaction:
        self._purge_expired()
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError("Draft not found or expired")

        unsigned_tx = draft["unsigned_tx"]
        tx = Transaction(
            sender=unsigned_tx["sender"],
            recipient=unsigned_tx["recipient"],
            amount=float(unsigned_tx["amount"]),
            fee=float(unsigned_tx["fee"]),
            nonce=unsigned_tx["nonce"],
            metadata=unsigned_tx.get("metadata") or {},
        )
        tx.timestamp = unsigned_tx["timestamp"]
        tx.public_key = public_key
        tx.signature = signature
        tx.tx_type = "mobile"

        if not tx.verify_signature():
            raise ValueError("Signature verification failed")

        tx.txid = tx.calculate_hash()

        if not self.blockchain.add_transaction(tx):
            raise ValueError("Failed to queue transaction—see node logs for details")

        draft["status"] = "submitted"
        draft["submitted_txid"] = tx.txid
        # Keep the draft around briefly so status queries show completion.
        draft["created_at"] = time.time()

        return tx

    def _get_fee_quote(self, priority: str) -> Dict[str, Any]:
        """
        Get fee quote for transaction.

        Uses fee optimizer if available, falls back to basic calculation.

        Args:
            priority: Transaction priority (low, normal, high)

        Returns:
            Fee quote dictionary with recommended_fee and conditions
        """
        pending = len(self.blockchain.pending_transactions)
        optimizer_quote: Optional[Dict[str, Any]] = None
        if self.fee_optimizer:
            try:
                optimizer_quote = self.fee_optimizer.predict_optimal_fee(
                    pending_tx_count=pending,
                    priority=priority,
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.warning(
                    "Fee optimizer failed, using fallback calculation",
                    extra={
                        "event": "mobile_bridge.fee_optimizer_error",
                        "error_type": type(e).__name__,
                        "priority": priority,
                    },
                )

        if optimizer_quote and optimizer_quote.get("success", True):
            telemetry = {
                "congestion_level": optimizer_quote.get("congestion_level"),
                "fee_percentiles": optimizer_quote.get("fee_percentiles") or {},
                "pressure": optimizer_quote.get("pressure") or {},
                "mempool_bytes": optimizer_quote.get("mempool_bytes"),
                "estimated_confirmation_blocks": optimizer_quote.get("estimated_confirmation_blocks"),
            }
            recommended_fee = optimizer_quote.get("recommended_fee")
            if recommended_fee is None:
                recommended_fee = optimizer_quote.get("recommended_fee_per_byte")
            try:
                fee_value = float(recommended_fee)
            except (TypeError, ValueError):
                fee_value = None
            if fee_value is not None:
                return {
                    "recommended_fee": fee_value,
                    "conditions": {
                        "priority": priority,
                        "pending_transactions": pending,
                        "congestion_level": telemetry.get("congestion_level"),
                    },
                    "confidence": optimizer_quote.get("confidence"),
                    "telemetry": telemetry,
                }

        base_fee = Decimal("0.05")
        if priority == "high":
            base_fee *= Decimal("1.5")
        elif priority == "low":
            base_fee *= Decimal("0.75")

        congestion = min(pending / 100.0, 2.0)
        recommended_fee = float(
            (base_fee * (1 + Decimal(str(congestion)))).quantize(Decimal("0.00000001"))
        )
        backlog_ratio = pending / DEFAULT_BLOCK_CAPACITY if DEFAULT_BLOCK_CAPACITY else pending
        telemetry = {
            "congestion_level": self._classify_congestion(backlog_ratio),
            "fee_percentiles": {},
            "pressure": {
                "backlog_ratio": round(backlog_ratio, 3),
                "block_capacity": DEFAULT_BLOCK_CAPACITY,
            },
            "mempool_bytes": None,
            "estimated_confirmation_blocks": max(1, int(backlog_ratio + 1)),
        }

        return {
            "recommended_fee": recommended_fee,
            "conditions": {
                "priority": priority,
                "pending_transactions": pending,
                "congestion_factor": round(congestion, 2),
            },
            "confidence": min(1.0, 0.5 + pending / 1000.0),
            "telemetry": telemetry,
        }

    @staticmethod
    def _classify_congestion(backlog_ratio: float) -> str:
        if backlog_ratio < 0.5:
            return "low"
        if backlog_ratio < 1.0:
            return "moderate"
        if backlog_ratio < 2.0:
            return "high"
        return "critical"

    def _active_drafts_for_sender(self, sender: str) -> List[str]:
        return [
            draft_id
            for draft_id, draft in self._drafts.items()
            if draft["unsigned_tx"]["sender"] == sender and draft["status"] == "draft"
        ]

    def _purge_expired(self):
        if not self._drafts:
            return
        now = time.time()
        expired = [
            draft_id
            for draft_id, draft in self._drafts.items()
            if draft["status"] == "draft" and (now - draft["created_at"]) > self.expiry_seconds
        ]
        for draft_id in expired:
            self._drafts.pop(draft_id, None)

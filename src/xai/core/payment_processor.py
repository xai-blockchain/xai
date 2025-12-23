from __future__ import annotations

"""
Lightweight PaymentProcessor shim to satisfy blockchain imports without external dependencies.
"""

import os
import time
from decimal import Decimal
from enum import Enum

class RefundReason(Enum):
    """Reasons for payment refunds"""
    DUPLICATE_PAYMENT = "duplicate_payment"
    CUSTOMER_REQUEST = "customer_request"
    FRAUDULENT = "fraudulent"
    SERVICE_NOT_PROVIDED = "service_not_provided"
    PROCESSING_ERROR = "processing_error"
    OTHER = "other"

class RefundStatus(Enum):
    """Status of refund processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentProcessor:
    """Simplified payment processor emulation for tests."""

    def __init__(self, stripe_api_key: str | None = None):
        self.stripe_api_key = stripe_api_key or os.getenv("STRIPE_API_KEY")
        self.test_mode = True if not self.stripe_api_key else False
        self.axn_usd_price = Decimal("0.0512")
        self.min_purchase_usd = Decimal("10.00")
        self.max_purchase_usd = Decimal("10000.00")
        self.credit_card_fee_percent = Decimal("0.029")
        self.credit_card_fee_fixed = Decimal("0.30")

        # Refund tracking (Task 108)
        self.payment_history: dict[str, Dict] = {}
        self.refund_history: list[Dict] = []
        self.refund_time_window_days = 30  # 30-day refund window

    def calculate_purchase(self, usd_amount: float) -> Dict:
        amount = Decimal(str(usd_amount))
        if amount < self.min_purchase_usd:
            return {"success": False, "error": f"Minimum purchase is ${self.min_purchase_usd}"}
        if amount > self.max_purchase_usd:
            return {"success": False, "error": f"Maximum purchase is ${self.max_purchase_usd}"}

        processing_fee = (amount * self.credit_card_fee_percent) + self.credit_card_fee_fixed
        net_amount = amount - processing_fee

        axn_amount = net_amount / self.axn_usd_price
        return {
            "success": True,
            "usd_amount": float(amount),
            "processing_fee": float(processing_fee),
            "net_amount": float(net_amount),
            "axn_amount": float(axn_amount),
            "axn_price": float(self.axn_usd_price),
            "fee_percent": float(self.credit_card_fee_percent * 100),
        }

    def process_card_payment(
        self, user_address: str, usd_amount: float, card_token: str, email: str
    ) -> Dict:
        calc = self.calculate_purchase(usd_amount)
        if not calc.get("success"):
            return calc

        payment_id = f"pay_{int(time.time() * 1000)}"
        payment_record = {
            "success": True,
            "payment_id": payment_id,
            "status": "succeeded",
            "user_address": user_address,
            "email": email,
            "usd_amount": calc["usd_amount"],
            "axn_amount": calc["axn_amount"],
            "processing_fee": calc["processing_fee"],
            "timestamp": time.time(),
            "test_mode": True,
            "payment_method": "credit_card",
            "refunded": False,
            "refund_amount": 0.0,
        }

        # Store payment for refund tracking (Task 108)
        self.payment_history[payment_id] = payment_record

        return payment_record

    def process_bank_transfer(
        self, user_address: str, usd_amount: float, bank_details: Dict
    ) -> Dict:
        calc = self.calculate_purchase(usd_amount)
        if not calc.get("success"):
            return calc

        bank_fee = Decimal("5.00")
        net_amount = Decimal(str(usd_amount)) - bank_fee
        if net_amount < 0:
            return {"success": False, "error": "Bank transfer amount too small to cover fee"}

        axn_amount = net_amount / self.axn_usd_price
        transfer_ref = f"bank_{int(time.time() * 1000)}"
        return {
            "success": True,
            "transfer_id": transfer_ref,
            "status": "pending",
            "method": "bank_transfer",
            "user_address": user_address,
            "usd_amount": float(usd_amount),
            "axn_amount": float(axn_amount),
            "processing_fee": float(bank_fee),
            "bank_account": bank_details.get("account_number", "****"),
            "routing": bank_details.get("routing_number", "****"),
            "estimated_completion": "1-3 business days",
            "timestamp": time.time(),
        }

    def get_supported_payment_methods(self) -> Dict:
        fee_text = (
            f"{float(self.credit_card_fee_percent * 100):.1f}% + ${self.credit_card_fee_fixed}"
        )
        return {
            "credit_card": {
                "enabled": True,
                "fee": fee_text,
                "min": float(self.min_purchase_usd),
                "max": float(self.max_purchase_usd),
                "instant": True,
            },
            "bank_transfer": {
                "enabled": True,
                "fee": "$5.00",
                "instant": False,
                "processing_time": "1-3 business days",
            },
        }

    def get_current_price(self) -> Dict:
        return {
            "AXN/USD": float(self.axn_usd_price),
            "AXN/EUR": float(self.axn_usd_price * Decimal("0.92")),
            "timestamp": time.time(),
            "source": "simulated",
        }

    # ==================== REFUND HANDLING (Task 108) ====================

    def process_refund(
        self,
        payment_id: str,
        refund_amount: float | None = None,
        reason: RefundReason = RefundReason.CUSTOMER_REQUEST,
        notes: str = ""
    ) -> Dict:
        """
        Process a refund for a previous payment.

        Args:
            payment_id: The payment ID to refund
            refund_amount: Amount to refund (None = full refund)
            reason: Reason for the refund
            notes: Additional notes about the refund

        Returns:
            Dict with refund status and details
        """
        # Validate payment exists
        if payment_id not in self.payment_history:
            return {
                "success": False,
                "error": "Payment not found",
                "payment_id": payment_id,
            }

        payment = self.payment_history[payment_id]

        # Check if payment is already fully refunded
        if payment.get("refunded", False):
            return {
                "success": False,
                "error": "Payment already fully refunded",
                "payment_id": payment_id,
                "refund_amount": payment.get("refund_amount", 0),
            }

        # Validate refund time window
        payment_age_days = (time.time() - payment["timestamp"]) / 86400
        if payment_age_days > self.refund_time_window_days:
            return {
                "success": False,
                "error": f"Refund window expired ({self.refund_time_window_days} days)",
                "payment_id": payment_id,
                "payment_age_days": round(payment_age_days, 1),
            }

        # Calculate refund amount
        original_amount = Decimal(str(payment["usd_amount"]))
        already_refunded = Decimal(str(payment.get("refund_amount", 0)))
        remaining_refundable = original_amount - already_refunded

        if refund_amount is None:
            # Full refund
            refund = remaining_refundable
        else:
            refund = Decimal(str(refund_amount))

        # Validate refund amount
        if refund <= 0:
            return {
                "success": False,
                "error": "Refund amount must be positive",
                "payment_id": payment_id,
            }

        if refund > remaining_refundable:
            return {
                "success": False,
                "error": f"Refund amount exceeds remaining refundable amount",
                "payment_id": payment_id,
                "requested": float(refund),
                "remaining_refundable": float(remaining_refundable),
            }

        # Create refund record
        refund_id = f"refund_{int(time.time() * 1000)}"
        refund_record = {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "refund_amount_usd": float(refund),
            "original_amount_usd": float(original_amount),
            "reason": reason.value,
            "notes": notes,
            "status": RefundStatus.COMPLETED.value,
            "timestamp": time.time(),
            "user_address": payment["user_address"],
            "test_mode": self.test_mode,
        }

        # Update payment record
        new_total_refunded = already_refunded + refund
        payment["refund_amount"] = float(new_total_refunded)
        payment["refunded"] = (new_total_refunded >= original_amount)

        # Store refund
        self.refund_history.append(refund_record)

        return {
            "success": True,
            "refund_id": refund_id,
            "payment_id": payment_id,
            "refund_amount": float(refund),
            "total_refunded": float(new_total_refunded),
            "remaining_refundable": float(original_amount - new_total_refunded),
            "status": RefundStatus.COMPLETED.value,
            "reason": reason.value,
        }

    def get_payment_status(self, payment_id: str) -> Dict:
        """
        Get the current status of a payment including refund information.

        Args:
            payment_id: The payment ID to query

        Returns:
            Dict with payment status and refund details
        """
        if payment_id not in self.payment_history:
            return {
                "success": False,
                "error": "Payment not found",
                "payment_id": payment_id,
            }

        payment = self.payment_history[payment_id]
        refunds = [r for r in self.refund_history if r["payment_id"] == payment_id]

        return {
            "success": True,
            "payment_id": payment_id,
            "original_amount": payment["usd_amount"],
            "axn_amount": payment["axn_amount"],
            "status": payment["status"],
            "refunded": payment.get("refunded", False),
            "total_refunded": payment.get("refund_amount", 0),
            "refund_count": len(refunds),
            "refunds": refunds,
            "payment_date": payment["timestamp"],
        }

    def get_refund_history(self, user_address: str | None = None, limit: int = 100) -> list[Dict]:
        """
        Get refund history, optionally filtered by user address.

        Args:
            user_address: Filter by user address (None = all)
            limit: Maximum number of refunds to return

        Returns:
            List of refund records
        """
        refunds = self.refund_history

        if user_address:
            refunds = [r for r in refunds if r.get("user_address") == user_address]

        # Sort by timestamp, most recent first
        refunds.sort(key=lambda x: x["timestamp"], reverse=True)

        return refunds[:limit]

    def cancel_refund(self, refund_id: str, reason: str = "") -> Dict:
        """
        Cancel a pending refund (only works for pending refunds).

        Args:
            refund_id: The refund ID to cancel
            reason: Reason for cancellation

        Returns:
            Dict with cancellation status
        """
        # Find refund
        refund = next((r for r in self.refund_history if r["refund_id"] == refund_id), None)

        if not refund:
            return {
                "success": False,
                "error": "Refund not found",
                "refund_id": refund_id,
            }

        # Can only cancel pending refunds
        if refund["status"] != RefundStatus.PENDING.value:
            return {
                "success": False,
                "error": f"Cannot cancel refund with status: {refund['status']}",
                "refund_id": refund_id,
                "current_status": refund["status"],
            }

        # Update refund status
        refund["status"] = RefundStatus.CANCELLED.value
        refund["cancellation_reason"] = reason
        refund["cancelled_at"] = time.time()

        # Restore payment refund amount
        payment_id = refund["payment_id"]
        payment = self.payment_history.get(payment_id)
        if payment:
            refund_amount = Decimal(str(refund["refund_amount_usd"]))
            current_refunded = Decimal(str(payment.get("refund_amount", 0)))
            payment["refund_amount"] = float(current_refunded - refund_amount)
            payment["refunded"] = False

        return {
            "success": True,
            "refund_id": refund_id,
            "status": RefundStatus.CANCELLED.value,
            "reason": reason,
        }

"""
Lightweight PaymentProcessor shim to satisfy blockchain imports without external dependencies.
"""

import os
import time
from decimal import Decimal
from typing import Dict, Optional


class PaymentProcessor:
    """Simplified payment processor emulation for tests."""

    def __init__(self, stripe_api_key: Optional[str] = None):
        self.stripe_api_key = stripe_api_key or os.getenv("STRIPE_API_KEY")
        self.test_mode = True if not self.stripe_api_key else False
        self.axn_usd_price = Decimal("0.0512")
        self.min_purchase_usd = Decimal("10.00")
        self.max_purchase_usd = Decimal("10000.00")
        self.credit_card_fee_percent = Decimal("0.029")
        self.credit_card_fee_fixed = Decimal("0.30")

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
        return {
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
        }

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

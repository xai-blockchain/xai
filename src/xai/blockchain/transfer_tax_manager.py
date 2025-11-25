import logging
from typing import List, Tuple

logger = logging.getLogger("xai.blockchain.transfer_tax")


class TransferTaxManager:
    def __init__(
        self, transfer_tax_rate_percentage: float = 0.5, exempt_addresses: List[str] = None
    ):
        if not isinstance(transfer_tax_rate_percentage, (int, float)) or not (
            0 <= transfer_tax_rate_percentage <= 100
        ):
            raise ValueError("Transfer tax rate percentage must be between 0 and 100.")

        self.transfer_tax_rate_percentage = transfer_tax_rate_percentage
        self.exempt_addresses = (
            [addr.lower() for addr in exempt_addresses] if exempt_addresses else []
        )
        logger.info(
            "TransferTaxManager initialized (rate %.2f%%, exempt=%s)",
            self.transfer_tax_rate_percentage,
            self.exempt_addresses,
        )

    def calculate_tax_amount(self, amount: float) -> float:
        """Calculates the tax amount for a given transfer amount."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Amount must be a non-negative number.")

        return amount * (self.transfer_tax_rate_percentage / 100.0)

    def apply_transfer_tax(self, sender: str, recipient: str, amount: float) -> Tuple[float, float]:
        """
        Applies transfer tax to an amount, returning the net amount and the tax amount.
        Returns (net_amount, tax_amount).
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Transfer amount must be a positive number.")
        if not sender or not recipient:
            raise ValueError("Sender and recipient addresses cannot be empty.")

        sender_lower = sender.lower()
        recipient_lower = recipient.lower()

        if sender_lower in self.exempt_addresses or recipient_lower in self.exempt_addresses:
            logger.info("Transfer %s -> %s (%.4f) exempt from tax", sender, recipient, amount)
            return amount, 0.0

        tax_amount = self.calculate_tax_amount(amount)
        net_amount = amount - tax_amount

        logger.info(
            "Applied %.2f%% tax on transfer %s -> %s (amount=%.4f, tax=%.4f, net=%.4f)",
            self.transfer_tax_rate_percentage,
            sender,
            recipient,
            amount,
            tax_amount,
            net_amount,
        )
        return net_amount, tax_amount

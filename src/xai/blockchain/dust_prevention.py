from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("xai.blockchain.dust_prevention")

class DustPreventionManager:
    def __init__(self, asset_symbol: str, dust_threshold_amount: float):
        if not asset_symbol:
            raise ValueError("Asset symbol cannot be empty.")
        if not isinstance(dust_threshold_amount, (int, float)) or dust_threshold_amount <= 0:
            raise ValueError("Dust threshold amount must be a positive number.")

        self.asset_symbol = asset_symbol
        self.dust_threshold_amount = dust_threshold_amount
        self.wallet_balances: dict[str, float] = {}  # {address: balance}
        self.dust_transactions_log: list[dict[str, Any]] = []

    def is_dust_amount(self, amount: float) -> bool:
        """Checks if a given amount is below the dust threshold."""
        return amount < self.dust_threshold_amount

    def process_incoming_transaction(
        self, to_address: str, amount: float, from_address: str = "0xSender"
    ):
        """
        Simulates processing an incoming transaction and identifies if it's a dust attack.
        """
        if not to_address:
            raise ValueError("Recipient address cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount must be a positive number.")

        if self.is_dust_amount(amount):
            logger.warning(
                "Dust transaction detected: %.8f %s to %s from %s",
                amount,
                self.asset_symbol,
                to_address,
                from_address,
            )
            self.dust_transactions_log.append(
                {
                    "to_address": to_address,
                    "amount": amount,
                    "from_address": from_address,
                    "timestamp": int(time.time()),
                    "status": "dust_ignored",
                }
            )
            # In a real system, this might not be added to the main balance or require user confirmation.
            # For this simulation, we'll still add it to the balance but log it as dust.
            self.wallet_balances[to_address] = self.wallet_balances.get(to_address, 0.0) + amount
            return False  # Indicate it was dust
        else:
            self.wallet_balances[to_address] = self.wallet_balances.get(to_address, 0.0) + amount
            logger.info(
                "Processed transaction: %.8f %s to %s (new balance %.8f)",
                amount,
                self.asset_symbol,
                to_address,
                self.wallet_balances[to_address],
            )
            return True  # Indicate it was not dust

    def consolidate_dust(self, main_address: str, addresses_to_consolidate: list[str]):
        """
        Simulates consolidating dust amounts from multiple addresses into a main address.
        """
        if not main_address:
            raise ValueError("Main address cannot be empty.")
        if not addresses_to_consolidate:
            logger.info("No addresses pending for dust consolidation.")
            return

        total_consolidated_amount = 0.0
        for address in addresses_to_consolidate:
            if address == main_address:
                continue  # Don't consolidate from main address to itself

            balance = self.wallet_balances.get(address, 0.0)
            if self.is_dust_amount(balance) and balance > 0:
                total_consolidated_amount += balance
                self.wallet_balances[address] = 0.0  # Clear balance from dust address
                logger.info("Consolidated %.8f %s from %s", balance, self.asset_symbol, address)
            elif balance > 0:
                logger.info(
                    "Address %s has %.8f %s (above dust threshold); skipping consolidation.",
                    address,
                    balance,
                    self.asset_symbol,
                )

        if total_consolidated_amount > 0:
            self.wallet_balances[main_address] = (
                self.wallet_balances.get(main_address, 0.0) + total_consolidated_amount
            )
            logger.info(
                "Total %.8f %s consolidated to %s (new balance %.8f)",
                total_consolidated_amount,
                self.asset_symbol,
                main_address,
                self.wallet_balances[main_address],
            )
        else:
            logger.info("No dust amounts found for consolidation.")


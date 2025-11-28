import logging
from typing import Dict, Any

logger = logging.getLogger("xai.blockchain.bridge_fee_manager")


class BridgeFeeManager:
    DEFAULT_TRANSFER_FEE_PERCENTAGE = 0.001  # 0.1% fee

    def __init__(self, transfer_fee_percentage: float = DEFAULT_TRANSFER_FEE_PERCENTAGE):
        if not isinstance(transfer_fee_percentage, (int, float)) or not (
            0 <= transfer_fee_percentage < 1
        ):
            raise ValueError("Transfer fee percentage must be between 0 and 1 (exclusive of 1).")

        self.transfer_fee_percentage = transfer_fee_percentage
        self.insurance_fund_balance = 0.0  # Accumulated fees

    def calculate_fee(self, amount: float) -> float:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount must be a positive number.")
        return amount * self.transfer_fee_percentage

    def collect_fee(self, amount: float) -> float:
        """
        Simulates collecting a fee from a transfer and adding it to the insurance fund.
        Returns the actual amount of fee collected.
        """
        fee = self.calculate_fee(amount)
        self.insurance_fund_balance += fee
        logger.info(
            "Collected %.4f in fees from transfer %.4f (fund balance %.4f)",
            fee,
            amount,
            self.insurance_fund_balance,
        )
        return fee

    def get_insurance_fund_balance(self) -> float:
        return self.insurance_fund_balance

    def __repr__(self):
        return (
            f"BridgeFeeManager(fee_percentage={self.transfer_fee_percentage*100}%, "
            f"fund_balance={self.insurance_fund_balance})"
        )

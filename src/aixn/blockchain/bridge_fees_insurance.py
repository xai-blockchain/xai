from typing import Dict, Any

class BridgeFeeManager:
    DEFAULT_TRANSFER_FEE_PERCENTAGE = 0.001 # 0.1% fee

    def __init__(self, transfer_fee_percentage: float = DEFAULT_TRANSFER_FEE_PERCENTAGE):
        if not isinstance(transfer_fee_percentage, (int, float)) or not (0 <= transfer_fee_percentage < 1):
            raise ValueError("Transfer fee percentage must be between 0 and 1 (exclusive of 1).")
        
        self.transfer_fee_percentage = transfer_fee_percentage
        self.insurance_fund_balance = 0.0 # Accumulated fees

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
        print(f"Collected {fee:.4f} in fees from transfer of {amount}. Insurance fund balance: {self.insurance_fund_balance:.4f}")
        return fee

    def get_insurance_fund_balance(self) -> float:
        return self.insurance_fund_balance

    def __repr__(self):
        return ("BridgeFeeManager(fee_percentage="+str(self.transfer_fee_percentage*100)+"%", "
                "fund_balance="+str(self.insurance_fund_balance)+")")

# Example Usage (for testing purposes)
if __name__ == "__main__":
    fee_manager = BridgeFeeManager(transfer_fee_percentage=0.005) # 0.5% fee

    print("--- Initial State ---")
    print(fee_manager)

    print("\n--- Simulating Transfers and Fee Collection ---")
    transfer1_amount = 1000.0
    fee1 = fee_manager.collect_fee(transfer1_amount)
    print(f"Transfer 1: {transfer1_amount}, Fee: {fee1}")

    transfer2_amount = 5000.0
    fee2 = fee_manager.collect_fee(transfer2_amount)
    print(f"Transfer 2: {transfer2_amount}, Fee: {fee2}")

    transfer3_amount = 200.0
    fee3 = fee_manager.collect_fee(transfer3_amount)
    print(f"Transfer 3: {transfer3_amount}, Fee: {fee3}")

    print("\n--- Final State ---")
    print(fee_manager)
    print(f"Total insurance fund: {fee_manager.get_insurance_fund_balance():.4f}")

    print("\n--- Testing edge cases ---")
    try:
        fee_manager.calculate_fee(-100)
    except ValueError as e:
        print(f"Error (expected): {e}")

    try:
        invalid_fee_manager = BridgeFeeManager(transfer_fee_percentage=1.1)
    except ValueError as e:
        print(f"Error (expected): {e}")

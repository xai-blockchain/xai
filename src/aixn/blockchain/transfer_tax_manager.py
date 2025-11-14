from typing import List, Tuple

class TransferTaxManager:
    def __init__(self, transfer_tax_rate_percentage: float = 0.5, exempt_addresses: List[str] = None):
        if not isinstance(transfer_tax_rate_percentage, (int, float)) or not (0 <= transfer_tax_rate_percentage <= 100):
            raise ValueError("Transfer tax rate percentage must be between 0 and 100.")
        
        self.transfer_tax_rate_percentage = transfer_tax_rate_percentage
        self.exempt_addresses = [addr.lower() for addr in exempt_addresses] if exempt_addresses else []
        print(f"TransferTaxManager initialized. Tax rate: {self.transfer_tax_rate_percentage}%. Exempt addresses: {self.exempt_addresses}")

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
            print(f"Transfer from {sender} to {recipient} for {amount:.2f} is exempt from tax.")
            return amount, 0.0
        
        tax_amount = self.calculate_tax_amount(amount)
        net_amount = amount - tax_amount
        
        print(f"Applied {self.transfer_tax_rate_percentage}% transfer tax. Original: {amount:.2f}, Tax: {tax_amount:.2f}, Net: {net_amount:.2f}")
        return net_amount, tax_amount

# Example Usage (for testing purposes)
if __name__ == "__main__":
    treasury_address = "0xTreasury"
    lp_pool_address = "0xLPPool"
    exempt_list = [treasury_address, lp_pool_address]

    tax_manager = TransferTaxManager(transfer_tax_rate_percentage=1.0, exempt_addresses=exempt_list) # 1% tax

    user_a = "0xUserA"
    user_b = "0xUserB"

    print("\n--- Normal Transfer ---")
    net_amount_1, tax_amount_1 = tax_manager.apply_transfer_tax(user_a, user_b, 1000.0)
    print(f"User A to User B: Net {net_amount_1:.2f}, Tax {tax_amount_1:.2f}")

    print("\n--- Transfer to Exempt Address (LP Pool) ---")
    net_amount_2, tax_amount_2 = tax_manager.apply_transfer_tax(user_a, lp_pool_address, 500.0)
    print(f"User A to LP Pool: Net {net_amount_2:.2f}, Tax {tax_amount_2:.2f}")

    print("\n--- Transfer from Exempt Address (Treasury) ---")
    net_amount_3, tax_amount_3 = tax_manager.apply_transfer_tax(treasury_address, user_b, 200.0)
    print(f"Treasury to User B: Net {net_amount_3:.2f}, Tax {tax_amount_3:.2f}")

    print("\n--- Transfer with Zero Amount (Error Expected) ---")
    try:
        tax_manager.apply_transfer_tax(user_a, user_b, 0.0)
    except ValueError as e:
        print(f"Error (expected): {e}")

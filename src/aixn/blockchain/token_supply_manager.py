class TokenSupplyManager:
    def __init__(self, max_supply: float):
        if not isinstance(max_supply, (int, float)) or max_supply <= 0:
            raise ValueError("Maximum supply must be a positive number.")

        self.MAX_SUPPLY = max_supply
        self.current_supply = 0.0
        print(f"TokenSupplyManager initialized. Max supply: {self.MAX_SUPPLY:.2f}")

    def mint_tokens(self, amount: float) -> float:
        """
        Mints new tokens, enforcing the maximum supply cap.
        Returns the new current supply.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Mint amount must be a positive number.")

        if self.current_supply + amount > self.MAX_SUPPLY:
            raise ValueError(
                f"Cannot mint {amount:.2f} tokens. Exceeds maximum supply cap of {self.MAX_SUPPLY:.2f}. "
                f"Current supply: {self.current_supply:.2f}, Available to mint: {self.MAX_SUPPLY - self.current_supply:.2f}"
            )

        self.current_supply += amount
        print(f"Minted {amount:.2f} tokens. New current supply: {self.current_supply:.2f}")
        return self.current_supply

    def burn_tokens(self, amount: float) -> float:
        """
        Burns tokens, reducing the current supply.
        Returns the new current supply.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Burn amount must be a positive number.")

        if self.current_supply - amount < 0:
            raise ValueError(
                f"Cannot burn {amount:.2f} tokens. Current supply ({self.current_supply:.2f}) is insufficient."
            )

        self.current_supply -= amount
        print(f"Burned {amount:.2f} tokens. New current supply: {self.current_supply:.2f}")
        return self.current_supply

    def get_current_supply(self) -> float:
        """Returns the current total supply of tokens."""
        return self.current_supply

    def get_max_supply(self) -> float:
        """Returns the maximum total supply of tokens."""
        return self.MAX_SUPPLY


# Example Usage (for testing purposes)
if __name__ == "__main__":
    supply_manager = TokenSupplyManager(max_supply=1000000.0)  # 1 million tokens

    print("\n--- Initial State ---")
    print(f"Current supply: {supply_manager.get_current_supply():.2f}")
    print(f"Max supply: {supply_manager.get_max_supply():.2f}")

    print("\n--- Minting Tokens ---")
    try:
        supply_manager.mint_tokens(500000.0)
        supply_manager.mint_tokens(250000.0)
        supply_manager.mint_tokens(100000.0)
    except ValueError as e:
        print(f"Error: {e}")

    print(f"Current supply after minting: {supply_manager.get_current_supply():.2f}")

    print("\n--- Attempting to Exceed Max Supply ---")
    try:
        supply_manager.mint_tokens(200000.0)  # This should fail (750k + 200k = 950k, still ok)
        supply_manager.mint_tokens(100000.0)  # This should fail (950k + 100k = 1.05M > 1M)
    except ValueError as e:
        print(f"Error (expected): {e}")

    print(f"Current supply after failed mint attempt: {supply_manager.get_current_supply():.2f}")

    print("\n--- Burning Tokens ---")
    try:
        supply_manager.burn_tokens(50000.0)
    except ValueError as e:
        print(f"Error: {e}")
    print(f"Current supply after burning: {supply_manager.get_current_supply():.2f}")

    print("\n--- Attempting to Burn More Than Available ---")
    try:
        supply_manager.burn_tokens(1000000.0)  # Should fail
    except ValueError as e:
        print(f"Error (expected): {e}")
    print(f"Current supply after failed burn attempt: {supply_manager.get_current_supply():.2f}")

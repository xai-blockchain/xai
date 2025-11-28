import logging

logger = logging.getLogger("xai.blockchain.token_supply_manager")


class TokenSupplyManager:
    def __init__(self, max_supply: float):
        if not isinstance(max_supply, (int, float)) or max_supply <= 0:
            raise ValueError("Maximum supply must be a positive number.")

        self.MAX_SUPPLY = max_supply
        self.current_supply = 0.0
        logger.info("TokenSupplyManager initialized with max supply %.2f", self.MAX_SUPPLY)

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
        logger.info("Minted %.2f tokens (current supply %.2f)", amount, self.current_supply)
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
        logger.info("Burned %.2f tokens (current supply %.2f)", amount, self.current_supply)
        return self.current_supply

    def get_current_supply(self) -> float:
        """Returns the current total supply of tokens."""
        return self.current_supply

    def get_max_supply(self) -> float:
        """Returns the maximum total supply of tokens."""
        return self.MAX_SUPPLY

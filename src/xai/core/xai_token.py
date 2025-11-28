import time


class SupplyCapExceededError(Exception):
    """Exception raised when minting would exceed the token's supply cap."""

    pass


class InsufficientBalanceError(Exception):
    """Exception raised when an operation requires more tokens than available in a balance."""

    pass


class XAIToken:
    def __init__(self, initial_supply: float = 0, supply_cap: float = 121_000_000):
        self.total_supply = initial_supply
        self.supply_cap = supply_cap
        self.balances = {}
        self.vesting_schedules = {}

    def mint(self, address: str, amount: float) -> bool:
        """
        Mints new tokens to a specific address.

        Args:
            address: The recipient address for the minted tokens.
            amount: The amount of tokens to mint.

        Returns:
            True if minting was successful, False otherwise.
        """
        # Check for zero or negative amounts
        if amount <= 0:
            return False

        # Check if minting would exceed the supply cap
        if self.total_supply + amount > self.supply_cap:
            return False

        self.total_supply += amount
        self.balances[address] = self.balances.get(address, 0) + amount
        return True

    def create_vesting_schedule(
        self, address: str, amount: float, cliff_duration: float, total_duration: float
    ) -> bool:
        """
        Creates a vesting schedule for a given address.

        Args:
            address: The address for which to create the vesting schedule.
            amount: The total amount of tokens to be vested.
            cliff_duration: The duration (in seconds) before vesting begins.
            total_duration: The total duration (in seconds) over which tokens will vest.

        Returns:
            True if the vesting schedule was created successfully, False otherwise.
        """
        # Check if address has sufficient balance
        if self.balances.get(address, 0) < amount:
            return False

        self.vesting_schedules[address] = {
            "amount": amount,
            "cliff_end": time.time() + cliff_duration,
            "end_date": time.time() + total_duration,
            "released": 0,
        }
        return True

    def get_token_metrics(self):
        """
        Returns a dictionary with key token metrics.
        """
        return {
            "total_supply": self.total_supply,
            "supply_cap": self.supply_cap,
            "circulating_supply": self.calculate_circulating_supply(),
        }

    def calculate_circulating_supply(self):
        """
        Calculates the circulating supply by excluding vested tokens.
        """
        vested_amount = sum(
            schedule["amount"] - schedule["released"]
            for schedule in self.vesting_schedules.values()
        )
        return self.total_supply - vested_amount

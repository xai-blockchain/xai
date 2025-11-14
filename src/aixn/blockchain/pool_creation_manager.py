from typing import Dict, Any, List
import time

class PoolCreationManager:
    def __init__(self, min_initial_liquidity: float = 1000.0, whitelisted_tokens: List[str] = None):
        if not isinstance(min_initial_liquidity, (int, float)) or min_initial_liquidity <= 0:
            raise ValueError("Minimum initial liquidity must be a positive number.")
        if whitelisted_tokens is None:
            self.whitelisted_tokens = ["ETH", "USDC", "DAI"] # Default whitelisted tokens
        else:
            self.whitelisted_tokens = [token.upper() for token in whitelisted_tokens]

        self.min_initial_liquidity = min_initial_liquidity
        # Stores pools: {pool_id: {"token_a": str, "token_b": str, "initial_liquidity": float, "creator": str, "timestamp": int}}
        self.pools: Dict[str, Dict[str, Any]] = {}
        self._pool_id_counter = 0

    def _generate_pool_id(self, token_a: str, token_b: str) -> str:
        """Generates a unique pool ID based on token pair."""
        # Ensure consistent ID regardless of token order
        sorted_tokens = sorted([token_a.upper(), token_b.upper()])
        return f"pool_{sorted_tokens[0]}_{sorted_tokens[1]}"

    def create_pool(self, token_a: str, token_b: str, initial_liquidity_amount: float, creator_address: str) -> str:
        """
        Attempts to create a new liquidity pool after validating against rules.
        """
        if not token_a or not token_b or not creator_address:
            raise ValueError("Token symbols and creator address cannot be empty.")
        if token_a.upper() == token_b.upper():
            raise ValueError("Cannot create a pool with two identical tokens.")
        if not isinstance(initial_liquidity_amount, (int, float)) or initial_liquidity_amount < self.min_initial_liquidity:
            raise ValueError(f"Initial liquidity amount must be at least {self.min_initial_liquidity}.")

        # Token whitelisting check
        if self.whitelisted_tokens and (token_a.upper() not in self.whitelisted_tokens or token_b.upper() not in self.whitelisted_tokens):
            raise ValueError(f"One or both tokens ({token_a}, {token_b}) are not whitelisted for pool creation.")

        pool_id = self._generate_pool_id(token_a, token_b)
        if pool_id in self.pools:
            raise ValueError(f"Pool for {token_a}-{token_b} already exists.")

        self.pools[pool_id] = {
            "token_a": token_a.upper(),
            "token_b": token_b.upper(),
            "initial_liquidity": initial_liquidity_amount,
            "creator": creator_address,
            "timestamp": int(time.time())
        }
        print(f"Successfully created pool {pool_id} with {initial_liquidity_amount:.2f} initial liquidity by {creator_address}.")
        return pool_id

    def get_existing_pools(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dictionary of all existing pools."""
        return self.pools

    def get_pool_info(self, token_a: str, token_b: str) -> Dict[str, Any]:
        """Returns information for a specific pool."""
        pool_id = self._generate_pool_id(token_a, token_b)
        return self.pools.get(pool_id)

# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = PoolCreationManager(min_initial_liquidity=500.0, whitelisted_tokens=["ETH", "USDC", "DAI", "UNI"])

    user1 = "0xCreator1"
    user2 = "0xCreator2"

    print("--- Initial State ---")
    print(f"Whitelisted tokens: {manager.whitelisted_tokens}")
    print(f"Minimum initial liquidity: {manager.min_initial_liquidity}")
    print(f"Existing pools: {manager.get_existing_pools()}")

    print("\n--- Attempting valid pool creation ---")
    try:
        pool1_id = manager.create_pool("ETH", "USDC", 1000.0, user1)
        pool2_id = manager.create_pool("DAI", "UNI", 750.0, user2)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Attempting invalid pool creation (below min liquidity) ---")
    try:
        manager.create_pool("ETH", "DAI", 400.0, user1)
    except ValueError as e:
        print(f"Error (expected): {e}")

    print("\n--- Attempting invalid pool creation (non-whitelisted token) ---")
    try:
        manager.create_pool("ETH", "SHIB", 1200.0, user1)
    except ValueError as e:
        print(f"Error (expected): {e}")

    print("\n--- Attempting invalid pool creation (duplicate pool) ---")
    try:
        manager.create_pool("USDC", "ETH", 1500.0, user2) # Order of tokens shouldn't matter
    except ValueError as e:
        print(f"Error (expected): {e}")

    print("\n--- Existing Pools after attempts ---")
    print(manager.get_existing_pools())
    print(f"Info for ETH-USDC pool: {manager.get_pool_info('ETH', 'USDC')}")

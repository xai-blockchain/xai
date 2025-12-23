from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger("xai.blockchain.pool_creation_manager")

class PoolCreationManager:
    def __init__(
        self,
        min_initial_liquidity: float = 1000.0,
        whitelisted_tokens: list[str] | None = None,
        time_provider: Callable[[], int] | None = None,
    ):
        if not isinstance(min_initial_liquidity, (int, float)) or min_initial_liquidity <= 0:
            raise ValueError("Minimum initial liquidity must be a positive number.")
        if whitelisted_tokens is None:
            self.whitelisted_tokens = ["ETH", "USDC", "DAI"]  # Default whitelisted tokens
        else:
            self.whitelisted_tokens = [token.upper() for token in whitelisted_tokens]

        self.min_initial_liquidity = min_initial_liquidity
        # Stores pools: {pool_id: {"token_a": str, "token_b": str, "initial_liquidity": float, "creator": str, "timestamp": int}}
        self.pools: dict[str, dict[str, Any]] = {}
        self._pool_id_counter = 0
        self._time_provider = time_provider or (lambda: int(time.time()))
        logger.info(
            "PoolCreationManager initialized (min liquidity %.2f, whitelist %s, deterministic time provider: %s)",
            self.min_initial_liquidity,
            self.whitelisted_tokens,
            bool(time_provider),
        )

    def _current_time(self) -> int:
        timestamp = self._time_provider()
        try:
            return int(timestamp)
        except (TypeError, ValueError) as exc:
            raise ValueError("time_provider must return an integer timestamp") from exc

    def _generate_pool_id(self, token_a: str, token_b: str) -> str:
        """Generates a unique pool ID based on token pair."""
        # Ensure consistent ID regardless of token order
        sorted_tokens = sorted([token_a.upper(), token_b.upper()])
        return f"pool_{sorted_tokens[0]}_{sorted_tokens[1]}"

    def create_pool(
        self, token_a: str, token_b: str, initial_liquidity_amount: float, creator_address: str
    ) -> str:
        """
        Attempts to create a new liquidity pool after validating against rules.
        """
        if not token_a or not token_b or not creator_address:
            raise ValueError("Token symbols and creator address cannot be empty.")
        if token_a.upper() == token_b.upper():
            raise ValueError("Cannot create a pool with two identical tokens.")
        if (
            not isinstance(initial_liquidity_amount, (int, float))
            or initial_liquidity_amount < self.min_initial_liquidity
        ):
            raise ValueError(
                f"Initial liquidity amount must be at least {self.min_initial_liquidity}."
            )

        # Token whitelisting check
        if self.whitelisted_tokens and (
            token_a.upper() not in self.whitelisted_tokens
            or token_b.upper() not in self.whitelisted_tokens
        ):
            raise ValueError(
                f"One or both tokens ({token_a}, {token_b}) are not whitelisted for pool creation."
            )

        pool_id = self._generate_pool_id(token_a, token_b)
        if pool_id in self.pools:
            raise ValueError(f"Pool for {token_a}-{token_b} already exists.")

        self.pools[pool_id] = {
            "token_a": token_a.upper(),
            "token_b": token_b.upper(),
            "initial_liquidity": initial_liquidity_amount,
            "creator": creator_address,
            "timestamp": self._current_time(),
        }
        logger.info(
            "Pool %s created for %s-%s with %.2f liquidity by %s",
            pool_id,
            token_a.upper(),
            token_b.upper(),
            initial_liquidity_amount,
            creator_address,
        )
        return pool_id

    def get_existing_pools(self) -> dict[str, dict[str, Any]]:
        """Returns a dictionary of all existing pools."""
        return self.pools

    def get_pool_info(self, token_a: str, token_b: str) -> dict[str, Any]:
        """Returns information for a specific pool."""
        pool_id = self._generate_pool_id(token_a, token_b)
        return self.pools.get(pool_id)

"""
Multi-Oracle Price Feed Redundancy Manager

Provides failover and redundancy across multiple oracle sources
following blockchain community best practices for price reliability.

Features:
- Primary/secondary/tertiary oracle fallback
- Cross-oracle price deviation detection
- Weighted median aggregation
- Circuit breaker on oracle disagreement
- Health monitoring per oracle
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from ..vm.exceptions import VMExecutionError

logger = logging.getLogger(__name__)


class OracleHealth(Enum):
    """Health status of an oracle source."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class OracleSource:
    """Configuration for a single oracle source."""

    name: str
    priority: int  # Lower = higher priority (1 = primary)
    weight: int = 100  # Weight for weighted median (basis points)

    # Health tracking
    health: OracleHealth = OracleHealth.HEALTHY
    last_response_time: float = 0.0
    last_error_time: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0

    # Thresholds
    max_response_time: float = 5.0  # seconds
    max_consecutive_failures: int = 3
    recovery_period: float = 300.0  # 5 minutes before retry


@dataclass
class OraclePrice:
    """Price data from a single oracle."""

    source: str
    price: int
    timestamp: float
    confidence: int = 10000  # basis points (100%)


class OracleInterface(Protocol):
    """Interface that oracle sources must implement."""

    def get_price(self, pair: str) -> tuple[int, float]:
        """Get current price and timestamp for a pair."""
        ...

    def is_available(self) -> bool:
        """Check if oracle is available."""
        ...


@dataclass
class OracleRedundancyManager:
    """
    Multi-oracle redundancy manager with failover support.

    Implements production-grade oracle redundancy:
    1. Primary oracle used when healthy
    2. Automatic failover to secondary on primary failure
    3. Cross-validation against multiple oracles
    4. Circuit breaker on significant deviation
    5. Health monitoring and recovery

    Example usage:
        manager = OracleRedundancyManager()
        manager.add_oracle("chainlink", priority=1, oracle_impl)
        manager.add_oracle("pyth", priority=2, oracle_impl)
        manager.add_oracle("internal", priority=3, oracle_impl)

        price, confidence = manager.get_price("XAI/USD")
    """

    # Oracle sources by priority
    oracles: dict[str, OracleSource] = field(default_factory=dict)
    oracle_impls: dict[str, OracleInterface] = field(default_factory=dict)

    # Cross-validation settings
    max_deviation_bps: int = 200  # 2% max deviation between oracles
    min_oracles_for_validation: int = 2
    require_cross_validation: bool = True

    # Circuit breaker
    circuit_breaker_active: bool = False
    circuit_breaker_reason: str = ""
    circuit_breaker_triggered_at: float = 0.0
    circuit_breaker_cooldown: float = 300.0  # 5 minutes

    # Aggregation settings
    aggregation_method: str = "weighted_median"  # median, mean, weighted_median

    # Cached prices for TWAP
    price_cache: dict[str, list[OraclePrice]] = field(default_factory=dict)
    cache_size: int = 100

    def add_oracle(
        self,
        name: str,
        priority: int,
        oracle: OracleInterface,
        weight: int = 100,
    ) -> None:
        """
        Add an oracle source.

        Args:
            name: Oracle identifier (e.g., "chainlink", "pyth")
            priority: Priority level (1 = highest)
            oracle: Oracle implementation
            weight: Weight for aggregation (basis points)
        """
        self.oracles[name] = OracleSource(
            name=name,
            priority=priority,
            weight=weight,
        )
        self.oracle_impls[name] = oracle

        logger.info(
            "Oracle source added",
            extra={
                "event": "oracle_redundancy.source_added",
                "oracle_name": name,
                "priority": priority,
            }
        )

    def remove_oracle(self, name: str) -> None:
        """Remove an oracle source."""
        if name in self.oracles:
            del self.oracles[name]
            del self.oracle_impls[name]

    def get_price(self, pair: str) -> tuple[int, int]:
        """
        Get aggregated price with redundancy.

        Returns:
            Tuple of (price, confidence_bps)

        Raises:
            VMExecutionError: If no reliable price available
        """
        if self.circuit_breaker_active:
            if time.time() - self.circuit_breaker_triggered_at < self.circuit_breaker_cooldown:
                raise VMExecutionError(
                    f"Circuit breaker active: {self.circuit_breaker_reason}"
                )
            else:
                # Reset circuit breaker after cooldown
                self.circuit_breaker_active = False
                self.circuit_breaker_reason = ""

        # Collect prices from all healthy oracles
        prices: list[OraclePrice] = []
        errors: list[str] = []

        for name in self._get_oracles_by_priority():
            source = self.oracles[name]
            oracle = self.oracle_impls[name]

            # Skip unhealthy oracles
            if source.health == OracleHealth.OFFLINE:
                if time.time() - source.last_error_time < source.recovery_period:
                    continue

            try:
                start_time = time.time()
                price, timestamp = oracle.get_price(pair)
                response_time = time.time() - start_time

                # Update health metrics
                source.total_requests += 1
                source.successful_requests += 1
                source.consecutive_failures = 0
                source.last_response_time = response_time

                # Check response time
                if response_time > source.max_response_time:
                    source.health = OracleHealth.DEGRADED
                else:
                    source.health = OracleHealth.HEALTHY

                prices.append(OraclePrice(
                    source=name,
                    price=price,
                    timestamp=timestamp,
                    confidence=10000 - int(response_time * 100),  # Reduce confidence for slow responses
                ))

            except Exception as e:
                source.total_requests += 1
                source.consecutive_failures += 1
                source.last_error_time = time.time()
                errors.append(f"{name}: {e}")

                if source.consecutive_failures >= source.max_consecutive_failures:
                    source.health = OracleHealth.OFFLINE
                    logger.warning(
                        "Oracle marked offline",
                        extra={
                            "event": "oracle_redundancy.oracle_offline",
                            "oracle_name": name,
                            "failures": source.consecutive_failures,
                        }
                    )

        if not prices:
            raise VMExecutionError(
                f"No oracle prices available. Errors: {'; '.join(errors)}"
            )

        # Cross-validation
        if self.require_cross_validation and len(prices) >= self.min_oracles_for_validation:
            self._validate_cross_oracle_prices(prices)

        # Aggregate prices
        final_price, confidence = self._aggregate_prices(prices)

        # Cache for TWAP
        self._cache_price(pair, OraclePrice(
            source="aggregated",
            price=final_price,
            timestamp=time.time(),
            confidence=confidence,
        ))

        return final_price, confidence

    def _get_oracles_by_priority(self) -> list[str]:
        """Get oracle names sorted by priority."""
        return sorted(
            self.oracles.keys(),
            key=lambda x: self.oracles[x].priority
        )

    def _validate_cross_oracle_prices(self, prices: list[OraclePrice]) -> None:
        """
        Validate that oracle prices agree within threshold.

        Triggers circuit breaker on significant disagreement.
        """
        if len(prices) < 2:
            return

        price_values = [p.price for p in prices]
        median_price = statistics.median(price_values)

        for p in prices:
            if median_price == 0:
                continue
            deviation_bps = abs(p.price - median_price) * 10000 // median_price

            if deviation_bps > self.max_deviation_bps:
                self._trigger_circuit_breaker(
                    f"Oracle {p.source} deviated {deviation_bps}bps from median"
                )
                raise VMExecutionError(
                    f"Oracle price deviation too high: {deviation_bps}bps > {self.max_deviation_bps}bps"
                )

    def _aggregate_prices(self, prices: list[OraclePrice]) -> tuple[int, int]:
        """
        Aggregate prices from multiple oracles.

        Returns:
            Tuple of (aggregated_price, confidence_bps)
        """
        if len(prices) == 1:
            return prices[0].price, prices[0].confidence

        if self.aggregation_method == "median":
            price = int(statistics.median(p.price for p in prices))
            confidence = min(p.confidence for p in prices)

        elif self.aggregation_method == "mean":
            price = int(statistics.mean(p.price for p in prices))
            confidence = min(p.confidence for p in prices)

        elif self.aggregation_method == "weighted_median":
            # Weighted by oracle weights and confidence
            weighted_prices = []
            for p in prices:
                source = self.oracles.get(p.source)
                weight = (source.weight if source else 100) * p.confidence // 10000
                weighted_prices.extend([p.price] * max(1, weight // 10))

            price = int(statistics.median(weighted_prices))
            confidence = int(statistics.mean(p.confidence for p in prices))

        else:
            raise VMExecutionError(f"Unknown aggregation method: {self.aggregation_method}")

        return price, confidence

    def _trigger_circuit_breaker(self, reason: str) -> None:
        """Trigger the circuit breaker."""
        self.circuit_breaker_active = True
        self.circuit_breaker_reason = reason
        self.circuit_breaker_triggered_at = time.time()

        logger.error(
            "Circuit breaker triggered",
            extra={
                "event": "oracle_redundancy.circuit_breaker",
                "reason": reason,
            }
        )

    def _cache_price(self, pair: str, price: OraclePrice) -> None:
        """Cache price for TWAP calculations."""
        if pair not in self.price_cache:
            self.price_cache[pair] = []

        self.price_cache[pair].append(price)

        # Trim cache
        if len(self.price_cache[pair]) > self.cache_size:
            self.price_cache[pair] = self.price_cache[pair][-self.cache_size:]

    def get_twap(self, pair: str, period_seconds: int = 600) -> int:
        """
        Get time-weighted average price.

        Args:
            pair: Trading pair
            period_seconds: TWAP period

        Returns:
            TWAP price
        """
        if pair not in self.price_cache:
            raise VMExecutionError(f"No price history for {pair}")

        current_time = time.time()
        cutoff_time = current_time - period_seconds

        recent_prices = [
            p for p in self.price_cache[pair]
            if p.timestamp >= cutoff_time
        ]

        if not recent_prices:
            raise VMExecutionError(f"No recent prices for {pair} in last {period_seconds}s")

        # Simple TWAP: average of prices in period
        return int(statistics.mean(p.price for p in recent_prices))

    def get_health_status(self) -> dict[str, dict]:
        """Get health status of all oracles."""
        return {
            name: {
                "health": source.health.value,
                "priority": source.priority,
                "weight": source.weight,
                "consecutive_failures": source.consecutive_failures,
                "success_rate": (
                    source.successful_requests / source.total_requests * 100
                    if source.total_requests > 0 else 100.0
                ),
                "last_response_time": source.last_response_time,
            }
            for name, source in self.oracles.items()
        }

    def reset_oracle_health(self, name: str) -> None:
        """Manually reset oracle health status."""
        if name in self.oracles:
            source = self.oracles[name]
            source.health = OracleHealth.HEALTHY
            source.consecutive_failures = 0
            logger.info(
                "Oracle health reset",
                extra={"event": "oracle_redundancy.health_reset", "oracle_name": name}
            )

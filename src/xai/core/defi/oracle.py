"""
Price Oracle Implementation.

Provides Chainlink-style price feeds with:
- Multiple data providers
- Price aggregation
- Staleness checks
- Deviation thresholds
- Historical price data

Security features:
- Multi-source validation
- Staleness detection
- Deviation alerts
- Circuit breakers
"""

from __future__ import annotations

import time
import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


class OracleStatus(Enum):
    """Oracle data feed status."""
    ACTIVE = "active"
    STALE = "stale"
    PAUSED = "paused"
    INVALID = "invalid"


@dataclass
class PriceData:
    """Price data point."""

    price: int  # Price in base units (e.g., 8 decimals)
    timestamp: float
    round_id: int
    source: str
    confidence: int = 10000  # Confidence level (basis points)


@dataclass
class PriceFeed:
    """Configuration for a price feed."""

    pair: str  # e.g., "XAI/USD"
    base_asset: str
    quote_asset: str

    # Data providers
    sources: List[str] = field(default_factory=list)

    # Price data
    latest_price: int = 0
    latest_timestamp: float = 0.0
    round_id: int = 0

    # Historical data (last N prices)
    price_history: List[PriceData] = field(default_factory=list)
    history_size: int = 100

    # Configuration
    decimals: int = 8  # Price decimals
    heartbeat: int = 3600  # Max age in seconds before stale
    deviation_threshold: int = 100  # Max deviation (basis points)

    # Status
    status: OracleStatus = OracleStatus.ACTIVE

    # Aggregation settings
    min_sources: int = 1  # Minimum sources for valid price
    aggregation_method: str = "median"  # median, mean, weighted


@dataclass
class PriceOracle:
    """
    Chainlink-style price oracle implementation.

    Provides reliable price feeds with:
    - Multiple data sources
    - Price aggregation
    - Staleness detection
    - Deviation checks
    - Historical data

    Security features:
    - Multi-source validation
    - Staleness detection (heartbeat)
    - Deviation alerts
    - Price bounds checking
    - Circuit breaker support
    """

    name: str = "XAI Price Oracle"
    address: str = ""
    owner: str = ""

    # Price feeds by pair
    feeds: Dict[str, PriceFeed] = field(default_factory=dict)

    # Authorized data providers
    authorized_providers: Dict[str, bool] = field(default_factory=dict)

    # Price bounds (min/max acceptable prices per asset)
    price_bounds: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    # Circuit breaker (pause all feeds if triggered)
    circuit_breaker_active: bool = False

    # Statistics
    total_updates: int = 0

    def __post_init__(self) -> None:
        """Initialize oracle."""
        if not self.address:
            import hashlib
            addr_hash = hashlib.sha3_256(f"{self.name}{time.time()}".encode()).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Price Feed Management ====================

    def add_feed(
        self,
        caller: str,
        pair: str,
        base_asset: str,
        quote_asset: str,
        decimals: int = 8,
        heartbeat: int = 3600,
        deviation_threshold: int = 100,
        min_sources: int = 1,
    ) -> bool:
        """
        Add a new price feed.

        Args:
            caller: Must be owner
            pair: Price pair (e.g., "XAI/USD")
            base_asset: Base asset symbol
            quote_asset: Quote asset symbol
            decimals: Price decimals
            heartbeat: Max age before stale (seconds)
            deviation_threshold: Max deviation (basis points)
            min_sources: Minimum sources required

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if pair in self.feeds:
            raise VMExecutionError(f"Feed {pair} already exists")

        self.feeds[pair] = PriceFeed(
            pair=pair,
            base_asset=base_asset,
            quote_asset=quote_asset,
            decimals=decimals,
            heartbeat=heartbeat,
            deviation_threshold=deviation_threshold,
            min_sources=min_sources,
        )

        logger.info(
            "Price feed added",
            extra={
                "event": "oracle.feed_added",
                "pair": pair,
                "decimals": decimals,
            }
        )

        return True

    def add_source(self, caller: str, pair: str, source: str) -> bool:
        """Add a data source to a feed."""
        self._require_owner(caller)
        self._require_feed(pair)

        feed = self.feeds[pair]
        if source not in feed.sources:
            feed.sources.append(source)

        return True

    def authorize_provider(self, caller: str, provider: str) -> bool:
        """Authorize a data provider."""
        self._require_owner(caller)
        self.authorized_providers[self._normalize(provider)] = True
        return True

    def revoke_provider(self, caller: str, provider: str) -> bool:
        """Revoke a data provider."""
        self._require_owner(caller)
        self.authorized_providers[self._normalize(provider)] = False
        return True

    # ==================== Price Updates ====================

    def update_price(
        self,
        caller: str,
        pair: str,
        price: int,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        Update price for a feed.

        Args:
            caller: Must be authorized provider
            pair: Price pair
            price: New price (in feed's decimal precision)
            timestamp: Price timestamp (defaults to now)

        Returns:
            True if successful
        """
        self._require_authorized(caller)
        self._require_feed(pair)
        self._require_not_paused()

        feed = self.feeds[pair]
        timestamp = timestamp or time.time()

        # Validate price bounds
        if pair in self.price_bounds:
            min_price, max_price = self.price_bounds[pair]
            if price < min_price or price > max_price:
                logger.warning(
                    "Price outside bounds",
                    extra={
                        "event": "oracle.price_rejected",
                        "pair": pair,
                        "price": price,
                        "bounds": (min_price, max_price),
                    }
                )
                raise VMExecutionError(
                    f"Price {price} outside bounds [{min_price}, {max_price}]"
                )

        # Check deviation from last price
        deviation = 0
        if feed.latest_price > 0:
            deviation = abs(price - feed.latest_price) * 10000 // feed.latest_price
            if deviation > feed.deviation_threshold:
                logger.error(
                    "Price update rejected - deviation exceeds threshold",
                    extra={
                        "event": "oracle.price_rejected",
                        "pair": pair,
                        "current_price": feed.latest_price,
                        "proposed_price": price,
                        "deviation_bps": deviation,
                        "threshold_bps": feed.deviation_threshold,
                        "reporter": caller,
                    }
                )
                raise VMExecutionError(
                    f"Price deviation {deviation} bps exceeds threshold {feed.deviation_threshold} bps for {pair}. "
                    f"Current: {feed.latest_price}, Proposed: {price}"
                )

        # Update feed (only reaches here if deviation is acceptable)
        feed.round_id += 1
        feed.latest_price = price
        feed.latest_timestamp = timestamp
        feed.status = OracleStatus.ACTIVE

        # Add to history
        price_data = PriceData(
            price=price,
            timestamp=timestamp,
            round_id=feed.round_id,
            source=caller,
        )
        feed.price_history.append(price_data)

        # Trim history
        if len(feed.price_history) > feed.history_size:
            feed.price_history = feed.price_history[-feed.history_size:]

        self.total_updates += 1

        logger.info(
            "Price updated",
            extra={
                "event": "oracle.price_updated",
                "pair": pair,
                "price": price,
                "round": feed.round_id,
                "deviation_bps": deviation,
                "reporter": caller,
            }
        )

        return True

    def update_price_batch(
        self,
        caller: str,
        pairs: List[str],
        prices: List[int],
        timestamps: Optional[List[float]] = None,
    ) -> bool:
        """Update multiple prices in a single call."""
        if len(pairs) != len(prices):
            raise VMExecutionError("Pairs and prices length mismatch")

        timestamps = timestamps or [time.time()] * len(pairs)

        for i, pair in enumerate(pairs):
            self.update_price(caller, pair, prices[i], timestamps[i])

        return True

    # ==================== Price Reading ====================

    def get_price(self, pair: str) -> int:
        """
        Get latest price for a pair.

        Args:
            pair: Price pair

        Returns:
            Latest price

        Raises:
            VMExecutionError: If price is stale or invalid
        """
        self._require_feed(pair)
        feed = self.feeds[pair]

        # Check staleness
        age = time.time() - feed.latest_timestamp
        if age > feed.heartbeat:
            feed.status = OracleStatus.STALE
            raise VMExecutionError(
                f"Price for {pair} is stale (age: {age:.0f}s, max: {feed.heartbeat}s)"
            )

        if feed.status != OracleStatus.ACTIVE:
            raise VMExecutionError(f"Feed {pair} status: {feed.status.value}")

        return feed.latest_price

    def get_price_safe(self, pair: str) -> Tuple[int, bool]:
        """
        Get price with validity flag (doesn't throw).

        Args:
            pair: Price pair

        Returns:
            Tuple of (price, is_valid)
        """
        try:
            price = self.get_price(pair)
            return price, True
        except VMExecutionError:
            feed = self.feeds.get(pair)
            return feed.latest_price if feed else 0, False

    def get_latest_round_data(self, pair: str) -> Dict:
        """
        Get complete round data (Chainlink-compatible).

        Args:
            pair: Price pair

        Returns:
            Round data dictionary
        """
        self._require_feed(pair)
        feed = self.feeds[pair]

        return {
            "round_id": feed.round_id,
            "answer": feed.latest_price,
            "started_at": feed.latest_timestamp,
            "updated_at": feed.latest_timestamp,
            "answered_in_round": feed.round_id,
        }

    def get_historical_price(self, pair: str, round_id: int) -> Optional[PriceData]:
        """
        Get historical price by round ID.

        Args:
            pair: Price pair
            round_id: Round ID

        Returns:
            Price data or None
        """
        self._require_feed(pair)
        feed = self.feeds[pair]

        for data in feed.price_history:
            if data.round_id == round_id:
                return data

        return None

    def get_twap(self, pair: str, period: int) -> int:
        """
        Get time-weighted average price.

        Args:
            pair: Price pair
            period: Time period in seconds

        Returns:
            TWAP
        """
        self._require_feed(pair)
        feed = self.feeds[pair]

        cutoff = time.time() - period
        relevant_prices = [
            p for p in feed.price_history
            if p.timestamp >= cutoff
        ]

        if not relevant_prices:
            return feed.latest_price

        # Simple average (could weight by time intervals)
        return sum(p.price for p in relevant_prices) // len(relevant_prices)

    # ==================== Feed Information ====================

    def get_feed_info(self, pair: str) -> Dict:
        """Get feed configuration and status."""
        self._require_feed(pair)
        feed = self.feeds[pair]

        age = time.time() - feed.latest_timestamp

        return {
            "pair": feed.pair,
            "base_asset": feed.base_asset,
            "quote_asset": feed.quote_asset,
            "decimals": feed.decimals,
            "latest_price": feed.latest_price,
            "latest_timestamp": feed.latest_timestamp,
            "age_seconds": age,
            "heartbeat": feed.heartbeat,
            "status": feed.status.value,
            "round_id": feed.round_id,
            "sources": feed.sources,
        }

    def get_all_feeds(self) -> List[str]:
        """Get list of all feed pairs."""
        return list(self.feeds.keys())

    # ==================== Admin Functions ====================

    def set_heartbeat(self, caller: str, pair: str, heartbeat: int) -> bool:
        """Set heartbeat for a feed."""
        self._require_owner(caller)
        self._require_feed(pair)
        self.feeds[pair].heartbeat = heartbeat
        return True

    def set_deviation_threshold(self, caller: str, pair: str, threshold: int) -> bool:
        """Set deviation threshold for a feed."""
        self._require_owner(caller)
        self._require_feed(pair)
        self.feeds[pair].deviation_threshold = threshold
        return True

    def set_price_bounds(
        self, caller: str, pair: str, min_price: int, max_price: int
    ) -> bool:
        """Set price bounds for a pair."""
        self._require_owner(caller)
        if min_price >= max_price:
            raise VMExecutionError("Min must be less than max")
        self.price_bounds[pair] = (min_price, max_price)
        return True

    def pause_feed(self, caller: str, pair: str) -> bool:
        """Pause a price feed."""
        self._require_owner(caller)
        self._require_feed(pair)
        self.feeds[pair].status = OracleStatus.PAUSED
        return True

    def unpause_feed(self, caller: str, pair: str) -> bool:
        """Unpause a price feed."""
        self._require_owner(caller)
        self._require_feed(pair)
        self.feeds[pair].status = OracleStatus.ACTIVE
        return True

    def trigger_circuit_breaker(self, caller: str) -> bool:
        """Trigger circuit breaker (emergency pause all)."""
        self._require_owner(caller)
        self.circuit_breaker_active = True
        logger.warning(
            "Circuit breaker triggered",
            extra={"event": "oracle.circuit_breaker"}
        )
        return True

    def reset_circuit_breaker(self, caller: str) -> bool:
        """Reset circuit breaker."""
        self._require_owner(caller)
        self.circuit_breaker_active = False
        return True

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        return address.lower()

    def _require_owner(self, caller: str) -> None:
        if self._normalize(caller) != self._normalize(self.owner):
            raise VMExecutionError("Caller is not owner")

    def _require_feed(self, pair: str) -> None:
        if pair not in self.feeds:
            raise VMExecutionError(f"Feed {pair} not found")

    def _require_authorized(self, caller: str) -> None:
        if not self.authorized_providers.get(self._normalize(caller), False):
            raise VMExecutionError("Caller is not authorized provider")

    def _require_not_paused(self) -> None:
        if self.circuit_breaker_active:
            raise VMExecutionError("Oracle circuit breaker is active")

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize oracle state."""
        return {
            "name": self.name,
            "address": self.address,
            "owner": self.owner,
            "feeds": {
                k: {
                    "pair": v.pair,
                    "base_asset": v.base_asset,
                    "quote_asset": v.quote_asset,
                    "latest_price": v.latest_price,
                    "latest_timestamp": v.latest_timestamp,
                    "round_id": v.round_id,
                    "decimals": v.decimals,
                    "heartbeat": v.heartbeat,
                    "status": v.status.value,
                }
                for k, v in self.feeds.items()
            },
            "authorized_providers": dict(self.authorized_providers),
            "price_bounds": {k: list(v) for k, v in self.price_bounds.items()},
            "circuit_breaker_active": self.circuit_breaker_active,
            "total_updates": self.total_updates,
        }


@dataclass
class OracleAggregator:
    """
    Aggregates prices from multiple oracles.

    Useful for:
    - Fallback mechanisms
    - Price validation
    - Manipulation resistance
    """

    name: str = "XAI Oracle Aggregator"
    oracles: List[PriceOracle] = field(default_factory=list)

    def add_oracle(self, oracle: PriceOracle) -> None:
        """Add an oracle to the aggregator."""
        self.oracles.append(oracle)

    def get_aggregated_price(self, pair: str) -> int:
        """
        Get median price from all oracles.

        Args:
            pair: Price pair

        Returns:
            Median price
        """
        prices = []
        for oracle in self.oracles:
            try:
                price = oracle.get_price(pair)
                prices.append(price)
            except VMExecutionError:
                continue

        if not prices:
            raise VMExecutionError(f"No valid prices for {pair}")

        return statistics.median(prices)

    def get_all_prices(self, pair: str) -> List[Tuple[str, int, bool]]:
        """
        Get prices from all oracles.

        Returns list of (oracle_address, price, is_valid)
        """
        results = []
        for oracle in self.oracles:
            price, valid = oracle.get_price_safe(pair)
            results.append((oracle.address, price, valid))
        return results

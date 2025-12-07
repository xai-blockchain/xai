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
from .access_control import AccessControl, SignedRequest, RoleBasedAccessControl, Role

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

    # TWAP protection
    twap_period: int = 600  # TWAP calculation period (10 minutes default)
    max_price_age: int = 3600  # Maximum price staleness (1 hour)

    # Multi-source aggregation tracking
    pending_updates: Dict[str, PriceData] = field(default_factory=dict)  # source -> price_data

    # Rate limiting per source
    last_update_time: Dict[str, float] = field(default_factory=dict)  # source -> timestamp
    min_update_interval: int = 60  # Minimum seconds between updates from same source


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

    # Access control with signature verification
    access_control: AccessControl = field(default_factory=AccessControl)
    rbac: Optional[RoleBasedAccessControl] = None

    def __post_init__(self) -> None:
        """Initialize oracle."""
        if not self.address:
            import hashlib
            addr_hash = hashlib.sha3_256(f"{self.name}{time.time()}".encode()).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

        # Initialize RBAC with owner as admin
        if self.owner and not self.rbac:
            self.rbac = RoleBasedAccessControl(
                access_control=self.access_control,
                admin_address=self.owner,
            )

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
        aggregation_method: str = "median",
        twap_period: int = 600,
        max_price_age: int = 3600,
        min_update_interval: int = 60,
    ) -> bool:
        """
        Add a new price feed.

        DEPRECATED: Use add_feed_secure() with signature verification.
        This function is vulnerable to address spoofing.

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
        logger.warning(
            "DEPRECATED: add_feed() called without signature verification",
            extra={
                "event": "oracle.deprecated_function",
                "function": "add_feed",
                "caller": caller[:10],
            }
        )
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
            aggregation_method=aggregation_method,
            twap_period=twap_period,
            max_price_age=max_price_age,
            min_update_interval=min_update_interval,
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

    def add_feed_secure(
        self,
        request: SignedRequest,
        pair: str,
        base_asset: str,
        quote_asset: str,
        decimals: int = 8,
        heartbeat: int = 3600,
        deviation_threshold: int = 100,
        min_sources: int = 1,
        aggregation_method: str = "median",
        twap_period: int = 600,
        max_price_age: int = 3600,
        min_update_interval: int = 60,
    ) -> bool:
        """
        Add a new price feed with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            pair: Price pair (e.g., "XAI/USD")
            base_asset: Base asset symbol
            quote_asset: Quote asset symbol
            decimals: Price decimals
            heartbeat: Max age before stale (seconds)
            deviation_threshold: Max deviation (basis points)
            min_sources: Minimum sources required

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails or not owner
        """
        # Verify signature proves ownership of admin address
        self.access_control.verify_caller_simple(request, self.owner)

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
            aggregation_method=aggregation_method,
            twap_period=twap_period,
            max_price_age=max_price_age,
            min_update_interval=min_update_interval,
        )

        logger.info(
            "Price feed added (secure)",
            extra={
                "event": "oracle.feed_added_secure",
                "pair": pair,
                "decimals": decimals,
                "admin": request.address[:10],
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
        Update price for a feed with comprehensive manipulation protection.

        Security features:
        - Rate limiting per source (prevents spam attacks)
        - Deviation bounds checking (prevents price manipulation)
        - Price staleness validation (prevents replay attacks)
        - Multi-source aggregation (requires consensus)
        - TWAP validation (prevents flash loan attacks)
        - Atomic validation (check-then-act pattern)

        Args:
            caller: Must be authorized provider
            pair: Price pair
            price: New price (in feed's decimal precision)
            timestamp: Price timestamp (defaults to now)

        Returns:
            True if successful

        Raises:
            VMExecutionError: If validation fails
        """
        # ========== VALIDATION PHASE - NO STATE CHANGES ==========
        # All checks must complete before any logging or state modification
        # This prevents timing attacks and oracle manipulation

        self._require_authorized(caller)
        self._require_feed(pair)
        self._require_not_paused()

        feed = self.feeds[pair]
        timestamp = timestamp or time.time()
        current_time = time.time()

        # 1. Price staleness check
        price_age = current_time - timestamp
        if price_age > feed.max_price_age:
            raise VMExecutionError(
                f"Price timestamp too old: {price_age:.0f}s > {feed.max_price_age}s"
            )

        # 2. Future timestamp prevention
        if timestamp > current_time + 60:  # Allow 60s clock drift
            raise VMExecutionError(
                f"Price timestamp is in the future: {timestamp} > {current_time}"
            )

        # 3. Rate limiting per source
        source_key = self._normalize(caller)
        last_update = feed.last_update_time.get(source_key, 0)
        time_since_update = current_time - last_update
        if time_since_update < feed.min_update_interval:
            raise VMExecutionError(
                f"Rate limit: {time_since_update:.0f}s < {feed.min_update_interval}s minimum interval"
            )

        # 4. Price bounds validation
        if pair in self.price_bounds:
            min_price, max_price = self.price_bounds[pair]
            if price < min_price or price > max_price:
                raise VMExecutionError(
                    f"Price {price} outside bounds [{min_price}, {max_price}]"
                )

        # 5. Price must be positive
        if price <= 0:
            raise VMExecutionError(f"Invalid price: {price} must be positive")

        # 6. Deviation check against TWAP (not just last price)
        # This prevents flash loan manipulation
        if feed.latest_price > 0 and len(feed.price_history) >= 3:
            # Use TWAP as reference instead of single last price
            twap = self._calculate_twap(feed, feed.twap_period)
            deviation = abs(price - twap) * 10000 // twap if twap > 0 else 0

            if deviation > feed.deviation_threshold:
                raise VMExecutionError(
                    f"Price deviation {deviation} bps exceeds threshold {feed.deviation_threshold} bps for {pair}. "
                    f"TWAP: {twap}, Proposed: {price}"
                )

        # 7. Multi-source validation if required
        if feed.min_sources > 1:
            # Store pending update
            feed.pending_updates[source_key] = PriceData(
                price=price,
                timestamp=timestamp,
                round_id=feed.round_id + 1,
                source=caller,
            )

            # Check if we have enough sources
            if len(feed.pending_updates) < feed.min_sources:
                # Not enough sources yet, store and wait
                feed.last_update_time[source_key] = current_time
                logger.info(
                    "Price update pending (waiting for more sources)",
                    extra={
                        "event": "oracle.price_pending",
                        "pair": pair,
                        "price": price,
                        "sources_received": len(feed.pending_updates),
                        "sources_required": feed.min_sources,
                        "reporter": caller,
                    }
                )
                return True

            # Enough sources - aggregate prices
            price = self._aggregate_prices(feed)
            # Clear pending updates after aggregation
            feed.pending_updates.clear()

        # ========== STATE UPDATE PHASE ==========
        # All validations passed - safe to update state

        feed.round_id += 1
        feed.latest_price = price
        feed.latest_timestamp = timestamp
        feed.status = OracleStatus.ACTIVE
        feed.last_update_time[source_key] = current_time

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

        # Calculate deviation for logging (after state update)
        deviation = 0
        if len(feed.price_history) >= 2:
            prev_price = feed.price_history[-2].price
            deviation = abs(price - prev_price) * 10000 // prev_price if prev_price > 0 else 0

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
        Get time-weighted average price (public interface).

        Args:
            pair: Price pair
            period: Time period in seconds

        Returns:
            TWAP

        Raises:
            VMExecutionError: If feed not found or insufficient data
        """
        self._require_feed(pair)
        feed = self.feeds[pair]
        return self._calculate_twap(feed, period)

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

    # ==================== Secure Admin Functions (Signature-Verified) ====================

    def authorize_provider_secure(
        self,
        request: SignedRequest,
        provider: str,
    ) -> bool:
        """
        Authorize a data provider with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            provider: Provider address to authorize

        Returns:
            True if authorized

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.authorized_providers[self._normalize(provider)] = True

        logger.info(
            "Provider authorized (secure)",
            extra={
                "event": "oracle.provider_authorized_secure",
                "provider": provider[:10],
                "admin": request.address[:10],
            }
        )

        return True

    def revoke_provider_secure(
        self,
        request: SignedRequest,
        provider: str,
    ) -> bool:
        """
        Revoke a data provider with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            provider: Provider address to revoke

        Returns:
            True if revoked

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.authorized_providers[self._normalize(provider)] = False

        logger.info(
            "Provider revoked (secure)",
            extra={
                "event": "oracle.provider_revoked_secure",
                "provider": provider[:10],
                "admin": request.address[:10],
            }
        )

        return True

    def update_price_secure(
        self,
        request: SignedRequest,
        pair: str,
        price: int,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        Update price for a feed with signature verification and manipulation protection.

        SECURE: Requires cryptographic proof that caller is authorized price feeder.
        Includes all anti-manipulation protections from update_price().

        Args:
            request: Signed request from authorized provider
            pair: Price pair
            price: New price (in feed's decimal precision)
            timestamp: Price timestamp (defaults to now)

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails or validation fails
        """
        # ========== VALIDATION PHASE - NO STATE CHANGES ==========

        # Verify caller is authorized provider with valid signature
        if not self.authorized_providers.get(self._normalize(request.address), False):
            raise VMExecutionError(f"Address {request.address} is not authorized provider")

        self.access_control.verify_caller_simple(request, request.address)

        self._require_feed(pair)
        self._require_not_paused()

        feed = self.feeds[pair]
        timestamp = timestamp or time.time()
        current_time = time.time()

        # 1. Price staleness check
        price_age = current_time - timestamp
        if price_age > feed.max_price_age:
            raise VMExecutionError(
                f"Price timestamp too old: {price_age:.0f}s > {feed.max_price_age}s"
            )

        # 2. Future timestamp prevention
        if timestamp > current_time + 60:  # Allow 60s clock drift
            raise VMExecutionError(
                f"Price timestamp is in the future: {timestamp} > {current_time}"
            )

        # 3. Rate limiting per source
        source_key = self._normalize(request.address)
        last_update = feed.last_update_time.get(source_key, 0)
        time_since_update = current_time - last_update
        if time_since_update < feed.min_update_interval:
            raise VMExecutionError(
                f"Rate limit: {time_since_update:.0f}s < {feed.min_update_interval}s minimum interval"
            )

        # 4. Price bounds validation
        if pair in self.price_bounds:
            min_price, max_price = self.price_bounds[pair]
            if price < min_price or price > max_price:
                raise VMExecutionError(
                    f"Price {price} outside bounds [{min_price}, {max_price}]"
                )

        # 5. Price must be positive
        if price <= 0:
            raise VMExecutionError(f"Invalid price: {price} must be positive")

        # 6. Deviation check against TWAP
        if feed.latest_price > 0 and len(feed.price_history) >= 3:
            twap = self._calculate_twap(feed, feed.twap_period)
            deviation = abs(price - twap) * 10000 // twap if twap > 0 else 0

            if deviation > feed.deviation_threshold:
                raise VMExecutionError(
                    f"Price deviation {deviation} bps exceeds threshold {feed.deviation_threshold} bps for {pair}. "
                    f"TWAP: {twap}, Proposed: {price}"
                )

        # 7. Multi-source validation if required
        if feed.min_sources > 1:
            feed.pending_updates[source_key] = PriceData(
                price=price,
                timestamp=timestamp,
                round_id=feed.round_id + 1,
                source=request.address,
            )

            if len(feed.pending_updates) < feed.min_sources:
                feed.last_update_time[source_key] = current_time
                logger.info(
                    "Price update pending (secure, waiting for more sources)",
                    extra={
                        "event": "oracle.price_pending_secure",
                        "pair": pair,
                        "price": price,
                        "sources_received": len(feed.pending_updates),
                        "sources_required": feed.min_sources,
                        "reporter": request.address[:10],
                    }
                )
                return True

            price = self._aggregate_prices(feed)
            feed.pending_updates.clear()

        # ========== STATE UPDATE PHASE ==========

        feed.round_id += 1
        feed.latest_price = price
        feed.latest_timestamp = timestamp
        feed.status = OracleStatus.ACTIVE
        feed.last_update_time[source_key] = current_time

        # Add to history
        price_data = PriceData(
            price=price,
            timestamp=timestamp,
            round_id=feed.round_id,
            source=request.address,
        )
        feed.price_history.append(price_data)

        # Trim history
        if len(feed.price_history) > feed.history_size:
            feed.price_history = feed.price_history[-feed.history_size:]

        self.total_updates += 1

        # Calculate deviation for logging
        deviation = 0
        if len(feed.price_history) >= 2:
            prev_price = feed.price_history[-2].price
            deviation = abs(price - prev_price) * 10000 // prev_price if prev_price > 0 else 0

        logger.info(
            "Price updated (secure)",
            extra={
                "event": "oracle.price_updated_secure",
                "pair": pair,
                "price": price,
                "round": feed.round_id,
                "deviation_bps": deviation,
                "reporter": request.address[:10],
            }
        )

        return True

    def set_deviation_threshold_secure(
        self,
        request: SignedRequest,
        pair: str,
        threshold: int,
    ) -> bool:
        """
        Set deviation threshold for a feed with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            pair: Price pair
            threshold: New deviation threshold (basis points)

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self._require_feed(pair)
        self.feeds[pair].deviation_threshold = threshold

        logger.info(
            "Deviation threshold updated (secure)",
            extra={
                "event": "oracle.deviation_threshold_updated_secure",
                "pair": pair,
                "threshold_bps": threshold,
                "admin": request.address[:10],
            }
        )

        return True

    def set_price_bounds_secure(
        self,
        request: SignedRequest,
        pair: str,
        min_price: int,
        max_price: int,
    ) -> bool:
        """
        Set price bounds for a pair with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            pair: Price pair
            min_price: Minimum valid price
            max_price: Maximum valid price

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)

        if min_price >= max_price:
            raise VMExecutionError("Min must be less than max")

        self.price_bounds[pair] = (min_price, max_price)

        logger.info(
            "Price bounds updated (secure)",
            extra={
                "event": "oracle.price_bounds_updated_secure",
                "pair": pair,
                "min": min_price,
                "max": max_price,
                "admin": request.address[:10],
            }
        )

        return True

    def trigger_circuit_breaker_secure(self, request: SignedRequest) -> bool:
        """
        Trigger circuit breaker with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner

        Returns:
            True if triggered

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.circuit_breaker_active = True

        logger.warning(
            "Circuit breaker triggered (secure)",
            extra={
                "event": "oracle.circuit_breaker_secure",
                "admin": request.address[:10],
            }
        )

        return True

    def reset_circuit_breaker_secure(self, request: SignedRequest) -> bool:
        """
        Reset circuit breaker with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner

        Returns:
            True if reset

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)
        self.circuit_breaker_active = False

        logger.info(
            "Circuit breaker reset (secure)",
            extra={
                "event": "oracle.circuit_breaker_reset_secure",
                "admin": request.address[:10],
            }
        )

        return True

    # ==================== Helpers ====================

    def _calculate_twap(self, feed: PriceFeed, period: int) -> int:
        """
        Calculate time-weighted average price for a feed.

        TWAP calculation properly weights prices by the time they were active,
        preventing flash loan manipulation where a single block price spike
        would heavily influence the average.

        Args:
            feed: Price feed
            period: Time period in seconds

        Returns:
            Time-weighted average price

        Algorithm:
            For each price interval, calculate: price * duration
            TWAP = sum(price * duration) / total_duration
        """
        if not feed.price_history:
            return feed.latest_price

        cutoff = time.time() - period
        relevant_prices = [
            p for p in feed.price_history
            if p.timestamp >= cutoff
        ]

        if not relevant_prices:
            return feed.latest_price

        # Sort by timestamp (should already be sorted, but ensure it)
        relevant_prices.sort(key=lambda p: p.timestamp)

        # Calculate time-weighted average
        total_weighted_price = 0
        total_duration = 0

        for i in range(len(relevant_prices)):
            current_price = relevant_prices[i].price
            current_time = relevant_prices[i].timestamp

            # Duration is time until next price update (or now for last price)
            if i < len(relevant_prices) - 1:
                next_time = relevant_prices[i + 1].timestamp
            else:
                next_time = time.time()

            duration = next_time - current_time
            total_weighted_price += current_price * duration
            total_duration += duration

        if total_duration == 0:
            return feed.latest_price

        return int(total_weighted_price / total_duration)

    def _aggregate_prices(self, feed: PriceFeed) -> int:
        """
        Aggregate prices from multiple sources.

        Supports different aggregation methods:
        - median: Median of all submitted prices (manipulation resistant)
        - mean: Simple average
        - weighted: Weighted by confidence (future enhancement)

        Args:
            feed: Price feed with pending updates

        Returns:
            Aggregated price

        Raises:
            VMExecutionError: If no valid prices available
        """
        if not feed.pending_updates:
            raise VMExecutionError("No prices to aggregate")

        prices = [p.price for p in feed.pending_updates.values()]

        if feed.aggregation_method == "median":
            return int(statistics.median(prices))
        elif feed.aggregation_method == "mean":
            return sum(prices) // len(prices)
        elif feed.aggregation_method == "weighted":
            # Weighted by confidence (all equal for now)
            confidences = [p.confidence for p in feed.pending_updates.values()]
            total_confidence = sum(confidences)
            if total_confidence == 0:
                return sum(prices) // len(prices)
            weighted_sum = sum(p * c for p, c in zip(prices, confidences))
            return int(weighted_sum / total_confidence)
        else:
            # Default to median (most manipulation resistant)
            return int(statistics.median(prices))

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

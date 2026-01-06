"""
DEX and Liquidity Pool Metrics for XAI Blockchain

Comprehensive Prometheus metrics for swap operations, liquidity management,
and pool health monitoring following proven patterns.
"""

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram


class DEXMetrics:
    """Metrics for DEX operations and liquidity pools."""

    def __init__(self, registry=None):
        self.registry = registry or REGISTRY

        # Swap metrics
        self.swaps_total = Counter(
            'xai_dex_swaps_total',
            'Total number of swaps executed',
            ['pool', 'token_in', 'token_out', 'status'],
            registry=self.registry
        )

        self.swap_volume = Counter(
            'xai_dex_swap_volume_total',
            'Total swap volume in base units',
            ['pool', 'denom'],
            registry=self.registry
        )

        self.swap_latency = Histogram(
            'xai_dex_swap_latency_seconds',
            'Swap execution latency',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )

        self.swap_slippage = Histogram(
            'xai_dex_swap_slippage_percent',
            'Swap slippage percentage',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )

        self.swap_fees_collected = Counter(
            'xai_dex_swap_fees_collected_total',
            'Total swap fees collected',
            ['pool', 'denom'],
            registry=self.registry
        )

        # Liquidity metrics
        self.liquidity_added = Counter(
            'xai_dex_liquidity_added_total',
            'Total liquidity added to pools',
            ['pool', 'denom'],
            registry=self.registry
        )

        self.liquidity_removed = Counter(
            'xai_dex_liquidity_removed_total',
            'Total liquidity removed from pools',
            ['pool', 'denom'],
            registry=self.registry
        )

        self.pool_reserves = Gauge(
            'xai_dex_pool_reserves',
            'Current pool reserves',
            ['pool', 'denom'],
            registry=self.registry
        )

        self.lp_token_supply = Gauge(
            'xai_dex_lp_token_supply',
            'LP token supply per pool',
            ['pool'],
            registry=self.registry
        )

        self.pool_tvl = Gauge(
            'xai_dex_pool_tvl_total',
            'Total Value Locked in pool',
            ['pool'],
            registry=self.registry
        )

        # Pool health metrics
        self.pools_total = Gauge(
            'xai_dex_pools_total',
            'Total number of liquidity pools',
            registry=self.registry
        )

        self.pool_creations = Counter(
            'xai_dex_pool_creations_total',
            'Total pools created',
            registry=self.registry
        )

        self.pool_imbalance_ratio = Gauge(
            'xai_dex_pool_imbalance_ratio',
            'Pool reserve ratio (reserve0/reserve1)',
            ['pool'],
            registry=self.registry
        )

        self.pool_fee_tier = Gauge(
            'xai_dex_pool_fee_tier',
            'Pool fee tier in basis points',
            ['pool'],
            registry=self.registry
        )

        # Concentrated liquidity metrics (XAI-specific)
        self.concentrated_liquidity_positions = Gauge(
            'xai_dex_concentrated_liquidity_positions',
            'Active concentrated liquidity positions',
            ['pool'],
            registry=self.registry
        )

        self.tick_liquidity = Gauge(
            'xai_dex_tick_liquidity',
            'Liquidity at specific price tick',
            ['pool', 'tick'],
            registry=self.registry
        )

        # Trading order metrics
        self.orders_placed = Counter(
            'xai_dex_orders_placed_total',
            'Orders placed',
            ['order_type'],
            registry=self.registry
        )

        self.orders_filled = Counter(
            'xai_dex_orders_filled_total',
            'Orders filled',
            ['order_type'],
            registry=self.registry
        )

        self.orders_cancelled = Counter(
            'xai_dex_orders_cancelled_total',
            'Orders cancelled',
            registry=self.registry
        )

        # Security metrics
        self.circuit_breaker_active = Gauge(
            'xai_dex_circuit_breaker_active',
            'Circuit breaker activation status (0=inactive, 1=active)',
            ['pool'],
            registry=self.registry
        )

        self.circuit_breaker_triggers = Counter(
            'xai_dex_circuit_breaker_triggers_total',
            'Circuit breaker trigger events',
            ['pool', 'reason'],
            registry=self.registry
        )

        self.mev_protections_triggered = Counter(
            'xai_dex_mev_protections_triggered_total',
            'MEV protection mechanisms triggered',
            ['pool', 'protection_type'],
            registry=self.registry
        )

        self.suspicious_activity = Counter(
            'xai_dex_suspicious_activity_detected_total',
            'Suspicious activity detections',
            ['type'],
            registry=self.registry
        )

        # TWAP metrics
        self.twap_updates = Counter(
            'xai_dex_twap_updates_total',
            'TWAP update operations',
            registry=self.registry
        )

        self.twap_price = Gauge(
            'xai_dex_twap_price',
            'Time-weighted average price',
            ['pool'],
            registry=self.registry
        )

        # Atomic swap metrics (XAI cross-chain)
        self.atomic_swaps_initiated = Counter(
            'xai_dex_atomic_swaps_initiated_total',
            'Atomic swaps initiated',
            ['dest_chain'],
            registry=self.registry
        )

        self.atomic_swaps_completed = Counter(
            'xai_dex_atomic_swaps_completed_total',
            'Atomic swaps completed',
            ['dest_chain'],
            registry=self.registry
        )

        self.atomic_swaps_refunded = Counter(
            'xai_dex_atomic_swaps_refunded_total',
            'Atomic swaps refunded after timeout',
            registry=self.registry
        )

        # Performance metrics
        self.price_impact = Histogram(
            'xai_dex_price_impact_percent',
            'Price impact of swaps',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
            registry=self.registry
        )

        self.route_hops = Histogram(
            'xai_dex_route_hops',
            'Number of hops in swap route',
            buckets=[1, 2, 3, 4, 5],
            registry=self.registry
        )


# Singleton instance
_dex_metrics_instance = None


def get_dex_metrics(registry=None):
    """Get or create singleton DEX metrics instance."""
    global _dex_metrics_instance
    if _dex_metrics_instance is None:
        _dex_metrics_instance = DEXMetrics(registry=registry)
    return _dex_metrics_instance


# Convenience function for tracking swaps
def track_swap(pool_id, token_in, token_out, volume, duration_seconds, slippage_percent, status='success'):
    """Track swap execution with automatic metric updates."""
    metrics = get_dex_metrics()

    # Record swap
    metrics.swaps_total.labels(
        pool=pool_id,
        token_in=token_in,
        token_out=token_out,
        status=status
    ).inc()

    # Record volume
    metrics.swap_volume.labels(
        pool=pool_id,
        denom=token_in
    ).inc(volume)

    # Record latency
    metrics.swap_latency.observe(duration_seconds)

    # Record slippage
    metrics.swap_slippage.observe(slippage_percent)


# Convenience function for tracking liquidity changes
def track_liquidity_change(pool_id, denom, amount, operation='add'):
    """Track liquidity additions/removals."""
    metrics = get_dex_metrics()

    if operation == 'add':
        metrics.liquidity_added.labels(pool=pool_id, denom=denom).inc(amount)
    elif operation == 'remove':
        metrics.liquidity_removed.labels(pool=pool_id, denom=denom).inc(amount)

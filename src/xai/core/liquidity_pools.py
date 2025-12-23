from __future__ import annotations

"""
XAI Built-In Liquidity Pools

AMM-style liquidity pools for instant swaps
All pairs supported - free market pricing
"""

import hashlib
import json
import os
import time
from enum import Enum

from xai.core.audit_signer import AuditSigner
from xai.core.config import Config

class PoolPair(Enum):
    """Supported liquidity pool pairs"""

    XAI_USDT = "XAI/USDT"
    XAI_USDC = "XAI/USDC"
    XAI_DAI = "XAI/DAI"
    XAI_BTC = "XAI/BTC"
    XAI_ETH = "XAI/ETH"
    XAI_LTC = "XAI/LTC"
    XAI_DOGE = "XAI/DOGE"
    XAI_BCH = "XAI/BCH"
    XAI_ZEC = "XAI/ZEC"
    XAI_DASH = "XAI/DASH"
    XAI_XMR = "XAI/XMR"

class LiquidityPool:
    """
    AMM-style liquidity pool using constant product formula (x * y = k)

    Like Uniswap but built into XAI protocol
    """

    def __init__(self, pair: PoolPair, fee_percentage: float = 0.003):
        self.pair = pair
        self.fee_percentage = fee_percentage  # 0.3% default
        self.protocol_fee_percentage = 0.0005  # 0.05% to protocol

        # Pool reserves
        self.xai_reserve = 0.0
        self.other_reserve = 0.0

        # Liquidity provider tracking
        self.total_liquidity_tokens = 0.0
        self.liquidity_providers = {}  # address -> lp_tokens

        # Stats
        self.total_volume = 0.0
        self.total_fees_collected = 0.0
        self.swap_count = 0
        self.protocol_fee_balance = 0.0
        self.event_log = []
        self.audit_signer = AuditSigner(os.path.join(Config.DATA_DIR, "liquidity_audit"))

    def add_liquidity(self, provider_address: str, xai_amount: float, other_amount: float) -> Dict:
        """
        Add liquidity to pool

        Returns LP tokens representing share of pool
        """
        # Import metrics
        from xai.core.dex_metrics import get_dex_metrics
        metrics = get_dex_metrics()

        if xai_amount <= 0 or other_amount <= 0:
            return {"success": False, "error": "Invalid amounts"}

        # First liquidity provider sets the ratio
        if self.total_liquidity_tokens == 0:
            lp_tokens = (xai_amount * other_amount) ** 0.5  # Geometric mean

            self.xai_reserve = xai_amount
            self.other_reserve = other_amount
            self.total_liquidity_tokens = lp_tokens

            if provider_address not in self.liquidity_providers:
                self.liquidity_providers[provider_address] = 0.0
            self.liquidity_providers[provider_address] += lp_tokens

            payload = {
                "provider": provider_address,
                "lp_tokens": lp_tokens,
                "xai": xai_amount,
                "other": other_amount,
                "pool_share": 100.0,
            }
            self._log_event("initial_liquidity", payload)
            return {
                "success": True,
                "lp_tokens": lp_tokens,
                "xai_deposited": xai_amount,
                "other_deposited": other_amount,
                "pool_share_percentage": 100.0,
                "initial_price": other_amount / xai_amount,
            }

        # Subsequent providers must match current ratio
        current_ratio = self.other_reserve / self.xai_reserve
        required_other = xai_amount * current_ratio

        # Use the amount that maintains ratio
        if other_amount > required_other:
            other_amount = required_other
        else:
            xai_amount = other_amount / current_ratio

        # Calculate LP tokens proportional to contribution
        lp_tokens = (xai_amount / self.xai_reserve) * self.total_liquidity_tokens

        # Update reserves and tokens
        self.xai_reserve += xai_amount
        self.other_reserve += other_amount
        self.total_liquidity_tokens += lp_tokens

        if provider_address not in self.liquidity_providers:
            self.liquidity_providers[provider_address] = 0.0
        self.liquidity_providers[provider_address] += lp_tokens

        pool_share = (lp_tokens / self.total_liquidity_tokens) * 100
        self._log_event(
            "add_liquidity",
            {
                "provider": provider_address,
                "xai": xai_amount,
                "other": other_amount,
                "lp_tokens": lp_tokens,
                "share": pool_share,
            },
        )

        # Record metrics
        pool_id = str(self.pair.value)
        metrics.liquidity_added.labels(pool=pool_id, denom="XAI").inc(xai_amount)
        metrics.liquidity_added.labels(pool=pool_id, denom=self.pair.value.split("/")[1]).inc(other_amount)
        metrics.pool_reserves.labels(pool=pool_id, denom="XAI").set(self.xai_reserve)
        metrics.pool_reserves.labels(pool=pool_id, denom=self.pair.value.split("/")[1]).set(self.other_reserve)
        metrics.lp_token_supply.labels(pool=pool_id).set(self.total_liquidity_tokens)

        return {
            "success": True,
            "lp_tokens": lp_tokens,
            "xai_deposited": xai_amount,
            "other_deposited": other_amount,
            "pool_share_percentage": pool_share,
            "current_price": self.other_reserve / self.xai_reserve,
        }

    def remove_liquidity(self, provider_address: str, lp_tokens: float) -> Dict:
        """
        Remove liquidity from pool

        Burns LP tokens, returns proportional share of reserves
        """

        if provider_address not in self.liquidity_providers:
            return {"success": False, "error": "Not a liquidity provider"}

        provider_tokens = self.liquidity_providers[provider_address]

        if lp_tokens > provider_tokens or lp_tokens <= 0:
            return {
                "success": False,
                "error": "Insufficient LP tokens",
                "available": provider_tokens,
                "requested": lp_tokens,
            }

        # Calculate share of pool
        share = lp_tokens / self.total_liquidity_tokens

        xai_amount = share * self.xai_reserve
        other_amount = share * self.other_reserve

        # Update reserves
        self.xai_reserve -= xai_amount
        self.other_reserve -= other_amount
        self.total_liquidity_tokens -= lp_tokens
        self.liquidity_providers[provider_address] -= lp_tokens
        self._log_event(
            "remove_liquidity",
            {
                "provider": provider_address,
                "xai_returned": xai_amount,
                "other_returned": other_amount,
                "lp_tokens": lp_tokens,
            },
        )

        return {
            "success": True,
            "xai_returned": xai_amount,
            "other_returned": other_amount,
            "lp_tokens_burned": lp_tokens,
            "remaining_lp_tokens": self.liquidity_providers[provider_address],
        }

    def swap_xai_for_other(self, xai_amount: float, max_slippage_pct: float = 5.0) -> Dict:
        """
        Swap XAI for other token

        Uses constant product formula: x * y = k
        """
        # Import metrics
        import time

        from xai.core.dex_metrics import get_dex_metrics
        metrics = get_dex_metrics()
        start_time = time.time()

        if xai_amount <= 0:
            return {"success": False, "error": "Invalid amount"}

        if self.xai_reserve == 0 or self.other_reserve == 0:
            return {"success": False, "error": "Pool has no liquidity"}

        # Apply trading fee
        xai_after_fee = xai_amount * (1 - self.fee_percentage - self.protocol_fee_percentage)

        # Calculate output using x * y = k
        # (x + dx) * (y - dy) = k
        # dy = y - (k / (x + dx))

        k = self.xai_reserve * self.other_reserve
        new_xai_reserve = self.xai_reserve + xai_after_fee
        new_other_reserve = k / new_xai_reserve

        other_output = self.other_reserve - new_other_reserve

        # Calculate price impact
        price_before = self.other_reserve / self.xai_reserve
        price_after = new_other_reserve / new_xai_reserve
        price_impact = abs(price_after - price_before) / price_before * 100

        if price_impact > max_slippage_pct:
            return {
                "success": False,
                "error": "Slippage too high",
                "price_impact_percent": price_impact,
                "max_slippage_pct": max_slippage_pct,
            }

        # Collect fees
        fee_amount = xai_amount * self.fee_percentage
        protocol_fee = xai_amount * self.protocol_fee_percentage
        self.protocol_fee_balance += protocol_fee

        # Update reserves
        self.xai_reserve = new_xai_reserve
        self.other_reserve = new_other_reserve

        # Update stats
        self.total_volume += xai_amount
        self.total_fees_collected += fee_amount
        self.swap_count += 1

        self._log_event(
            "swap",
            {
                "input_xai": xai_amount,
                "output_other": other_output,
                "protocol_fee": protocol_fee,
                "price_impact": price_impact,
            },
        )

        # Record metrics
        pool_id = str(self.pair.value)
        metrics.swaps_total.labels(pool=pool_id, token_in="XAI", token_out=self.pair.value.split("/")[1], status="success").inc()
        metrics.swap_volume.labels(pool=pool_id, denom="XAI").inc(xai_amount)
        metrics.swap_latency.observe(time.time() - start_time)
        metrics.swap_slippage.observe(price_impact)
        metrics.swap_fees_collected.labels(pool=pool_id, denom="XAI").inc(fee_amount)
        metrics.pool_reserves.labels(pool=pool_id, denom="XAI").set(self.xai_reserve)
        metrics.pool_reserves.labels(pool=pool_id, denom=self.pair.value.split("/")[1]).set(self.other_reserve)

        return {
            "success": True,
            "input_xai": xai_amount,
            "output_other": other_output,
            "effective_price": other_output / xai_amount,
            "price_impact_percent": price_impact,
            "trading_fee": fee_amount,
            "protocol_fee": protocol_fee,
        }

    def swap_other_for_xai(self, other_amount: float, max_slippage_pct: float = 5.0) -> Dict:
        """
        Swap other token for XAI
        """

        if other_amount <= 0:
            return {"success": False, "error": "Invalid amount"}

        if self.xai_reserve == 0 or self.other_reserve == 0:
            return {"success": False, "error": "Pool has no liquidity"}

        # Apply trading fee
        other_after_fee = other_amount * (1 - self.fee_percentage - self.protocol_fee_percentage)

        # Calculate output
        k = self.xai_reserve * self.other_reserve
        new_other_reserve = self.other_reserve + other_after_fee
        new_xai_reserve = k / new_other_reserve

        xai_output = self.xai_reserve - new_xai_reserve

        # Calculate price impact
        price_before = self.other_reserve / self.xai_reserve
        price_after = new_other_reserve / new_xai_reserve
        price_impact = abs(price_after - price_before) / price_before * 100

        if price_impact > max_slippage_pct:
            return {
                "success": False,
                "error": "Slippage too high",
                "price_impact_percent": price_impact,
                "max_slippage_pct": max_slippage_pct,
            }

        # Collect fees
        fee_amount = other_amount * self.fee_percentage
        protocol_fee = other_amount * self.protocol_fee_percentage

        # Update reserves
        self.xai_reserve = new_xai_reserve
        self.other_reserve = new_other_reserve

        # Update stats
        self.total_volume += xai_output
        self.total_fees_collected += fee_amount
        self.swap_count += 1

        self.protocol_fee_balance += protocol_fee

        self._log_event(
            "swap",
            {
                "input_other": other_amount,
                "output_xai": xai_output,
                "protocol_fee": protocol_fee,
                "price_impact": price_impact,
            },
        )

        return {
            "success": True,
            "input_other": other_amount,
            "output_xai": xai_output,
            "effective_price": other_amount / xai_output,
            "price_impact_percent": price_impact,
            "trading_fee": fee_amount,
            "protocol_fee": protocol_fee,
        }

    def get_quote(self, input_amount: float, input_is_xai: bool) -> Dict:
        """
        Get quote for swap without executing
        """

        if self.xai_reserve == 0 or self.other_reserve == 0:
            return {"success": False, "error": "Pool has no liquidity"}

        if input_is_xai:
            input_after_fee = input_amount * (
                1 - self.fee_percentage - self.protocol_fee_percentage
            )
            k = self.xai_reserve * self.other_reserve
            new_xai_reserve = self.xai_reserve + input_after_fee
            new_other_reserve = k / new_xai_reserve
            output_amount = self.other_reserve - new_other_reserve
        else:
            input_after_fee = input_amount * (
                1 - self.fee_percentage - self.protocol_fee_percentage
            )
            k = self.xai_reserve * self.other_reserve
            new_other_reserve = self.other_reserve + input_after_fee
            new_xai_reserve = k / new_other_reserve
            output_amount = self.xai_reserve - new_xai_reserve

        return {
            "success": True,
            "input_amount": input_amount,
            "estimated_output": output_amount,
            "rate": output_amount / input_amount if input_amount > 0 else 0,
            "fee_amount": input_amount * self.fee_percentage,
        }

    def get_stats(self) -> Dict:
        """Get pool statistics"""

        return {
            "pair": self.pair.value,
            "xai_reserve": self.xai_reserve,
            "other_reserve": self.other_reserve,
            "total_liquidity_tokens": self.total_liquidity_tokens,
            "liquidity_providers_count": len(self.liquidity_providers),
            "current_price": self.other_reserve / self.xai_reserve if self.xai_reserve > 0 else 0,
            "total_volume": self.total_volume,
            "total_fees_collected": self.total_fees_collected,
            "swap_count": self.swap_count,
            "tvl_xai": self.xai_reserve,
            "tvl_other": self.other_reserve,
        }

    def withdraw_protocol_fees(self, destination: str, amount: float | None = None) -> Dict:
        amount = amount or self.protocol_fee_balance
        if amount <= 0 or amount > self.protocol_fee_balance:
            return {"success": False, "error": "Invalid amount"}

        self.protocol_fee_balance -= amount
        self._log_event("protocol_fee_withdrawal", {"destination": destination, "amount": amount})

        return {
            "success": True,
            "withdrawn": amount,
            "remaining_balance": self.protocol_fee_balance,
            "destination": destination,
        }

    def _log_event(self, event_type: str, payload: Dict):
        entry = {"event": event_type, "payload": payload, "timestamp": time.time()}
        signature = self.audit_signer.sign(json.dumps(entry, sort_keys=True))
        entry["signature"] = signature
        self.event_log.append(entry)

        log_dir = os.path.join(Config.DATA_DIR, "liquidity_events")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, f"{self.pair.value.replace('/', '_')}_events.log")
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

class PoolManager:
    """Manages all liquidity pools"""

    def __init__(self):
        self.pools = {}

        # Create pools for all pairs
        for pair in PoolPair:
            self.pools[pair.value] = LiquidityPool(pair)

    def get_pool(self, pair: str) -> LiquidityPool | None:
        """Get specific pool"""
        return self.pools.get(pair)

    def get_all_pools_stats(self) -> list[Dict]:
        """Get stats for all pools"""

        stats = []
        for pool in self.pools.values():
            pool_stats = pool.get_stats()
            if pool_stats["xai_reserve"] > 0:  # Only show pools with liquidity
                stats.append(pool_stats)

        # Sort by TVL
        stats.sort(key=lambda x: x["tvl_xai"], reverse=True)
        return stats

    def find_best_price(self, xai_amount: float, target_coin: str) -> Dict:
        """
        Find pool with best price for swap

        Useful when multiple paths exist
        """

        best_pool = None
        best_output = 0

        for pair_name, pool in self.pools.items():
            if target_coin in pair_name:
                quote = pool.get_quote(xai_amount, input_is_xai=True)
                if quote["success"] and quote["estimated_output"] > best_output:
                    best_output = quote["estimated_output"]
                    best_pool = pair_name

        return {"best_pool": best_pool, "estimated_output": best_output, "xai_input": xai_amount}

# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI LIQUIDITY POOLS")
    print("=" * 70)

    # Create pool manager
    manager = PoolManager()

    # Get XAI/BTC pool
    btc_pool = manager.get_pool("XAI/BTC")

    print("\nAdding liquidity to XAI/BTC pool...")
    print("(Free market pricing - all 11 pairs active)")

    # First provider (Example: 1 BTC = $45,000, XAI = $0.20, ratio = 0.2/45000 = 0.0000044)
    result1 = btc_pool.add_liquidity("provider_1", 10000, 0.044)
    print(f"\nProvider 1:")
    print(f"  Deposited: {result1['xai_deposited']} XAI + {result1['other_deposited']} BTC")
    print(f"  LP Tokens: {result1['lp_tokens']:.2f}")
    print(f"  Pool Share: {result1['pool_share_percentage']:.2f}%")
    print(f"  Initial XAI/BTC Rate: {result1['initial_price']:.8f}")

    # Second provider
    result2 = btc_pool.add_liquidity("provider_2", 5000, 0.022)
    print(f"\nProvider 2:")
    print(f"  Deposited: {result2['xai_deposited']:.2f} XAI + {result2['other_deposited']:.6f} BTC")
    print(f"  LP Tokens: {result2['lp_tokens']:.2f}")
    print(f"  Pool Share: {result2['pool_share_percentage']:.2f}%")

    # Test swap
    print("\n" + "=" * 70)
    print("SWAP TEST")
    print("=" * 70)

    print(f"\nBefore swap:")
    print(f"  XAI Reserve: {btc_pool.xai_reserve:.2f}")
    print(f"  BTC Reserve: {btc_pool.other_reserve:.6f}")
    print(f"  XAI/BTC Rate: {btc_pool.other_reserve / btc_pool.xai_reserve:.8f}")

    # Swap 1000 XAI for BTC
    swap_result = btc_pool.swap_xai_for_other(1000)
    print(f"\nSwap 1000 XAI:")
    print(f"  Received: {swap_result['output_other']:.6f} BTC")
    print(f"  Effective XAI/BTC: {swap_result['effective_price']:.8f}")
    print(f"  Price Impact: {swap_result['price_impact_percent']:.2f}%")
    print(f"  Trading Fee: {swap_result['trading_fee']:.2f} XAI")

    # Pool stats
    print("\n" + "=" * 70)
    print("POOL STATISTICS")
    print("=" * 70)

    all_stats = manager.get_all_pools_stats()
    for stats in all_stats:
        print(f"\n{stats['pair']}:")
        print(f"  XAI Reserve: {stats['xai_reserve']:.2f}")
        print(f"  Other Reserve: {stats['other_reserve']:.6f}")
        print(f"  Exchange Rate: {stats['current_price']:.8f}")
        print(f"  Total Volume: {stats['total_volume']:.2f} XAI")
        print(f"  Fees Collected: {stats['total_fees_collected']:.2f}")
        print(f"  LPs: {stats['liquidity_providers_count']}")

    print("\n" + "=" * 70)

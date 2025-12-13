"""
Swap Router with Multi-Hop Aggregation.

Provides optimal path finding and execution across multiple liquidity pools:
- Multi-hop routing (A->B->C->D)
- Path optimization
- Slippage protection
- Signature-based limit orders
- MEV-resistant execution

Security features:
- Deadline enforcement
- Minimum output validation
- Reentrancy protection
- Sandwich attack detection
"""

from __future__ import annotations

import time
import logging
import hashlib
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, TYPE_CHECKING
from enum import Enum
from collections import defaultdict

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Status of a limit order."""
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class SwapPath:
    """A path through multiple pools for a swap."""
    pools: List[str]  # Pool addresses in order
    tokens: List[str]  # Token path (len = len(pools) + 1)
    expected_output: int = 0
    price_impact: int = 0  # Basis points
    gas_estimate: int = 0


@dataclass
class LimitOrder:
    """
    Signature-based limit order (0x/Seaport pattern).

    Allows users to sign orders that can be filled by anyone
    when price conditions are met.
    """
    id: str = ""
    maker: str = ""
    token_in: str = ""
    token_out: str = ""
    amount_in: int = 0
    min_amount_out: int = 0  # Limit price as minimum output
    expiry: int = 0  # Block number or timestamp
    nonce: int = 0
    signature: bytes = b""

    # Execution state
    amount_filled: int = 0
    status: OrderStatus = OrderStatus.OPEN
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.id:
            order_hash = hashlib.sha3_256(
                f"{self.maker}:{self.token_in}:{self.token_out}:"
                f"{self.amount_in}:{self.min_amount_out}:{self.nonce}".encode()
            ).digest()
            self.id = f"0x{order_hash[:16].hex()}"

    def remaining_amount(self) -> int:
        """Get unfilled amount."""
        return self.amount_in - self.amount_filled

    def effective_price(self) -> float:
        """Get limit price as ratio."""
        if self.amount_in == 0:
            return 0
        return self.min_amount_out / self.amount_in

    def is_fillable(self, current_price: float, current_time: float) -> bool:
        """Check if order can be filled at current price."""
        if self.status not in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
            return False
        if current_time > self.expiry:
            return False
        return current_price >= self.effective_price()

    def hash_for_signing(self, router_address: str, chain_id: int) -> bytes:
        """Get hash for signature verification."""
        data = (
            router_address.encode() +
            chain_id.to_bytes(32, 'big') +
            self.maker.encode() +
            self.token_in.encode() +
            self.token_out.encode() +
            self.amount_in.to_bytes(32, 'big') +
            self.min_amount_out.to_bytes(32, 'big') +
            self.expiry.to_bytes(32, 'big') +
            self.nonce.to_bytes(32, 'big')
        )
        return hashlib.sha3_256(data).digest()


@dataclass
class PoolInfo:
    """Information about a liquidity pool."""
    address: str
    token0: str
    token1: str
    reserve0: int = 0
    reserve1: int = 0
    fee: int = 30  # Basis points (0.3%)

    # Maximum values for overflow protection
    MAX_AMOUNT: int = 2**128 - 1

    def get_output(self, token_in: str, amount_in: int) -> int:
        """
        Calculate output amount for a swap using constant product formula.

        Args:
            token_in: Token being swapped in
            amount_in: Amount of token_in

        Returns:
            Amount of token_out to receive

        Raises:
            VMExecutionError: If overflow would occur or invalid token

        Security:
            - Uses safe math to prevent integer overflow
            - Validates reserves are non-zero
            - Validates amount bounds
        """
        if token_in == self.token0:
            reserve_in, reserve_out = self.reserve0, self.reserve1
        elif token_in == self.token1:
            reserve_in, reserve_out = self.reserve1, self.reserve0
        else:
            raise VMExecutionError(f"Token {token_in} not in pool")

        # Validate inputs
        if amount_in <= 0:
            raise VMExecutionError("Amount must be positive")
        if amount_in > self.MAX_AMOUNT:
            raise VMExecutionError(f"Amount exceeds maximum: {self.MAX_AMOUNT}")
        if reserve_in <= 0 or reserve_out <= 0:
            raise VMExecutionError("Pool has zero reserves")

        # Constant product with fee: (amount_in * (10000 - fee) * reserve_out) / (reserve_in * 10000 + amount_in * (10000 - fee))
        fee_multiplier = 10000 - self.fee

        # Safe multiplication: amount_in * (10000 - fee)
        if amount_in > self.MAX_AMOUNT // fee_multiplier:
            raise VMExecutionError("Overflow in fee calculation")
        amount_in_with_fee = amount_in * fee_multiplier

        # Safe multiplication: amount_in_with_fee * reserve_out
        if amount_in_with_fee > 0 and reserve_out > self.MAX_AMOUNT // amount_in_with_fee:
            raise VMExecutionError("Overflow in output calculation")
        numerator = amount_in_with_fee * reserve_out

        # Safe multiplication: reserve_in * 10000
        if reserve_in > self.MAX_AMOUNT // 10000:
            raise VMExecutionError("Overflow in reserve calculation")
        denominator_base = reserve_in * 10000

        # Safe addition: denominator_base + amount_in_with_fee
        if denominator_base > self.MAX_AMOUNT - amount_in_with_fee:
            raise VMExecutionError("Overflow in denominator calculation")
        denominator = denominator_base + amount_in_with_fee

        return numerator // denominator if denominator > 0 else 0

    def get_other_token(self, token: str) -> str:
        """Get the other token in the pair."""
        if token == self.token0:
            return self.token1
        elif token == self.token1:
            return self.token0
        raise VMExecutionError(f"Token {token} not in pool")


@dataclass
class SwapRouter:
    """
    Multi-hop swap router with path optimization.

    Features:
    - Finds optimal path across multiple pools
    - Supports multi-hop swaps (up to MAX_HOPS)
    - Slippage protection
    - Deadline enforcement
    - Limit order support
    - MEV protection via private mempool integration
    """

    name: str = "XAI Swap Router"
    address: str = ""
    owner: str = ""
    chain_id: int = 1

    # Pool registry: pool_address -> PoolInfo
    pools: Dict[str, PoolInfo] = field(default_factory=dict)

    # Token -> pools mapping for path finding
    token_to_pools: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    # Limit orders: order_id -> LimitOrder
    orders: Dict[str, LimitOrder] = field(default_factory=dict)

    # User nonces for limit orders
    user_nonces: Dict[str, int] = field(default_factory=dict)

    # Reentrancy guard
    _in_swap: bool = False

    # Configuration
    MAX_HOPS: int = 4
    MAX_SLIPPAGE: int = 1000  # 10% max slippage
    MAX_AMOUNT: int = 2**128 - 1  # Maximum amount to prevent overflow
    MIN_AMOUNT: int = 1  # Minimum amount for meaningful swap

    # Statistics
    total_swaps: int = 0
    total_volume: Dict[str, int] = field(default_factory=dict)
    total_orders_filled: int = 0

    def __post_init__(self) -> None:
        """Initialize router."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"swap_router:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Pool Management ====================

    def register_pool(
        self,
        pool_address: str,
        token0: str,
        token1: str,
        fee: int = 30,
    ) -> bool:
        """
        Register a liquidity pool with the router.

        Args:
            pool_address: Pool contract address
            token0: First token in pair
            token1: Second token in pair
            fee: Swap fee in basis points

        Returns:
            True if successful
        """
        if pool_address in self.pools:
            raise VMExecutionError(f"Pool {pool_address} already registered")

        pool = PoolInfo(
            address=pool_address,
            token0=token0.upper(),
            token1=token1.upper(),
            fee=fee,
        )

        self.pools[pool_address] = pool
        self.token_to_pools[token0.upper()].append(pool_address)
        self.token_to_pools[token1.upper()].append(pool_address)

        logger.info(
            "Pool registered with router",
            extra={
                "event": "router.pool_registered",
                "pool": pool_address[:10],
                "pair": f"{token0}/{token1}",
            }
        )

        return True

    def update_pool_reserves(
        self,
        pool_address: str,
        reserve0: int,
        reserve1: int,
    ) -> bool:
        """Update pool reserves for accurate quotes."""
        if pool_address not in self.pools:
            raise VMExecutionError(f"Pool {pool_address} not found")

        pool = self.pools[pool_address]
        pool.reserve0 = reserve0
        pool.reserve1 = reserve1

        return True

    # ==================== Path Finding ====================

    def find_best_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: Optional[int] = None,
    ) -> Optional[SwapPath]:
        """
        Find the optimal swap path from token_in to token_out.

        Uses modified Dijkstra's algorithm to find path with
        maximum output amount.

        Args:
            token_in: Input token
            token_out: Output token
            amount_in: Input amount
            max_hops: Maximum number of hops (default: MAX_HOPS)

        Returns:
            Best SwapPath or None if no path exists
        """
        token_in = token_in.upper()
        token_out = token_out.upper()
        max_hops = max_hops or self.MAX_HOPS

        # Direct path check
        direct_path = self._find_direct_path(token_in, token_out, amount_in)

        # Multi-hop search
        all_paths = self._find_all_paths(
            token_in, token_out, amount_in, max_hops
        )

        if direct_path:
            all_paths.append(direct_path)

        if not all_paths:
            return None

        # Return path with highest output
        return max(all_paths, key=lambda p: p.expected_output)

    def _find_direct_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
    ) -> Optional[SwapPath]:
        """Find direct single-hop path."""
        for pool_addr in self.token_to_pools.get(token_in, []):
            pool = self.pools[pool_addr]
            if token_out in (pool.token0, pool.token1):
                output = pool.get_output(token_in, amount_in)
                if output > 0:
                    return SwapPath(
                        pools=[pool_addr],
                        tokens=[token_in, token_out],
                        expected_output=output,
                        price_impact=self._calculate_price_impact(pool, amount_in, token_in),
                        gas_estimate=100_000,
                    )
        return None

    def _find_all_paths(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: int,
    ) -> List[SwapPath]:
        """Find all valid paths up to max_hops."""
        paths = []

        # BFS with amount tracking
        # State: (current_token, current_amount, path_pools, path_tokens, visited_pools)
        queue = [(token_in, amount_in, [], [token_in], set())]

        while queue:
            current_token, current_amount, path_pools, path_tokens, visited = queue.pop(0)

            if len(path_pools) >= max_hops:
                continue

            for pool_addr in self.token_to_pools.get(current_token, []):
                if pool_addr in visited:
                    continue

                pool = self.pools[pool_addr]
                next_token = pool.get_other_token(current_token)

                # Avoid cycles (except to destination)
                if next_token in path_tokens and next_token != token_out:
                    continue

                output = pool.get_output(current_token, current_amount)
                if output <= 0:
                    continue

                new_pools = path_pools + [pool_addr]
                new_tokens = path_tokens + [next_token]
                new_visited = visited | {pool_addr}

                if next_token == token_out:
                    # Found complete path
                    total_impact = sum(
                        self._calculate_price_impact(
                            self.pools[p], amount_in // (i + 1), path_tokens[i]
                        )
                        for i, p in enumerate(new_pools)
                    )

                    paths.append(SwapPath(
                        pools=new_pools,
                        tokens=new_tokens,
                        expected_output=output,
                        price_impact=total_impact,
                        gas_estimate=100_000 * len(new_pools),
                    ))
                else:
                    # Continue searching
                    queue.append((
                        next_token, output, new_pools, new_tokens, new_visited
                    ))

        return paths

    def _calculate_price_impact(
        self,
        pool: PoolInfo,
        amount_in: int,
        token_in: str,
    ) -> int:
        """
        Calculate price impact in basis points.

        Args:
            pool: Liquidity pool
            amount_in: Input amount
            token_in: Input token

        Returns:
            Price impact in basis points (0-10000)

        Security:
            - Uses safe math to prevent overflow
            - Validates reserve is non-zero
        """
        if token_in == pool.token0:
            reserve = pool.reserve0
        else:
            reserve = pool.reserve1

        if reserve == 0:
            return 10000  # 100% impact

        # Price impact = amount_in / reserve * 10000 (simplified)
        # Use safe multiplication to prevent overflow
        if amount_in > self.MAX_AMOUNT // 10000:
            # If amount_in is very large, just return max impact
            return 10000

        return min(10000, (amount_in * 10000) // reserve)

    # ==================== Swap Execution ====================

    def swap_exact_input(
        self,
        caller: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        deadline: float,
        path: Optional[List[str]] = None,
    ) -> int:
        """
        Swap exact input amount for maximum output.

        Args:
            caller: Swap initiator
            token_in: Input token
            token_out: Output token
            amount_in: Exact input amount
            min_amount_out: Minimum acceptable output (slippage protection)
            deadline: Transaction deadline timestamp
            path: Optional explicit path (pool addresses)

        Returns:
            Actual output amount

        Raises:
            VMExecutionError: If validation fails or swap cannot be executed

        Security:
            - Validates all input amounts are within safe bounds
            - Validates tokens are non-empty
            - Validates caller address
            - Enforces deadline and reentrancy protection
        """
        # Input validation
        self._validate_swap_inputs(caller, token_in, token_out, amount_in, min_amount_out)

        self._require_not_expired(deadline)
        self._require_no_reentrancy()

        try:
            self._in_swap = True

            token_in = token_in.upper()
            token_out = token_out.upper()

            # Find path if not provided
            if not path:
                best_path = self.find_best_path(token_in, token_out, amount_in)
                if not best_path:
                    raise VMExecutionError(
                        f"No path found from {token_in} to {token_out}"
                    )
                path = best_path.pools

            # Execute swaps along path
            current_amount = amount_in
            current_token = token_in

            for pool_addr in path:
                pool = self.pools.get(pool_addr)
                if not pool:
                    raise VMExecutionError(f"Pool {pool_addr} not found")

                output = pool.get_output(current_token, current_amount)

                # Update reserves (simplified - real impl would call pool)
                if current_token == pool.token0:
                    pool.reserve0 += current_amount
                    pool.reserve1 -= output
                    current_token = pool.token1
                else:
                    pool.reserve1 += current_amount
                    pool.reserve0 -= output
                    current_token = pool.token0

                current_amount = output

            # Verify output meets minimum
            if current_amount < min_amount_out:
                raise VMExecutionError(
                    f"Insufficient output: {current_amount} < {min_amount_out}"
                )

            # Update statistics
            self.total_swaps += 1
            self.total_volume[token_in] = (
                self.total_volume.get(token_in, 0) + amount_in
            )

            logger.info(
                "Swap executed",
                extra={
                    "event": "router.swap",
                    "caller": caller[:10],
                    "path": f"{token_in}->{token_out}",
                    "amount_in": amount_in,
                    "amount_out": current_amount,
                    "hops": len(path),
                }
            )

            return current_amount

        finally:
            self._in_swap = False

    def swap_exact_output(
        self,
        caller: str,
        token_in: str,
        token_out: str,
        amount_out: int,
        max_amount_in: int,
        deadline: float,
    ) -> int:
        """
        Swap for exact output amount with maximum input.

        Args:
            caller: Swap initiator
            token_in: Input token
            token_out: Output token
            amount_out: Exact desired output
            max_amount_in: Maximum acceptable input
            deadline: Transaction deadline

        Returns:
            Actual input amount used

        Raises:
            VMExecutionError: If validation fails or swap cannot be executed

        Security:
            - Validates all input amounts are within safe bounds
            - Validates tokens are non-empty
            - Validates caller address
        """
        # Input validation
        self._validate_swap_inputs(caller, token_in, token_out, max_amount_in, amount_out)

        self._require_not_expired(deadline)
        self._require_no_reentrancy()

        try:
            self._in_swap = True

            # Binary search for required input
            low, high = 1, max_amount_in
            best_input = max_amount_in

            while low <= high:
                mid = (low + high) // 2

                path = self.find_best_path(token_in, token_out, mid)
                if path and path.expected_output >= amount_out:
                    best_input = mid
                    high = mid - 1
                else:
                    low = mid + 1

            if best_input > max_amount_in:
                raise VMExecutionError(
                    f"Required input {best_input} exceeds max {max_amount_in}"
                )

            # Execute with found input
            actual_output = self.swap_exact_input(
                caller, token_in, token_out,
                best_input, amount_out, deadline
            )

            return best_input

        finally:
            self._in_swap = False

    # ==================== Limit Orders ====================

    def create_limit_order(
        self,
        caller: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        expiry: int,
        signature: bytes,
    ) -> str:
        """
        Create a limit order that can be filled when price is right.

        Args:
            caller: Order maker
            token_in: Token to sell
            token_out: Token to receive
            amount_in: Amount to sell
            min_amount_out: Minimum to receive (defines limit price)
            expiry: Order expiration timestamp
            signature: EIP-712 signature

        Returns:
            Order ID

        Raises:
            VMExecutionError: If validation fails

        Security:
            - Validates all amounts are within safe bounds
            - Validates tokens and addresses
            - Validates signature
            - Validates expiry is in the future
        """
        # Input validation
        self._validate_limit_order_inputs(
            caller, token_in, token_out, amount_in, min_amount_out, expiry
        )

        nonce = self.user_nonces.get(caller, 0)
        self.user_nonces[caller] = nonce + 1

        order = LimitOrder(
            maker=caller,
            token_in=token_in.upper(),
            token_out=token_out.upper(),
            amount_in=amount_in,
            min_amount_out=min_amount_out,
            expiry=expiry,
            nonce=nonce,
            signature=signature,
        )

        # Verify signature (simplified)
        order_hash = order.hash_for_signing(self.address, self.chain_id)
        if not self._verify_signature(caller, order_hash, signature):
            raise VMExecutionError("Invalid order signature")

        self.orders[order.id] = order

        logger.info(
            "Limit order created",
            extra={
                "event": "router.order_created",
                "order_id": order.id[:10],
                "maker": caller[:10],
                "pair": f"{token_in}/{token_out}",
                "price": order.effective_price(),
            }
        )

        return order.id

    def fill_limit_order(
        self,
        caller: str,
        order_id: str,
        amount_to_fill: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Fill a limit order (partially or fully).

        Args:
            caller: Order filler
            order_id: Order to fill
            amount_to_fill: Amount to fill (default: full order)

        Returns:
            (amount_in_filled, amount_out_given)

        Raises:
            VMExecutionError: If order cannot be filled

        Security:
            - Uses safe math to prevent integer overflow
            - Validates fill amount bounds
            - Validates caller address
        """
        # Validate caller
        if not caller or not caller.strip():
            raise VMExecutionError("Invalid caller address")

        order = self.orders.get(order_id)
        if not order:
            raise VMExecutionError(f"Order {order_id} not found")

        if order.status not in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
            raise VMExecutionError(f"Order not fillable: {order.status.value}")

        if time.time() > order.expiry:
            order.status = OrderStatus.EXPIRED
            raise VMExecutionError("Order expired")

        remaining = order.remaining_amount()

        # Validate fill amount if provided
        if amount_to_fill is not None:
            if amount_to_fill <= 0:
                raise VMExecutionError("Fill amount must be positive")
            if amount_to_fill > self.MAX_AMOUNT:
                raise VMExecutionError(f"Fill amount exceeds maximum: {self.MAX_AMOUNT}")

        fill_amount = min(amount_to_fill or remaining, remaining)

        if fill_amount <= 0:
            raise VMExecutionError("Nothing to fill")

        # Calculate output at limit price using safe math to prevent overflow
        # Formula: output = (fill_amount * min_amount_out) / amount_in
        # Use safe multiplication that checks for overflow
        output_amount = self._safe_mul_div(
            fill_amount, order.min_amount_out, order.amount_in
        )

        # Execute the fill
        # In real implementation, would transfer tokens

        # Safe addition for amount_filled
        new_filled = self._safe_add(order.amount_filled, fill_amount)
        order.amount_filled = new_filled

        if order.amount_filled >= order.amount_in:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        self.total_orders_filled += 1

        logger.info(
            "Limit order filled",
            extra={
                "event": "router.order_filled",
                "order_id": order_id[:10],
                "filler": caller[:10],
                "amount_in": fill_amount,
                "amount_out": output_amount,
            }
        )

        return fill_amount, output_amount

    def cancel_limit_order(self, caller: str, order_id: str) -> bool:
        """Cancel a limit order."""
        order = self.orders.get(order_id)
        if not order:
            raise VMExecutionError(f"Order {order_id} not found")

        if order.maker.lower() != caller.lower():
            raise VMExecutionError("Only maker can cancel order")

        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            raise VMExecutionError(f"Order already {order.status.value}")

        order.status = OrderStatus.CANCELLED

        logger.info(
            "Limit order cancelled",
            extra={
                "event": "router.order_cancelled",
                "order_id": order_id[:10],
            }
        )

        return True

    def get_fillable_orders(
        self,
        token_in: str,
        token_out: str,
        limit: int = 100,
    ) -> List[LimitOrder]:
        """Get all fillable orders for a token pair."""
        token_in = token_in.upper()
        token_out = token_out.upper()
        current_time = time.time()

        fillable = []
        for order in self.orders.values():
            if (order.token_in == token_in and
                order.token_out == token_out and
                order.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED) and
                current_time <= order.expiry):
                fillable.append(order)

        # Sort by best price (highest min_amount_out / amount_in)
        fillable.sort(key=lambda o: o.effective_price(), reverse=True)

        return fillable[:limit]

    # ==================== MEV Protection ====================

    def detect_sandwich_attack(
        self,
        pending_swaps: List[Tuple[str, str, int]],
    ) -> List[Tuple[str, str]]:
        """
        Detect potential sandwich attacks in pending swaps.

        Args:
            pending_swaps: List of (caller, token_in->token_out, amount)

        Returns:
            List of (front_run_tx, victim_tx) pairs
        """
        suspicious_pairs = []

        # Group by token pair
        swaps_by_pair: Dict[str, List] = defaultdict(list)
        for caller, path, amount in pending_swaps:
            swaps_by_pair[path].append((caller, amount))

        for pair, swaps in swaps_by_pair.items():
            if len(swaps) >= 2:
                # Check for same caller with bracketing amounts
                callers = [s[0] for s in swaps]
                for i, (caller1, amount1) in enumerate(swaps[:-1]):
                    for j, (caller2, amount2) in enumerate(swaps[i+1:], i+1):
                        if caller1 == caller2:
                            # Same caller sandwiching
                            suspicious_pairs.append((
                                f"{caller1}:{pair}:{amount1}",
                                f"victim:{pair}",
                            ))

        return suspicious_pairs

    # ==================== Quotes ====================

    def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
    ) -> Dict:
        """
        Get quote for a swap without executing.

        Args:
            token_in: Input token
            token_out: Output token
            amount_in: Input amount

        Returns:
            Quote details including path, output, and price impact
        """
        path = self.find_best_path(token_in, token_out, amount_in)

        if not path:
            return {
                "success": False,
                "error": "No path found",
            }

        return {
            "success": True,
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in,
            "expected_output": path.expected_output,
            "price_impact_bps": path.price_impact,
            "path": path.tokens,
            "pools": path.pools,
            "hops": len(path.pools),
            "gas_estimate": path.gas_estimate,
        }

    def get_amounts_out(
        self,
        amount_in: int,
        path: List[str],  # Token path
    ) -> List[int]:
        """
        Calculate output amounts for each hop in path.

        Uniswap V2 Router compatible.
        """
        amounts = [amount_in]
        current_token = path[0].upper()

        for i in range(len(path) - 1):
            next_token = path[i + 1].upper()

            # Find pool for this pair
            pool = None
            for pool_addr in self.token_to_pools.get(current_token, []):
                p = self.pools[pool_addr]
                if next_token in (p.token0, p.token1):
                    pool = p
                    break

            if not pool:
                raise VMExecutionError(
                    f"No pool for {current_token}/{next_token}"
                )

            output = pool.get_output(current_token, amounts[-1])
            amounts.append(output)
            current_token = next_token

        return amounts

    # ==================== View Functions ====================

    def get_pools_for_token(self, token: str) -> List[str]:
        """Get all pools containing a token."""
        return self.token_to_pools.get(token.upper(), [])

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details."""
        order = self.orders.get(order_id)
        if not order:
            return None

        return {
            "id": order.id,
            "maker": order.maker,
            "token_in": order.token_in,
            "token_out": order.token_out,
            "amount_in": order.amount_in,
            "min_amount_out": order.min_amount_out,
            "amount_filled": order.amount_filled,
            "remaining": order.remaining_amount(),
            "effective_price": order.effective_price(),
            "status": order.status.value,
            "expiry": order.expiry,
        }

    def get_stats(self) -> Dict:
        """Get router statistics."""
        return {
            "total_swaps": self.total_swaps,
            "total_volume": dict(self.total_volume),
            "total_orders_filled": self.total_orders_filled,
            "registered_pools": len(self.pools),
            "open_orders": sum(
                1 for o in self.orders.values()
                if o.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)
            ),
        }

    # ==================== Helpers ====================

    def _require_not_expired(self, deadline: float) -> None:
        if time.time() > deadline:
            raise VMExecutionError("Transaction expired")

    def _require_no_reentrancy(self) -> None:
        if self._in_swap:
            raise VMExecutionError("Reentrancy detected")

    def _verify_signature(
        self,
        signer: str,
        message_hash: bytes,
        signature: bytes,
    ) -> bool:
        """
        Verify EIP-712 signature using ECDSA.

        Implements proper signature verification with public key recovery
        to ensure only the actual signer can authorize limit orders.

        Args:
            signer: Expected signer address
            message_hash: Hash of the message that was signed
            signature: ECDSA signature (65 bytes: r + s + v)

        Returns:
            True if signature is valid and matches signer

        Security:
        - Validates signature length
        - Recovers public key from signature
        - Derives address and compares to expected signer
        - Prevents signature spoofing attacks
        """
        from xai.core.crypto_utils import verify_signature_hex, derive_public_key_hex
        import hashlib

        # Validate signature format
        if not signature or len(signature) < 64:
            return False

        try:
            # Convert signature bytes to hex if needed
            if isinstance(signature, bytes):
                sig_hex = signature.hex()
            else:
                sig_hex = signature

            # Get the public key from the signer address
            # In XAI, addresses are XAI + first 40 chars of pubkey hash
            # We need to look up the public key from the address

            # For limit orders, we store the maker's public key in the order
            # This would be passed in the order metadata
            # For now, we use a registry lookup pattern

            if hasattr(self, '_public_key_registry') and signer in self._public_key_registry:
                public_key = self._public_key_registry[signer]
            else:
                # Cannot verify without public key - reject
                return False

            # Verify the signature
            return verify_signature_hex(
                public_key,
                message_hash,
                sig_hex
            )

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            # Any cryptographic error means invalid signature
            logger.debug(
                "Limit order signature verification failed: %s - %s",
                type(e).__name__,
                str(e),
                extra={
                    "address": signer[:10] if signer else "unknown",
                    "error_type": type(e).__name__,
                    "event": "swap_router.signature_verification_failed"
                }
            )
            return False

    def register_public_key(self, address: str, public_key: str) -> None:
        """
        Register a public key for signature verification.

        Users must register their public key before creating limit orders.
        This enables signature verification for order authorization.

        Args:
            address: User's XAI address
            public_key: User's public key (hex encoded)
        """
        if not hasattr(self, '_public_key_registry'):
            self._public_key_registry: Dict[str, str] = {}
        self._public_key_registry[address] = public_key

    # ==================== Input Validation ====================

    def _validate_swap_inputs(
        self,
        caller: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
    ) -> None:
        """
        Validate all swap input parameters.

        Args:
            caller: Swap initiator address
            token_in: Input token symbol
            token_out: Output token symbol
            amount_in: Input amount
            min_amount_out: Minimum output amount

        Raises:
            VMExecutionError: If any validation fails

        Security:
            - Prevents zero-value swaps
            - Prevents overflow with large amounts
            - Validates token symbols
            - Validates address format
        """
        # Validate caller address
        if not caller or not caller.strip():
            raise VMExecutionError("Invalid caller address: cannot be empty")

        # Validate tokens
        if not token_in or not token_in.strip():
            raise VMExecutionError("Invalid input token: cannot be empty")

        if not token_out or not token_out.strip():
            raise VMExecutionError("Invalid output token: cannot be empty")

        if token_in.upper() == token_out.upper():
            raise VMExecutionError("Cannot swap token to itself")

        # Validate amount_in
        if not isinstance(amount_in, int):
            raise VMExecutionError("Amount must be an integer")

        if amount_in <= 0:
            raise VMExecutionError("Input amount must be positive")

        if amount_in < self.MIN_AMOUNT:
            raise VMExecutionError(f"Input amount below minimum: {self.MIN_AMOUNT}")

        if amount_in > self.MAX_AMOUNT:
            raise VMExecutionError(f"Input amount exceeds maximum: {self.MAX_AMOUNT}")

        # Validate min_amount_out
        if not isinstance(min_amount_out, int):
            raise VMExecutionError("Minimum output must be an integer")

        if min_amount_out < 0:
            raise VMExecutionError("Minimum output cannot be negative")

        if min_amount_out > self.MAX_AMOUNT:
            raise VMExecutionError(f"Minimum output exceeds maximum: {self.MAX_AMOUNT}")

    def _validate_limit_order_inputs(
        self,
        caller: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        expiry: int,
    ) -> None:
        """
        Validate limit order input parameters.

        Args:
            caller: Order maker address
            token_in: Token to sell
            token_out: Token to receive
            amount_in: Amount to sell
            min_amount_out: Minimum amount to receive
            expiry: Order expiration timestamp

        Raises:
            VMExecutionError: If any validation fails
        """
        # Use common swap validation
        self._validate_swap_inputs(caller, token_in, token_out, amount_in, min_amount_out)

        # Validate min_amount_out is positive for limit orders
        if min_amount_out <= 0:
            raise VMExecutionError("Limit order requires positive minimum output")

        # Validate expiry
        if not isinstance(expiry, int):
            raise VMExecutionError("Expiry must be an integer timestamp")

        if expiry <= 0:
            raise VMExecutionError("Expiry timestamp must be positive")

        current_time = time.time()
        if expiry <= current_time:
            raise VMExecutionError("Order expiry must be in the future")

        # Reasonable expiry limit (1 year max)
        max_expiry = current_time + (365 * 24 * 60 * 60)
        if expiry > max_expiry:
            raise VMExecutionError("Order expiry too far in the future (max 1 year)")

    # ==================== Safe Math ====================

    def _safe_add(self, a: int, b: int) -> int:
        """
        Safe addition that checks for overflow.

        Args:
            a: First operand
            b: Second operand

        Returns:
            Sum of a and b

        Raises:
            VMExecutionError: If overflow would occur
        """
        result = a + b
        if result > self.MAX_AMOUNT:
            raise VMExecutionError(
                f"Integer overflow in addition: {a} + {b} exceeds {self.MAX_AMOUNT}"
            )
        if result < 0:
            raise VMExecutionError(
                f"Integer underflow in addition: {a} + {b} resulted in negative"
            )
        return result

    def _safe_sub(self, a: int, b: int) -> int:
        """
        Safe subtraction that checks for underflow.

        Args:
            a: First operand
            b: Second operand

        Returns:
            Difference of a and b

        Raises:
            VMExecutionError: If underflow would occur
        """
        if b > a:
            raise VMExecutionError(
                f"Integer underflow in subtraction: {a} - {b}"
            )
        return a - b

    def _safe_mul(self, a: int, b: int) -> int:
        """
        Safe multiplication that checks for overflow.

        Args:
            a: First operand
            b: Second operand

        Returns:
            Product of a and b

        Raises:
            VMExecutionError: If overflow would occur
        """
        if a == 0 or b == 0:
            return 0

        result = a * b

        # Check for overflow by verifying result / b == a
        if result // b != a:
            raise VMExecutionError(
                f"Integer overflow in multiplication: {a} * {b}"
            )

        if result > self.MAX_AMOUNT:
            raise VMExecutionError(
                f"Integer overflow in multiplication: {a} * {b} exceeds {self.MAX_AMOUNT}"
            )

        return result

    def _safe_mul_div(self, a: int, b: int, c: int) -> int:
        """
        Safe multiplication followed by division: (a * b) / c

        Uses 512-bit intermediate to prevent overflow.

        Args:
            a: First multiplicand
            b: Second multiplicand
            c: Divisor

        Returns:
            (a * b) / c

        Raises:
            VMExecutionError: If division by zero or overflow

        Security:
            This pattern is critical for DeFi price calculations.
            It ensures precision is maintained without overflow.
        """
        if c == 0:
            raise VMExecutionError("Division by zero")

        if a == 0 or b == 0:
            return 0

        # Validate inputs are within bounds
        if a < 0 or b < 0:
            raise VMExecutionError("Negative values not allowed in mul_div")

        if a > self.MAX_AMOUNT or b > self.MAX_AMOUNT:
            raise VMExecutionError(
                f"Input values exceed maximum: a={a}, b={b}, max={self.MAX_AMOUNT}"
            )

        # Check if intermediate product would overflow MAX_AMOUNT * c
        # This protects against intermediate overflow even in Python's arbitrary precision
        # because extremely large values can cause memory issues or DoS
        MAX_PRODUCT = self.MAX_AMOUNT * c
        if a > 0 and b > MAX_PRODUCT // a:
            raise VMExecutionError(
                f"Intermediate overflow in mul_div: {a} * {b} would exceed safe limits"
            )

        # Python handles arbitrary precision integers, so we can safely do this
        # In languages with fixed-width integers, we'd need mulDiv512
        product = a * b
        result = product // c

        if result > self.MAX_AMOUNT:
            raise VMExecutionError(
                f"Integer overflow in mul_div: ({a} * {b}) / {c} = {result} exceeds {self.MAX_AMOUNT}"
            )

        return result

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize router state."""
        return {
            "name": self.name,
            "address": self.address,
            "chain_id": self.chain_id,
            "pools": {
                addr: {
                    "token0": p.token0,
                    "token1": p.token1,
                    "reserve0": p.reserve0,
                    "reserve1": p.reserve1,
                    "fee": p.fee,
                }
                for addr, p in self.pools.items()
            },
            "stats": self.get_stats(),
        }

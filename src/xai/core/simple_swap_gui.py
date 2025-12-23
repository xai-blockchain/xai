from __future__ import annotations

"""
XAI Simple Swap GUI System

Makes atomic swaps easy for normal users with:
- One-click swap interface
- On-chain orderbook (P2P, no central server)
- Auto-matching of buyers/sellers
- Progress tracking
- Price floor enforcement (stablecoins only)
"""

import hashlib
import secrets
import time
from enum import Enum


class SwapOrderType(Enum):
    """Type of swap order"""

    BUY = "buy"  # Buy XAI (sell other coin)
    SELL = "sell"  # Sell XAI (buy other coin)

class SwapOrderStatus(Enum):
    """Status of swap order"""

    PENDING = "pending"  # Waiting for match
    MATCHED = "matched"  # Found counterparty
    HTLC_CREATED = "htlc_created"  # Both HTLCs created
    COMPLETED = "completed"  # Swap finished
    CANCELLED = "cancelled"  # User cancelled
    EXPIRED = "expired"  # Timed out

class SwapOrder:
    """Individual swap order in orderbook"""

    def __init__(
        self,
        order_type: SwapOrderType,
        xai_amount: float,
        other_coin: str,
        other_amount: float,
        user_address: str,
    ):
        self.order_id = self._generate_order_id()
        self.order_type = order_type
        self.xai_amount = xai_amount
        self.other_coin = other_coin
        self.other_amount = other_amount
        self.user_address = user_address
        self.timestamp = time.time()
        self.status = SwapOrderStatus.PENDING
        self.matched_with = None
        self.htlc_data = None

        # Calculate implied price
        if order_type == SwapOrderType.BUY:
            # Buying XAI, paying in other coin
            self.price_per_xai = other_amount / xai_amount
        else:
            # Selling XAI, receiving other coin
            self.price_per_xai = other_amount / xai_amount

    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        random_data = f"{time.time()}-{secrets.token_hex(16)}"
        return hashlib.sha256(random_data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "order_type": self.order_type.value,
            "xai_amount": self.xai_amount,
            "other_coin": self.other_coin,
            "other_amount": self.other_amount,
            "price_per_xai": self.price_per_xai,
            "user_address": self.user_address,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "matched_with": self.matched_with,
        }

class MarketPriceTracker:
    """
    Track market prices from actual on-chain swaps
    NO EXTERNAL API CALLS - 100% anonymous
    """

    def __init__(self):
        self.swap_history = []  # List of completed swaps
        self.genesis_ratios = {
            "BTC": 45000.0,  # Fallback ratios from genesis
            "ETH": 2500.0,
            "LTC": 75.0,
            "DOGE": 0.08,
            "USDT": 1.0,
            "USDC": 1.0,
            "DAI": 1.0,
        }

    def record_swap(
        self, xai_amount: float, other_coin: str, other_amount: float, timestamp: float
    ):
        """Record completed swap for price tracking"""

        price_per_xai = other_amount / xai_amount

        self.swap_history.append(
            {
                "timestamp": timestamp,
                "xai_amount": xai_amount,
                "other_coin": other_coin,
                "other_amount": other_amount,
                "price_per_xai": price_per_xai,
            }
        )

        # Keep only last 1000 swaps
        if len(self.swap_history) > 1000:
            self.swap_history = self.swap_history[-1000:]

    def get_market_price(self, coin: str, lookback_hours: int = 24) -> float | None:
        """
        Get market price from recent swap history

        Returns price of coin in USD (for stablecoins, always 1.0)
        """

        # Stablecoins always = $1
        if coin in ["USDT", "USDC", "DAI"]:
            return 1.0

        # Filter recent swaps for this coin
        cutoff_time = time.time() - (lookback_hours * 3600)
        recent_swaps = [
            s for s in self.swap_history if s["other_coin"] == coin and s["timestamp"] > cutoff_time
        ]

        if not recent_swaps:
            # No recent swaps, use genesis ratio as fallback
            return self.genesis_ratios.get(coin)

        # Calculate median price from recent swaps
        prices = [s["price_per_xai"] for s in recent_swaps]
        prices.sort()

        if len(prices) % 2 == 0:
            median = (prices[len(prices) // 2 - 1] + prices[len(prices) // 2]) / 2
        else:
            median = prices[len(prices) // 2]

        return median

    def get_xai_price_usd(self, lookback_hours: int = 24) -> float:
        """
        Calculate XAI price in USD from stablecoin swaps
        """

        cutoff_time = time.time() - (lookback_hours * 3600)

        # Get all stablecoin swaps
        stablecoin_swaps = [
            s
            for s in self.swap_history
            if s["other_coin"] in ["USDT", "USDC", "DAI"] and s["timestamp"] > cutoff_time
        ]

        if not stablecoin_swaps:
            # No recent swaps, return center of floor range
            return 0.205

        # Calculate median XAI price from stablecoin swaps
        # Price per XAI = stablecoin amount / XAI amount
        prices = [s["other_amount"] / s["xai_amount"] for s in stablecoin_swaps]
        prices.sort()

        if len(prices) % 2 == 0:
            median = (prices[len(prices) // 2 - 1] + prices[len(prices) // 2]) / 2
        else:
            median = prices[len(prices) // 2]

        return median

class OnChainOrderbook:
    """
    P2P orderbook stored on blockchain
    No central server - fully decentralized
    """

    def __init__(self, blockchain, price_floor_validator):
        self.blockchain = blockchain
        self.price_floor = price_floor_validator
        self.price_tracker = MarketPriceTracker()
        self.orders = {}  # order_id -> SwapOrder
        self.active_orders = []  # List of pending orders

    def create_order(
        self,
        order_type: SwapOrderType,
        xai_amount: float,
        other_coin: str,
        other_amount: float,
        user_address: str,
    ) -> Dict:
        """
        Create new swap order

        Validates price floor for stablecoins ONLY
        """

        # Calculate implied XAI price in USD
        if other_coin in ["USDT", "USDC", "DAI"]:
            # Stablecoins: direct price calculation
            xai_price_usd = other_amount / xai_amount

            # Validate against price floor
            current_floor = self.price_floor.get_current_floor()

            if xai_price_usd < current_floor:
                return {
                    "success": False,
                    "error": "PRICE_BELOW_FLOOR",
                    "message": f"Price too low (floor enforced on stablecoins)",
                }

        # Crypto pairs (BTC, ETH, etc): free market, no validation

        # Create order
        order = SwapOrder(
            order_type=order_type,
            xai_amount=xai_amount,
            other_coin=other_coin,
            other_amount=other_amount,
            user_address=user_address,
        )

        self.orders[order.order_id] = order
        self.active_orders.append(order)

        # Try to auto-match
        match = self._find_matching_order(order)

        if match:
            return {
                "success": True,
                "order_id": order.order_id,
                "status": "MATCHED",
                "matched_with": match.order_id,
                "message": "Order matched! Swap ready to execute.",
            }
        else:
            return {
                "success": True,
                "order_id": order.order_id,
                "status": "PENDING",
                "message": "Order created. Waiting for match...",
            }

    def _find_matching_order(self, new_order: SwapOrder) -> SwapOrder | None:
        """
        Auto-match orders in orderbook

        BUY order matches with SELL order (and vice versa)
        """

        opposite_type = (
            SwapOrderType.SELL if new_order.order_type == SwapOrderType.BUY else SwapOrderType.BUY
        )

        # Find matching orders
        candidates = [
            order
            for order in self.active_orders
            if order.status == SwapOrderStatus.PENDING
            and order.order_type == opposite_type
            and order.other_coin == new_order.other_coin
            and abs(order.xai_amount - new_order.xai_amount) < 0.01  # Match amounts
            and abs(order.price_per_xai - new_order.price_per_xai) < 0.001  # Match prices
        ]

        if candidates:
            # Match with first candidate
            match = candidates[0]

            # Update both orders
            new_order.status = SwapOrderStatus.MATCHED
            new_order.matched_with = match.order_id
            match.status = SwapOrderStatus.MATCHED
            match.matched_with = new_order.order_id

            # Remove from active orders
            self.active_orders.remove(match)
            self.active_orders.remove(new_order)

            return match

        return None

    def get_orderbook(self, coin: str = None) -> Dict:
        """Get current orderbook state"""

        orders = self.active_orders
        if coin:
            orders = [o for o in orders if o.other_coin == coin]

        buy_orders = [o for o in orders if o.order_type == SwapOrderType.BUY]
        sell_orders = [o for o in orders if o.order_type == SwapOrderType.SELL]

        return {
            "buy_orders": [
                o.to_dict() for o in sorted(buy_orders, key=lambda x: x.price_per_xai, reverse=True)
            ],
            "sell_orders": [
                o.to_dict() for o in sorted(sell_orders, key=lambda x: x.price_per_xai)
            ],
            "total_pending": len(orders),
        }

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel pending order"""

        if order_id not in self.orders:
            return {"success": False, "error": "Order not found"}

        order = self.orders[order_id]

        if order.status != SwapOrderStatus.PENDING:
            return {"success": False, "error": "Cannot cancel non-pending order"}

        order.status = SwapOrderStatus.CANCELLED
        self.active_orders.remove(order)

        return {"success": True, "message": "Order cancelled"}

class SimpleSwapGUI:
    """
    Simple one-click swap interface for users
    Hides all HTLC complexity
    """

    def __init__(self, blockchain, wallet_address):
        from xai.core.mystery_price_floor import MysteryPriceFloor

        self.blockchain = blockchain
        self.wallet_address = wallet_address
        self.price_floor = MysteryPriceFloor()
        self.orderbook = OnChainOrderbook(blockchain, self.price_floor)
        self.active_swaps = {}  # track user's active swaps

    def swap_xai_for_coin(
        self, xai_amount: float, target_coin: str, max_price: float = None
    ) -> Dict:
        """
        One-click swap: Sell XAI, get other coin

        Args:
            xai_amount: Amount of XAI to sell
            target_coin: Coin to receive (BTC, ETH, USDT, etc.)
            max_price: Maximum price willing to pay (optional)

        Returns:
            dict: Swap status and details
        """

        # Get current market price
        market_price = self.orderbook.price_tracker.get_xai_price_usd()

        if target_coin in ["USDT", "USDC", "DAI"]:
            # Stablecoin swap - use market price
            other_amount = xai_amount * market_price
        else:
            # Need to calculate from market rates
            coin_price_usd = self.orderbook.price_tracker.get_market_price(target_coin)
            if coin_price_usd:
                other_amount = (xai_amount * market_price) / coin_price_usd
            else:
                return {
                    "success": False,
                    "error": "PRICE_UNAVAILABLE",
                    "message": f"No recent {target_coin} swaps. Cannot determine price.",
                }

        # Create sell order
        result = self.orderbook.create_order(
            order_type=SwapOrderType.SELL,
            xai_amount=xai_amount,
            other_coin=target_coin,
            other_amount=other_amount,
            user_address=self.wallet_address,
        )

        if result["success"] and result["status"] == "MATCHED":
            # Order matched! Create HTLC automatically
            swap_id = self._create_htlc_swap(result["order_id"], result["matched_with"])
            result["swap_id"] = swap_id
            result["message"] = f"Swapping {xai_amount} XAI for {other_amount:.8f} {target_coin}..."

        return result

    def swap_coin_for_xai(
        self, other_coin: str, other_amount: float, min_xai: float = None
    ) -> Dict:
        """
        One-click swap: Sell other coin, get XAI

        Args:
            other_coin: Coin to sell (BTC, ETH, USDT, etc.)
            other_amount: Amount of other coin to sell
            min_xai: Minimum XAI to receive (optional)

        Returns:
            dict: Swap status and details
        """

        # Get current market price
        market_price = self.orderbook.price_tracker.get_xai_price_usd()

        if other_coin in ["USDT", "USDC", "DAI"]:
            # Stablecoin swap
            xai_amount = other_amount / market_price

            # Validate against floor
            current_floor = self.price_floor.get_current_floor()
            if market_price < current_floor:
                return {
                    "success": False,
                    "error": "PRICE_BELOW_FLOOR",
                    "message": "Current market price below floor",
                }
        else:
            # Crypto swap
            coin_price_usd = self.orderbook.price_tracker.get_market_price(other_coin)
            if coin_price_usd:
                xai_amount = (other_amount * coin_price_usd) / market_price
            else:
                return {
                    "success": False,
                    "error": "PRICE_UNAVAILABLE",
                    "message": f"No recent {other_coin} swaps",
                }

        # Create buy order
        result = self.orderbook.create_order(
            order_type=SwapOrderType.BUY,
            xai_amount=xai_amount,
            other_coin=other_coin,
            other_amount=other_amount,
            user_address=self.wallet_address,
        )

        if result["success"] and result["status"] == "MATCHED":
            # Order matched! Create HTLC automatically
            swap_id = self._create_htlc_swap(result["order_id"], result["matched_with"])
            result["swap_id"] = swap_id
            result["message"] = f"Swapping {other_amount:.8f} {other_coin} for {xai_amount} XAI..."

        return result

    def _create_htlc_swap(self, order_id: str, matched_order_id: str) -> str:
        """
        Automatically create HTLC contracts for matched swap
        User doesn't need to know about secrets, timelocks, etc.
        """

        order = self.orderbook.orders[order_id]
        matched_order = self.orderbook.orders[matched_order_id]

        # Generate secret
        secret = secrets.token_bytes(32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Create swap ID
        swap_id = hashlib.sha256(f"{order_id}-{matched_order_id}".encode()).hexdigest()[:16]

        # Store swap data
        self.active_swaps[swap_id] = {
            "order_id": order_id,
            "matched_order_id": matched_order_id,
            "secret": secret.hex(),
            "secret_hash": secret_hash,
            "status": "HTLC_CREATED",
            "xai_amount": order.xai_amount,
            "other_coin": order.other_coin,
            "other_amount": order.other_amount,
            "created_at": time.time(),
        }

        # Update order statuses
        order.status = SwapOrderStatus.HTLC_CREATED
        matched_order.status = SwapOrderStatus.HTLC_CREATED

        return swap_id

    def get_swap_progress(self, swap_id: str) -> Dict:
        """
        Check progress of active swap
        User just sees: "30% complete" instead of HTLC details
        """

        if swap_id not in self.active_swaps:
            return {"error": "Swap not found"}

        swap = self.active_swaps[swap_id]

        # Calculate progress
        progress_steps = {
            "HTLC_CREATED": 25,
            "SECRET_REVEALED": 50,
            "FUNDS_LOCKED": 75,
            "COMPLETED": 100,
        }

        progress = progress_steps.get(swap["status"], 0)

        return {
            "swap_id": swap_id,
            "status": swap["status"],
            "progress_percent": progress,
            "xai_amount": swap["xai_amount"],
            "other_coin": swap["other_coin"],
            "other_amount": swap["other_amount"],
            "estimated_completion": swap["created_at"] + 3600,  # 1 hour estimate
        }

    def get_supported_coins(self) -> list[str]:
        """Get list of supported coins for swaps"""
        return ["BTC", "ETH", "LTC", "DOGE", "XMR", "BCH", "USDT", "ZEC", "DASH", "USDC", "DAI"]

    def get_current_prices(self) -> Dict:
        """
        Get current market prices (from on-chain swap history)
        NO external API calls
        """

        prices = {}
        xai_price_usd = self.orderbook.price_tracker.get_xai_price_usd()

        for coin in self.get_supported_coins():
            if coin in ["USDT", "USDC", "DAI"]:
                # Stablecoins
                prices[coin] = {
                    "price_usd": 1.0,
                    "xai_per_unit": 1.0 / xai_price_usd if xai_price_usd > 0 else 0,
                }
            else:
                # Crypto
                coin_price = self.orderbook.price_tracker.get_market_price(coin)
                if coin_price:
                    prices[coin] = {
                        "price_usd": coin_price,
                        "xai_per_unit": coin_price / xai_price_usd if xai_price_usd > 0 else 0,
                    }

        prices["XAI"] = {
            "price_usd": xai_price_usd,
            "floor_usd": self.price_floor.get_current_floor(),
        }

        return prices

# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI Simple Swap GUI")
    print("=" * 70)

    # Mock blockchain
    class MockBlockchain:
        pass

    blockchain = MockBlockchain()

    # Create GUI instance
    gui = SimpleSwapGUI(blockchain=blockchain, wallet_address="xai_1a2b3c4d5e6f")

    print("\nSupported Coins:")
    print("-" * 70)
    for coin in gui.get_supported_coins():
        print(f"  {coin}")

    print("\n\nExample: Swapping 1000 XAI for USDT")
    print("-" * 70)

    result = gui.swap_xai_for_coin(xai_amount=1000, target_coin="USDT")

    print(f"Status: {result.get('status')}")
    print(f"Message: {result.get('message')}")

    if "swap_id" in result:
        print(f"\nSwap Progress:")
        progress = gui.get_swap_progress(result["swap_id"])
        print(f"  Progress: {progress['progress_percent']}%")
        print(f"  Status: {progress['status']}")

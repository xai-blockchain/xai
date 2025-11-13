"""
AXN Market Making Bot - Automated Liquidity Provider
Maintains buy and sell orders to ensure trading is always possible
"""

import time
import random
from decimal import Decimal
from typing import List, Dict, Optional
import requests
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class MarketMaker:
    """Automated market maker that maintains liquidity"""

    def __init__(self, node_url: str, maker_address: str):
        self.node_url = node_url
        self.maker_address = maker_address

        # Market making strategy
        self.base_price = Decimal('0.0512')  # Base AXN price in USD
        self.spread_percent = Decimal('0.01')  # 1% spread
        self.order_size_min = Decimal('50')    # Min 50 AXN per order
        self.order_size_max = Decimal('500')   # Max 500 AXN per order
        self.num_levels = 5  # Number of price levels on each side

        # Order book depth
        self.price_step = Decimal('0.001')  # $0.001 price increments

        # Safety limits
        self.max_total_usd_locked = 5000.0  # Max $5K locked in orders
        self.max_total_axn_locked = 100000.0  # Max 100K AXN locked

        # Trading pairs
        self.pairs = ['AXN/USD', 'AXN/BTC', 'AXN/ETH']

        print(f"🤖 Market Maker initialized for {maker_address}")
        print(f"   Base price: ${self.base_price}")
        print(f"   Spread: {float(self.spread_percent * 100)}%")
        print(f"   Order size: {self.order_size_min}-{self.order_size_max} AXN")

    def calculate_order_levels(self, pair: str = 'AXN/USD') -> Dict:
        """Calculate buy and sell order levels"""
        base_price = self.base_price

        # Calculate bid/ask prices with spread
        mid_price = base_price
        half_spread = mid_price * self.spread_percent / 2

        buy_price = mid_price - half_spread
        sell_price = mid_price + half_spread

        # Generate multiple price levels
        buy_levels = []
        sell_levels = []

        for i in range(self.num_levels):
            # Buy side - descending prices
            level_buy_price = buy_price - (self.price_step * i)
            buy_amount = random.uniform(
                float(self.order_size_min),
                float(self.order_size_max)
            )
            buy_levels.append({
                'price': float(level_buy_price),
                'amount': round(buy_amount, 2),
                'total': float(level_buy_price * Decimal(str(buy_amount)))
            })

            # Sell side - ascending prices
            level_sell_price = sell_price + (self.price_step * i)
            sell_amount = random.uniform(
                float(self.order_size_min),
                float(self.order_size_max)
            )
            sell_levels.append({
                'price': float(level_sell_price),
                'amount': round(sell_amount, 2),
                'total': float(level_sell_price * Decimal(str(sell_amount)))
            })

        return {
            'pair': pair,
            'mid_price': float(mid_price),
            'spread': float(self.spread_percent * 100),
            'buy_orders': buy_levels,
            'sell_orders': sell_levels,
            'timestamp': time.time()
        }

    def place_liquidity_orders(self, pair: str = 'AXN/USD') -> Dict:
        """Place market making orders on the exchange"""
        levels = self.calculate_order_levels(pair)

        placed_orders = {
            'buy': [],
            'sell': [],
            'total_usd_locked': 0,
            'total_axn_locked': 0
        }

        # Place buy orders
        for level in levels['buy_orders']:
            try:
                response = requests.post(
                    f"{self.node_url}/exchange/place-order",
                    json={
                        'address': self.maker_address,
                        'order_type': 'buy',
                        'pair': pair,
                        'price': level['price'],
                        'amount': level['amount']
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        placed_orders['buy'].append(result['order'])
                        placed_orders['total_usd_locked'] += level['total']

            except Exception as e:
                print(f"Failed to place buy order: {e}")

        # Place sell orders
        for level in levels['sell_orders']:
            try:
                response = requests.post(
                    f"{self.node_url}/exchange/place-order",
                    json={
                        'address': self.maker_address,
                        'order_type': 'sell',
                        'pair': pair,
                        'price': level['price'],
                        'amount': level['amount']
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        placed_orders['sell'].append(result['order'])
                        placed_orders['total_axn_locked'] += level['amount']

            except Exception as e:
                print(f"Failed to place sell order: {e}")

        return placed_orders

    def get_current_orders(self) -> List[Dict]:
        """Get market maker's current orders"""
        try:
            response = requests.get(
                f"{self.node_url}/exchange/my-orders/{self.maker_address}",
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('orders', [])

        except Exception as e:
            print(f"Failed to get orders: {e}")

        return []

    def cancel_stale_orders(self, max_age_seconds: int = 3600):
        """Cancel orders older than specified age"""
        current_orders = self.get_current_orders()
        current_time = time.time()

        cancelled = []
        for order in current_orders:
            if order['status'] == 'open':
                age = current_time - order['timestamp']
                if age > max_age_seconds:
                    try:
                        response = requests.post(
                            f"{self.node_url}/exchange/cancel-order",
                            json={'order_id': order['id']},
                            timeout=5
                        )

                        if response.status_code == 200:
                            cancelled.append(order['id'])

                    except Exception as e:
                        print(f"Failed to cancel order {order['id']}: {e}")

        return cancelled

    def maintain_liquidity(self):
        """Main loop to maintain market liquidity"""
        print("🔄 Starting liquidity maintenance...")

        # Cancel old orders
        cancelled = self.cancel_stale_orders(max_age_seconds=1800)  # 30 min
        if cancelled:
            print(f"   Cancelled {len(cancelled)} stale orders")

        # Check current order book
        current_orders = self.get_current_orders()
        open_orders = [o for o in current_orders if o['status'] == 'open']

        print(f"   Current open orders: {len(open_orders)}")

        # Place new orders if needed
        if len(open_orders) < self.num_levels * 2:  # Need orders on both sides
            print("   Placing new liquidity orders...")
            result = self.place_liquidity_orders('AXN/USD')

            print(f"   ✅ Placed {len(result['buy'])} buy orders")
            print(f"   ✅ Placed {len(result['sell'])} sell orders")
            print(f"   💰 Locked ${result['total_usd_locked']:.2f} USD")
            print(f"   💰 Locked {result['total_axn_locked']:.2f} AXN")

        return {
            'orders_cancelled': len(cancelled) if cancelled else 0,
            'orders_placed': len(open_orders),
            'timestamp': time.time()
        }

    def run_continuously(self, interval_seconds: int = 300):
        """Run market maker continuously"""
        print(f"\n{'='*60}")
        print("🤖 MARKET MAKER BOT STARTED")
        print(f"{'='*60}")
        print(f"Running every {interval_seconds} seconds (Ctrl+C to stop)\n")

        try:
            while True:
                try:
                    self.maintain_liquidity()
                except Exception as e:
                    print(f"❌ Error in maintenance cycle: {e}")

                print(f"\n⏰ Next cycle in {interval_seconds} seconds...\n")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n🛑 Market maker stopped by user")

    def get_stats(self) -> Dict:
        """Get market maker statistics"""
        orders = self.get_current_orders()

        buy_orders = [o for o in orders if o['order_type'] == 'buy' and o['status'] == 'open']
        sell_orders = [o for o in orders if o['order_type'] == 'sell' and o['status'] == 'open']
        filled_orders = [o for o in orders if o['status'] == 'filled']

        total_usd_locked = sum(o.get('total', 0) for o in buy_orders)
        total_axn_locked = sum(o.get('amount', 0) for o in sell_orders)

        return {
            'total_orders': len(orders),
            'open_buy_orders': len(buy_orders),
            'open_sell_orders': len(sell_orders),
            'filled_orders': len(filled_orders),
            'usd_locked': total_usd_locked,
            'axn_locked': total_axn_locked,
            'base_price': float(self.base_price),
            'spread_percent': float(self.spread_percent * 100)
        }

"""
AXN Exchange Trading Fee Configuration
Implements tiered fee structure to encourage AXN-centric trading
"""

from decimal import Decimal
from typing import Dict

class TradingFees:
    """Manages trading fees for all exchange pairs"""

    def __init__(self):
        # Fee structure designed to make AXN the central trading hub

        # LOW FEES: AXN pairs (encourage AXN trading)
        self.axn_pair_fee = Decimal('0.001')  # 0.1% - Very competitive

        # HIGH FEES: Non-AXN pairs (discourage trading other coins)
        self.non_axn_pair_fee = Decimal('0.03')  # 3.0% - Significantly higher

        # PREMIUM FEES: Fiat pairs (highest fees)
        self.fiat_pair_fee = Decimal('0.05')  # 5.0% - Discourage fiat speculation

        # Maker/Taker fee differential (optional)
        self.maker_discount = Decimal('0.5')  # 50% discount for makers (liquidity providers)

    def get_fee_rate(self, trading_pair: str, is_maker: bool = False) -> Decimal:
        """
        Calculate fee rate for a trading pair

        Args:
            trading_pair: Format "BASE/QUOTE" (e.g., "AXN/USD", "BTC/ETH")
            is_maker: True if maker order (provides liquidity), False if taker

        Returns:
            Fee rate as decimal (e.g., 0.001 = 0.1%)
        """
        base, quote = trading_pair.split('/')

        # AXN pairs get LOW fees (encourage AXN trading)
        if base == 'AXN' or quote == 'AXN':
            base_fee = self.axn_pair_fee
        # Fiat pairs get PREMIUM fees
        elif base == 'USD' or quote == 'USD':
            base_fee = self.fiat_pair_fee
        # All other pairs get HIGH fees (discourage non-AXN trading)
        else:
            base_fee = self.non_axn_pair_fee

        # Apply maker discount if applicable
        if is_maker:
            return base_fee * self.maker_discount

        return base_fee

    def calculate_fee(self, trading_pair: str, trade_amount: float, is_maker: bool = False) -> float:
        """
        Calculate actual fee in currency units

        Args:
            trading_pair: Format "BASE/QUOTE"
            trade_amount: Amount being traded (in quote currency)
            is_maker: True if maker order

        Returns:
            Fee amount in same currency as trade_amount
        """
        fee_rate = self.get_fee_rate(trading_pair, is_maker)
        amount_decimal = Decimal(str(trade_amount))

        return float(amount_decimal * fee_rate)

    def get_fee_schedule(self) -> Dict:
        """Get complete fee schedule for display"""
        return {
            'axn_pairs': {
                'description': 'AXN trading pairs (e.g., AXN/USD, AXN/BTC, AXN/ETH)',
                'taker_fee': f"{float(self.axn_pair_fee * 100):.2f}%",
                'maker_fee': f"{float(self.axn_pair_fee * self.maker_discount * 100):.2f}%",
                'examples': ['AXN/USD', 'AXN/BTC', 'AXN/ETH', 'AXN/SOL', 'AXN/DOGE']
            },
            'crypto_pairs': {
                'description': 'Non-AXN cryptocurrency pairs (e.g., BTC/ETH, SOL/USDT)',
                'taker_fee': f"{float(self.non_axn_pair_fee * 100):.2f}%",
                'maker_fee': f"{float(self.non_axn_pair_fee * self.maker_discount * 100):.2f}%",
                'examples': ['BTC/ETH', 'SOL/USDT', 'DOGE/BTC', 'MATIC/ETH']
            },
            'fiat_pairs': {
                'description': 'Fiat trading pairs (e.g., BTC/USD, ETH/USD)',
                'taker_fee': f"{float(self.fiat_pair_fee * 100):.2f}%",
                'maker_fee': f"{float(self.fiat_pair_fee * self.maker_discount * 100):.2f}%",
                'examples': ['BTC/USD', 'ETH/USD', 'SOL/USD']
            },
            'note': 'Makers (liquidity providers) receive 50% discount on all fees'
        }

    def get_fee_comparison(self, trade_amount_usd: float = 1000.0) -> Dict:
        """
        Show fee comparison for a sample trade amount

        Args:
            trade_amount_usd: Sample trade amount in USD

        Returns:
            Fee comparison showing costs for different pair types
        """
        return {
            'trade_amount': f"${trade_amount_usd:.2f}",
            'fees': {
                'AXN/USD (taker)': f"${self.calculate_fee('AXN/USD', trade_amount_usd, False):.2f}",
                'AXN/USD (maker)': f"${self.calculate_fee('AXN/USD', trade_amount_usd, True):.2f}",
                'BTC/ETH (taker)': f"${self.calculate_fee('BTC/ETH', trade_amount_usd, False):.2f}",
                'BTC/ETH (maker)': f"${self.calculate_fee('BTC/ETH', trade_amount_usd, True):.2f}",
                'BTC/USD (taker)': f"${self.calculate_fee('BTC/USD', trade_amount_usd, False):.2f}",
                'BTC/USD (maker)': f"${self.calculate_fee('BTC/USD', trade_amount_usd, True):.2f}",
            },
            'explanation': 'AXN pairs are 30x cheaper than non-AXN crypto pairs, making AXN the preferred trading hub'
        }


# Global fee manager instance
fee_manager = TradingFees()


# Quick access functions
def get_trading_fee(pair: str, amount: float, is_maker: bool = False) -> float:
    """Calculate trading fee for a pair"""
    return fee_manager.calculate_fee(pair, amount, is_maker)


def get_fee_rate(pair: str, is_maker: bool = False) -> float:
    """Get fee rate as percentage"""
    return float(fee_manager.get_fee_rate(pair, is_maker) * 100)


if __name__ == '__main__':
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Test fee structure
    print("AXN Exchange Fee Structure")
    print("=" * 60)

    fees = TradingFees()

    # Show fee schedule
    schedule = fees.get_fee_schedule()
    print("\nFee Schedule:")
    print("-" * 60)

    for pair_type, details in schedule.items():
        if pair_type == 'note':
            print(f"\nNOTE: {details}")
            continue

        print(f"\n{pair_type.upper()}:")
        print(f"  {details['description']}")
        print(f"  Taker Fee: {details['taker_fee']}")
        print(f"  Maker Fee: {details['maker_fee']}")
        print(f"  Examples: {', '.join(details['examples'])}")

    # Show comparison
    print("\n" + "=" * 60)
    print("Fee Comparison (for $1,000 trade):")
    print("-" * 60)

    comparison = fees.get_fee_comparison(1000.0)
    for pair, fee in comparison['fees'].items():
        print(f"  {pair:20s} -> {fee:>10s}")

    print(f"\nINSIGHT: {comparison['explanation']}")

    # Show specific examples
    print("\n" + "=" * 60)
    print("Specific Examples:")
    print("-" * 60)

    examples = [
        ('AXN/USD', 500, False),
        ('AXN/BTC', 500, True),
        ('BTC/ETH', 500, False),
        ('SOL/USDT', 500, False),
    ]

    for pair, amount, is_maker in examples:
        fee = fees.calculate_fee(pair, amount, is_maker)
        rate = fees.get_fee_rate(pair, is_maker)
        order_type = "Maker" if is_maker else "Taker"
        print(f"  {pair} ${amount} ({order_type})")
        print(f"    Fee Rate: {float(rate * 100):.3f}%")
        print(f"    Fee Amount: ${fee:.2f}")
        print()

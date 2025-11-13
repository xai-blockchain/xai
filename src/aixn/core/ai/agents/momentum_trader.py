"""Momentum trader and market data helpers for AI simulations."""

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Dict, List, Optional


class Signal(Enum):
    """Indicator about the market direction."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class MarketData:
    """Simple market snapshot for the momentum trader demo."""
    symbol: str
    price: float
    volume: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: float


@dataclass
class TradeDecision:
    """Simplified trading decision used in the launch script."""
    action: Signal
    amount: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: str


class MomentumTrader:
    """Momentum-based AI trader stub used in the launch sequence."""

    def __init__(self):
        self.config = {
            'risk_per_trade': 0.015,
            'min_confidence': 0.3,
            'default_amount': 1200.0
        }
        self.performance = {
            'total_value': 50000.0,
            'open_positions': 0
        }

    def analyze_market(self, market_data: List[MarketData]) -> Dict[str, object]:
        if not market_data:
            return {
                'signal': Signal.HOLD,
                'confidence': 0.0,
                'indicators': {
                    'ma_short': 0.0,
                    'ma_long': 0.0,
                    'rsi': 50.0,
                    'volume_ratio': 1.0,
                    'momentum_score': 0.0
                }
            }

        prices = [entry.price for entry in market_data]
        short_window = prices[-5:] if len(prices) >= 5 else prices
        long_window = prices[-20:] if len(prices) >= 20 else prices
        ma_short = mean(short_window)
        ma_long = mean(long_window)
        momentum_score = (ma_short - ma_long) / max(ma_long, 1e-8)
        signal = Signal.HOLD
        if momentum_score > 0.01:
            signal = Signal.BUY
        elif momentum_score < -0.01:
            signal = Signal.SELL

        volume_ratio = (market_data[-1].volume / max(min(m.volume for m in market_data), 1.0))
        rsi = 50 + (momentum_score * 25)
        confidence = min(1.0, max(0.0, 0.3 + abs(momentum_score)))

        return {
            'signal': signal,
            'confidence': confidence,
            'indicators': {
                'ma_short': ma_short,
                'ma_long': ma_long,
                'rsi': rsi,
                'volume_ratio': volume_ratio,
                'momentum_score': momentum_score
            }
        }

    def make_trading_decision(self, analysis: Dict[str, object]) -> Optional[TradeDecision]:
        if analysis['confidence'] < self.config['min_confidence']:
            return None

        action = analysis['signal']
        entry_price = (analysis['indicators']['ma_short'] + analysis['indicators']['ma_long']) / 2
        amount = self.config['default_amount'] * analysis['confidence']
        stop_loss = entry_price * 0.995
        take_profit = entry_price * 1.01
        reasoning = (
            f"{action.value} signal with {analysis['confidence']*100:.1f}% "
            f"confidence (momentum {analysis['indicators']['momentum_score']:.3f})"
        )

        return TradeDecision(
            action=action,
            amount=amount,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning
        )

    def execute_trade(self, decision: TradeDecision) -> Dict[str, object]:
        self.performance['open_positions'] += 1
        self.performance['total_value'] += decision.amount * 0.02

        return {
            'message': (
                f"Simulated {decision.action.value} for {decision.amount:.2f} USDC "
                f"at ${decision.entry_price:.6f}"
            ),
            'status': 'simulated'
        }

    def get_performance_report(self) -> Dict[str, object]:
        return dict(self.performance)

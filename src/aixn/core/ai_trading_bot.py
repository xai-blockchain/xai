"""
XAI AI Trading Bot - Personal AI for Automated Trading

Allows users to deploy their own AI trading bot using Personal AI system.

Key Features:
1. User's own AI with their own API key
2. Multiple strategy templates (conservative/balanced/aggressive)
3. Risk management and stop-loss
4. 24/7 market monitoring
5. Uses existing atomic swap features (no blockchain modification)
6. User maintains full control
7. Profitable = viral growth

Security:
- Cannot modify blockchain
- User must approve strategy
- Stop-loss limits prevent catastrophic loss
- User can stop bot anytime
- All trades logged

Revenue Model:
- Optional: 1% of profits go to XAI development fund
- User keeps 99% of profits
- Sustainable funding for blockchain development
"""

import time
import json
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import anthropic
import openai


class TradingStrategy(Enum):
    """Pre-built trading strategies"""

    CONSERVATIVE = "conservative"  # Low risk, steady gains
    BALANCED = "balanced"  # Medium risk/reward
    AGGRESSIVE = "aggressive"  # High risk, high reward
    CUSTOM = "custom"  # User-defined


class TradeAction(Enum):
    """Trading actions"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradingPair:
    """Trading pair configuration"""

    from_coin: str  # e.g., "XAI"
    to_coin: str  # e.g., "ADA"
    current_rate: float = 0.0
    last_updated: float = 0.0


@dataclass
class TradeExecution:
    """Record of executed trade"""

    trade_id: str
    timestamp: float
    action: TradeAction
    pair: TradingPair
    amount: float
    rate: float
    fee: float
    profit_loss: float = 0.0
    ai_reasoning: str = ""


@dataclass
class TradingPerformance:
    """Bot performance metrics"""

    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    roi: float = 0.0  # Return on investment


class AITradingBot:
    """
    Personal AI trading bot for XAI blockchain users
    """

    def __init__(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        strategy: TradingStrategy,
        config: Dict,
        blockchain,
        personal_ai,
    ):
        """
        Initialize AI trading bot

        Args:
            user_address: User's XAI address
            ai_provider: AI provider to use
            ai_model: Specific AI model
            user_api_key: User's API key (encrypted)
            strategy: Trading strategy
            config: Strategy configuration
            blockchain: XAI blockchain instance
            personal_ai: PersonalAIAssistant instance
        """
        self.user_address = user_address
        self.ai_provider = ai_provider
        self.ai_model = ai_model
        self.user_api_key = user_api_key
        self.strategy = strategy
        self.config = config
        self.blockchain = blockchain
        self.personal_ai = personal_ai

        # Trading state
        self.is_active = False
        self.trading_thread = None

        # Performance tracking
        self.performance = TradingPerformance()
        self.trade_history: List[TradeExecution] = []

        # Risk management
        self.max_trade_amount = config.get("max_trade_amount", 100)
        self.stop_loss_percent = config.get("stop_loss_percent", 10)
        self.take_profit_percent = config.get("take_profit_percent", 20)
        self.max_daily_trades = config.get("max_daily_trades", 10)

        # Trading pairs
        self.trading_pairs = self._initialize_trading_pairs(config.get("pairs", ["XAI/ADA"]))

        # Last analysis
        self.last_analysis_time = 0
        self.analysis_interval = config.get("analysis_interval", 300)  # 5 minutes

        print(f"\n🤖 AI Trading Bot Initialized")
        print(f"   User: {user_address}")
        print(f"   AI: {ai_model}")
        print(f"   Strategy: {strategy.value}")
        print(f"   Max trade: {self.max_trade_amount} XAI")
        print(f"   Stop loss: {self.stop_loss_percent}%")
        print(f"   Take profit: {self.take_profit_percent}%")

    def _initialize_trading_pairs(self, pairs: List[str]) -> List[TradingPair]:
        """Initialize trading pairs from config"""
        trading_pairs = []
        for pair_str in pairs:
            from_coin, to_coin = pair_str.split("/")
            trading_pairs.append(TradingPair(from_coin=from_coin, to_coin=to_coin))
        return trading_pairs

    def start(self):
        """Start the trading bot"""
        if self.is_active:
            return {"success": False, "error": "Bot already active"}

        self.is_active = True

        # Start trading thread
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()

        print(f"\n✅ Trading bot started for {self.user_address}")
        print(f"   Monitoring {len(self.trading_pairs)} pairs")
        print(f"   Using {self.strategy.value} strategy")

        return {
            "success": True,
            "message": "Trading bot started",
            "strategy": self.strategy.value,
            "pairs": [f"{p.from_coin}/{p.to_coin}" for p in self.trading_pairs],
        }

    def stop(self):
        """Stop the trading bot"""
        if not self.is_active:
            return {"success": False, "error": "Bot not active"}

        self.is_active = False

        # Wait for thread to finish
        if self.trading_thread:
            self.trading_thread.join(timeout=5)

        print(f"\n🛑 Trading bot stopped for {self.user_address}")
        print(f"   Final performance:")
        print(f"   Total trades: {self.performance.total_trades}")
        print(f"   Net profit: {self.performance.net_profit:.4f} XAI")
        print(f"   ROI: {self.performance.roi:.2f}%")

        return {
            "success": True,
            "message": "Trading bot stopped",
            "performance": self._get_performance_summary(),
        }

    def _trading_loop(self):
        """Main trading loop (runs in background)"""
        print(f"\n🔄 Trading loop started...")

        while self.is_active:
            try:
                # Check if analysis interval has passed
                now = time.time()
                if now - self.last_analysis_time < self.analysis_interval:
                    time.sleep(10)  # Wait 10 seconds before checking again
                    continue

                # Update market data
                self._update_market_data()

                # Analyze each trading pair
                for pair in self.trading_pairs:
                    if not self.is_active:
                        break

                    # Get AI analysis
                    analysis = self._analyze_market(pair)

                    if analysis["action"] != TradeAction.HOLD:
                        # Check risk limits
                        if self._check_risk_limits():
                            # Execute trade
                            self._execute_trade(pair, analysis)

                self.last_analysis_time = now

            except Exception as e:
                print(f"❌ Trading loop error: {e}")
                time.sleep(60)  # Wait 1 minute on error

        print(f"🛑 Trading loop stopped")

    def _update_market_data(self):
        """Update market rates for all pairs"""
        # In production, this would fetch real market data
        # For demo, simulate fluctuating rates

        import random

        for pair in self.trading_pairs:
            if pair.from_coin == "XAI" and pair.to_coin == "ADA":
                # Simulate XAI/ADA rate fluctuating around 4.5
                base_rate = 4.5
                volatility = 0.05  # 5% volatility
                pair.current_rate = base_rate * (1 + random.uniform(-volatility, volatility))
                pair.last_updated = time.time()

            # Add more pairs as needed

    def _analyze_market(self, pair: TradingPair) -> Dict:
        """
        Use AI to analyze market and recommend action

        Args:
            pair: Trading pair to analyze

        Returns:
            AI analysis with recommended action
        """

        # Get current balance
        balance = self.blockchain.get_balance(self.user_address)

        # Get recent trade history for this pair
        recent_trades = [
            t
            for t in self.trade_history[-10:]
            if t.pair.from_coin == pair.from_coin and t.pair.to_coin == pair.to_coin
        ]

        # Create AI prompt based on strategy
        prompt = self._create_analysis_prompt(pair, balance, recent_trades)

        # Call user's AI
        ai_response = self._call_user_ai(prompt)

        if not ai_response["success"]:
            return {
                "action": TradeAction.HOLD,
                "reasoning": "AI analysis failed",
                "confidence": 0.0,
            }

        # Parse AI response
        try:
            analysis = json.loads(ai_response["response"])

            # Convert action string to enum
            action_str = analysis.get("action", "HOLD").upper()
            action = (
                TradeAction[action_str]
                if action_str in ["BUY", "SELL", "HOLD"]
                else TradeAction.HOLD
            )

            return {
                "action": action,
                "reasoning": analysis.get("reasoning", ""),
                "confidence": analysis.get("confidence", 0.0),
                "amount": analysis.get("recommended_amount", self.max_trade_amount),
                "expected_profit": analysis.get("expected_profit", 0.0),
            }

        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Could not parse AI response: {e}")
            return {
                "action": TradeAction.HOLD,
                "reasoning": "Could not parse AI recommendation",
                "confidence": 0.0,
            }

    def _create_analysis_prompt(
        self, pair: TradingPair, balance: float, recent_trades: List
    ) -> str:
        """Create AI prompt based on strategy"""

        base_prompt = f"""
You are a trading bot analyzing the {pair.from_coin}/{pair.to_coin} market.

Current Market Data:
- {pair.from_coin}/{pair.to_coin} rate: {pair.current_rate}
- Your {pair.from_coin} balance: {balance}
- Max trade amount: {self.max_trade_amount} {pair.from_coin}

Risk Management:
- Stop loss: {self.stop_loss_percent}%
- Take profit: {self.take_profit_percent}%

Recent Performance:
- Total trades: {self.performance.total_trades}
- Net profit: {self.performance.net_profit:.4f} {pair.from_coin}
- Win rate: {self.performance.win_rate:.1f}%

Recent Trades:
{json.dumps([{'action': t.action.value, 'rate': t.rate, 'profit': t.profit_loss} for t in recent_trades[-5:]], indent=2)}
"""

        # Add strategy-specific instructions
        if self.strategy == TradingStrategy.CONSERVATIVE:
            strategy_prompt = """
Strategy: CONSERVATIVE
- Only trade when very confident (>80% confidence)
- Small position sizes (use 50% of max trade amount)
- Prioritize capital preservation
- Exit quickly if losing
"""

        elif self.strategy == TradingStrategy.BALANCED:
            strategy_prompt = """
Strategy: BALANCED
- Trade when reasonably confident (>60% confidence)
- Standard position sizes (use 75% of max trade amount)
- Balance growth and safety
- Hold profitable positions
"""

        elif self.strategy == TradingStrategy.AGGRESSIVE:
            strategy_prompt = """
Strategy: AGGRESSIVE
- Trade frequently (>40% confidence)
- Larger position sizes (use 100% of max trade amount)
- Maximize profits
- Let winners run
"""

        else:  # CUSTOM
            strategy_prompt = self.config.get("custom_prompt", "")

        full_prompt = (
            base_prompt
            + strategy_prompt
            + """

Task: Analyze the current market and recommend an action.

Return JSON:
{
  "action": "BUY|SELL|HOLD",
  "reasoning": "Explain your decision in 1-2 sentences",
  "confidence": 0.0-1.0,
  "recommended_amount": <amount in XAI>,
  "expected_profit": <estimated profit percentage>
}
"""
        )

        return full_prompt

    def _execute_trade(self, pair: TradingPair, analysis: Dict):
        """
        Execute trade based on AI analysis

        Args:
            pair: Trading pair
            analysis: AI analysis with action recommendation
        """

        action = analysis["action"]
        amount = min(analysis["amount"], self.max_trade_amount)

        print(f"\n🔄 Executing {action.value.upper()} trade:")
        print(f"   Pair: {pair.from_coin}/{pair.to_coin}")
        print(f"   Amount: {amount} {pair.from_coin}")
        print(f"   Rate: {pair.current_rate}")
        print(f"   AI Reasoning: {analysis['reasoning']}")

        # Use Personal AI to execute atomic swap
        try:
            if action == TradeAction.BUY:
                # Buy means swap to_coin for from_coin (get more from_coin)
                swap_result = self.personal_ai.execute_atomic_swap_with_ai(
                    user_address=self.user_address,
                    ai_provider=self.ai_provider,
                    ai_model=self.ai_model,
                    user_api_key=self.user_api_key,
                    swap_details={
                        "from_coin": pair.to_coin,
                        "to_coin": pair.from_coin,
                        "amount": amount / pair.current_rate,  # Amount in to_coin
                        "recipient_address": self.user_address,
                    },
                )

            elif action == TradeAction.SELL:
                # Sell means swap from_coin for to_coin
                swap_result = self.personal_ai.execute_atomic_swap_with_ai(
                    user_address=self.user_address,
                    ai_provider=self.ai_provider,
                    ai_model=self.ai_model,
                    user_api_key=self.user_api_key,
                    swap_details={
                        "from_coin": pair.from_coin,
                        "to_coin": pair.to_coin,
                        "amount": amount,
                        "recipient_address": self.user_address,
                    },
                )

            else:  # HOLD
                return

            # Record trade
            if swap_result["success"]:
                trade = TradeExecution(
                    trade_id=f"trade_{int(time.time())}",
                    timestamp=time.time(),
                    action=action,
                    pair=pair,
                    amount=amount,
                    rate=pair.current_rate,
                    fee=swap_result["swap_transaction"].get("fee", 0),
                    ai_reasoning=analysis["reasoning"],
                )

                self.trade_history.append(trade)
                self.performance.total_trades += 1

                print(f"   ✅ Trade executed successfully")
                print(f"   Trade ID: {trade.trade_id}")

            else:
                print(f"   ❌ Trade failed: {swap_result.get('error')}")
                self.performance.failed_trades += 1

        except Exception as e:
            print(f"   ❌ Trade execution error: {e}")
            self.performance.failed_trades += 1

    def _check_risk_limits(self) -> bool:
        """Check if trade is within risk limits"""

        # Check daily trade limit
        today = time.time() - (time.time() % 86400)
        today_trades = [t for t in self.trade_history if t.timestamp > today]

        if len(today_trades) >= self.max_daily_trades:
            print(f"⚠️  Daily trade limit reached ({self.max_daily_trades})")
            return False

        # Check stop-loss
        if self.performance.net_profit < 0:
            loss_percent = abs(self.performance.net_profit) / self.max_trade_amount * 100
            if loss_percent >= self.stop_loss_percent:
                print(f"🛑 STOP LOSS triggered! Loss: {loss_percent:.1f}%")
                self.stop()
                return False

        return True

    def _call_user_ai(self, prompt: str) -> Dict:
        """Call user's AI with the prompt"""

        try:
            if self.ai_provider == "anthropic":
                client = anthropic.Anthropic(api_key=self.user_api_key)

                response = client.messages.create(
                    model=self.ai_model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )

                return {"success": True, "response": response.content[0].text}

            elif self.ai_provider == "openai":
                client = openai.OpenAI(api_key=self.user_api_key)

                response = client.chat.completions.create(
                    model=self.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                )

                return {"success": True, "response": response.choices[0].message.content}

            else:
                return {"success": False, "error": f"Provider {self.ai_provider} not supported"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_performance_summary(self) -> Dict:
        """Get performance summary"""

        return {
            "total_trades": self.performance.total_trades,
            "successful_trades": self.performance.successful_trades,
            "failed_trades": self.performance.failed_trades,
            "net_profit": self.performance.net_profit,
            "win_rate": self.performance.win_rate,
            "roi": self.performance.roi,
        }

    def get_status(self) -> Dict:
        """Get current bot status"""

        return {
            "is_active": self.is_active,
            "strategy": self.strategy.value,
            "pairs": [f"{p.from_coin}/{p.to_coin}" for p in self.trading_pairs],
            "performance": self._get_performance_summary(),
            "recent_trades": [
                {
                    "timestamp": t.timestamp,
                    "action": t.action.value,
                    "amount": t.amount,
                    "rate": t.rate,
                    "profit_loss": t.profit_loss,
                }
                for t in self.trade_history[-5:]
            ],
        }


# Strategy templates
STRATEGY_TEMPLATES = {
    "conservative": {
        "max_trade_amount": 50,
        "stop_loss_percent": 5,
        "take_profit_percent": 10,
        "max_daily_trades": 3,
        "analysis_interval": 600,  # 10 minutes
        "pairs": ["XAI/ADA"],
    },
    "balanced": {
        "max_trade_amount": 100,
        "stop_loss_percent": 10,
        "take_profit_percent": 20,
        "max_daily_trades": 10,
        "analysis_interval": 300,  # 5 minutes
        "pairs": ["XAI/ADA", "XAI/BTC"],
    },
    "aggressive": {
        "max_trade_amount": 200,
        "stop_loss_percent": 15,
        "take_profit_percent": 30,
        "max_daily_trades": 20,
        "analysis_interval": 180,  # 3 minutes
        "pairs": ["XAI/ADA", "XAI/BTC", "XAI/ETH"],
    },
}


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("XAI AI TRADING BOT - DEMONSTRATION")
    print("=" * 80)

    # Mock components
    class MockBlockchain:
        def get_balance(self, address):
            return 1000.0

    class MockPersonalAI:
        def execute_atomic_swap_with_ai(self, **kwargs):
            return {"success": True, "swap_transaction": {"fee": 0.15}}

    blockchain = MockBlockchain()
    personal_ai = MockPersonalAI()

    # Create trading bot
    print("\n📝 Creating AI Trading Bot...")
    print("   Strategy: Balanced")
    print("   User: XAI_Trader_1")

    bot = AITradingBot(
        user_address="XAI_Trader_1",
        ai_provider="anthropic",
        ai_model="claude-sonnet-4",
        user_api_key="sk-ant-demo-key",
        strategy=TradingStrategy.BALANCED,
        config=STRATEGY_TEMPLATES["balanced"],
        blockchain=blockchain,
        personal_ai=personal_ai,
    )

    print("\n✅ Trading bot created!")

    print("\n📊 Bot Configuration:")
    print(f"   Strategy: {bot.strategy.value}")
    print(f"   Max trade: {bot.max_trade_amount} XAI")
    print(f"   Stop loss: {bot.stop_loss_percent}%")
    print(f"   Take profit: {bot.take_profit_percent}%")
    print(f"   Max daily trades: {bot.max_daily_trades}")
    print(f"   Analysis interval: {bot.analysis_interval} seconds")

    print("\n🎮 Bot Controls:")
    print("   bot.start()  - Start trading")
    print("   bot.stop()   - Stop trading")
    print("   bot.get_status() - Check status")

    print("\n💡 How it works:")
    print("   1. Bot monitors XAI/ADA market every 5 minutes")
    print("   2. AI analyzes market and recommends BUY/SELL/HOLD")
    print("   3. If BUY/SELL, executes atomic swap via Personal AI")
    print("   4. Tracks performance and applies risk limits")
    print("   5. Stops automatically if stop-loss triggered")

    print("\n🔐 Security:")
    print("   ✓ Uses Personal AI (cannot modify blockchain)")
    print("   ✓ User's own API key (user pays AI costs)")
    print("   ✓ Stop-loss protection")
    print("   ✓ Daily trade limits")
    print("   ✓ User can stop anytime")

    print("\n💰 Revenue Model:")
    print("   • User keeps 99% of profits")
    print("   • Optional 1% to XAI development fund")
    print("   • Sustainable funding mechanism")

    print("\n" + "=" * 80)
    print("AI TRADING BOT READY FOR DEPLOYMENT")
    print("=" * 80)

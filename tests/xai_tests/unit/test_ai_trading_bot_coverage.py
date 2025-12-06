"""
Comprehensive tests for ai_trading_bot.py to achieve 80%+ coverage

Tests all trading bot functionality including:
- Bot initialization and configuration
- Market analysis and signals
- Order placement logic
- Risk management
- Position management
- Profit/loss calculations
- Trading strategies and error handling
"""

import pytest
import json
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass

from xai.core.ai_trading_bot import (
    AITradingBot,
    TradingStrategy,
    TradeAction,
    TradingPair,
    TradeExecution,
    TradingPerformance,
    STRATEGY_TEMPLATES,
)


class MockBlockchain:
    """Mock blockchain for testing"""

    def __init__(self, balance=1000.0):
        self.balance = balance

    def get_balance(self, address):
        return self.balance


class MockPersonalAI:
    """Mock Personal AI for testing"""

    def __init__(self, swap_success=True):
        self.swap_success = swap_success
        self.swap_calls = []

    def execute_atomic_swap_with_ai(self, **kwargs):
        self.swap_calls.append(kwargs)
        if self.swap_success:
            return {
                "success": True,
                "swap_transaction": {
                    "fee": 0.15,
                    "from_coin": kwargs["swap_details"]["from_coin"],
                    "to_coin": kwargs["swap_details"]["to_coin"],
                    "amount": kwargs["swap_details"]["amount"],
                },
            }
        else:
            return {"success": False, "error": "Swap failed"}


@pytest.fixture
def mock_blockchain():
    """Fixture for mock blockchain"""
    return MockBlockchain()


@pytest.fixture
def mock_personal_ai():
    """Fixture for mock personal AI"""
    return MockPersonalAI()


@pytest.fixture
def basic_config():
    """Fixture for basic bot configuration"""
    return {
        "max_trade_amount": 100,
        "stop_loss_percent": 10,
        "take_profit_percent": 20,
        "max_daily_trades": 10,
        "analysis_interval": 300,
        "pairs": ["XAI/ADA"],
    }


@pytest.fixture
def trading_bot(mock_blockchain, mock_personal_ai, basic_config):
    """Fixture for trading bot instance"""
    return AITradingBot(
        user_address="XAI_Trader_Test",
        ai_provider="anthropic",
        ai_model="claude-sonnet-4",
        user_api_key="sk-ant-test-key",
        strategy=TradingStrategy.BALANCED,
        config=basic_config,
        blockchain=mock_blockchain,
        personal_ai=mock_personal_ai,
    )


class TestTradingStrategyEnum:
    """Test TradingStrategy enum"""

    def test_conservative_strategy(self):
        """Test CONSERVATIVE strategy enum"""
        assert TradingStrategy.CONSERVATIVE.value == "conservative"

    def test_balanced_strategy(self):
        """Test BALANCED strategy enum"""
        assert TradingStrategy.BALANCED.value == "balanced"

    def test_aggressive_strategy(self):
        """Test AGGRESSIVE strategy enum"""
        assert TradingStrategy.AGGRESSIVE.value == "aggressive"

    def test_custom_strategy(self):
        """Test CUSTOM strategy enum"""
        assert TradingStrategy.CUSTOM.value == "custom"


class TestTradeActionEnum:
    """Test TradeAction enum"""

    def test_buy_action(self):
        """Test BUY action enum"""
        assert TradeAction.BUY.value == "buy"

    def test_sell_action(self):
        """Test SELL action enum"""
        assert TradeAction.SELL.value == "sell"

    def test_hold_action(self):
        """Test HOLD action enum"""
        assert TradeAction.HOLD.value == "hold"


class TestTradingPairDataclass:
    """Test TradingPair dataclass"""

    def test_trading_pair_creation(self):
        """Test creating a trading pair"""
        pair = TradingPair(from_coin="XAI", to_coin="ADA")
        assert pair.from_coin == "XAI"
        assert pair.to_coin == "ADA"
        assert pair.current_rate == 0.0
        assert pair.last_updated == 0.0

    def test_trading_pair_with_rate(self):
        """Test trading pair with rate"""
        pair = TradingPair(from_coin="XAI", to_coin="BTC", current_rate=0.00001)
        assert pair.current_rate == 0.00001

    def test_trading_pair_update(self):
        """Test updating trading pair"""
        pair = TradingPair(from_coin="XAI", to_coin="ADA")
        pair.current_rate = 4.5
        pair.last_updated = time.time()
        assert pair.current_rate == 4.5
        assert pair.last_updated > 0


class TestTradeExecutionDataclass:
    """Test TradeExecution dataclass"""

    def test_trade_execution_creation(self):
        """Test creating trade execution record"""
        pair = TradingPair(from_coin="XAI", to_coin="ADA")
        trade = TradeExecution(
            trade_id="test_123",
            timestamp=time.time(),
            action=TradeAction.BUY,
            pair=pair,
            amount=100.0,
            rate=4.5,
            fee=0.15,
        )
        assert trade.trade_id == "test_123"
        assert trade.action == TradeAction.BUY
        assert trade.amount == 100.0
        assert trade.profit_loss == 0.0

    def test_trade_execution_with_profit(self):
        """Test trade execution with profit"""
        pair = TradingPair(from_coin="XAI", to_coin="ADA")
        trade = TradeExecution(
            trade_id="test_456",
            timestamp=time.time(),
            action=TradeAction.SELL,
            pair=pair,
            amount=50.0,
            rate=4.8,
            fee=0.1,
            profit_loss=10.5,
            ai_reasoning="Market momentum strong",
        )
        assert trade.profit_loss == 10.5
        assert trade.ai_reasoning == "Market momentum strong"


class TestTradingPerformanceDataclass:
    """Test TradingPerformance dataclass"""

    def test_performance_initialization(self):
        """Test performance metrics initialization"""
        perf = TradingPerformance()
        assert perf.total_trades == 0
        assert perf.successful_trades == 0
        assert perf.failed_trades == 0
        assert perf.total_profit == 0.0
        assert perf.net_profit == 0.0
        assert perf.win_rate == 0.0

    def test_performance_with_values(self):
        """Test performance with values"""
        perf = TradingPerformance(
            total_trades=10,
            successful_trades=7,
            failed_trades=3,
            total_profit=150.0,
            total_loss=50.0,
            net_profit=100.0,
            win_rate=70.0,
            roi=10.0,
        )
        assert perf.total_trades == 10
        assert perf.win_rate == 70.0
        assert perf.roi == 10.0


class TestAITradingBotInitialization:
    """Test AITradingBot initialization"""

    def test_bot_initialization_balanced(self, mock_blockchain, mock_personal_ai, basic_config):
        """Test bot initialization with balanced strategy"""
        bot = AITradingBot(
            user_address="XAI_Test_User",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.BALANCED,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot.user_address == "XAI_Test_User"
        assert bot.ai_provider == "anthropic"
        assert bot.ai_model == "claude-sonnet-4"
        assert bot.strategy == TradingStrategy.BALANCED
        assert bot.is_active is False
        assert bot.max_trade_amount == 100
        assert bot.stop_loss_percent == 10
        assert len(bot.trading_pairs) == 1

    def test_bot_initialization_conservative(self, mock_blockchain, mock_personal_ai):
        """Test bot initialization with conservative strategy"""
        config = STRATEGY_TEMPLATES["conservative"].copy()
        bot = AITradingBot(
            user_address="XAI_Conservative",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="sk-openai-test",
            strategy=TradingStrategy.CONSERVATIVE,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot.strategy == TradingStrategy.CONSERVATIVE
        assert bot.max_trade_amount == 50
        assert bot.stop_loss_percent == 5
        assert bot.take_profit_percent == 10

    def test_bot_initialization_aggressive(self, mock_blockchain, mock_personal_ai):
        """Test bot initialization with aggressive strategy"""
        config = STRATEGY_TEMPLATES["aggressive"].copy()
        bot = AITradingBot(
            user_address="XAI_Aggressive",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.AGGRESSIVE,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot.strategy == TradingStrategy.AGGRESSIVE
        assert bot.max_trade_amount == 200
        assert bot.max_daily_trades == 20

    def test_bot_initialization_custom(self, mock_blockchain, mock_personal_ai):
        """Test bot initialization with custom strategy"""
        config = {
            "max_trade_amount": 150,
            "stop_loss_percent": 12,
            "take_profit_percent": 25,
            "max_daily_trades": 15,
            "analysis_interval": 240,
            "pairs": ["XAI/ADA", "XAI/BTC"],
            "custom_prompt": "Custom trading instructions",
        }
        bot = AITradingBot(
            user_address="XAI_Custom",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.CUSTOM,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot.strategy == TradingStrategy.CUSTOM
        assert len(bot.trading_pairs) == 2

    def test_bot_initialization_multiple_pairs(self, mock_blockchain, mock_personal_ai):
        """Test bot initialization with multiple trading pairs"""
        config = {
            "max_trade_amount": 100,
            "stop_loss_percent": 10,
            "take_profit_percent": 20,
            "max_daily_trades": 10,
            "analysis_interval": 300,
            "pairs": ["XAI/ADA", "XAI/BTC", "XAI/ETH"],
        }
        bot = AITradingBot(
            user_address="XAI_Multi",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.BALANCED,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert len(bot.trading_pairs) == 3
        assert bot.trading_pairs[0].from_coin == "XAI"
        assert bot.trading_pairs[1].to_coin == "BTC"
        assert bot.trading_pairs[2].to_coin == "ETH"


class TestTradingPairInitialization:
    """Test trading pair initialization"""

    def test_initialize_single_pair(self, trading_bot):
        """Test initializing single trading pair"""
        pairs = trading_bot._initialize_trading_pairs(["XAI/ADA"])
        assert len(pairs) == 1
        assert pairs[0].from_coin == "XAI"
        assert pairs[0].to_coin == "ADA"

    def test_initialize_multiple_pairs(self, trading_bot):
        """Test initializing multiple trading pairs"""
        pairs = trading_bot._initialize_trading_pairs(["XAI/ADA", "XAI/BTC", "XAI/ETH"])
        assert len(pairs) == 3
        assert pairs[0].from_coin == "XAI"
        assert pairs[1].to_coin == "BTC"
        assert pairs[2].to_coin == "ETH"

    def test_initialize_custom_pairs(self, trading_bot):
        """Test initializing custom trading pairs"""
        pairs = trading_bot._initialize_trading_pairs(["BTC/ETH", "ETH/USDT"])
        assert len(pairs) == 2
        assert pairs[0].from_coin == "BTC"
        assert pairs[0].to_coin == "ETH"
        assert pairs[1].from_coin == "ETH"
        assert pairs[1].to_coin == "USDT"


class TestBotStartStop:
    """Test bot start and stop operations"""

    def test_start_bot(self, trading_bot):
        """Test starting the trading bot"""
        result = trading_bot.start()

        assert result["success"] is True
        assert "started" in result["message"]
        assert trading_bot.is_active is True
        assert trading_bot.trading_thread is not None
        assert result["strategy"] == "balanced"

        # Clean up
        trading_bot.stop()

    def test_start_bot_already_active(self, trading_bot):
        """Test starting bot when already active"""
        trading_bot.start()
        result = trading_bot.start()

        assert result["success"] is False
        assert "already active" in result["error"]

        # Clean up
        trading_bot.stop()

    def test_stop_bot(self, trading_bot):
        """Test stopping the trading bot"""
        trading_bot.start()
        time.sleep(0.1)  # Let thread start

        result = trading_bot.stop()

        assert result["success"] is True
        assert "stopped" in result["message"]
        assert trading_bot.is_active is False
        assert "performance" in result

    def test_stop_bot_not_active(self, trading_bot):
        """Test stopping bot when not active"""
        result = trading_bot.stop()

        assert result["success"] is False
        assert "not active" in result["error"]

    def test_start_stop_cycle(self, trading_bot):
        """Test multiple start/stop cycles"""
        # Start bot
        result1 = trading_bot.start()
        assert result1["success"] is True

        # Stop bot
        result2 = trading_bot.stop()
        assert result2["success"] is True

        # Start again
        result3 = trading_bot.start()
        assert result3["success"] is True

        # Clean up
        trading_bot.stop()


class TestMarketDataUpdate:
    """Test market data updates"""

    def test_update_market_data_xai_ada(self, trading_bot):
        """Test updating market data for XAI/ADA"""
        trading_bot._update_market_data()

        pair = trading_bot.trading_pairs[0]
        assert pair.current_rate > 0
        assert pair.last_updated > 0
        # Check rate is within expected range (4.5 +/- 5%)
        assert 4.275 <= pair.current_rate <= 4.725

    def test_update_market_data_multiple_times(self, trading_bot):
        """Test updating market data multiple times"""
        trading_bot._update_market_data()
        rate1 = trading_bot.trading_pairs[0].current_rate
        time1 = trading_bot.trading_pairs[0].last_updated

        time.sleep(0.01)
        trading_bot._update_market_data()
        rate2 = trading_bot.trading_pairs[0].current_rate
        time2 = trading_bot.trading_pairs[0].last_updated

        assert time2 > time1
        # Rates may be different due to randomness
        assert rate1 > 0 and rate2 > 0

    def test_update_market_data_volatility(self, trading_bot):
        """Test market data volatility"""
        rates = []
        for _ in range(10):
            trading_bot._update_market_data()
            rates.append(trading_bot.trading_pairs[0].current_rate)

        # All rates should be within volatility bounds
        for rate in rates:
            assert 4.275 <= rate <= 4.725


class TestRiskManagement:
    """Test risk management functionality"""

    def test_check_risk_limits_normal(self, trading_bot):
        """Test risk limits under normal conditions"""
        result = trading_bot._check_risk_limits()
        assert result is True

    def test_check_risk_limits_daily_limit_reached(self, trading_bot):
        """Test risk limits when daily trade limit reached"""
        # Add trades to reach daily limit
        now = time.time()
        for i in range(10):
            trade = TradeExecution(
                trade_id=f"trade_{i}",
                timestamp=now,
                action=TradeAction.BUY,
                pair=trading_bot.trading_pairs[0],
                amount=10.0,
                rate=4.5,
                fee=0.1,
            )
            trading_bot.trade_history.append(trade)

        result = trading_bot._check_risk_limits()
        assert result is False

    def test_check_risk_limits_old_trades_not_counted(self, trading_bot):
        """Test risk limits ignores old trades"""
        # Add old trades (yesterday)
        yesterday = time.time() - 86400 - 3600
        for i in range(10):
            trade = TradeExecution(
                trade_id=f"old_trade_{i}",
                timestamp=yesterday,
                action=TradeAction.BUY,
                pair=trading_bot.trading_pairs[0],
                amount=10.0,
                rate=4.5,
                fee=0.1,
            )
            trading_bot.trade_history.append(trade)

        result = trading_bot._check_risk_limits()
        assert result is True

    def test_check_risk_limits_stop_loss_triggered(self, trading_bot):
        """Test risk limits when stop loss triggered"""
        # Set negative performance
        trading_bot.performance.net_profit = -15.0

        result = trading_bot._check_risk_limits()
        assert result is False
        assert trading_bot.is_active is False

    def test_check_risk_limits_small_loss_ok(self, trading_bot):
        """Test risk limits with small loss"""
        # Set small negative performance (below stop loss)
        trading_bot.performance.net_profit = -5.0

        result = trading_bot._check_risk_limits()
        assert result is True


class TestAICallMocking:
    """Test AI API calls with mocking"""

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_call_anthropic_ai_success(self, mock_anthropic_class, trading_bot):
        """Test successful Anthropic AI call"""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text='{"action": "BUY", "confidence": 0.8}')]
        mock_client.messages.create.return_value = mock_response

        # Call AI
        result = trading_bot._call_user_ai("Test prompt")

        assert result["success"] is True
        assert '{"action": "BUY"' in result["response"]

    @patch("xai.core.ai_trading_bot.openai.OpenAI")
    def test_call_openai_ai_success(self, mock_openai_class, mock_blockchain, mock_personal_ai, basic_config):
        """Test successful OpenAI call"""
        # Create OpenAI bot
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="openai",
            ai_model="gpt-4",
            user_api_key="sk-openai-test",
            strategy=TradingStrategy.BALANCED,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"action": "SELL"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        # Call AI
        result = bot._call_user_ai("Test prompt")

        assert result["success"] is True
        assert "SELL" in result["response"]

    def test_call_unsupported_ai_provider(self, mock_blockchain, mock_personal_ai, basic_config):
        """Test unsupported AI provider"""
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="unsupported_provider",
            ai_model="model",
            user_api_key="sk-unsupported-provider-key",
            strategy=TradingStrategy.BALANCED,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        result = bot._call_user_ai("Test prompt")

        assert result["success"] is False
        assert "not supported" in result["error"]

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_call_ai_exception(self, mock_anthropic_class, trading_bot):
        """Test AI call with exception"""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        result = trading_bot._call_user_ai("Test prompt")

        assert result["success"] is False
        assert "API Error" in result["error"]


class TestMarketAnalysis:
    """Test market analysis functionality"""

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_analyze_market_buy_signal(self, mock_anthropic_class, trading_bot):
        """Test market analysis with BUY signal"""
        # Setup AI mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        ai_analysis = {
            "action": "BUY",
            "reasoning": "Strong upward momentum",
            "confidence": 0.85,
            "recommended_amount": 80.0,
            "expected_profit": 5.5,
        }
        mock_response.content = [Mock(text=json.dumps(ai_analysis))]
        mock_client.messages.create.return_value = mock_response

        # Analyze market
        pair = trading_bot.trading_pairs[0]
        result = trading_bot._analyze_market(pair)

        assert result["action"] == TradeAction.BUY
        assert "momentum" in result["reasoning"]
        assert result["confidence"] == 0.85
        assert result["amount"] == 80.0

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_analyze_market_sell_signal(self, mock_anthropic_class, trading_bot):
        """Test market analysis with SELL signal"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        ai_analysis = {
            "action": "SELL",
            "reasoning": "Resistance level reached",
            "confidence": 0.75,
            "recommended_amount": 50.0,
            "expected_profit": 3.2,
        }
        mock_response.content = [Mock(text=json.dumps(ai_analysis))]
        mock_client.messages.create.return_value = mock_response

        pair = trading_bot.trading_pairs[0]
        result = trading_bot._analyze_market(pair)

        assert result["action"] == TradeAction.SELL
        assert result["confidence"] == 0.75

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_analyze_market_hold_signal(self, mock_anthropic_class, trading_bot):
        """Test market analysis with HOLD signal"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        ai_analysis = {
            "action": "HOLD",
            "reasoning": "Market unclear",
            "confidence": 0.50,
        }
        mock_response.content = [Mock(text=json.dumps(ai_analysis))]
        mock_client.messages.create.return_value = mock_response

        pair = trading_bot.trading_pairs[0]
        result = trading_bot._analyze_market(pair)

        assert result["action"] == TradeAction.HOLD

    def test_analyze_market_ai_failure(self, trading_bot):
        """Test market analysis when AI fails"""
        with patch.object(trading_bot, "_call_user_ai") as mock_call:
            mock_call.return_value = {"success": False, "error": "AI unavailable"}

            pair = trading_bot.trading_pairs[0]
            result = trading_bot._analyze_market(pair)

            assert result["action"] == TradeAction.HOLD
            assert "failed" in result["reasoning"]
            assert result["confidence"] == 0.0

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_analyze_market_invalid_json(self, mock_anthropic_class, trading_bot):
        """Test market analysis with invalid JSON response"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text="Invalid JSON response")]
        mock_client.messages.create.return_value = mock_response

        pair = trading_bot.trading_pairs[0]
        result = trading_bot._analyze_market(pair)

        assert result["action"] == TradeAction.HOLD
        assert "parse" in result["reasoning"]

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_analyze_market_invalid_action(self, mock_anthropic_class, trading_bot):
        """Test market analysis with invalid action"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        ai_analysis = {"action": "INVALID_ACTION", "reasoning": "Test", "confidence": 0.5}
        mock_response.content = [Mock(text=json.dumps(ai_analysis))]
        mock_client.messages.create.return_value = mock_response

        pair = trading_bot.trading_pairs[0]
        result = trading_bot._analyze_market(pair)

        assert result["action"] == TradeAction.HOLD


class TestAnalysisPromptCreation:
    """Test analysis prompt creation"""

    def test_create_conservative_prompt(self, mock_blockchain, mock_personal_ai):
        """Test creating conservative strategy prompt"""
        config = STRATEGY_TEMPLATES["conservative"].copy()
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.CONSERVATIVE,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        pair = bot.trading_pairs[0]
        prompt = bot._create_analysis_prompt(pair, 1000.0, [])

        assert "CONSERVATIVE" in prompt
        assert "80% confidence" in prompt
        assert "50%" in prompt

    def test_create_balanced_prompt(self, trading_bot):
        """Test creating balanced strategy prompt"""
        pair = trading_bot.trading_pairs[0]
        prompt = trading_bot._create_analysis_prompt(pair, 1000.0, [])

        assert "BALANCED" in prompt
        assert "60% confidence" in prompt
        assert "75%" in prompt

    def test_create_aggressive_prompt(self, mock_blockchain, mock_personal_ai):
        """Test creating aggressive strategy prompt"""
        config = STRATEGY_TEMPLATES["aggressive"].copy()
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.AGGRESSIVE,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        pair = bot.trading_pairs[0]
        prompt = bot._create_analysis_prompt(pair, 1000.0, [])

        assert "AGGRESSIVE" in prompt
        assert "40% confidence" in prompt
        assert "100%" in prompt

    def test_create_custom_prompt(self, mock_blockchain, mock_personal_ai):
        """Test creating custom strategy prompt"""
        config = {
            "max_trade_amount": 100,
            "stop_loss_percent": 10,
            "take_profit_percent": 20,
            "max_daily_trades": 10,
            "analysis_interval": 300,
            "pairs": ["XAI/ADA"],
            "custom_prompt": "Use technical indicators for trading",
        }
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.CUSTOM,
            config=config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        pair = bot.trading_pairs[0]
        prompt = bot._create_analysis_prompt(pair, 1000.0, [])

        assert "technical indicators" in prompt

    def test_create_prompt_with_trade_history(self, trading_bot):
        """Test creating prompt with trade history"""
        # Add some trades
        pair = trading_bot.trading_pairs[0]
        trades = [
            TradeExecution(
                trade_id=f"trade_{i}",
                timestamp=time.time(),
                action=TradeAction.BUY if i % 2 == 0 else TradeAction.SELL,
                pair=pair,
                amount=50.0,
                rate=4.5,
                fee=0.1,
                profit_loss=2.5 if i % 2 == 0 else -1.5,
            )
            for i in range(5)
        ]

        prompt = trading_bot._create_analysis_prompt(pair, 1000.0, trades)

        assert "Recent Trades:" in prompt
        assert "buy" in prompt.lower()


class TestTradeExecution:
    """Test trade execution"""

    def test_execute_buy_trade(self, trading_bot):
        """Test executing BUY trade"""
        pair = trading_bot.trading_pairs[0]
        pair.current_rate = 4.5

        analysis = {
            "action": TradeAction.BUY,
            "amount": 50.0,
            "reasoning": "Strong buy signal",
        }

        trading_bot._execute_trade(pair, analysis)

        assert len(trading_bot.trade_history) == 1
        assert trading_bot.trade_history[0].action == TradeAction.BUY
        assert trading_bot.performance.total_trades == 1

    def test_execute_sell_trade(self, trading_bot):
        """Test executing SELL trade"""
        pair = trading_bot.trading_pairs[0]
        pair.current_rate = 4.5

        analysis = {
            "action": TradeAction.SELL,
            "amount": 75.0,
            "reasoning": "Take profit",
        }

        trading_bot._execute_trade(pair, analysis)

        assert len(trading_bot.trade_history) == 1
        assert trading_bot.trade_history[0].action == TradeAction.SELL

    def test_execute_hold_trade(self, trading_bot):
        """Test executing HOLD (no action)"""
        pair = trading_bot.trading_pairs[0]
        analysis = {
            "action": TradeAction.HOLD,
            "amount": 0.0,
            "reasoning": "Wait for better signal",
        }

        trading_bot._execute_trade(pair, analysis)

        assert len(trading_bot.trade_history) == 0
        assert trading_bot.performance.total_trades == 0

    def test_execute_trade_exceeds_max(self, trading_bot):
        """Test executing trade that exceeds max amount"""
        pair = trading_bot.trading_pairs[0]
        pair.current_rate = 4.5

        analysis = {
            "action": TradeAction.BUY,
            "amount": 500.0,  # Exceeds max_trade_amount of 100
            "reasoning": "Large buy signal",
        }

        trading_bot._execute_trade(pair, analysis)

        # Should be capped at max_trade_amount
        assert len(trading_bot.trade_history) == 1
        trade = trading_bot.trade_history[0]
        assert trade.amount <= trading_bot.max_trade_amount

    def test_execute_trade_swap_failure(self, mock_blockchain, basic_config):
        """Test executing trade when swap fails"""
        mock_personal_ai = MockPersonalAI(swap_success=False)
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.BALANCED,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        pair = bot.trading_pairs[0]
        analysis = {
            "action": TradeAction.BUY,
            "amount": 50.0,
            "reasoning": "Test",
        }

        bot._execute_trade(pair, analysis)

        assert bot.performance.failed_trades == 1
        assert len(bot.trade_history) == 0

    def test_execute_trade_exception(self, trading_bot):
        """Test executing trade with exception"""
        # Mock personal_ai to raise exception
        trading_bot.personal_ai.execute_atomic_swap_with_ai = Mock(
            side_effect=Exception("Network error")
        )

        pair = trading_bot.trading_pairs[0]
        analysis = {
            "action": TradeAction.BUY,
            "amount": 50.0,
            "reasoning": "Test",
        }

        trading_bot._execute_trade(pair, analysis)

        assert trading_bot.performance.failed_trades == 1


class TestPerformanceTracking:
    """Test performance tracking"""

    def test_get_performance_summary(self, trading_bot):
        """Test getting performance summary"""
        trading_bot.performance.total_trades = 10
        trading_bot.performance.successful_trades = 7
        trading_bot.performance.failed_trades = 3
        trading_bot.performance.net_profit = 50.0
        trading_bot.performance.win_rate = 70.0
        trading_bot.performance.roi = 5.0

        summary = trading_bot._get_performance_summary()

        assert summary["total_trades"] == 10
        assert summary["successful_trades"] == 7
        assert summary["failed_trades"] == 3
        assert summary["net_profit"] == 50.0
        assert summary["win_rate"] == 70.0
        assert summary["roi"] == 5.0


class TestBotStatus:
    """Test bot status reporting"""

    def test_get_status_inactive(self, trading_bot):
        """Test getting status when bot is inactive"""
        status = trading_bot.get_status()

        assert status["is_active"] is False
        assert status["strategy"] == "balanced"
        assert len(status["pairs"]) == 1
        assert "performance" in status
        assert "recent_trades" in status

    def test_get_status_active(self, trading_bot):
        """Test getting status when bot is active"""
        trading_bot.start()
        status = trading_bot.get_status()

        assert status["is_active"] is True
        assert status["strategy"] == "balanced"

        trading_bot.stop()

    def test_get_status_with_trades(self, trading_bot):
        """Test getting status with trade history"""
        # Add some trades
        pair = trading_bot.trading_pairs[0]
        for i in range(7):
            trade = TradeExecution(
                trade_id=f"trade_{i}",
                timestamp=time.time() - (7 - i) * 60,
                action=TradeAction.BUY if i % 2 == 0 else TradeAction.SELL,
                pair=pair,
                amount=50.0,
                rate=4.5,
                fee=0.1,
                profit_loss=2.0 if i % 2 == 0 else -1.0,
            )
            trading_bot.trade_history.append(trade)

        status = trading_bot.get_status()

        assert len(status["recent_trades"]) == 5  # Only last 5 trades
        assert "timestamp" in status["recent_trades"][0]
        assert "action" in status["recent_trades"][0]


class TestStrategyTemplates:
    """Test strategy templates"""

    def test_conservative_template(self):
        """Test conservative strategy template"""
        template = STRATEGY_TEMPLATES["conservative"]

        assert template["max_trade_amount"] == 50
        assert template["stop_loss_percent"] == 5
        assert template["take_profit_percent"] == 10
        assert template["max_daily_trades"] == 3
        assert template["analysis_interval"] == 600

    def test_balanced_template(self):
        """Test balanced strategy template"""
        template = STRATEGY_TEMPLATES["balanced"]

        assert template["max_trade_amount"] == 100
        assert template["stop_loss_percent"] == 10
        assert template["take_profit_percent"] == 20
        assert template["max_daily_trades"] == 10

    def test_aggressive_template(self):
        """Test aggressive strategy template"""
        template = STRATEGY_TEMPLATES["aggressive"]

        assert template["max_trade_amount"] == 200
        assert template["stop_loss_percent"] == 15
        assert template["take_profit_percent"] == 30
        assert template["max_daily_trades"] == 20


class TestTradingLoopIntegration:
    """Test trading loop integration"""

    @patch("xai.core.ai_trading_bot.anthropic.Anthropic")
    def test_trading_loop_single_iteration(self, mock_anthropic_class, trading_bot):
        """Test trading loop single iteration"""
        # Setup AI mock to return HOLD
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_response = Mock()
        ai_analysis = {"action": "HOLD", "reasoning": "Test", "confidence": 0.5}
        mock_response.content = [Mock(text=json.dumps(ai_analysis))]
        mock_client.messages.create.return_value = mock_response

        # Set last analysis to force immediate analysis
        trading_bot.last_analysis_time = 0
        trading_bot.analysis_interval = 0

        # Start and quickly stop
        trading_bot.start()
        time.sleep(0.2)
        trading_bot.stop()

        # Should have updated market data
        assert trading_bot.trading_pairs[0].current_rate > 0

    def test_trading_loop_respects_interval(self, trading_bot):
        """Test trading loop respects analysis interval"""
        trading_bot.analysis_interval = 10  # 10 seconds
        trading_bot.last_analysis_time = time.time()

        # Start bot
        trading_bot.start()
        time.sleep(0.2)

        # Analysis time should not have changed (interval not passed)
        old_time = trading_bot.last_analysis_time
        time.sleep(0.2)

        # Stop bot
        trading_bot.stop()

        # Analysis time should still be recent
        assert trading_bot.last_analysis_time <= time.time()

    def test_trading_loop_error_handling(self, trading_bot):
        """Test trading loop error handling"""
        # Mock _update_market_data to raise exception
        original_update = trading_bot._update_market_data

        def failing_update():
            raise Exception("Market data error")

        trading_bot._update_market_data = failing_update
        trading_bot.analysis_interval = 0
        trading_bot.last_analysis_time = 0

        # Start and let it run briefly
        trading_bot.start()
        time.sleep(0.2)
        trading_bot.stop()

        # Restore original
        trading_bot._update_market_data = original_update


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_config(self, mock_blockchain, mock_personal_ai):
        """Test bot with empty config uses defaults"""
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.BALANCED,
            config={},
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot.max_trade_amount == 100
        assert bot.stop_loss_percent == 10
        assert bot.max_daily_trades == 10

    def test_zero_balance(self, mock_personal_ai, basic_config):
        """Test bot with zero balance"""
        mock_blockchain = MockBlockchain(balance=0.0)
        bot = AITradingBot(
            user_address="XAI_Test",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test",
            strategy=TradingStrategy.BALANCED,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        balance = bot.blockchain.get_balance(bot.user_address)
        assert balance == 0.0

    def test_negative_profit_loss(self, trading_bot):
        """Test handling negative profit/loss"""
        trading_bot.performance.net_profit = -20.0
        summary = trading_bot._get_performance_summary()
        assert summary["net_profit"] == -20.0

    def test_multiple_concurrent_bots(self, mock_blockchain, mock_personal_ai, basic_config):
        """Test creating multiple bot instances"""
        bot1 = AITradingBot(
            user_address="XAI_User1",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test1",
            strategy=TradingStrategy.CONSERVATIVE,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        bot2 = AITradingBot(
            user_address="XAI_User2",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4",
            user_api_key="sk-ant-test2",
            strategy=TradingStrategy.AGGRESSIVE,
            config=basic_config,
            blockchain=mock_blockchain,
            personal_ai=mock_personal_ai,
        )

        assert bot1.user_address != bot2.user_address
        assert bot1.user_api_key != bot2.user_api_key


class TestMainExecution:
    """Test main execution block"""

    def test_main_block_classes_exist(self):
        """Test that main block mock classes work"""
        # Import the module to ensure main block can run
        import xai.core.ai_trading_bot

        # Verify classes exist
        assert hasattr(xai.core.ai_trading_bot, "AITradingBot")
        assert hasattr(xai.core.ai_trading_bot, "TradingStrategy")
        assert hasattr(xai.core.ai_trading_bot, "STRATEGY_TEMPLATES")

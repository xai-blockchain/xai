"""
Unit tests for AI Safety Controls module

Tests emergency stop, personal AI cancellation, trading bot controls, and safety levels
"""

import pytest
import time
from xai.core.ai_safety_controls import (
    StopReason,
    AISafetyLevel,
    AISafetyControls,
)


class MockAITradingBot:
    """Mock trading bot for testing"""

    def __init__(self):
        self.is_active = True

    def stop(self):
        """Stop the bot"""
        self.is_active = False
        return {"success": True, "message": "Bot stopped"}


class MockBlockchain:
    """Mock blockchain"""

    def __init__(self):
        self.chain = []


class TestAISafetyControls:
    """Test AI safety control system"""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        return MockBlockchain()

    @pytest.fixture
    def safety(self, blockchain):
        """Create AISafetyControls instance"""
        return AISafetyControls(blockchain)

    def test_init(self, safety):
        """Test initialization"""
        assert safety.safety_level == AISafetyLevel.NORMAL
        assert safety.emergency_stop_active is False
        assert len(safety.personal_ai_requests) == 0
        assert len(safety.trading_bots) == 0

    def test_register_personal_ai_request(self, safety):
        """Test registering personal AI request"""
        success = safety.register_personal_ai_request(
            request_id="req_001",
            user_address="XAI_USER",
            operation="swap",
            ai_provider="openai",
            ai_model="gpt-4"
        )

        assert success is True
        assert "req_001" in safety.personal_ai_requests

    def test_register_personal_ai_request_during_emergency(self, safety):
        """Test registration blocked during emergency stop"""
        safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        success = safety.register_personal_ai_request(
            request_id="req_001",
            user_address="XAI_USER",
            operation="swap",
            ai_provider="openai",
            ai_model="gpt-4"
        )

        assert success is False

    def test_cancel_personal_ai_request(self, safety):
        """Test canceling personal AI request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )

        result = safety.cancel_personal_ai_request("req_001", "XAI_USER")

        assert result["success"] is True
        assert safety.is_request_cancelled("req_001")

    def test_cancel_personal_ai_request_not_found(self, safety):
        """Test canceling non-existent request"""
        result = safety.cancel_personal_ai_request("nonexistent", "XAI_USER")

        assert result["success"] is False

    def test_cancel_personal_ai_request_wrong_user(self, safety):
        """Test user cannot cancel another user's request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_OWNER", "swap", "openai", "gpt-4"
        )

        result = safety.cancel_personal_ai_request("req_001", "XAI_WRONG")

        assert result["success"] is False

    def test_complete_personal_ai_request(self, safety):
        """Test completing AI request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )

        safety.complete_personal_ai_request("req_001")

        assert safety.personal_ai_requests["req_001"]["status"] == "completed"

    def test_register_trading_bot(self, safety):
        """Test registering trading bot"""
        bot = MockAITradingBot()

        success = safety.register_trading_bot("XAI_USER", bot)

        assert success is True
        assert "XAI_USER" in safety.trading_bots

    def test_emergency_stop_trading_bot(self, safety):
        """Test emergency stop for trading bot"""
        bot = MockAITradingBot()
        safety.register_trading_bot("XAI_USER", bot)

        result = safety.emergency_stop_trading_bot("XAI_USER")

        assert result["success"] is True
        assert bot.is_active is False

    def test_emergency_stop_trading_bot_not_found(self, safety):
        """Test stopping non-existent bot"""
        result = safety.emergency_stop_trading_bot("XAI_UNKNOWN")

        assert result["success"] is False

    def test_stop_all_trading_bots(self, safety):
        """Test stopping all trading bots"""
        # Register multiple bots
        for i in range(3):
            bot = MockAITradingBot()
            safety.register_trading_bot(f"XAI_USER_{i}", bot)

        result = safety.stop_all_trading_bots(StopReason.EMERGENCY)

        assert result["success"] is True
        assert result["stopped_count"] == 3

    def test_authorize_safety_caller(self, safety):
        """Test authorizing safety caller"""
        result = safety.authorize_safety_caller("new_caller")

        assert result["success"] is True
        assert safety.is_authorized_caller("new_caller")

    def test_revoke_safety_caller(self, safety):
        """Test revoking safety caller"""
        safety.authorize_safety_caller("temp_caller")
        result = safety.revoke_safety_caller("temp_caller")

        assert result["success"] is True
        assert not safety.is_authorized_caller("temp_caller")

    def test_is_authorized_caller_system(self, safety):
        """Test system is authorized by default"""
        assert safety.is_authorized_caller("system") is True

    def test_register_governance_task(self, safety):
        """Test registering governance task"""
        success = safety.register_governance_task(
            task_id="task_001",
            proposal_id="prop_001",
            task_type="code_review",
            ai_count=5
        )

        assert success is True
        assert "task_001" in safety.governance_tasks

    def test_pause_governance_task(self, safety):
        """Test pausing governance task"""
        safety.register_governance_task("task_001", "prop_001", "review", 5)

        result = safety.pause_governance_task("task_001", "admin")

        assert result["success"] is True
        assert safety.is_task_paused("task_001")

    def test_resume_governance_task(self, safety):
        """Test resuming governance task"""
        safety.register_governance_task("task_001", "prop_001", "review", 5)
        safety.pause_governance_task("task_001", "admin")

        result = safety.resume_governance_task("task_001")

        assert result["success"] is True
        assert not safety.is_task_paused("task_001")

    def test_pause_governance_task_not_found(self, safety):
        """Test pausing non-existent task"""
        result = safety.pause_governance_task("nonexistent", "admin")

        assert result["success"] is False

    def test_activate_emergency_stop(self, safety):
        """Test activating emergency stop"""
        result = safety.activate_emergency_stop(
            StopReason.SECURITY_THREAT,
            details="Critical security issue",
            activator="system"
        )

        assert result["success"] is True
        assert safety.emergency_stop_active is True

    def test_activate_emergency_stop_unauthorized(self, safety):
        """Test unauthorized emergency stop"""
        result = safety.activate_emergency_stop(
            StopReason.EMERGENCY,
            activator="unauthorized_user"
        )

        assert result["success"] is False

    def test_activate_emergency_stop_stops_all(self, safety):
        """Test emergency stop halts all AI operations"""
        # Register various operations
        safety.register_personal_ai_request("req_001", "XAI_A", "swap", "openai", "gpt-4")
        safety.register_governance_task("task_001", "prop_001", "review", 5)
        bot = MockAITradingBot()
        safety.register_trading_bot("XAI_B", bot)

        result = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        assert result["success"] is True
        assert result["personal_ai_stopped"] == 1
        assert result["governance_tasks_paused"] == 1
        assert result["trading_bots_stopped"] == 1

    def test_deactivate_emergency_stop(self, safety):
        """Test deactivating emergency stop"""
        safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        result = safety.deactivate_emergency_stop("system")

        assert result["success"] is True
        assert safety.emergency_stop_active is False

    def test_deactivate_emergency_stop_not_active(self, safety):
        """Test deactivating when not active"""
        result = safety.deactivate_emergency_stop("system")

        assert result["success"] is False

    def test_set_safety_level(self, safety):
        """Test setting safety level"""
        result = safety.set_safety_level(AISafetyLevel.CAUTION, "system")

        assert result["success"] is True
        assert result["new_level"] == AISafetyLevel.CAUTION.value

    def test_set_safety_level_unauthorized(self, safety):
        """Test setting safety level without authorization"""
        result = safety.set_safety_level(AISafetyLevel.CAUTION, "unauthorized")

        assert result["success"] is False

    def test_set_safety_level_emergency_triggers_stop(self, safety):
        """Test emergency level triggers stop"""
        result = safety.set_safety_level(AISafetyLevel.EMERGENCY_STOP, "system")

        assert result["success"] is True
        assert safety.emergency_stop_active is True

    def test_get_status(self, safety):
        """Test getting safety status"""
        # Register some operations
        safety.register_personal_ai_request("req_001", "XAI_A", "swap", "openai", "gpt-4")
        bot = MockAITradingBot()
        safety.register_trading_bot("XAI_B", bot)

        status = safety.get_status()

        assert status["safety_level"] == AISafetyLevel.NORMAL.value
        assert status["emergency_stop_active"] is False
        assert status["personal_ai"]["total_requests"] == 1
        assert status["trading_bots"]["active_bots"] == 1

    def test_get_active_operations(self, safety):
        """Test getting active operations"""
        safety.register_personal_ai_request("req_001", "XAI_A", "swap", "openai", "gpt-4")
        safety.register_governance_task("task_001", "prop_001", "review", 5)

        operations = safety.get_active_operations()

        assert len(operations["personal_ai_requests"]) == 1
        assert len(operations["governance_tasks"]) == 1

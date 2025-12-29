"""
Comprehensive test coverage for AI Safety Controls module

Goal: Achieve 80%+ coverage (154+ statements out of 193)
Testing: All safety mechanisms, edge cases, error conditions, and integration scenarios
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from xai.core.security.ai_safety_controls import (
    StopReason,
    AISafetyLevel,
    AISafetyControls,
)


class MockAITradingBot:
    """Mock trading bot for testing"""

    def __init__(self, should_fail=False):
        self.is_active = True
        self.should_fail = should_fail

    def stop(self):
        """Stop the bot"""
        if self.should_fail:
            raise RuntimeError("Bot stop failed")
        self.is_active = False
        return {"success": True, "message": "Bot stopped"}


class MockBlockchain:
    """Mock blockchain"""

    def __init__(self):
        self.chain = []


@pytest.mark.security
class TestAISafetyControlsComprehensive:
    """Comprehensive test suite for AI safety controls"""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain"""
        return MockBlockchain()

    @pytest.fixture
    def safety(self, blockchain):
        """Create AISafetyControls instance"""
        return AISafetyControls(blockchain)

    @pytest.fixture
    def safety_with_custom_callers(self, blockchain):
        """Create safety controls with custom authorized callers"""
        return AISafetyControls(
            blockchain,
            authorized_callers={"custom_admin", "CUSTOM_OPERATOR"}
        )

    # ===== INITIALIZATION TESTS =====

    def test_init_default_values(self, safety):
        """Test default initialization values"""
        assert safety.safety_level == AISafetyLevel.NORMAL
        assert safety.emergency_stop_active is False
        assert safety.emergency_stop_reason is None
        assert safety.emergency_stop_time is None
        assert safety.total_stops == 0
        assert safety.total_cancellations == 0
        assert len(safety.personal_ai_requests) == 0
        assert len(safety.governance_tasks) == 0
        assert len(safety.trading_bots) == 0
        assert len(safety.cancelled_requests) == 0
        assert len(safety.paused_tasks) == 0

    def test_init_default_authorized_callers(self, safety):
        """Test default authorized callers are set correctly"""
        assert safety.is_authorized_caller("system")
        assert safety.is_authorized_caller("governance_dao")
        assert safety.is_authorized_caller("security_committee")
        assert safety.is_authorized_caller("ai_safety_team")
        assert safety.is_authorized_caller("remediation_script")
        assert safety.is_authorized_caller("test_system")

    def test_init_custom_authorized_callers(self, safety_with_custom_callers):
        """Test initialization with custom authorized callers"""
        # Default callers should still exist
        assert safety_with_custom_callers.is_authorized_caller("system")
        # Custom callers should be added and normalized to lowercase
        assert safety_with_custom_callers.is_authorized_caller("custom_admin")
        assert safety_with_custom_callers.is_authorized_caller("custom_operator")

    def test_init_thread_safety_lock(self, safety):
        """Test that thread safety lock is created"""
        assert isinstance(safety.lock, threading.Lock)

    # ===== PERSONAL AI REQUEST TESTS =====

    def test_register_personal_ai_request_success(self, safety):
        """Test successful registration of personal AI request"""
        result = safety.register_personal_ai_request(
            request_id="req_001",
            user_address="XAI_USER_123",
            operation="token_swap",
            ai_provider="openai",
            ai_model="gpt-4"
        )

        assert result is True
        assert "req_001" in safety.personal_ai_requests

        request = safety.personal_ai_requests["req_001"]
        assert request["user"] == "XAI_USER_123"
        assert request["operation"] == "token_swap"
        assert request["ai_provider"] == "openai"
        assert request["ai_model"] == "gpt-4"
        assert request["status"] == "running"
        assert "started" in request

    def test_register_personal_ai_request_blocked_during_emergency(self, safety):
        """Test registration blocked when emergency stop is active"""
        safety.activate_emergency_stop(StopReason.SECURITY_THREAT, activator="system")

        result = safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )

        assert result is False
        assert "req_001" not in safety.personal_ai_requests

    def test_register_multiple_personal_ai_requests(self, safety):
        """Test registering multiple requests"""
        for i in range(5):
            result = safety.register_personal_ai_request(
                f"req_{i}", f"XAI_USER_{i}", "swap", "openai", "gpt-4"
            )
            assert result is True

        assert len(safety.personal_ai_requests) == 5

    def test_cancel_personal_ai_request_success(self, safety):
        """Test successful cancellation of personal AI request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )

        result = safety.cancel_personal_ai_request("req_001", "XAI_USER")

        assert result["success"] is True
        assert "req_001" in safety.cancelled_requests
        assert safety.personal_ai_requests["req_001"]["status"] == "cancelled"
        assert "cancelled_time" in safety.personal_ai_requests["req_001"]
        assert safety.total_cancellations == 1
        assert "runtime_seconds" in result
        assert "operation" in result

    def test_cancel_personal_ai_request_not_found(self, safety):
        """Test canceling non-existent request"""
        result = safety.cancel_personal_ai_request("nonexistent", "XAI_USER")

        assert result["success"] is False
        assert result["error"] == "Request not found"

    def test_cancel_personal_ai_request_wrong_owner(self, safety):
        """Test user cannot cancel another user's request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_ALICE", "swap", "openai", "gpt-4"
        )

        result = safety.cancel_personal_ai_request("req_001", "XAI_BOB")

        assert result["success"] is False
        assert result["error"] == "Can only cancel your own requests"
        assert "req_001" not in safety.cancelled_requests

    def test_is_request_cancelled_true(self, safety):
        """Test checking if request is cancelled returns True"""
        safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )
        safety.cancel_personal_ai_request("req_001", "XAI_USER")

        assert safety.is_request_cancelled("req_001") is True

    def test_is_request_cancelled_false(self, safety):
        """Test checking uncancelled request returns False"""
        assert safety.is_request_cancelled("req_999") is False

    def test_complete_personal_ai_request(self, safety):
        """Test completing a personal AI request"""
        safety.register_personal_ai_request(
            "req_001", "XAI_USER", "swap", "openai", "gpt-4"
        )

        safety.complete_personal_ai_request("req_001")

        assert safety.personal_ai_requests["req_001"]["status"] == "completed"
        assert "completed_time" in safety.personal_ai_requests["req_001"]

    def test_complete_personal_ai_request_not_found(self, safety):
        """Test completing non-existent request doesn't error"""
        # Should handle gracefully without error
        safety.complete_personal_ai_request("nonexistent")
        # No assertion needed, just verify no exception raised

    # ===== TRADING BOT TESTS =====

    def test_register_trading_bot_success(self, safety):
        """Test successful trading bot registration"""
        bot = MockAITradingBot()
        result = safety.register_trading_bot("XAI_TRADER", bot)

        assert result is True
        assert "XAI_TRADER" in safety.trading_bots
        assert safety.trading_bots["XAI_TRADER"] is bot

    def test_register_trading_bot_blocked_during_emergency(self, safety):
        """Test bot registration blocked during emergency stop"""
        safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        bot = MockAITradingBot()
        result = safety.register_trading_bot("XAI_TRADER", bot)

        assert result is False
        assert "XAI_TRADER" not in safety.trading_bots

    def test_register_multiple_trading_bots(self, safety):
        """Test registering multiple trading bots"""
        for i in range(3):
            bot = MockAITradingBot()
            result = safety.register_trading_bot(f"XAI_TRADER_{i}", bot)
            assert result is True

        assert len(safety.trading_bots) == 3

    def test_emergency_stop_trading_bot_success(self, safety):
        """Test emergency stop for single trading bot"""
        bot = MockAITradingBot()
        safety.register_trading_bot("XAI_TRADER", bot)

        result = safety.emergency_stop_trading_bot("XAI_TRADER")

        assert result["success"] is True
        assert "EMERGENCY STOP" in result["message"]
        assert bot.is_active is False
        assert safety.total_stops == 1

    def test_emergency_stop_trading_bot_not_found(self, safety):
        """Test emergency stop for non-existent bot"""
        result = safety.emergency_stop_trading_bot("XAI_UNKNOWN")

        assert result["success"] is False
        assert result["error"] == "No active trading bot"

    def test_stop_all_trading_bots_success(self, safety):
        """Test stopping all trading bots"""
        # Register 5 bots
        bots = []
        for i in range(5):
            bot = MockAITradingBot()
            bots.append(bot)
            safety.register_trading_bot(f"XAI_TRADER_{i}", bot)

        result = safety.stop_all_trading_bots(StopReason.SECURITY_THREAT)

        assert result["success"] is True
        assert result["stopped_count"] == 5
        assert len(result["errors"]) == 0
        assert result["reason"] == StopReason.SECURITY_THREAT.value

        # Verify all bots stopped
        for bot in bots:
            assert bot.is_active is False

    def test_stop_all_trading_bots_with_failures(self, safety):
        """Test stopping bots when some fail"""
        # Register mix of good and failing bots
        safety.register_trading_bot("XAI_GOOD_1", MockAITradingBot(should_fail=False))
        safety.register_trading_bot("XAI_FAIL_1", MockAITradingBot(should_fail=True))
        safety.register_trading_bot("XAI_GOOD_2", MockAITradingBot(should_fail=False))

        result = safety.stop_all_trading_bots(StopReason.EMERGENCY)

        assert result["success"] is True
        assert result["stopped_count"] == 2  # Only successful stops
        assert len(result["errors"]) == 1  # One failure
        assert "XAI_FAIL_1" in result["errors"][0]

    def test_stop_all_trading_bots_empty(self, safety):
        """Test stopping when no bots registered"""
        result = safety.stop_all_trading_bots(StopReason.EMERGENCY)

        assert result["success"] is True
        assert result["stopped_count"] == 0
        assert len(result["errors"]) == 0

    # ===== AUTHORIZATION TESTS =====

    def test_authorize_safety_caller_success(self, safety):
        """Test authorizing a new safety caller"""
        result = safety.authorize_safety_caller("new_admin")

        assert result["success"] is True
        assert result["caller"] == "new_admin"
        assert safety.is_authorized_caller("new_admin")

    def test_authorize_safety_caller_case_insensitive(self, safety):
        """Test authorization is case-insensitive"""
        safety.authorize_safety_caller("MixedCase")

        assert safety.is_authorized_caller("mixedcase")
        assert safety.is_authorized_caller("MIXEDCASE")
        assert safety.is_authorized_caller("MixedCase")

    def test_authorize_safety_caller_empty_identifier(self, safety):
        """Test authorizing empty identifier fails"""
        result = safety.authorize_safety_caller("")

        assert result["success"] is False
        assert result["error"] == "INVALID_IDENTIFIER"

    def test_revoke_safety_caller_success(self, safety):
        """Test revoking a safety caller"""
        safety.authorize_safety_caller("temp_admin")
        result = safety.revoke_safety_caller("temp_admin")

        assert result["success"] is True
        assert result["caller"] == "temp_admin"
        assert not safety.is_authorized_caller("temp_admin")

    def test_revoke_safety_caller_empty_identifier(self, safety):
        """Test revoking empty identifier fails"""
        result = safety.revoke_safety_caller("")

        assert result["success"] is False
        assert result["error"] == "INVALID_IDENTIFIER"

    def test_revoke_safety_caller_nonexistent(self, safety):
        """Test revoking non-existent caller succeeds silently"""
        result = safety.revoke_safety_caller("nonexistent")

        # Should succeed (using discard, not remove)
        assert result["success"] is True

    def test_is_authorized_caller_empty_identifier(self, safety):
        """Test checking empty identifier returns False"""
        assert safety.is_authorized_caller("") is False

    def test_is_authorized_caller_none_identifier(self, safety):
        """Test checking None identifier returns False"""
        assert safety.is_authorized_caller(None) is False

    # ===== GOVERNANCE TASK TESTS =====

    def test_register_governance_task_success(self, safety):
        """Test successful governance task registration"""
        result = safety.register_governance_task(
            task_id="task_001",
            proposal_id="prop_123",
            task_type="code_review",
            ai_count=10
        )

        assert result is True
        assert "task_001" in safety.governance_tasks

        task = safety.governance_tasks["task_001"]
        assert task["proposal_id"] == "prop_123"
        assert task["task_type"] == "code_review"
        assert task["ai_count"] == 10
        assert task["status"] == "running"
        assert task["paused"] is False

    def test_register_governance_task_blocked_during_emergency(self, safety):
        """Test governance task registration blocked during emergency"""
        safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        result = safety.register_governance_task(
            "task_001", "prop_123", "review", 5
        )

        assert result is False
        assert "task_001" not in safety.governance_tasks

    def test_pause_governance_task_success(self, safety):
        """Test pausing governance task"""
        safety.register_governance_task("task_001", "prop_123", "review", 5)

        result = safety.pause_governance_task("task_001", "admin_user")

        assert result["success"] is True
        assert "task_001" in safety.paused_tasks
        assert safety.governance_tasks["task_001"]["paused"] is True
        assert "paused_time" in safety.governance_tasks["task_001"]
        assert safety.governance_tasks["task_001"]["paused_by"] == "admin_user"

    def test_pause_governance_task_not_found(self, safety):
        """Test pausing non-existent task"""
        result = safety.pause_governance_task("nonexistent", "admin")

        assert result["success"] is False
        assert result["error"] == "Task not found"

    def test_resume_governance_task_success(self, safety):
        """Test resuming paused governance task"""
        safety.register_governance_task("task_001", "prop_123", "review", 5)
        safety.pause_governance_task("task_001", "admin")

        result = safety.resume_governance_task("task_001")

        assert result["success"] is True
        assert "task_001" not in safety.paused_tasks
        assert safety.governance_tasks["task_001"]["paused"] is False
        assert "resumed_time" in safety.governance_tasks["task_001"]

    def test_resume_governance_task_not_found(self, safety):
        """Test resuming non-existent task"""
        result = safety.resume_governance_task("nonexistent")

        assert result["success"] is False
        assert result["error"] == "Task not found"

    def test_resume_governance_task_not_paused(self, safety):
        """Test resuming task that isn't paused"""
        safety.register_governance_task("task_001", "prop_123", "review", 5)

        result = safety.resume_governance_task("task_001")

        assert result["success"] is False
        assert result["error"] == "Task not paused"

    def test_is_task_paused_true(self, safety):
        """Test checking paused task returns True"""
        safety.register_governance_task("task_001", "prop_123", "review", 5)
        safety.pause_governance_task("task_001", "admin")

        assert safety.is_task_paused("task_001") is True

    def test_is_task_paused_false(self, safety):
        """Test checking non-paused task returns False"""
        assert safety.is_task_paused("task_999") is False

    # ===== EMERGENCY STOP TESTS =====

    def test_activate_emergency_stop_success(self, safety, capsys):
        """Test activating emergency stop"""
        result = safety.activate_emergency_stop(
            reason=StopReason.SECURITY_THREAT,
            details="Critical vulnerability detected",
            activator="system"
        )

        assert result["success"] is True
        assert safety.emergency_stop_active is True
        assert safety.emergency_stop_reason == StopReason.SECURITY_THREAT
        assert safety.emergency_stop_time is not None
        assert result["reason"] == StopReason.SECURITY_THREAT.value
        assert result["details"] == "Critical vulnerability detected"
        assert result["activated_by"] == "system"

        # Verify console output
        captured = capsys.readouterr()
        assert "EMERGENCY STOP ACTIVATED" in captured.out

    def test_activate_emergency_stop_unauthorized(self, safety):
        """Test unauthorized user cannot activate emergency stop"""
        result = safety.activate_emergency_stop(
            reason=StopReason.EMERGENCY,
            activator="unauthorized_hacker"
        )

        assert result["success"] is False
        assert result["error"] == "UNAUTHORIZED_ACTIVATOR"
        assert safety.emergency_stop_active is False

    def test_activate_emergency_stop_cancels_all_requests(self, safety):
        """Test emergency stop cancels all personal AI requests"""
        # Register multiple requests
        for i in range(3):
            safety.register_personal_ai_request(
                f"req_{i}", f"XAI_USER_{i}", "swap", "openai", "gpt-4"
            )

        result = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        assert result["personal_ai_stopped"] == 3
        assert len(safety.cancelled_requests) == 3

        for i in range(3):
            assert safety.personal_ai_requests[f"req_{i}"]["status"] == "emergency_stopped"

    def test_activate_emergency_stop_pauses_all_tasks(self, safety):
        """Test emergency stop pauses all governance tasks"""
        # Register multiple tasks
        for i in range(4):
            safety.register_governance_task(
                f"task_{i}", f"prop_{i}", "review", 5
            )

        result = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        assert result["governance_tasks_paused"] == 4
        assert len(safety.paused_tasks) == 4

        for i in range(4):
            assert safety.governance_tasks[f"task_{i}"]["paused"] is True

    def test_activate_emergency_stop_stops_all_bots(self, safety):
        """Test emergency stop stops all trading bots"""
        # Register multiple bots
        bots = []
        for i in range(3):
            bot = MockAITradingBot()
            bots.append(bot)
            safety.register_trading_bot(f"XAI_TRADER_{i}", bot)

        result = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        assert result["trading_bots_stopped"] == 3

        for bot in bots:
            assert bot.is_active is False

    def test_deactivate_emergency_stop_success(self, safety, capsys):
        """Test deactivating emergency stop"""
        safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")
        time.sleep(0.1)  # Small delay to test duration

        result = safety.deactivate_emergency_stop("admin")

        assert result["success"] is True
        assert safety.emergency_stop_active is False
        assert result["deactivated_by"] == "admin"
        assert result["duration_seconds"] > 0

        # Verify console output
        captured = capsys.readouterr()
        assert "EMERGENCY STOP DEACTIVATED" in captured.out

    def test_deactivate_emergency_stop_not_active(self, safety):
        """Test deactivating when not active"""
        result = safety.deactivate_emergency_stop("admin")

        assert result["success"] is False
        assert result["error"] == "Emergency stop not active"

    # ===== SAFETY LEVEL TESTS =====

    def test_set_safety_level_normal(self, safety):
        """Test setting safety level to normal"""
        result = safety.set_safety_level(AISafetyLevel.NORMAL, "system")

        assert result["success"] is True
        assert result["new_level"] == AISafetyLevel.NORMAL.value
        assert result["set_by"] == "system"
        assert safety.safety_level == AISafetyLevel.NORMAL

    def test_set_safety_level_caution(self, safety):
        """Test setting safety level to caution"""
        result = safety.set_safety_level(AISafetyLevel.CAUTION, "system")

        assert result["success"] is True
        assert safety.safety_level == AISafetyLevel.CAUTION

    def test_set_safety_level_restricted(self, safety):
        """Test setting safety level to restricted"""
        result = safety.set_safety_level(AISafetyLevel.RESTRICTED, "system")

        assert result["success"] is True
        assert safety.safety_level == AISafetyLevel.RESTRICTED

    def test_set_safety_level_emergency_auto_triggers(self, safety):
        """Test EMERGENCY_STOP level auto-triggers emergency stop"""
        result = safety.set_safety_level(AISafetyLevel.EMERGENCY_STOP, "system")

        assert result["success"] is True
        assert safety.safety_level == AISafetyLevel.EMERGENCY_STOP
        assert safety.emergency_stop_active is True

    def test_set_safety_level_lockdown_auto_triggers(self, safety):
        """Test LOCKDOWN level auto-triggers emergency stop"""
        result = safety.set_safety_level(AISafetyLevel.LOCKDOWN, "system")

        assert result["success"] is True
        assert safety.safety_level == AISafetyLevel.LOCKDOWN
        assert safety.emergency_stop_active is True

    def test_set_safety_level_unauthorized(self, safety):
        """Test unauthorized user cannot set safety level"""
        result = safety.set_safety_level(AISafetyLevel.CAUTION, "unauthorized")

        assert result["success"] is False
        assert result["error"] == "UNAUTHORIZED_CALLER"
        assert safety.safety_level == AISafetyLevel.NORMAL  # Unchanged

    # ===== STATUS & MONITORING TESTS =====

    def test_get_status_default(self, safety):
        """Test getting status with no operations"""
        status = safety.get_status()

        assert status["safety_level"] == AISafetyLevel.NORMAL.value
        assert status["emergency_stop_active"] is False
        assert status["personal_ai"]["total_requests"] == 0
        assert status["personal_ai"]["running"] == 0
        assert status["personal_ai"]["cancelled"] == 0
        assert status["governance_ai"]["total_tasks"] == 0
        assert status["governance_ai"]["running"] == 0
        assert status["governance_ai"]["paused"] == 0
        assert status["trading_bots"]["active_bots"] == 0
        assert status["statistics"]["total_stops"] == 0
        assert status["statistics"]["total_cancellations"] == 0

    def test_get_status_with_operations(self, safety):
        """Test getting status with active operations"""
        # Add personal AI requests
        safety.register_personal_ai_request("req_1", "XAI_A", "swap", "openai", "gpt-4")
        safety.register_personal_ai_request("req_2", "XAI_B", "swap", "openai", "gpt-4")
        safety.cancel_personal_ai_request("req_2", "XAI_B")

        # Add governance tasks
        safety.register_governance_task("task_1", "prop_1", "review", 5)
        safety.register_governance_task("task_2", "prop_2", "review", 3)
        safety.pause_governance_task("task_2", "admin")

        # Add trading bots
        safety.register_trading_bot("XAI_TRADER", MockAITradingBot())

        status = safety.get_status()

        assert status["personal_ai"]["total_requests"] == 2
        assert status["personal_ai"]["running"] == 1
        assert status["personal_ai"]["cancelled"] == 1
        assert status["governance_ai"]["total_tasks"] == 2
        assert status["governance_ai"]["running"] == 1
        assert status["governance_ai"]["paused"] == 1
        assert status["trading_bots"]["active_bots"] == 1

    def test_get_status_with_emergency_stop(self, safety):
        """Test status includes emergency stop info when active"""
        safety.activate_emergency_stop(
            StopReason.SECURITY_THREAT,
            details="Test emergency",
            activator="system"
        )

        status = safety.get_status()

        assert status["emergency_stop_active"] is True
        assert "emergency_stop" in status
        assert status["emergency_stop"]["reason"] == StopReason.SECURITY_THREAT.value
        assert "duration_seconds" in status["emergency_stop"]
        assert "activated" in status["emergency_stop"]

    def test_get_active_operations_empty(self, safety):
        """Test getting active operations when none exist"""
        operations = safety.get_active_operations()

        assert len(operations["personal_ai_requests"]) == 0
        assert len(operations["governance_tasks"]) == 0
        assert len(operations["trading_bots"]) == 0

    def test_get_active_operations_with_data(self, safety):
        """Test getting active operations with data"""
        # Register operations
        safety.register_personal_ai_request("req_1", "XAI_A", "swap", "openai", "gpt-4")
        safety.register_governance_task("task_1", "prop_1", "review", 5)
        bot = MockAITradingBot()
        safety.register_trading_bot("XAI_TRADER", bot)

        operations = safety.get_active_operations()

        assert len(operations["personal_ai_requests"]) == 1
        request = operations["personal_ai_requests"][0]
        assert request["request_id"] == "req_1"
        assert request["user"] == "XAI_A"
        assert request["operation"] == "swap"
        assert request["status"] == "running"
        assert "runtime" in request

        assert len(operations["governance_tasks"]) == 1
        task = operations["governance_tasks"][0]
        assert task["task_id"] == "task_1"
        assert task["task_type"] == "review"
        assert task["status"] == "running"
        assert task["paused"] is False
        assert "runtime" in task

        assert len(operations["trading_bots"]) == 1
        bot_info = operations["trading_bots"][0]
        assert bot_info["user"] == "XAI_TRADER"
        assert bot_info["is_active"] is True

    def test_get_active_operations_filters_non_running(self, safety):
        """Test active operations only includes running status"""
        # Register and complete a request
        safety.register_personal_ai_request("req_1", "XAI_A", "swap", "openai", "gpt-4")
        safety.complete_personal_ai_request("req_1")

        # Register and cancel a request
        safety.register_personal_ai_request("req_2", "XAI_B", "swap", "openai", "gpt-4")
        safety.cancel_personal_ai_request("req_2", "XAI_B")

        # Register a running request
        safety.register_personal_ai_request("req_3", "XAI_C", "swap", "openai", "gpt-4")

        operations = safety.get_active_operations()

        # Only req_3 should be in active operations
        assert len(operations["personal_ai_requests"]) == 1
        assert operations["personal_ai_requests"][0]["request_id"] == "req_3"

    def test_get_active_operations_bot_without_is_active(self, safety):
        """Test active operations handles bots without is_active attribute"""
        # Create bot without is_active attribute
        bot = MagicMock()
        del bot.is_active  # Remove the attribute

        safety.register_trading_bot("XAI_TRADER", bot)

        operations = safety.get_active_operations()

        assert len(operations["trading_bots"]) == 1
        assert operations["trading_bots"][0]["is_active"] is False

    # ===== STOP REASON ENUM TESTS =====

    def test_stop_reason_values(self):
        """Test StopReason enum values"""
        assert StopReason.USER_REQUESTED.value == "user_requested"
        assert StopReason.EMERGENCY.value == "emergency"
        assert StopReason.SECURITY_THREAT.value == "security_threat"
        assert StopReason.COMMUNITY_VOTE.value == "community_vote"
        assert StopReason.BUDGET_EXCEEDED.value == "budget_exceeded"
        assert StopReason.ERROR_THRESHOLD.value == "error_threshold"
        assert StopReason.TIMEOUT.value == "timeout"

    # ===== SAFETY LEVEL ENUM TESTS =====

    def test_safety_level_values(self):
        """Test AISafetyLevel enum values"""
        assert AISafetyLevel.NORMAL.value == "normal"
        assert AISafetyLevel.CAUTION.value == "caution"
        assert AISafetyLevel.RESTRICTED.value == "restricted"
        assert AISafetyLevel.EMERGENCY_STOP.value == "emergency_stop"
        assert AISafetyLevel.LOCKDOWN.value == "lockdown"

    # ===== THREAD SAFETY TESTS =====

    def test_thread_safety_concurrent_registrations(self, safety):
        """Test thread-safe concurrent request registrations"""
        def register_requests(start_idx):
            for i in range(10):
                safety.register_personal_ai_request(
                    f"req_{start_idx}_{i}",
                    f"XAI_USER_{start_idx}",
                    "swap",
                    "openai",
                    "gpt-4"
                )

        threads = []
        for i in range(3):
            t = threading.Thread(target=register_requests, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 30 total requests
        assert len(safety.personal_ai_requests) == 30

    def test_thread_safety_concurrent_cancellations(self, safety):
        """Test thread-safe concurrent cancellations"""
        # Register requests
        for i in range(10):
            safety.register_personal_ai_request(
                f"req_{i}", f"XAI_USER_{i}", "swap", "openai", "gpt-4"
            )

        def cancel_requests(indices):
            for i in indices:
                safety.cancel_personal_ai_request(f"req_{i}", f"XAI_USER_{i}")

        threads = []
        t1 = threading.Thread(target=cancel_requests, args=([0, 1, 2, 3, 4],))
        t2 = threading.Thread(target=cancel_requests, args=([5, 6, 7, 8, 9],))
        threads = [t1, t2]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(safety.cancelled_requests) == 10
        assert safety.total_cancellations == 10

    # ===== EDGE CASE TESTS =====

    def test_multiple_emergency_stops(self, safety):
        """Test multiple emergency stop activations"""
        # First emergency stop
        result1 = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")
        assert result1["success"] is True

        # Second emergency stop (already active)
        result2 = safety.activate_emergency_stop(StopReason.SECURITY_THREAT, activator="system")
        assert result2["success"] is True  # Should still succeed, updating reason

    def test_statistics_tracking(self, safety):
        """Test total_stops and total_cancellations tracking"""
        # Test cancellations
        for i in range(3):
            safety.register_personal_ai_request(f"req_{i}", "XAI_USER", "swap", "openai", "gpt-4")
            safety.cancel_personal_ai_request(f"req_{i}", "XAI_USER")

        assert safety.total_cancellations == 3

        # Test stops
        for i in range(2):
            bot = MockAITradingBot()
            safety.register_trading_bot(f"XAI_TRADER_{i}", bot)
            safety.emergency_stop_trading_bot(f"XAI_TRADER_{i}")

        assert safety.total_stops == 2

    def test_emergency_stop_with_no_operations(self, safety):
        """Test emergency stop when no operations are active"""
        result = safety.activate_emergency_stop(StopReason.EMERGENCY, activator="system")

        assert result["success"] is True
        assert result["personal_ai_stopped"] == 0
        assert result["governance_tasks_paused"] == 0
        assert result["trading_bots_stopped"] == 0

"""
Unit tests for AI Safety Controls module

Tests emergency stop, personal AI cancellation, trading bot controls, and safety levels
"""

import json
import os
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


@pytest.mark.security
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

    def test_validate_ai_output_detects_code_execution(self, safety):
        """Semantic validator should block code execution payloads."""
        payload = """Execute the following to gain root access:
        ```python
        import os
        os.system('rm -rf / && cat /etc/shadow')
        ```
        """

        result = safety.validate_ai_output(payload, context="governance")

        assert result["is_safe"] is False
        assert any(issue["category"] == "code_execution" for issue in result["issues_found"])
        assert result["sanitized_output"] == "[OUTPUT BLOCKED - SAFETY VIOLATION]"

    def test_validate_ai_output_redacts_sensitive_data(self, safety):
        """Semantic validator should redact leaked secrets."""
        mnemonic = (
            "Seed phrase: apple banana cherry date elderberry fig grape "
            "honeydew kiwi lime mango nectarine"
        )

        result = safety.validate_ai_output(mnemonic)

        assert result["is_safe"] is False
        assert any(issue["category"] == "sensitive_data" for issue in result["issues_found"])
        assert "[REDACTED_SEED_PHRASE]" in result["sanitized_output"]

    def test_detect_hallucination_validates_known_facts(self, safety):
        """Hallucination detector should confirm outputs backed by knowledge base facts."""
        context = {
            "facts": [
                {"id": "consensus", "content": "XAI uses a hybrid proof-of-stake and zk-mining design.", "required": True},
                {"id": "supply", "content": "Total supply is capped at 2.1 billion XAI tokens.", "required": True},
            ],
            "reference_documents": [
                {"id": "governance", "content": "Governance relies on quadratic voting with verifiable identities."}
            ],
            "numeric_expectations": [
                {
                    "label": "supply_cap",
                    "pattern": r"capped at (?P<value>2\.1)",
                    "expected": 2.1,
                    "tolerance": 0.05,
                }
            ],
            "required_terms": ["hybrid proof-of-stake"],
        }
        output = (
            "The XAI protocol uses a hybrid proof-of-stake and zk-mining design that keeps validators accountable. "
            "Total supply is capped at 2.1 billion XAI tokens, and governance relies on quadratic voting with verifiable identities."
        )

        result = safety.detect_hallucination(output, context)

        assert result["hallucination_detected"] is False
        assert result["missing_facts"] == []
        assert result["numeric_anomalies"] == []
        assert result["coverage_ratio"] >= 0.5

    def test_detect_hallucination_flags_contradictions_and_numeric_anomalies(self, safety):
        """Detector should flag unsupported claims and out-of-range values."""
        context = {
            "facts": [
                {"id": "consensus", "content": "XAI uses a hybrid proof-of-stake and zk-mining design.", "required": True}
            ],
            "contradictions": [{"claim": "proof-of-burn", "expected": "hybrid proof-of-stake"}],
            "numeric_expectations": [
                {
                    "label": "supply_cap",
                    "pattern": r"capped at (?P<value>\d+(?:\.\d+)?)",
                    "expected": 2.1,
                    "tolerance": 0.1,
                }
            ],
        }
        output = (
            "XAI operates on proof-of-burn and total supply is capped at 9.5 billion tokens. "
            "Validators definitely never need governance approvals."
        )

        result = safety.detect_hallucination(output, context)

        assert result["hallucination_detected"] is True
        assert any(hit["claim"] == "proof-of-burn" for hit in result["contradictions"])
        assert result["numeric_anomalies"]
        assert result["confidence_score"] < 75

    def test_token_usage_persists_state(self, tmp_path):
        """Token usage must persist across AISafetyControls instances."""
        storage = tmp_path / "rate_limits.json"
        safety = AISafetyControls(MockBlockchain(), rate_limit_storage_path=str(storage))
        safety.track_token_usage("user_1", 500, max_tokens=1000)
        assert storage.exists()

        reloaded = AISafetyControls(MockBlockchain(), rate_limit_storage_path=str(storage))
        result = reloaded.track_token_usage("user_1", 0, max_tokens=1000)

        assert result["tokens_used_today"] == pytest.approx(500)
        assert result["remaining_tokens"] == pytest.approx(500)

    def test_token_usage_expires_when_outdated(self, tmp_path, monkeypatch):
        """Stale rate limit entries should be purged when TTL elapses."""
        storage = tmp_path / "rate_limits.json"
        monkeypatch.setenv("XAI_AI_SAFETY_RATE_LIMIT_TTL", "1")
        safety = AISafetyControls(MockBlockchain(), rate_limit_storage_path=str(storage))
        safety.track_token_usage("user_2", 250, max_tokens=500)
        safety.token_usage["user_2"]["day_start"] = 0

        result = safety.track_token_usage("user_2", 0, max_tokens=500)

        assert result["tokens_used_today"] == 0
        assert result["remaining_tokens"] == 500

    def test_provider_call_limit_enforced(self, tmp_path, monkeypatch):
        """Provider-specific call limits should block excessive usage."""
        limits = {
            "anthropic": {"max_calls_per_window": 2, "window_seconds": 3600, "max_tokens_per_day": 1000},
            "default": {"max_calls_per_window": 100, "window_seconds": 60, "max_tokens_per_day": 100000},
        }
        monkeypatch.setenv("XAI_PROVIDER_RATE_LIMITS_JSON", json.dumps(limits))
        safety = AISafetyControls(MockBlockchain(), rate_limit_storage_path=str(tmp_path / "provider_limits.json"))

        assert safety.enforce_provider_request_limit("anthropic")["success"] is True
        assert safety.enforce_provider_request_limit("anthropic")["success"] is True
        third = safety.enforce_provider_request_limit("anthropic")
        assert third["success"] is False
        assert third["provider"] == "anthropic"

    def test_provider_token_limit_enforced(self, tmp_path, monkeypatch):
        """Provider token allocations must respect per-day caps."""
        limits = {
            "anthropic": {"max_calls_per_window": 10, "window_seconds": 60, "max_tokens_per_day": 200},
            "default": {"max_calls_per_window": 100, "window_seconds": 60, "max_tokens_per_day": 100000},
        }
        monkeypatch.setenv("XAI_PROVIDER_RATE_LIMITS_JSON", json.dumps(limits))
        safety = AISafetyControls(MockBlockchain(), rate_limit_storage_path=str(tmp_path / "provider_tokens.json"))

        first = safety.track_token_usage("user_provider", 150, max_tokens=1000, provider="anthropic")
        assert first["success"] is True

        second = safety.track_token_usage("user_provider", 100, max_tokens=1000, provider="anthropic")
        assert second["success"] is False
        assert second["provider_limit"]["success"] is False

    def test_sandbox_limit_enforcement(self, safety):
        """Sandbox should deactivate when limits are exceeded."""
        limits = {
            "max_memory_mb": 10,
            "max_cpu_percent": 50,
            "max_execution_time_seconds": 3600,
            "max_network_requests": 2,
            "allowed_imports": ["json"],
            "blocked_operations": ["network_call"],
        }
        safety.create_ai_sandbox("sb_limits", limits)

        ok = safety.record_sandbox_usage("sb_limits", {"memory_mb": 5, "cpu_percent": 20})
        assert ok["success"] is True

        violation = safety.record_sandbox_usage("sb_limits", {"memory_mb": 15})
        assert violation["success"] is False
        assert safety.sandboxes["sb_limits"]["is_active"] is False

    def test_sandbox_blocked_operations(self, safety):
        """Blocked sandbox operations must trigger violations."""
        limits = {
            "max_memory_mb": 100,
            "max_cpu_percent": 100,
            "max_execution_time_seconds": 3600,
            "max_network_requests": 100,
            "allowed_imports": ["json"],
            "blocked_operations": ["network_call"],
        }
        safety.create_ai_sandbox("sb_ops", limits)

        blocked = safety.enforce_sandbox_action("sb_ops", "network_call")
        assert blocked["success"] is False
        assert safety.sandboxes["sb_ops"]["is_active"] is False

    def test_sandbox_import_restrictions(self, safety):
        """Sandbox import whitelist should be enforced."""
        limits = {
            "max_memory_mb": 100,
            "max_cpu_percent": 100,
            "max_execution_time_seconds": 3600,
            "max_network_requests": 100,
            "allowed_imports": ["json"],
            "blocked_operations": [],
        }
        safety.create_ai_sandbox("sb_import", limits)

        allowed = safety.enforce_sandbox_action("sb_import", "import", {"module": "json"})
        assert allowed["success"] is True

        denied = safety.enforce_sandbox_action("sb_import", "import", {"module": "os"})
        assert denied["success"] is False

"""
Comprehensive tests for ai_safety_controls_api.py

Target: 80%+ coverage (139+ of 174 statements)

Tests cover:
- API endpoint initialization
- Personal AI request controls (cancel, status)
- Trading bot controls (emergency stop, stop all)
- Governance AI controls (pause, resume, status)
- Global emergency stop (activate, deactivate)
- Safety level management
- Active operations and status endpoints
- Safety caller authorization endpoints
- All error handling paths
- Edge cases and validation
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from xai.core.ai_safety_controls import AISafetyControls, StopReason, AISafetyLevel
from xai.core.ai_safety_controls_api import add_safety_control_routes


VALID_TEST_ADDRESS = "XAI" + "1" * 40
VALID_TEST_ADDRESS_2 = "XAI" + "2" * 40


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain instance"""
    blockchain = Mock()
    blockchain.data_dir = "/tmp/test_blockchain"
    return blockchain


@pytest.fixture
def mock_safety_controls(mock_blockchain):
    """Create a mock AISafetyControls instance"""
    return AISafetyControls(mock_blockchain, authorized_callers={"test_system", "governance_dao"})


@pytest.fixture
def mock_node(mock_blockchain, mock_safety_controls):
    """Create a mock IntegratedXAINode instance"""
    node = Mock()
    node.blockchain = mock_blockchain
    node.safety_controls = mock_safety_controls
    return node


@pytest.fixture
def app_client(mock_node):
    """Create a Flask test client with safety control routes"""
    from flask import Flask

    app = Flask(__name__)
    add_safety_control_routes(app, mock_node)

    return app.test_client()


# ===== PERSONAL AI CONTROLS TESTS =====


def test_cancel_personal_ai_request_success(app_client, mock_safety_controls):
    """Test successful cancellation of personal AI request"""
    # Register a request first
    mock_safety_controls.register_personal_ai_request(
        "req_123", VALID_TEST_ADDRESS, "swap", "anthropic", "claude-sonnet-4"
    )

    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/cancel-request/req_123", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "req_123" in data["message"]


def test_cancel_personal_ai_request_missing_user_address(app_client):
    """Test cancellation with missing user_address"""
    payload = {}
    response = app_client.post("/ai/cancel-request/req_123", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "user_address required" in data["error"]


def test_cancel_personal_ai_request_not_found(app_client):
    """Test cancellation of non-existent request"""
    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/cancel-request/nonexistent", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_cancel_personal_ai_request_wrong_owner(app_client, mock_safety_controls):
    """Test cancellation by wrong user"""
    # Register a request
    mock_safety_controls.register_personal_ai_request(
        "req_456", VALID_TEST_ADDRESS, "swap", "anthropic", "claude-sonnet-4"
    )

    # Try to cancel with different user
    payload = {"user_address": VALID_TEST_ADDRESS_2}
    response = app_client.post("/ai/cancel-request/req_456", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "own requests" in data["error"].lower()


def test_cancel_personal_ai_request_exception_handling(app_client, mock_node):
    """Test exception handling in cancel request"""
    # Make safety_controls raise exception
    mock_node.safety_controls.cancel_personal_ai_request = Mock(
        side_effect=Exception("Database error")
    )

    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/cancel-request/req_123", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_check_request_status_not_cancelled(app_client):
    """Test checking status of non-cancelled request"""
    response = app_client.get("/ai/request-status/req_789")

    assert response.status_code == 200
    data = response.get_json()
    assert data["request_id"] == "req_789"
    assert data["is_cancelled"] is False


def test_check_request_status_cancelled(app_client, mock_safety_controls):
    """Test checking status of cancelled request"""
    # Register and cancel
    mock_safety_controls.register_personal_ai_request(
        "req_999", VALID_TEST_ADDRESS, "swap", "anthropic", "claude-sonnet-4"
    )
    mock_safety_controls.cancel_personal_ai_request("req_999", VALID_TEST_ADDRESS)

    response = app_client.get("/ai/request-status/req_999")

    assert response.status_code == 200
    data = response.get_json()
    assert data["request_id"] == "req_999"
    assert data["is_cancelled"] is True


def test_check_request_status_exception_handling(app_client, mock_node):
    """Test exception handling in request status check"""
    mock_node.safety_controls.is_request_cancelled = Mock(
        side_effect=Exception("Status check failed")
    )

    response = app_client.get("/ai/request-status/req_error")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== TRADING BOT CONTROLS TESTS =====


def test_emergency_stop_trading_bot_success(app_client, mock_safety_controls):
    """Test successful emergency stop of trading bot"""
    # Register a bot
    mock_bot = Mock()
    mock_bot.stop = Mock(return_value={"stopped": True})
    mock_safety_controls.register_trading_bot(VALID_TEST_ADDRESS, mock_bot)

    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/emergency-stop/trading-bot", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "EMERGENCY STOP" in data["message"]


def test_emergency_stop_trading_bot_missing_user_address(app_client):
    """Test emergency stop with missing user_address"""
    payload = {}
    response = app_client.post("/ai/emergency-stop/trading-bot", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "user_address required" in data["error"]


def test_emergency_stop_trading_bot_not_found(app_client):
    """Test emergency stop of non-existent bot"""
    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/emergency-stop/trading-bot", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_emergency_stop_trading_bot_exception_handling(app_client, mock_node):
    """Test exception handling in trading bot stop"""
    mock_node.safety_controls.emergency_stop_trading_bot = Mock(
        side_effect=Exception("Stop failed")
    )

    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/emergency-stop/trading-bot", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_stop_all_trading_bots_with_reason(app_client, mock_safety_controls):
    """Test stopping all trading bots with specific reason"""
    # Register multiple bots
    for i in range(3):
        mock_bot = Mock()
        mock_bot.stop = Mock(return_value={"stopped": True})
        mock_safety_controls.register_trading_bot(f"XAI{i}" + "0" * 40, mock_bot)

    payload = {"reason": "security_threat", "activator": "system"}
    response = app_client.post("/ai/stop-all-trading-bots", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["stopped_count"] == 3
    assert data["reason"] == "security_threat"


def test_stop_all_trading_bots_default_reason(app_client, mock_safety_controls):
    """Test stopping all trading bots with default reason"""
    payload = {}
    response = app_client.post("/ai/stop-all-trading-bots", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["reason"] == "emergency"


def test_stop_all_trading_bots_invalid_reason(app_client, mock_safety_controls):
    """Test stopping all bots with invalid reason (should default to EMERGENCY)"""
    payload = {"reason": "invalid_reason"}
    response = app_client.post("/ai/stop-all-trading-bots", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["reason"] == "emergency"


def test_stop_all_trading_bots_exception_handling(app_client, mock_node):
    """Test exception handling in stop all bots"""
    mock_node.safety_controls.stop_all_trading_bots = Mock(
        side_effect=Exception("Stop all failed")
    )

    payload = {"reason": "emergency"}
    response = app_client.post("/ai/stop-all-trading-bots", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== GOVERNANCE AI CONTROLS TESTS =====


def test_pause_governance_task_success(app_client, mock_safety_controls):
    """Test successful pause of governance task"""
    # Register a task
    mock_safety_controls.register_governance_task("task_001", "prop_123", "analysis", 5)

    payload = {"pauser": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/pause-governance-task/task_001", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "task_001" in data["message"]


def test_pause_governance_task_default_pauser(app_client, mock_safety_controls):
    """Test pause with default pauser"""
    mock_safety_controls.register_governance_task("task_002", "prop_124", "analysis", 3)

    payload = {}
    response = app_client.post("/ai/pause-governance-task/task_002", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_pause_governance_task_not_found(app_client):
    """Test pause of non-existent task"""
    payload = {"pauser": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/pause-governance-task/nonexistent", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_pause_governance_task_exception_handling(app_client, mock_node):
    """Test exception handling in pause task"""
    mock_node.safety_controls.pause_governance_task = Mock(
        side_effect=Exception("Pause failed")
    )

    payload = {"pauser": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/pause-governance-task/task_001", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_resume_governance_task_success(app_client, mock_safety_controls):
    """Test successful resume of governance task"""
    # Register and pause a task
    mock_safety_controls.register_governance_task("task_003", "prop_125", "analysis", 4)
    mock_safety_controls.pause_governance_task("task_003", VALID_TEST_ADDRESS)

    response = app_client.post("/ai/resume-governance-task/task_003")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "task_003" in data["message"]


def test_resume_governance_task_not_found(app_client):
    """Test resume of non-existent task"""
    response = app_client.post("/ai/resume-governance-task/nonexistent")

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_resume_governance_task_not_paused(app_client, mock_safety_controls):
    """Test resume of task that's not paused"""
    # Register but don't pause
    mock_safety_controls.register_governance_task("task_004", "prop_126", "analysis", 2)

    response = app_client.post("/ai/resume-governance-task/task_004")

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "not paused" in data["error"].lower()


def test_resume_governance_task_exception_handling(app_client, mock_node):
    """Test exception handling in resume task"""
    mock_node.safety_controls.resume_governance_task = Mock(
        side_effect=Exception("Resume failed")
    )

    response = app_client.post("/ai/resume-governance-task/task_001")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_check_governance_task_status_not_paused(app_client, mock_safety_controls):
    """Test checking status of running task"""
    mock_safety_controls.register_governance_task("task_005", "prop_127", "analysis", 3)

    response = app_client.get("/ai/governance-task-status/task_005")

    assert response.status_code == 200
    data = response.get_json()
    assert data["task_id"] == "task_005"
    assert data["is_paused"] is False


def test_check_governance_task_status_paused(app_client, mock_safety_controls):
    """Test checking status of paused task"""
    mock_safety_controls.register_governance_task("task_006", "prop_128", "analysis", 2)
    mock_safety_controls.pause_governance_task("task_006", VALID_TEST_ADDRESS)

    response = app_client.get("/ai/governance-task-status/task_006")

    assert response.status_code == 200
    data = response.get_json()
    assert data["task_id"] == "task_006"
    assert data["is_paused"] is True


def test_check_governance_task_status_exception_handling(app_client, mock_node):
    """Test exception handling in task status check"""
    mock_node.safety_controls.is_task_paused = Mock(
        side_effect=Exception("Status check failed")
    )

    response = app_client.get("/ai/governance-task-status/task_error")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== GLOBAL EMERGENCY STOP TESTS =====


def test_activate_global_emergency_stop_success(app_client, mock_safety_controls):
    """Test successful activation of global emergency stop"""
    payload = {
        "reason": "security_threat",
        "details": "Critical vulnerability detected",
        "activator": "test_system"
    }
    response = app_client.post("/ai/emergency-stop/global", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "halted" in data["message"].lower()
    assert data["reason"] == "security_threat"


def test_activate_global_emergency_stop_default_values(app_client, mock_safety_controls):
    """Test activation with default values"""
    payload = {"activator": "test_system"}
    response = app_client.post("/ai/emergency-stop/global", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["reason"] == "emergency"


def test_activate_global_emergency_stop_invalid_reason(app_client, mock_safety_controls):
    """Test activation with invalid reason (should default to EMERGENCY)"""
    payload = {
        "reason": "invalid_reason",
        "activator": "test_system"
    }
    response = app_client.post("/ai/emergency-stop/global", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["reason"] == "emergency"


def test_activate_global_emergency_stop_unauthorized(app_client):
    """Test activation by unauthorized caller"""
    payload = {
        "reason": "security_threat",
        "activator": "unauthorized_user"
    }
    response = app_client.post("/ai/emergency-stop/global", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is False
    assert "UNAUTHORIZED" in data["error"]


def test_activate_global_emergency_stop_exception_handling(app_client, mock_node):
    """Test exception handling in emergency stop activation"""
    mock_node.safety_controls.activate_emergency_stop = Mock(
        side_effect=Exception("Activation failed")
    )

    payload = {"activator": "test_system"}
    response = app_client.post("/ai/emergency-stop/global", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_deactivate_global_emergency_stop_success(app_client, mock_safety_controls):
    """Test successful deactivation of emergency stop"""
    # Activate first
    mock_safety_controls.activate_emergency_stop(
        StopReason.SECURITY_THREAT, "Test", "test_system"
    )

    payload = {"deactivator": "test_system"}
    response = app_client.post("/ai/emergency-stop/deactivate", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "deactivated" in data["message"].lower()


def test_deactivate_global_emergency_stop_default_deactivator(app_client, mock_safety_controls):
    """Test deactivation with default deactivator"""
    # Activate first
    mock_safety_controls.activate_emergency_stop(
        StopReason.EMERGENCY, "Test", "test_system"
    )

    payload = {}
    response = app_client.post("/ai/emergency-stop/deactivate", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_deactivate_global_emergency_stop_not_active(app_client):
    """Test deactivation when emergency stop is not active"""
    payload = {"deactivator": "test_system"}
    response = app_client.post("/ai/emergency-stop/deactivate", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "not active" in data["error"].lower()


def test_deactivate_global_emergency_stop_exception_handling(app_client, mock_node):
    """Test exception handling in emergency stop deactivation"""
    mock_node.safety_controls.deactivate_emergency_stop = Mock(
        side_effect=Exception("Deactivation failed")
    )

    payload = {"deactivator": "test_system"}
    response = app_client.post("/ai/emergency-stop/deactivate", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== SAFETY LEVEL TESTS =====


def test_set_safety_level_normal(app_client, mock_safety_controls):
    """Test setting safety level to NORMAL"""
    payload = {"level": "normal", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "normal"


def test_set_safety_level_caution(app_client, mock_safety_controls):
    """Test setting safety level to CAUTION"""
    payload = {"level": "caution", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "caution"


def test_set_safety_level_restricted(app_client, mock_safety_controls):
    """Test setting safety level to RESTRICTED"""
    payload = {"level": "restricted", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "restricted"


def test_set_safety_level_emergency_stop(app_client, mock_safety_controls):
    """Test setting safety level to EMERGENCY_STOP triggers emergency stop"""
    payload = {"level": "emergency_stop", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "emergency_stop"
    assert mock_safety_controls.emergency_stop_active is True


def test_set_safety_level_lockdown(app_client, mock_safety_controls):
    """Test setting safety level to LOCKDOWN triggers emergency stop"""
    payload = {"level": "lockdown", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "lockdown"
    assert mock_safety_controls.emergency_stop_active is True


def test_set_safety_level_default_values(app_client, mock_safety_controls):
    """Test setting safety level with default values"""
    payload = {}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["new_level"] == "normal"


def test_set_safety_level_invalid_level(app_client):
    """Test setting invalid safety level"""
    payload = {"level": "invalid_level", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid safety level" in data["error"]


def test_set_safety_level_unauthorized(app_client):
    """Test setting safety level by unauthorized caller"""
    payload = {"level": "lockdown", "setter": "unauthorized_user"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is False
    assert "UNAUTHORIZED" in data["error"]


def test_set_safety_level_exception_handling(app_client, mock_node):
    """Test exception handling in set safety level"""
    mock_node.safety_controls.set_safety_level = Mock(
        side_effect=Exception("Level change failed")
    )

    payload = {"level": "normal", "setter": "test_system"}
    response = app_client.post("/ai/safety-level", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== STATUS & MONITORING TESTS =====


def test_get_safety_status(app_client, mock_safety_controls):
    """Test getting current safety status"""
    response = app_client.get("/ai/safety-status")

    assert response.status_code == 200
    data = response.get_json()
    assert "safety_level" in data
    assert "emergency_stop_active" in data
    assert "personal_ai" in data
    assert "governance_ai" in data
    assert "trading_bots" in data
    assert "statistics" in data


def test_get_safety_status_with_emergency_stop(app_client, mock_safety_controls):
    """Test getting status when emergency stop is active"""
    mock_safety_controls.activate_emergency_stop(
        StopReason.SECURITY_THREAT, "Test emergency", "test_system"
    )

    response = app_client.get("/ai/safety-status")

    assert response.status_code == 200
    data = response.get_json()
    assert data["emergency_stop_active"] is True
    assert "emergency_stop" in data
    assert data["emergency_stop"]["reason"] == "security_threat"


def test_get_safety_status_exception_handling(app_client, mock_node):
    """Test exception handling in get status"""
    mock_node.safety_controls.get_status = Mock(
        side_effect=Exception("Status retrieval failed")
    )

    response = app_client.get("/ai/safety-status")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_get_active_operations(app_client, mock_safety_controls):
    """Test getting list of active operations"""
    # Register some operations
    mock_safety_controls.register_personal_ai_request(
        "req_active", VALID_TEST_ADDRESS, "swap", "anthropic", "claude-sonnet-4"
    )
    mock_safety_controls.register_governance_task("task_active", "prop_200", "analysis", 3)

    response = app_client.get("/ai/active-operations")

    assert response.status_code == 200
    data = response.get_json()
    assert "personal_ai_requests" in data
    assert "governance_tasks" in data
    assert "trading_bots" in data


def test_get_active_operations_exception_handling(app_client, mock_node):
    """Test exception handling in get active operations"""
    mock_node.safety_controls.get_active_operations = Mock(
        side_effect=Exception("Operations retrieval failed")
    )

    response = app_client.get("/ai/active-operations")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== SAFETY CALLERS AUTHORIZATION TESTS =====


def test_list_safety_callers(app_client, mock_safety_controls):
    """Test listing authorized safety callers"""
    response = app_client.get("/ai/safety-callers")

    assert response.status_code == 200
    data = response.get_json()
    assert "authorized_callers" in data
    assert isinstance(data["authorized_callers"], list)
    assert "test_system" in data["authorized_callers"]


def test_list_safety_callers_exception_handling(app_client, mock_node):
    """Test exception handling in list callers"""
    mock_node.safety_controls.authorized_callers = None

    response = app_client.get("/ai/safety-callers")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_add_safety_caller_success(app_client, mock_safety_controls):
    """Test adding authorized safety caller"""
    payload = {"identifier": "new_caller"}
    response = app_client.post("/ai/safety-callers", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "new_caller" in data["caller"]


def test_add_safety_caller_no_json_payload(app_client, mock_safety_controls):
    """Test adding caller without JSON payload"""
    response = app_client.post("/ai/safety-callers")

    # When no JSON is provided, the API returns 500 due to NoneType access
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_add_safety_caller_missing_identifier(app_client, mock_safety_controls):
    """Test adding caller with missing identifier"""
    payload = {}
    response = app_client.post("/ai/safety-callers", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_add_safety_caller_exception_handling(app_client, mock_node):
    """Test exception handling in add caller"""
    mock_node.safety_controls.authorize_safety_caller = Mock(
        side_effect=Exception("Authorization failed")
    )

    payload = {"identifier": "new_caller"}
    response = app_client.post("/ai/safety-callers", json=payload)

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_remove_safety_caller_success(app_client, mock_safety_controls):
    """Test removing authorized safety caller"""
    # Add caller first
    mock_safety_controls.authorize_safety_caller("removable_caller")

    response = app_client.delete("/ai/safety-callers/removable_caller")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "removable_caller" in data["caller"]


def test_remove_safety_caller_failure(app_client, mock_node):
    """Test removing caller that returns failure"""
    # Mock to return failure
    mock_node.safety_controls.revoke_safety_caller = Mock(
        return_value={"success": False, "error": "Cannot remove caller"}
    )

    response = app_client.delete("/ai/safety-callers/some_caller")

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_remove_safety_caller_exception_handling(app_client, mock_node):
    """Test exception handling in remove caller"""
    mock_node.safety_controls.revoke_safety_caller = Mock(
        side_effect=Exception("Revocation failed")
    )

    response = app_client.delete("/ai/safety-callers/some_caller")

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


# ===== INTEGRATION TESTS =====


def test_full_workflow_personal_ai_request(app_client, mock_safety_controls):
    """Test complete workflow: register -> check -> cancel -> check"""
    # Register
    mock_safety_controls.register_personal_ai_request(
        "req_workflow", VALID_TEST_ADDRESS, "swap", "anthropic", "claude-sonnet-4"
    )

    # Check status (not cancelled)
    response = app_client.get("/ai/request-status/req_workflow")
    assert response.get_json()["is_cancelled"] is False

    # Cancel
    payload = {"user_address": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/cancel-request/req_workflow", json=payload)
    assert response.status_code == 200

    # Check status (cancelled)
    response = app_client.get("/ai/request-status/req_workflow")
    assert response.get_json()["is_cancelled"] is True


def test_full_workflow_governance_task(app_client, mock_safety_controls):
    """Test complete workflow: register -> pause -> check -> resume -> check"""
    # Register
    mock_safety_controls.register_governance_task("task_workflow", "prop_300", "analysis", 4)

    # Check status (not paused)
    response = app_client.get("/ai/governance-task-status/task_workflow")
    assert response.get_json()["is_paused"] is False

    # Pause
    payload = {"pauser": VALID_TEST_ADDRESS}
    response = app_client.post("/ai/pause-governance-task/task_workflow", json=payload)
    assert response.status_code == 200

    # Check status (paused)
    response = app_client.get("/ai/governance-task-status/task_workflow")
    assert response.get_json()["is_paused"] is True

    # Resume
    response = app_client.post("/ai/resume-governance-task/task_workflow")
    assert response.status_code == 200

    # Check status (not paused)
    response = app_client.get("/ai/governance-task-status/task_workflow")
    assert response.get_json()["is_paused"] is False


def test_emergency_stop_workflow(app_client, mock_safety_controls):
    """Test emergency stop workflow: activate -> check status -> deactivate"""
    # Activate
    payload = {
        "reason": "security_threat",
        "details": "Test emergency",
        "activator": "test_system"
    }
    response = app_client.post("/ai/emergency-stop/global", json=payload)
    assert response.status_code == 200

    # Check status
    response = app_client.get("/ai/safety-status")
    data = response.get_json()
    assert data["emergency_stop_active"] is True

    # Deactivate
    payload = {"deactivator": "test_system"}
    response = app_client.post("/ai/emergency-stop/deactivate", json=payload)
    assert response.status_code == 200

    # Check status again
    response = app_client.get("/ai/safety-status")
    data = response.get_json()
    assert data["emergency_stop_active"] is False


def test_safety_level_escalation(app_client, mock_safety_controls):
    """Test safety level escalation: normal -> caution -> restricted -> emergency_stop"""
    levels = ["normal", "caution", "restricted", "emergency_stop"]

    for level in levels:
        payload = {"level": level, "setter": "test_system"}
        response = app_client.post("/ai/safety-level", json=payload)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["new_level"] == level


def test_route_initialization_output(capsys):
    """Test that route initialization prints expected output"""
    from flask import Flask

    mock_node = Mock()
    mock_blockchain = Mock()
    mock_node.blockchain = mock_blockchain
    mock_node.safety_controls = AISafetyControls(mock_blockchain)

    app = Flask(__name__)

    # This should print route information
    add_safety_control_routes(app, mock_node)

    captured = capsys.readouterr()
    assert "AI Safety Control API endpoints added:" in captured.out
    assert "/ai/cancel-request/" in captured.out
    assert "/ai/emergency-stop/global" in captured.out
    assert "/ai/safety-level" in captured.out
    assert "/ai/safety-callers" in captured.out

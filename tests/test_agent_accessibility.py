"""
Tests for Agent Accessibility Improvements

Tests CLI commands, batch transactions, webhooks, and structured error responses.
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest


class TestGovernanceCommands:
    """Test governance CLI commands."""

    def test_governance_client_initialization(self):
        """Test GovernanceClient initializes correctly."""
        from xai.cli.governance_commands import GovernanceClient

        client = GovernanceClient("http://localhost:8080", api_key="test-key")
        assert client.node_url == "http://localhost:8080"
        assert client.api_key == "test-key"
        assert client.timeout == 30.0

    def test_governance_client_url_normalization(self):
        """Test that trailing slashes are stripped from URLs."""
        from xai.cli.governance_commands import GovernanceClient

        client = GovernanceClient("http://localhost:8080/")
        assert client.node_url == "http://localhost:8080"

    @patch("xai.cli.governance_commands.requests.request")
    def test_list_proposals_request(self, mock_request):
        """Test listing proposals makes correct API call."""
        from xai.cli.governance_commands import GovernanceClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"proposals": [], "count": 0}
        mock_request.return_value = mock_response

        client = GovernanceClient("http://localhost:8080")
        result = client.list_proposals(status="active", limit=10)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["status"] == "active"
        assert call_args.kwargs["params"]["limit"] == 10

    @patch("xai.cli.governance_commands.requests.request")
    def test_vote_request(self, mock_request):
        """Test voting makes correct API call."""
        from xai.cli.governance_commands import GovernanceClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response

        client = GovernanceClient("http://localhost:8080")
        result = client.vote("prop_123", "XAI_VOTER", "yes")

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args.kwargs["json"]["proposal_id"] == "prop_123"
        assert call_args.kwargs["json"]["voter_address"] == "XAI_VOTER"
        assert call_args.kwargs["json"]["vote"] == "yes"


class TestTreasuryCommands:
    """Test treasury CLI commands."""

    def test_treasury_client_initialization(self):
        """Test TreasuryClient initializes correctly."""
        from xai.cli.treasury_commands import TreasuryClient

        client = TreasuryClient("http://localhost:8080")
        assert client.node_url == "http://localhost:8080"

    @patch("xai.cli.treasury_commands.requests.request")
    def test_get_balance_request(self, mock_request):
        """Test balance query makes correct API call."""
        from xai.cli.treasury_commands import TreasuryClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"balance": 1000.0}
        mock_request.return_value = mock_response

        client = TreasuryClient("http://localhost:8080")
        result = client.get_balance("XAI_ADDRESS")

        mock_request.assert_called_once()
        assert "/balance/XAI_ADDRESS" in mock_request.call_args[0][1]


class TestWebhookManager:
    """Test webhook manager functionality."""

    def test_webhook_event_types(self):
        """Test all webhook event types are defined."""
        from xai.core.webhook_manager import WebhookEvent

        expected_events = [
            "new_block",
            "new_transaction",
            "governance_vote",
            "proposal_created",
            "proposal_executed",
            "balance_change",
            "contract_deployed",
            "contract_called",
            "mining_reward",
            "ai_task_completed",
        ]

        for event in expected_events:
            assert hasattr(WebhookEvent, event.upper())

    def test_webhook_registration(self):
        """Test webhook registration."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        result = manager.register_webhook(
            url="https://example.com/webhook",
            events=["new_block", "new_transaction"],
            owner="XAI_OWNER",
        )

        assert result["success"] is True
        assert "webhook_id" in result
        assert "secret" in result
        assert result["webhook_id"].startswith("wh_")
        assert len(result["secret"]) == 64  # 32 bytes hex

        manager.shutdown()

    def test_webhook_registration_invalid_url(self):
        """Test webhook registration with invalid URL."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        result = manager.register_webhook(
            url="ftp://invalid.com/webhook",
            events=["new_block"],
            owner="XAI_OWNER",
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == "invalid_url"

        manager.shutdown()

    def test_webhook_registration_invalid_events(self):
        """Test webhook registration with invalid events."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        result = manager.register_webhook(
            url="https://example.com/webhook",
            events=["invalid_event"],
            owner="XAI_OWNER",
        )

        assert result["success"] is False
        assert result["error"]["code"] == "invalid_events"

        manager.shutdown()

    def test_webhook_unregistration(self):
        """Test webhook unregistration."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        # Register first
        reg_result = manager.register_webhook(
            url="https://example.com/webhook",
            events=["new_block"],
            owner="XAI_OWNER",
        )
        webhook_id = reg_result["webhook_id"]

        # Unregister
        unreg_result = manager.unregister_webhook(webhook_id, "XAI_OWNER")
        assert unreg_result["success"] is True

        # Verify removed
        assert manager.get_webhook(webhook_id) is None

        manager.shutdown()

    def test_webhook_unregistration_wrong_owner(self):
        """Test webhook unregistration with wrong owner."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        reg_result = manager.register_webhook(
            url="https://example.com/webhook",
            events=["new_block"],
            owner="XAI_OWNER",
        )
        webhook_id = reg_result["webhook_id"]

        unreg_result = manager.unregister_webhook(webhook_id, "WRONG_OWNER")
        assert unreg_result["success"] is False
        assert unreg_result["error"]["code"] == "unauthorized"

        manager.shutdown()

    def test_webhook_update(self):
        """Test webhook update."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        reg_result = manager.register_webhook(
            url="https://example.com/webhook",
            events=["new_block"],
            owner="XAI_OWNER",
        )
        webhook_id = reg_result["webhook_id"]

        update_result = manager.update_webhook(
            webhook_id=webhook_id,
            owner="XAI_OWNER",
            events=["new_block", "governance_vote"],
            active=True,
        )

        assert update_result["success"] is True
        webhook = update_result["webhook"]
        assert "governance_vote" in webhook["events"]

        manager.shutdown()

    def test_webhook_owner_limit(self):
        """Test webhook per-owner limit."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        # Register up to limit
        for i in range(manager.MAX_WEBHOOKS_PER_OWNER):
            result = manager.register_webhook(
                url=f"https://example.com/webhook{i}",
                events=["new_block"],
                owner="XAI_OWNER",
            )
            assert result["success"] is True

        # Try one more
        result = manager.register_webhook(
            url="https://example.com/webhook_extra",
            events=["new_block"],
            owner="XAI_OWNER",
        )
        assert result["success"] is False
        assert result["error"]["code"] == "webhook_limit_reached"

        manager.shutdown()

    def test_webhook_signature_generation(self):
        """Test webhook signature generation."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        secret = "test_secret_key"
        payload = {"event": "new_block", "data": {"height": 100}}

        signature = manager._generate_signature(secret, payload)
        assert signature.startswith("sha256=")
        assert len(signature) == 7 + 64  # "sha256=" + 64 hex chars

        manager.shutdown()

    def test_webhook_list_by_owner(self):
        """Test listing webhooks by owner."""
        from xai.core.webhook_manager import WebhookManager

        manager = WebhookManager()

        manager.register_webhook(
            url="https://example.com/webhook1",
            events=["new_block"],
            owner="OWNER_A",
        )
        manager.register_webhook(
            url="https://example.com/webhook2",
            events=["new_block"],
            owner="OWNER_B",
        )

        owner_a_hooks = manager.list_webhooks("OWNER_A")
        owner_b_hooks = manager.list_webhooks("OWNER_B")
        all_hooks = manager.list_webhooks()

        assert len(owner_a_hooks) == 1
        assert len(owner_b_hooks) == 1
        assert len(all_hooks) == 2

        manager.shutdown()


class TestStructuredErrorResponses:
    """Test structured error response module."""

    def test_error_code_enum(self):
        """Test error codes are properly defined."""
        from xai.core.error_response import ErrorCode

        assert ErrorCode.UNAUTHORIZED.value == "UNAUTHORIZED"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.RATE_LIMITED.value == "RATE_LIMITED"

    def test_api_error_structure(self):
        """Test APIError produces correct structure."""
        from xai.core.error_response import APIError, ErrorCode

        error = APIError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            details={"field": "amount"},
        )

        response = error.to_dict()
        assert "error" in response
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Invalid input"
        assert response["error"]["details"]["field"] == "amount"

    def test_error_response_function(self):
        """Test error_response helper function."""
        from xai.core.error_response import ErrorCode, error_response

        response, status = error_response(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            details={"id": "123"},
        )

        assert status == 404
        assert response["error"]["code"] == "NOT_FOUND"

    def test_validation_error_helper(self):
        """Test validation_error helper."""
        from xai.core.error_response import validation_error

        response, status = validation_error(
            message="Invalid amount",
            field="amount",
            value=-100,
        )

        assert status == 400
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["details"]["field"] == "amount"

    def test_not_found_error_helper(self):
        """Test not_found_error helper."""
        from xai.core.error_response import not_found_error

        response, status = not_found_error("Transaction", "tx_123")

        assert status == 404
        assert "tx_123" in response["error"]["message"]

    def test_rate_limit_error_helper(self):
        """Test rate_limit_error helper."""
        from xai.core.error_response import rate_limit_error

        response, status = rate_limit_error(
            limit=100,
            window_seconds=60,
            retry_after=30,
        )

        assert status == 429
        assert response["error"]["code"] == "RATE_LIMITED"
        assert response["error"]["details"]["retry_after"] == 30

    def test_error_responses_factory(self):
        """Test ErrorResponses factory methods."""
        from xai.core.error_response import ErrorResponses

        # Invalid address
        response, status = ErrorResponses.invalid_address("INVALID_ADDR")
        assert status == 400
        assert response["error"]["code"] == "INVALID_ADDRESS"

        # Insufficient balance
        response, status = ErrorResponses.insufficient_balance(100.0, 50.0)
        assert status == 403
        assert response["error"]["details"]["shortfall"] == 50.0

        # Batch too large
        response, status = ErrorResponses.batch_too_large(100, 200)
        assert status == 400
        assert response["error"]["code"] == "BATCH_TOO_LARGE"


class TestBatchTransactionRoutes:
    """Test batch transaction API routes."""

    def test_parse_csv_transactions(self):
        """Test CSV transaction parsing."""
        from xai.core.api_routes.batch import _parse_csv_transactions

        csv_content = """sender,recipient,amount,fee
XAI_SENDER1,XAI_RECIPIENT1,10.0,0.001
XAI_SENDER2,XAI_RECIPIENT2,20.0,0.002"""

        transactions = _parse_csv_transactions(csv_content)

        assert len(transactions) == 2
        assert transactions[0]["sender"] == "XAI_SENDER1"
        assert transactions[0]["amount"] == 10.0
        assert transactions[1]["recipient"] == "XAI_RECIPIENT2"

    def test_parse_json_transactions(self):
        """Test JSON transaction parsing."""
        from xai.core.api_routes.batch import _parse_json_transactions

        json_content = json.dumps([
            {"sender": "XAI1", "recipient": "XAI2", "amount": 10.0},
            {"sender": "XAI3", "recipient": "XAI4", "amount": 20.0},
        ])

        transactions = _parse_json_transactions(json_content)

        assert len(transactions) == 2
        assert transactions[0]["sender"] == "XAI1"

    def test_parse_json_transactions_with_wrapper(self):
        """Test JSON parsing with transactions wrapper."""
        from xai.core.api_routes.batch import _parse_json_transactions

        json_content = json.dumps({
            "transactions": [
                {"sender": "XAI1", "recipient": "XAI2", "amount": 10.0},
            ]
        })

        transactions = _parse_json_transactions(json_content)
        assert len(transactions) == 1

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        from xai.core.api_routes.batch import _parse_json_transactions

        transactions = _parse_json_transactions("invalid json {")
        assert transactions == []


class TestAICommands:
    """Test AI CLI command additions."""

    def test_ai_compute_client_exists(self):
        """Test AIComputeClient is importable."""
        from xai.cli.ai_commands import AIComputeClient

        client = AIComputeClient("http://localhost:8080")
        assert client.node_url == "http://localhost:8080"

    @patch("xai.cli.ai_commands.requests.request")
    def test_submit_task_request(self, mock_request):
        """Test task submission makes correct API call."""
        from xai.cli.ai_commands import AIComputeClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "task_id": "task_123"}
        mock_request.return_value = mock_response

        client = AIComputeClient("http://localhost:8080")
        result = client.submit_task({
            "task_type": "analysis",
            "input_data": "test data",
        })

        assert result["success"] is True
        assert result["task_id"] == "task_123"


class TestCLIIntegration:
    """Integration tests for CLI command groups."""

    def test_governance_group_exists(self):
        """Test governance command group is defined."""
        from xai.cli.governance_commands import governance
        assert governance.name == "governance"

    def test_treasury_group_exists(self):
        """Test treasury command group is defined."""
        from xai.cli.treasury_commands import treasury
        assert treasury.name == "treasury"

    def test_ai_group_exists(self):
        """Test AI command group is defined."""
        from xai.cli.ai_commands import ai
        assert ai.name == "ai"

    def test_governance_commands_registered(self):
        """Test governance subcommands are registered."""
        from xai.cli.governance_commands import governance

        command_names = [cmd for cmd in governance.commands.keys()]
        assert "list" in command_names
        assert "show" in command_names
        assert "propose" in command_names
        assert "vote" in command_names
        assert "power" in command_names

    def test_treasury_commands_registered(self):
        """Test treasury subcommands are registered."""
        from xai.cli.treasury_commands import treasury

        command_names = [cmd for cmd in treasury.commands.keys()]
        assert "balance" in command_names
        assert "history" in command_names
        assert "metrics" in command_names
        assert "fees" in command_names

    def test_ai_new_commands_registered(self):
        """Test new AI subcommands are registered."""
        from xai.cli.ai_commands import ai

        command_names = [cmd for cmd in ai.commands.keys()]
        assert "analyze" in command_names
        assert "predict" in command_names
        assert "model-status" in command_names
        assert "models" in command_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

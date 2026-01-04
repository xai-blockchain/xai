from __future__ import annotations

"""
Governance API Handler

Handles all governance-related API endpoints including:
- Proposal submission and retrieval
- Voting on proposals
- Voting power calculation
- Fiat unlock governance
"""

import hashlib
import logging
import time
from typing import Any

from flask import Flask, jsonify, request

from xai.core.security.security_validation import ValidationError

logger = logging.getLogger(__name__)
ATTACHMENT_SAFE = True

class GovernanceAPIHandler:
    """Handles all governance-related API endpoints."""

    def __init__(self, node: Any, app: Flask):
        """
        Initialize Governance API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
        """
        self.node = node
        self.app = app

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all governance routes."""

        @self.app.route("/governance/proposals/submit", methods=["POST"])
        def submit_proposal() -> tuple[dict[str, Any], int]:
            """Submit AI development proposal."""
            return self.submit_proposal_handler()

        @self.app.route("/governance/proposals", methods=["GET"])
        def get_proposals() -> tuple[dict[str, Any], int]:
            """Get proposals by status."""
            return self.get_proposals_handler()

        @self.app.route("/governance/vote", methods=["POST"])
        def submit_vote() -> tuple[dict[str, Any], int]:
            """Vote on proposal."""
            return self.submit_vote_handler()

        @self.app.route("/governance/voting-power/<address>", methods=["GET"])
        def get_voting_power(address: str) -> tuple[dict[str, Any], int]:
            """Calculate voting power."""
            return self.get_voting_power_handler(address)

        @self.app.route("/governance/fiat-unlock/vote", methods=["POST"])
        def governance_fiat_unlock_vote() -> tuple[dict[str, Any], int]:
            """Vote on fiat unlock governance."""
            return self.fiat_unlock_vote_handler()

        @self.app.route("/governance/fiat-unlock/status", methods=["GET"])
        def governance_fiat_unlock_status() -> tuple[dict[str, Any], int]:
            """Get fiat unlock governance status."""
            return self.fiat_unlock_status_handler()

    def submit_proposal_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle proposal submission.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json

        # Create proposal (would integrate with governance_dao)
        proposal_id = hashlib.sha256(f"{time.time()}{data.get('title')}".encode()).hexdigest()[:16]

        # In production, this would call governance_dao.submit_proposal()
        return (
            jsonify(
                {
                    "success": True,
                    "proposal_id": proposal_id,
                    "status": "security_review",
                    "message": "Proposal submitted for security analysis",
                }
            ),
            200,
        )

    def get_proposals_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle proposal retrieval.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        status = request.args.get("status", "community_vote")
        limit = request.args.get("limit", 10, type=int)

        # In production, query from governance_dao
        # For now, return sample data
        return jsonify({"count": 0, "proposals": []}), 200

    def submit_vote_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle vote submission.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json

        proposal_id = data.get("proposal_id")
        voter_address = data.get("voter_address")
        vote = data.get("vote")

        # In production, integrate with enhanced_voting_system
        return (
            jsonify(
                {
                    "success": True,
                    "proposal_id": proposal_id,
                    "vote": vote,
                    "voting_power": 7503.5,
                    "breakdown": {"coin_power": 7000, "donation_power": 503.5},
                }
            ),
            200,
        )

    def get_voting_power_handler(self, address: str) -> tuple[dict[str, Any], int]:
        """
        Handle voting power calculation.

        Args:
            address: Wallet address to calculate voting power for

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        try:
            balance = self.node.blockchain.get_balance(address)
        except Exception as exc:
            logger.error(
                "Failed to retrieve voting power balance: %s",
                exc,
                extra={
                    "error_type": type(exc).__name__,
                    "address": address,
                },
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "VOTING_POWER_UNAVAILABLE",
                        "message": str(exc),
                    }
                ),
                500,
            )

        # In production, integrate with enhanced_voting_system
        coin_power = balance * 0.70
        donation_power = 0  # Would query from AI donation history

        return (
            jsonify(
                {
                    "address": address,
                    "xai_balance": balance,
                    "voting_power": {
                        "coin_power": coin_power,
                        "donation_power": donation_power,
                        "total": coin_power + donation_power,
                    },
                }
            ),
            200,
        )

    def fiat_unlock_vote_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle fiat unlock governance vote.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        payload = request.json or {}
        address = payload.get("governance_address") or payload.get("user_address")
        support = payload.get("support", True)
        reason = payload.get("reason")

        if not address:
            return jsonify({"success": False, "error": "governance_address required"}), 400

        try:
            self.node.validator.validate_address(address)
        except ValidationError as ve:
            logger.warning(
                "ValidationError in fiat_unlock_vote_handler",
                extra={
                    "error_type": "ValidationError",
                    "error": str(ve),
                    "function": "fiat_unlock_vote_handler"
                }
            )
            return (
                jsonify({"success": False, "error": "INVALID_ADDRESS", "message": str(ve)}),
                400,
            )

        try:
            status = self.node.fiat_unlock_manager.cast_vote(address, bool(support), reason)
        except ValueError as ve:
            logger.warning(
                "ValueError in fiat_unlock_vote_handler",
                extra={
                    "error_type": "ValueError",
                    "error": str(ve),
                    "function": "fiat_unlock_vote_handler"
                }
            )
            return (
                jsonify({"success": False, "error": "VOTING_NOT_OPEN", "message": str(ve)}),
                400,
            )

        return jsonify({"success": True, "status": status}), 200

    def fiat_unlock_status_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle fiat unlock governance status retrieval.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        status = self.node.fiat_unlock_manager.get_status()
        return jsonify({"success": True, "status": status}), 200

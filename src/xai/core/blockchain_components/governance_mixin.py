"""
Blockchain Governance Mixin - Handles governance proposals, voting, and execution.

Extracted from blockchain.py for better separation of concerns.
Delegates to GovernanceManager for actual implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BlockchainGovernanceMixin:
    """
    Mixin providing governance functionality for the Blockchain class.

    All methods delegate to GovernanceManager for god class refactoring.

    Includes:
    - Proposal submission
    - Vote casting
    - Code review submission
    - Proposal execution
    - Governance state queries
    """

    def submit_governance_proposal(
        self,
        submitter: str,
        title: str,
        description: str,
        proposal_type: str,
        proposal_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a governance proposal. Delegates to GovernanceManager."""
        return self.governance_manager.submit_governance_proposal(
            submitter, title, description, proposal_type, proposal_data
        )

    def cast_governance_vote(
        self,
        voter: str,
        proposal_id: str,
        vote: str,
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """Cast a vote on a governance proposal. Delegates to GovernanceManager."""
        return self.governance_manager.cast_governance_vote(voter, proposal_id, vote, voting_power)

    def submit_code_review(
        self,
        reviewer: str,
        proposal_id: str,
        approved: bool,
        comments: str = "",
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """Submit a code review. Delegates to GovernanceManager."""
        return self.governance_manager.submit_code_review(
            reviewer, proposal_id, approved, comments, voting_power
        )

    def execute_governance_proposal(self, proposal_id: str, executor: str = "system") -> dict[str, Any]:
        """Execute an approved governance proposal. Delegates to GovernanceManager."""
        return self.governance_manager.execute_governance_proposal(proposal_id, executor)

    def vote_implementation(
        self,
        voter: str,
        proposal_id: str,
        approved: bool = True,
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """Vote on a governance proposal implementation. Delegates to GovernanceManager."""
        return self.governance_manager.vote_implementation(voter, proposal_id, approved, voting_power)

    def execute_proposal(self, executor: str, proposal_id: str) -> dict[str, Any]:
        """Execute an approved governance proposal. Delegates to GovernanceManager."""
        return self.governance_manager.execute_proposal(executor, proposal_id)

    def get_governance_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """Get details of a governance proposal. Delegates to GovernanceManager."""
        return self.governance_manager.get_governance_proposal(proposal_id)

    def list_governance_proposals(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all governance proposals. Delegates to GovernanceManager."""
        return self.governance_manager.list_governance_proposals(status)

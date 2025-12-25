"""
Governance Manager - Handles all governance-related operations for the blockchain.

This module encapsulates governance proposal submission, voting, code reviews,
execution, and state management. It acts as a facade to the GovernanceState
and GovernanceExecutionEngine components.
"""

from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING, Any

from xai.core.governance_transactions import (
    GovernanceState,
    GovernanceTransaction,
    GovernanceTxType,
)
from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain
    from xai.core.blockchain_components.block import Block
    from xai.core.transaction import Transaction


# Metadata type to governance transaction type mapping
_GOVERNANCE_METADATA_TYPE_MAP = {
    "governance_proposal": GovernanceTxType.SUBMIT_PROPOSAL,
    "governance_vote": GovernanceTxType.CAST_VOTE,
    "code_review": GovernanceTxType.SUBMIT_CODE_REVIEW,
    "implementation_vote": GovernanceTxType.VOTE_IMPLEMENTATION,
    "proposal_execution": GovernanceTxType.EXECUTE_PROPOSAL,
    "rollback_change": GovernanceTxType.ROLLBACK_CHANGE,
}


class GovernanceManager:
    """
    Manages all governance-related operations for the blockchain.

    This class handles:
    - Proposal submission and tracking
    - Vote casting and vote implementation
    - Code review submission
    - Proposal execution
    - Governance state reconstruction from chain
    - Integration with GovernanceExecutionEngine
    """

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize the GovernanceManager.

        Args:
            blockchain: Reference to the parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def rebuild_governance_state_from_chain(self) -> None:
        """
        Reconstruct governance state by replaying governance transactions.

        This method is called during blockchain initialization to rebuild
        the governance state from the persisted chain data.
        """
        # Need to load full blocks for this
        mining_start = (
            self.blockchain.chain[0].timestamp if self.blockchain.chain else time.time()
        )
        self.blockchain.governance_state = GovernanceState(mining_start_time=mining_start)

        for header in self.blockchain.chain:
            block = self.blockchain.storage.load_block_from_disk(header.index)
            if block:
                self.process_governance_block_transactions(block)

    def transaction_to_governance_transaction(
        self, tx: Transaction
    ) -> GovernanceTransaction | None:
        """
        Convert a regular transaction to a governance transaction if applicable.

        Args:
            tx: Transaction to convert

        Returns:
            GovernanceTransaction if the transaction is governance-related, None otherwise
        """
        metadata = getattr(tx, "metadata", {}) or {}
        metadata_type = metadata.get("type")
        if not metadata_type:
            return None

        tx_enum = _GOVERNANCE_METADATA_TYPE_MAP.get(metadata_type)
        if not tx_enum:
            return None

        proposal_id = metadata.get("proposal_id")
        if not proposal_id:
            return None

        data = {
            key: copy.deepcopy(value)
            for key, value in metadata.items()
            if key not in {"type", "timestamp"}
        }

        gtx = GovernanceTransaction(
            tx_type=tx_enum, submitter=tx.sender, proposal_id=proposal_id, data=data
        )
        gtx.timestamp = tx.timestamp
        gtx.txid = tx.txid or gtx.txid
        return gtx

    def find_pending_proposal_payload(self, proposal_id: str) -> dict[str, Any]:
        """
        Find the proposal payload that was submitted on-chain.

        Args:
            proposal_id: ID of the proposal to find

        Returns:
            Proposal payload dictionary, or empty dict if not found
        """
        for tx in self.blockchain.pending_transactions:
            metadata = getattr(tx, "metadata", {}) or {}
            if metadata.get("type") != "governance_proposal":
                continue
            if metadata.get("proposal_id") != proposal_id:
                continue

            return metadata.get("proposal_payload") or metadata.get("proposal_data") or {}

        return {}

    def process_governance_block_transactions(self, block: Block) -> None:
        """
        Apply governance transactions that appear in a block.

        Args:
            block: Block containing transactions to process
        """
        if not self.blockchain.governance_state:
            return

        for tx in block.transactions:
            gtx = self.transaction_to_governance_transaction(tx)
            if not gtx:
                continue
            self.apply_governance_transaction(gtx)

    def apply_governance_transaction(self, gtx: GovernanceTransaction) -> dict[str, Any]:
        """
        Route governance transaction to the GovernanceState and ExecutionEngine.

        Args:
            gtx: Governance transaction to apply

        Returns:
            Result dictionary with success status and details
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance state unavailable"}

        tx_type = GovernanceTxType(gtx.tx_type)

        if tx_type == GovernanceTxType.SUBMIT_PROPOSAL:
            return self.blockchain.governance_state.submit_proposal(gtx)
        if tx_type == GovernanceTxType.CAST_VOTE:
            return self.blockchain.governance_state.cast_vote(gtx)
        if tx_type == GovernanceTxType.SUBMIT_CODE_REVIEW:
            return self.blockchain.governance_state.submit_code_review(gtx)
        if tx_type == GovernanceTxType.VOTE_IMPLEMENTATION:
            return self.blockchain.governance_state.vote_implementation(gtx)
        if tx_type == GovernanceTxType.EXECUTE_PROPOSAL:
            result = self.blockchain.governance_state.execute_proposal(gtx)
            if result.get("success"):
                execution_result = self.run_governance_execution(gtx.proposal_id)
                result["execution_result"] = execution_result
            return result
        if tx_type == GovernanceTxType.ROLLBACK_CHANGE:
            return self.blockchain.governance_state.rollback_change(gtx)

        return {
            "success": False,
            "error": f"Unsupported governance transaction type: {tx_type.value}",
        }

    def run_governance_execution(self, proposal_id: str) -> dict[str, Any]:
        """
        Execute approved proposal payloads via the execution engine.

        Args:
            proposal_id: ID of the proposal to execute

        Returns:
            Execution result dictionary
        """
        if not self.blockchain.governance_executor or not self.blockchain.governance_state:
            return {"success": False, "error": "Governance executor unavailable"}

        proposal = self.blockchain.governance_state.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        payload = dict(proposal.payload)
        payload.setdefault("proposal_type", proposal.proposal_type)
        if not payload:
            return {"success": False, "error": "Missing proposal payload for execution"}

        try:
            return self.blockchain.governance_executor.execute_proposal(proposal_id, payload)
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "Governance proposal execution failed",
                extra={
                    "proposal_id": proposal_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return {
                "success": False,
                "error": f"Execution engine error: {exc}",
            }

    # ==================== PUBLIC API METHODS ====================

    def submit_governance_proposal(
        self,
        submitter: str,
        title: str,
        description: str,
        proposal_type: str,
        proposal_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Submit a governance proposal to the blockchain.

        Creates a governance transaction and adds it to pending transactions.
        The proposal will be processed when included in a mined block.

        Args:
            submitter: Address of the proposal submitter
            title: Short title for the proposal
            description: Detailed description of what the proposal does
            proposal_type: Type of proposal (ai_improvement, parameter_change, emergency)
            proposal_data: Additional payload data for the proposal

        Returns:
            Dict with proposal_id, txid, and status
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance not initialized"}

        import uuid

        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"

        # Get submitter's voting power (based on balance)
        submitter_voting_power = self.blockchain.get_balance(submitter)

        # Create governance transaction
        gtx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter=submitter,
            proposal_id=proposal_id,
            data={
                "title": title,
                "description": description,
                "proposal_type": proposal_type,
                "submitter_voting_power": submitter_voting_power,
                "proposal_payload": proposal_data or {},
            },
        )

        # Process the proposal in governance state
        result = self.blockchain.governance_state.submit_proposal(gtx)

        # Add to pending as a governance marker (for block inclusion)
        # We use a special marker transaction for governance
        return {
            "proposal_id": proposal_id,
            "txid": gtx.txid,
            "status": "pending",
            "success": result.get("success", True),
        }

    def cast_governance_vote(
        self,
        voter: str,
        proposal_id: str,
        vote: str,
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """
        Cast a vote on a governance proposal.

        Args:
            voter: Address of the voter
            proposal_id: ID of the proposal to vote on
            vote: Vote value ("yes", "no", "abstain")
            voting_power: Voting power of the voter (0 = auto-calculate from balance)

        Returns:
            Dict with txid, status, and vote details
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance not initialized"}

        # Auto-calculate voting power from balance if not provided
        if voting_power <= 0:
            voting_power = self.blockchain.get_balance(voter)

        gtx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter=voter,
            proposal_id=proposal_id,
            data={
                "vote": vote.lower(),
                "voting_power": voting_power,
            },
        )

        result = self.blockchain.governance_state.cast_vote(gtx)

        return {
            "txid": gtx.txid,
            "status": "recorded" if result.get("success", True) else "failed",
            "vote_count": result.get("vote_count", 0),
            "success": result.get("success", True),
        }

    def submit_code_review(
        self,
        reviewer: str,
        proposal_id: str,
        approved: bool,
        comments: str = "",
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """
        Submit a code review for a governance proposal.

        Args:
            reviewer: Address of the reviewer
            proposal_id: ID of the proposal being reviewed
            approved: Whether the reviewer approves the code changes
            comments: Optional review comments
            voting_power: Reviewer's voting power (0 = auto-calculate)

        Returns:
            Dict with txid, status, and review count
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance not initialized"}

        if voting_power <= 0:
            voting_power = self.blockchain.get_balance(reviewer)

        gtx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_CODE_REVIEW,
            submitter=reviewer,
            proposal_id=proposal_id,
            data={
                "approved": approved,
                "comments": comments,
                "voting_power": voting_power,
            },
        )

        result = self.blockchain.governance_state.submit_code_review(gtx)

        return {
            "txid": gtx.txid,
            "status": "submitted" if result.get("success", True) else "failed",
            "review_count": result.get("review_count", 0),
            "success": result.get("success", True),
        }

    def execute_governance_proposal(
        self, proposal_id: str, executor: str = "system"
    ) -> dict[str, Any]:
        """
        Execute an approved governance proposal.

        Args:
            proposal_id: ID of the proposal to execute
            executor: Address executing the proposal

        Returns:
            Dict with execution status and details
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance not initialized"}

        proposal = self.blockchain.governance_state.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        gtx = GovernanceTransaction(
            tx_type=GovernanceTxType.EXECUTE_PROPOSAL,
            submitter=executor,
            proposal_id=proposal_id,
            data={
                "proposal_payload": proposal.payload,
            },
        )

        result = self.blockchain.governance_state.execute_proposal(gtx)

        if result.get("success"):
            # Run actual execution logic
            exec_result = self.run_governance_execution(proposal_id)
            result["execution_result"] = exec_result

        return result

    def vote_implementation(
        self,
        voter: str,
        proposal_id: str,
        approved: bool = True,
        voting_power: float = 0.0,
    ) -> dict[str, Any]:
        """
        Vote on a governance proposal implementation.

        Args:
            voter: Address of the voter
            proposal_id: ID of the proposal to vote on
            approved: Whether to approve the implementation
            voting_power: Voting power (defaults to balance if 0)

        Returns:
            Dict with txid, status, and vote result
        """
        if not self.blockchain.governance_state:
            return {"success": False, "error": "Governance not initialized"}

        if voting_power <= 0:
            voting_power = self.blockchain.get_balance(voter)

        gtx = GovernanceTransaction(
            tx_type=GovernanceTxType.VOTE_IMPLEMENTATION,
            submitter=voter,
            proposal_id=proposal_id,
            data={
                "approved": approved,
                "voting_power": voting_power,
            },
        )

        result = self.blockchain.governance_state.vote_implementation(gtx)

        return {
            "txid": gtx.txid,
            "status": "approved" if result.get("success", True) else "failed",
            "success": result.get("success", True),
            "error": result.get("error"),
        }

    def execute_proposal(self, executor: str, proposal_id: str) -> dict[str, Any]:
        """
        Execute an approved governance proposal (alias for execute_governance_proposal).

        Args:
            executor: Address executing the proposal
            proposal_id: ID of the proposal to execute

        Returns:
            Dict with execution status and details
        """
        return self.execute_governance_proposal(proposal_id, executor)

    def get_governance_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """
        Get details of a governance proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            Proposal state dictionary or None if not found
        """
        if not self.blockchain.governance_state:
            return None
        return self.blockchain.governance_state.get_proposal_state(proposal_id)

    def list_governance_proposals(self, status: str | None = None) -> list[dict[str, Any]]:
        """
        List all governance proposals, optionally filtered by status.

        Args:
            status: Filter by status (active, approved, executed, rejected)

        Returns:
            List of proposal dictionaries
        """
        if not self.blockchain.governance_state:
            return []

        proposals = []
        for proposal_id, proposal in self.blockchain.governance_state.proposals.items():
            proposal_dict = proposal.to_dict()
            if status is None or proposal_dict.get("status") == status:
                proposals.append(proposal_dict)

        return proposals

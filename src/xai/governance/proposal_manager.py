from typing import Dict, Any, Optional, List
import time
import logging
import threading

logger = logging.getLogger(__name__)


class ProposalManager:
    def __init__(self, minimum_stake_for_proposal: float, quorum_percentage: float = 10.0,
                 approval_threshold: float = 51.0, voting_period_seconds: int = 604800):
        """
        Initialize the ProposalManager with vote tallying capabilities.

        Args:
            minimum_stake_for_proposal: Minimum stake required to submit a proposal
            quorum_percentage: Minimum percentage of total supply that must vote
            approval_threshold: Percentage of votes needed to pass (51% = majority)
            voting_period_seconds: Duration of voting period (default: 7 days)
        """
        if (
            not isinstance(minimum_stake_for_proposal, (int, float))
            or minimum_stake_for_proposal <= 0
        ):
            raise ValueError("Minimum stake for proposal must be a positive number.")

        if not 0 < quorum_percentage <= 100:
            raise ValueError("Quorum percentage must be between 0 and 100")

        if not 0 < approval_threshold <= 100:
            raise ValueError("Approval threshold must be between 0 and 100")

        self.minimum_stake_for_proposal = minimum_stake_for_proposal
        self.quorum_percentage = quorum_percentage
        self.approval_threshold = approval_threshold
        self.voting_period_seconds = voting_period_seconds

        # Stores active proposals with voting data
        self.active_proposals: Dict[str, Dict[str, Any]] = {}
        self._proposal_id_counter = 0
        self._lock = threading.RLock()

        # Track total voting supply (for quorum calculation)
        self.total_voting_supply = 0.0

        logger.info(
            f"ProposalManager initialized. Minimum stake: {self.minimum_stake_for_proposal:.2f}, "
            f"Quorum: {self.quorum_percentage}%, Threshold: {self.approval_threshold}%, "
            f"Voting period: {self.voting_period_seconds}s"
        )

    def set_total_voting_supply(self, total_supply: float):
        """Set the total voting supply for quorum calculations."""
        with self._lock:
            self.total_voting_supply = total_supply
            logger.info(f"Total voting supply set to {total_supply:.2f}")

    def submit_proposal(
        self, proposer_address: str, proposal_details: str, staked_amount: float
    ) -> str:
        """
        Submits a new governance proposal, checking for the minimum stake requirement.
        Returns the proposal ID if successful.
        """
        if not proposer_address:
            raise ValueError("Proposer address cannot be empty.")
        if not proposal_details:
            raise ValueError("Proposal details cannot be empty.")
        if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
            raise ValueError("Staked amount must be a positive number.")

        if staked_amount < self.minimum_stake_for_proposal:
            raise ValueError(
                f"Staked amount ({staked_amount:.2f}) is less than the minimum required stake ({self.minimum_stake_for_proposal:.2f})."
            )

        with self._lock:
            self._proposal_id_counter += 1
            proposal_id = f"proposal_{self._proposal_id_counter}"

            voting_start = int(time.time())
            voting_end = voting_start + self.voting_period_seconds

            self.active_proposals[proposal_id] = {
                "proposer": proposer_address,
                "proposal_details": proposal_details,
                "staked_amount": staked_amount,
                "status": "voting",
                "created_at": voting_start,
                "voting_end": voting_end,
                "votes_for": 0.0,
                "votes_against": 0.0,
                "total_votes": 0.0,
                "voters": set(),  # Track who has voted to prevent double voting
                "result": None,
                "execution_data": None
            }
            logger.info(
                f"Proposal {proposal_id} submitted by {proposer_address} with stake {staked_amount:.2f}. "
                f"Voting ends at {time.ctime(voting_end)}"
            )
            return proposal_id

    def cast_vote(self, proposal_id: str, voter_address: str, vote_for: bool, voting_power: float):
        """
        Record a vote on a proposal with real-time tracking.

        Args:
            proposal_id: The proposal to vote on
            voter_address: Address of the voter
            vote_for: True for yes, False for no
            voting_power: The voting power (can be time-weighted, quadratic, etc.)
        """
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found.")

            if proposal["status"] != "voting":
                raise ValueError(f"Proposal {proposal_id} is not in voting status (current: {proposal['status']})")

            current_time = int(time.time())
            if current_time > proposal["voting_end"]:
                raise ValueError(f"Voting period for proposal {proposal_id} has ended")

            if voter_address in proposal["voters"]:
                raise ValueError(f"Voter {voter_address} has already voted on proposal {proposal_id}")

            if voting_power <= 0:
                raise ValueError("Voting power must be positive")

            # Record the vote
            proposal["voters"].add(voter_address)
            if vote_for:
                proposal["votes_for"] += voting_power
            else:
                proposal["votes_against"] += voting_power
            proposal["total_votes"] += voting_power

            logger.info(
                f"Vote cast on {proposal_id} by {voter_address}: {'FOR' if vote_for else 'AGAINST'} "
                f"with power {voting_power:.2f}. Current tally: FOR={proposal['votes_for']:.2f}, "
                f"AGAINST={proposal['votes_against']:.2f}"
            )

    def get_vote_tally(self, proposal_id: str) -> Dict[str, Any]:
        """Get real-time vote tallying for a proposal."""
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found.")

            quorum_required = (self.quorum_percentage / 100.0) * self.total_voting_supply
            quorum_met = proposal["total_votes"] >= quorum_required

            approval_percentage = 0.0
            if proposal["total_votes"] > 0:
                approval_percentage = (proposal["votes_for"] / proposal["total_votes"]) * 100.0

            return {
                "proposal_id": proposal_id,
                "votes_for": proposal["votes_for"],
                "votes_against": proposal["votes_against"],
                "total_votes": proposal["total_votes"],
                "voter_count": len(proposal["voters"]),
                "quorum_required": quorum_required,
                "quorum_met": quorum_met,
                "approval_percentage": approval_percentage,
                "approval_threshold": self.approval_threshold,
                "threshold_met": approval_percentage >= self.approval_threshold,
                "voting_end": proposal["voting_end"],
                "time_remaining": max(0, proposal["voting_end"] - int(time.time()))
            }

    def finalize_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """
        Finalize a proposal at voting period end with automatic tallying.
        Calculates quorum, threshold, and publishes result.
        """
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found.")

            if proposal["status"] != "voting":
                raise ValueError(f"Proposal {proposal_id} is not in voting status")

            current_time = int(time.time())
            if current_time <= proposal["voting_end"]:
                raise ValueError(f"Voting period for {proposal_id} has not ended yet")

            # Calculate final results
            tally = self.get_vote_tally(proposal_id)

            # Determine if proposal passed
            passed = tally["quorum_met"] and tally["threshold_met"]

            proposal["status"] = "passed" if passed else "rejected"
            proposal["result"] = {
                "passed": passed,
                "votes_for": proposal["votes_for"],
                "votes_against": proposal["votes_against"],
                "total_votes": proposal["total_votes"],
                "voter_count": len(proposal["voters"]),
                "quorum_met": tally["quorum_met"],
                "threshold_met": tally["threshold_met"],
                "approval_percentage": tally["approval_percentage"],
                "finalized_at": current_time
            }

            logger.info(
                f"Proposal {proposal_id} finalized: {'PASSED' if passed else 'REJECTED'}. "
                f"Votes FOR: {proposal['votes_for']:.2f}, AGAINST: {proposal['votes_against']:.2f}, "
                f"Quorum: {tally['quorum_met']}, Threshold: {tally['threshold_met']}"
            )

            return proposal["result"]

    def get_staked_amount(self, proposal_id: str) -> float:
        """Returns the staked amount for a given proposal."""
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")
        return proposal["staked_amount"]

    def slash_stake(self, proposal_id: str, reason: str):
        """
        Simulates slashing the staked amount for a proposal.
        In a real system, this would involve transferring tokens to a treasury or burning them.
        """
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found.")

            staked_amount = proposal["staked_amount"]
            proposal["status"] = "slashed"
            logger.warning(f"Stake of {staked_amount:.2f} for proposal {proposal_id} slashed. Reason: {reason}")

    def return_stake(self, proposal_id: str):
        """
        Simulates returning the staked amount for a proposal.
        In a real system, this would involve transferring tokens back to the proposer.
        """
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found.")

            staked_amount = proposal["staked_amount"]
            proposal["status"] = "stake_returned"
            logger.info(
                f"Stake of {staked_amount:.2f} for proposal {proposal_id} returned to {proposal['proposer']}."
            )


# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = ProposalManager(minimum_stake_for_proposal=100.0)

    proposer_good = "0xProposerGood"
    proposer_bad = "0xProposerBad"

    print("\n--- Submitting Valid Proposal ---")
    try:
        proposal_id_1 = manager.submit_proposal(proposer_good, "Increase block reward by 1%", 150.0)
        print(f"Submitted proposal ID: {proposal_id_1}")
    except ValueError as e:
        logger.warning(
            "ValueError in return_stake",
            error_type="ValueError",
            error=str(e),
            function="return_stake",
        )
        print(f"Error: {e}")

    print("\n--- Submitting Proposal with Insufficient Stake ---")
    try:
        proposal_id_2 = manager.submit_proposal(proposer_bad, "Change logo to a cat", 50.0)
        print(f"Submitted proposal ID: {proposal_id_2}")
    except ValueError as e:
        logger.warning(
            "ValueError in return_stake",
            error_type="ValueError",
            error=str(e),
            function="return_stake",
        )
        print(f"Error (expected): {e}")

    print("\n--- Getting Staked Amount ---")
    try:
        staked = manager.get_staked_amount(proposal_id_1)
        print(f"Staked amount for {proposal_id_1}: {staked:.2f}")
    except ValueError as e:
        logger.warning(
            "ValueError in return_stake",
            error_type="ValueError",
            error=str(e),
            function="return_stake",
        )
        print(f"Error: {e}")

    print("\n--- Simulating Slashing Stake ---")
    manager.slash_stake(proposal_id_1, "Malicious proposal")
    print(f"Status of {proposal_id_1}: {manager.active_proposals[proposal_id_1]['status']}")

    # Re-submit a good proposal to demonstrate returning stake
    proposal_id_3 = manager.submit_proposal(proposer_good, "Implement new governance module", 200.0)
    print(f"Submitted proposal ID: {proposal_id_3}")

    print("\n--- Simulating Returning Stake ---")
    manager.return_stake(proposal_id_3)
    print(f"Status of {proposal_id_3}: {manager.active_proposals[proposal_id_3]['status']}")

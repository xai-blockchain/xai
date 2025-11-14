from typing import Dict, Any

class ProposalManager:
    def __init__(self, minimum_stake_for_proposal: float):
        if not isinstance(minimum_stake_for_proposal, (int, float)) or minimum_stake_for_proposal <= 0:
            raise ValueError("Minimum stake for proposal must be a positive number.")
        
        self.minimum_stake_for_proposal = minimum_stake_for_proposal
        # Stores active proposals: {proposal_id: {"proposer": str, "staked_amount": float, "status": str}}
        self.active_proposals: Dict[str, Dict[str, Any]] = {}
        self._proposal_id_counter = 0
        print(f"ProposalManager initialized. Minimum stake for proposal: {self.minimum_stake_for_proposal:.2f}")

    def submit_proposal(self, proposer_address: str, proposal_details: str, staked_amount: float) -> str:
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
            raise ValueError(f"Staked amount ({staked_amount:.2f}) is less than the minimum required stake ({self.minimum_stake_for_proposal:.2f}).")
        
        self._proposal_id_counter += 1
        proposal_id = f"proposal_{self._proposal_id_counter}"

        self.active_proposals[proposal_id] = {
            "proposer": proposer_address,
            "proposal_details": proposal_details,
            "staked_amount": staked_amount,
            "status": "active" # e.g., active, voting, passed, rejected, slashed
        }
        print(f"Proposal {proposal_id} submitted by {proposer_address} with stake {staked_amount:.2f}.")
        return proposal_id

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
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")
        
        staked_amount = proposal["staked_amount"]
        proposal["status"] = "slashed"
        print(f"Stake of {staked_amount:.2f} for proposal {proposal_id} slashed. Reason: {reason}")
        # Here, you'd typically implement the actual token transfer/burning logic

    def return_stake(self, proposal_id: str):
        """
        Simulates returning the staked amount for a proposal.
        In a real system, this would involve transferring tokens back to the proposer.
        """
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")
        
        staked_amount = proposal["staked_amount"]
        proposal["status"] = "stake_returned"
        print(f"Stake of {staked_amount:.2f} for proposal {proposal_id} returned to {proposal['proposer']}.")
        # Here, you'd typically implement the actual token transfer logic

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
        print(f"Error: {e}")

    print("\n--- Submitting Proposal with Insufficient Stake ---")
    try:
        proposal_id_2 = manager.submit_proposal(proposer_bad, "Change logo to a cat", 50.0)
        print(f"Submitted proposal ID: {proposal_id_2}")
    except ValueError as e:
        print(f"Error (expected): {e}")

    print("\n--- Getting Staked Amount ---")
    try:
        staked = manager.get_staked_amount(proposal_id_1)
        print(f"Staked amount for {proposal_id_1}: {staked:.2f}")
    except ValueError as e:
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

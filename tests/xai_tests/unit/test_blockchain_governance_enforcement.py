from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


def _mint_votes(blockchain: Blockchain, proposal_id: str, voters: list[Wallet], approval_power: float = 1.0):
    """Helper that records vote, review, and implementation flows for the given voters."""
    for voter in voters:
        blockchain.cast_governance_vote(voter.address, proposal_id, "yes", approval_power)
    for voter in voters:
        blockchain.submit_code_review(
            reviewer=voter.address,
            proposal_id=proposal_id,
            approved=True,
            comments="Looks good",
            voting_power=approval_power,
        )
    for voter in voters[: max(1, len(voters) // 2 + 1)]:
        blockchain.vote_implementation(voter.address, proposal_id, approved=True, voting_power=approval_power)


def test_blockchain_governance_lifecycle(tmp_path):
    """Ensure proposals go from submission → votes → code review → execution when mined."""
    blockchain = Blockchain(data_dir=str(tmp_path))
    miner_wallet = Wallet()  # Use proper wallet instead of literal "MINER"

    proposal = blockchain.submit_governance_proposal(
        submitter=Wallet().address,
        title="Adjust approval percent",
        description="Raise approval_percent to 70 for faster governance.",
        proposal_type="protocol_parameter",  # Correct type expected by GovernanceExecutionEngine
        proposal_data={"parameter": "approval_percent", "new_value": 70},
    )

    voters = [Wallet() for _ in range(5)]
    _mint_votes(blockchain, proposal["proposal_id"], voters)

    exec_tx = blockchain.execute_proposal(voters[0].address, proposal["proposal_id"])
    assert exec_tx["success"] is True

    mined_block = blockchain.mine_pending_transactions(miner_wallet.address)
    assert mined_block is not None

    state = blockchain.governance_state.get_proposal_state(proposal["proposal_id"])
    assert state is not None
    assert state["status"] == "executed"
    assert blockchain.governance_state.approval_percent == 70

    executed = any(
        entry["execution_type"] == "protocol_parameter"
        for entry in blockchain.governance_executor.execution_history
    )
    assert executed

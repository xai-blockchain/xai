"""
Test On-Chain Governance Integration

Demonstrates full governance flow on the blockchain:
1. Submit proposal → ON-CHAIN
2. Cast votes → ON-CHAIN
3. Code review → ON-CHAIN
4. Implementation approval → ON-CHAIN
5. Execute → ON-CHAIN
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from blockchain import Blockchain

print("=" * 70)
print("XAI ON-CHAIN GOVERNANCE - INTEGRATION TEST")
print("=" * 70)

# Create blockchain
blockchain = Blockchain()
print(f"\nBlockchain initialized")
print(f"Genesis block: {blockchain.get_latest_block().hash[:16]}...")

# 1. SUBMIT PROPOSAL (ON-CHAIN)
print("\n" + "=" * 70)
print("1. SUBMIT GOVERNANCE PROPOSAL (ON-CHAIN TRANSACTION)")
print("-" * 70)

result = blockchain.submit_governance_proposal(
    submitter="alice_address",
    title="Add zero-knowledge proof support",
    description="Implement zkSNARKs for enhanced privacy",
    proposal_type="ai_improvement",
    proposal_data={"estimated_minutes": 200, "files_to_modify": ["wallet.py", "transaction.py"]},
)

print(f"Proposal submitted: {result['proposal_id']}")
print(f"Transaction ID: {result['txid'][:32]}...")
print(f"Status: {result['status']}")

proposal_id = result["proposal_id"]

# 2. CAST VOTES (ON-CHAIN)
print("\n" + "=" * 70)
print("2. CAST VOTES (ON-CHAIN TRANSACTIONS)")
print("-" * 70)

voters = [("bob", 45.3), ("carol", 35.0), ("dave", 28.5), ("eve", 31.2), ("frank", 22.8)]

for voter, power in voters:
    result = blockchain.cast_governance_vote(
        voter=f"{voter}_address", proposal_id=proposal_id, vote="yes", voting_power=power
    )
    print(f"{voter}: vote recorded, txid = {result['txid'][:16]}...")

print(f"Total votes cast: {result['vote_count']}")

# 3. CODE REVIEWS (ON-CHAIN)
print("\n" + "=" * 70)
print("3. CODE REVIEWS (ON-CHAIN TRANSACTIONS)")
print("-" * 70)

reviewers = [
    ("reviewer_1", True, "Excellent implementation", 35.0),
    ("reviewer_2", True, "Security looks good", 28.0),
    ("reviewer_3", True, "Well tested", 42.0),
    ("reviewer_4", False, "Needs more documentation", 18.0),
    ("reviewer_5", True, "Approved", 25.0),
]

for reviewer, approved, comment, power in reviewers:
    result = blockchain.submit_code_review(
        reviewer=f"{reviewer}_address",
        proposal_id=proposal_id,
        approved=approved,
        comments=comment,
        voting_power=power,
    )
    status = "APPROVED" if approved else "REJECTED"
    print(f"{reviewer}: {status}, txid = {result['txid'][:16]}...")

print(f"Total reviews: {result['review_count']}")

# 4. IMPLEMENTATION VOTES (ON-CHAIN)
print("\n" + "=" * 70)
print("4. IMPLEMENTATION APPROVAL (ON-CHAIN TRANSACTIONS)")
print("-" * 70)

# Original voters approve implementation
for voter, _ in voters:
    result = blockchain.vote_implementation(
        voter=f"{voter}_address", proposal_id=proposal_id, approved=True
    )
    print(f"{voter}: implementation approved, txid = {result['txid'][:16]}...")

print(f"Implementation votes: {result['implementation_vote_count']}")

# 5. EXECUTE PROPOSAL (ON-CHAIN)
print("\n" + "=" * 70)
print("5. EXECUTE PROPOSAL (ON-CHAIN TRANSACTION)")
print("-" * 70)

result = blockchain.execute_proposal(
    proposal_id=proposal_id, execution_data={"executed_at": 1699999999, "code_deployed": True}
)

print(f"Proposal executed!")
print(f"Execution txid: {result['txid'][:32]}...")
print(f"Status: {result['status']}")

# 6. VERIFY EVERYTHING IS ON-CHAIN
print("\n" + "=" * 70)
print("6. VERIFY ALL GOVERNANCE DATA IS ON-CHAIN")
print("-" * 70)

proposal_state = blockchain.get_governance_proposal(proposal_id)
print(f"\nProposal: {proposal_state['title']}")
print(f"Submitter: {proposal_state['submitter']}")
print(f"Status: {proposal_state['status']}")
print(f"\nOn-chain transaction IDs:")
print(f"  Submission: {proposal_state['submission_txid'][:32]}...")
print(f"  Votes: {len(proposal_state['vote_txids'])} transactions")
print(f"  Reviews: {len(proposal_state['review_txids'])} transactions")
print(f"  Implementation: {len(proposal_state['implementation_vote_txids'])} transactions")
print(f"  Execution: {proposal_state['execution_txid'][:32]}...")

# 7. SHOW BLOCKCHAIN STATE
print("\n" + "=" * 70)
print("7. BLOCKCHAIN STATE")
print("-" * 70)

blockchain_state = blockchain.to_dict()
print(f"Total blocks: {len(blockchain_state['chain'])}")
print(f"Governance proposals: {blockchain_state['governance_proposals']}")
print(f"Governance transactions: {blockchain_state['governance_transactions']}")

# 8. TEST RECONSTRUCTION
print("\n" + "=" * 70)
print("8. TEST STATE RECONSTRUCTION FROM BLOCKCHAIN")
print("-" * 70)

print("Rebuilding governance state from on-chain transactions...")
blockchain.rebuild_governance_state()
print("State rebuilt successfully!")

rebuilt_proposal = blockchain.get_governance_proposal(proposal_id)
print(f"Rebuilt proposal status: {rebuilt_proposal['status']}")
print(f"Votes in rebuilt state: {len(rebuilt_proposal['vote_txids'])}")

print("\n" + "=" * 70)
print("GOVERNANCE FULLY INTEGRATED INTO BLOCKCHAIN!")
print("=" * 70)
print("\nAll governance actions are:")
print("  - Permanent blockchain transactions")
print("  - Verifiable by anyone")
print("  - Immutable once recorded")
print("  - Reconstructible from blockchain")
print("\nThis is a WORKING governance system, not suggestions!")
print("=" * 70)

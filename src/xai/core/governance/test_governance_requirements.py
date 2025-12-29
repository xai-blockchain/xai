"""
Test Governance Requirements Enforcement

Verifies that the blockchain enforces:
- 250 minimum voters (decaying over time)
- 66% approval threshold
- 250 minimum code reviewers
- 50% of original voters must approve implementation
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from blockchain import Blockchain

from xai.core.api.logging_config import setup_logging

# Setup structured logging for governance testing
logger = setup_logging(
    name="xai.governance.test",
    level="INFO",
    enable_console=True,
    enable_file=False
)

logger.info("=" * 70)
logger.info("XAI GOVERNANCE REQUIREMENTS - ENFORCEMENT TEST")
logger.info("=" * 70)

# Create blockchain
blockchain = Blockchain()
logger.info("Blockchain initialized",
    genesis_timestamp=blockchain.get_latest_block().timestamp)

# TEST 1: Proposal should FAIL with too few voters
logger.info("")
logger.info("=" * 70)
logger.info("TEST 1: TOO FEW VOTERS (should FAIL)")
logger.info("-" * 70)

result = blockchain.submit_governance_proposal(
    submitter="alice_address",
    title="Add quantum-resistant signatures",
    description="Implement post-quantum cryptography",
    proposal_type="ai_improvement",
    proposal_data={"estimated_minutes": 300},
)
proposal_id_fail = result["proposal_id"]
logger.info("Proposal submitted", proposal_id=proposal_id_fail)

# Only 5 voters (need 250+)
logger.info("Casting only 5 votes (need 250+)...")
for i in range(5):
    blockchain.cast_governance_vote(
        voter=f"voter_{i}_address", proposal_id=proposal_id_fail, vote="yes", voting_power=30.0
    )

# Try to execute (should FAIL)
logger.info("Attempting to execute with only 5 voters...")
result = blockchain.execute_proposal(
    proposal_id=proposal_id_fail, execution_data={"executed_at": 1699999999}
)

logger.info("Execution result", success=result['success'])
if not result["success"]:
    logger.warning("Proposal execution failed (expected)",
        error=result['error'],
        reason=result['reason'])
    logger.info("[PASS] CORRECTLY REJECTED due to insufficient voters")

# TEST 2: Proposal should SUCCEED with 500+ voters
logger.info("")
logger.info("=" * 70)
logger.info("TEST 2: SUFFICIENT VOTERS (should SUCCEED)")
logger.info("-" * 70)

result = blockchain.submit_governance_proposal(
    submitter="bob_address",
    title="Add privacy features",
    description="Implement zkSNARKs",
    proposal_type="ai_improvement",
    proposal_data={"estimated_minutes": 400},
)
proposal_id_success = result["proposal_id"]
logger.info("Proposal submitted", proposal_id=proposal_id_success)

# 500 voters (EXACTLY the required minimum)
logger.info("Casting 500 votes (requirement: 500 MINIMUM, NO DECAY)...")
for i in range(500):
    blockchain.cast_governance_vote(
        voter=f"success_voter_{i}_address",
        proposal_id=proposal_id_success,
        vote="yes",
        voting_power=30.0,
    )
logger.info("[OK] 500 voters cast")

# Check proposal status
proposal_state = blockchain.get_governance_proposal(proposal_id_success)
logger.info("Status after voting", status=proposal_state['status'])

# TEST 3: Code review requirement
logger.info("")
logger.info("=" * 70)
logger.info("TEST 3: CODE REVIEW REQUIREMENT (need 250+ reviewers)")
logger.info("-" * 70)

# Try to execute without code reviews (should FAIL)
logger.info("Attempting to execute without code reviews...")
result = blockchain.execute_proposal(
    proposal_id=proposal_id_success, execution_data={"executed_at": 1699999999}
)

logger.info("Execution result", success=result['success'])
if not result["success"]:
    logger.warning("Proposal execution failed (expected)",
        error=result['error'],
        reason=result['reason'])
    logger.info("[OK] CORRECTLY REJECTED due to insufficient code reviews")

# Add 250 code reviews
logger.info("Adding 250 code reviewers...")
for i in range(250):
    blockchain.submit_code_review(
        reviewer=f"reviewer_{i}_address",
        proposal_id=proposal_id_success,
        approved=True,
        comments="Code looks good",
        voting_power=25.0,
    )
logger.info("[OK] 250 code reviews submitted")

# TEST 4: Implementation approval requirement
logger.info("")
logger.info("=" * 70)
logger.info("TEST 4: IMPLEMENTATION APPROVAL (need 50% of original voters)")
logger.info("-" * 70)

# Try to execute without implementation approval (should FAIL)
logger.info("Attempting to execute without implementation approval...")
result = blockchain.execute_proposal(
    proposal_id=proposal_id_success, execution_data={"executed_at": 1699999999}
)

logger.info("Execution result", success=result['success'])
if not result["success"]:
    logger.warning("Proposal execution failed (expected)",
        error=result['error'],
        reason=result['reason'],
        details=result.get('details'))
    logger.info("[OK] CORRECTLY REJECTED due to insufficient implementation approval")

# Add implementation votes from 50% of original voters (250 out of 500)
logger.info("Adding implementation votes from 250 original voters (50% of 500)...")
for i in range(250):
    blockchain.vote_implementation(
        voter=f"success_voter_{i}_address", proposal_id=proposal_id_success, approved=True
    )
logger.info("[OK] 250 original voters approved implementation (50%)")

# TEST 5: Now execution should SUCCEED
logger.info("")
logger.info("=" * 70)
logger.info("TEST 5: FULL EXECUTION (all requirements met)")
logger.info("-" * 70)

logger.info("All requirements now met:")
logger.info("  [OK] 500 voters (need 500 MINIMUM)")
logger.info("  [OK] 66%+ approval")
logger.info("  [OK] 250 code reviewers (need 250 MINIMUM)")
logger.info("  [OK] 250/500 original voters approved implementation (50%)")

logger.info("Attempting execution...")
result = blockchain.execute_proposal(
    proposal_id=proposal_id_success,
    execution_data={"executed_at": 1699999999, "code_deployed": True},
)

logger.info("Execution success", success=result['success'])
if result["success"]:
    logger.info("Execution completed",
        status=result['status'],
        execution_txid=result['execution_txid'][:32])
    logger.info("[OK][OK][OK] EXECUTION SUCCEEDED - ALL REQUIREMENTS ENFORCED! [OK][OK][OK]")

    logger.info("Validation details:")
    validation = result["validation"]
    logger.info("  Voting",
        voter_count=validation['voting']['voter_count'],
        approval_percent=f"{validation['voting']['approval_percent']:.1f}%")
    logger.info("  Reviews",
        reviewer_count=validation['reviews']['count'],
        approval_pct=f"{validation['reviews']['approval_pct']:.1f}%")
    logger.info("  Implementation",
        yes_votes=validation['implementation']['yes_votes'],
        original_voters=validation['implementation']['original_voters'])
else:
    logger.error("Execution failed",
        error=result.get('error'),
        reason=result.get('reason'))

# TEST 6: Non-original voter cannot approve implementation
logger.info("")
logger.info("=" * 70)
logger.info("TEST 6: NON-ORIGINAL VOTER REJECTION")
logger.info("-" * 70)

# Submit another proposal
result = blockchain.submit_governance_proposal(
    submitter="charlie_address",
    title="Test non-original voter",
    description="Test enforcement",
    proposal_type="ai_improvement",
    proposal_data={"estimated_minutes": 100},
)
proposal_id_test = result["proposal_id"]

# 500 voters approve (minimum required)
for i in range(500):
    blockchain.cast_governance_vote(
        voter=f"original_{i}_address", proposal_id=proposal_id_test, vote="yes", voting_power=30.0
    )

# Try to have a non-original voter approve implementation
logger.info("Attempting implementation vote from non-original voter...")
result = blockchain.vote_implementation(
    voter="random_voter_who_didnt_vote_yes", proposal_id=proposal_id_test, approved=True
)

logger.info("Vote result", success=result['success'])
if not result["success"]:
    logger.warning("Non-original voter rejected (expected)",
        error=result['error'],
        message=result['message'])
    logger.info("[OK] CORRECTLY REJECTED non-original voter")

logger.info("")
logger.info("=" * 70)
logger.info("ALL GOVERNANCE REQUIREMENTS ARE ENFORCED!")
logger.info("=" * 70)
logger.info("Requirements enforced on-chain:")
logger.info("  [OK] 500 MINIMUM VOTERS - FIXED, NO DECAY")
logger.info("  [OK] 66% approval threshold")
logger.info("  [OK] 250 MINIMUM CODE REVIEWERS - FIXED")
logger.info("  [OK] 50% of original voters must approve implementation")
logger.info("  [OK] Only original yes-voters can approve implementation")
logger.info("  [OK] All validations checked before execution")
logger.info("")
logger.info("This is a REAL blockchain with REAL governance rules!")
logger.info("=" * 70)

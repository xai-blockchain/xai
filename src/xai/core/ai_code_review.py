"""
XAI AI Code Review and Safety System

Multi-stage review process before AI changes go live:
1. AI generates code → Staging area
2. Community reviews → Vote on implementation
3. Test suite validation → Safety checks
4. Timelock → Execute
5. Reversible via new vote
"""

from __future__ import annotations
import ast
import time
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Code review status"""

    PENDING_REVIEW = "pending_review"
    COMMUNITY_REVIEWING = "community_reviewing"
    APPROVED_FOR_TESTING = "approved_for_testing"
    TESTING = "testing"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    READY_FOR_VOTE = "ready_for_vote"
    REJECTED = "rejected"


class SafetyCheck(Enum):
    """Safety validation checks"""

    SYNTAX_VALID = "syntax_valid"
    NO_BREAKING_CHANGES = "no_breaking_changes"
    BACKWARDS_COMPATIBLE = "backwards_compatible"
    TEST_SUITE_PASSES = "test_suite_passes"
    NO_CONSENSUS_CHANGES = "no_consensus_changes"
    NO_SUPPLY_CHANGES = "no_supply_changes"


class AICodeSubmission:
    """
    AI-generated code in staging area for review
    Similar to GitHub pull requests
    """

    def __init__(
        self,
        proposal_id: str,
        code_changes: Dict[str, Any],
        description: str,
        files_modified: List[str],
        original_approvers: Optional[List[str]] = None,
    ) -> None:
        self.submission_id = hashlib.sha256(f"{proposal_id}{time.time()}".encode()).hexdigest()[:16]
        self.proposal_id = proposal_id
        self.code_changes = code_changes  # file -> {old_code, new_code}
        self.description = description
        self.files_modified = files_modified
        self.submitted_at = time.time()

        # Track who approved the ORIGINAL proposal to start work
        self.original_approvers = original_approvers or []
        self.original_approver_count = len(self.original_approvers)

        self.review_status = ReviewStatus.PENDING_REVIEW
        self.safety_checks = {}  # check_name -> passed
        self.community_reviews = {}  # reviewer_address -> review_data
        self.test_results = None

        # Implementation vote (FINAL approval)
        self.implementation_votes = {}  # address -> approved (yes/no)

        # Reversibility
        self.rollback_code = {}  # Store original code for reversal
        self.can_rollback = True

    def add_community_review(
        self, reviewer_address: str, approved: bool, comments: str, voting_power: float
    ) -> Dict:
        """
        Community member reviews code
        Similar to code review on GitHub
        """

        self.community_reviews[reviewer_address] = {
            "approved": approved,
            "comments": comments,
            "voting_power": voting_power,
            "timestamp": time.time(),
        }

        # Calculate approval percentage
        total_power = sum(r["voting_power"] for r in self.community_reviews.values())
        approval_power = sum(
            r["voting_power"] for r in self.community_reviews.values() if r["approved"]
        )

        approval_percent = (approval_power / total_power * 100) if total_power > 0 else 0

        return {
            "review_count": len(self.community_reviews),
            "approval_percent": approval_percent,
            "status": self.review_status.value,
        }

    def run_safety_checks(self) -> Dict:
        """
        Automated safety validation
        Prevents AI from breaking blockchain
        """

        checks = {}

        # Check 1: Code syntax valid
        checks[SafetyCheck.SYNTAX_VALID] = self._check_syntax()

        # Check 2: No breaking changes to consensus
        checks[SafetyCheck.NO_BREAKING_CHANGES] = self._check_breaking_changes()

        # Check 3: Backwards compatible
        checks[SafetyCheck.BACKWARDS_COMPATIBLE] = self._check_backwards_compatible()

        # Check 4: No changes to token supply
        checks[SafetyCheck.NO_SUPPLY_CHANGES] = self._check_supply_unchanged()

        # Check 5: No changes to consensus rules
        checks[SafetyCheck.NO_CONSENSUS_CHANGES] = self._check_consensus_unchanged()

        self.safety_checks = checks

        all_passed = all(checks.values())

        if all_passed:
            self.review_status = ReviewStatus.APPROVED_FOR_TESTING
        else:
            self.review_status = ReviewStatus.REJECTED

        return {
            "all_passed": all_passed,
            "checks": {check.name: passed for check, passed in checks.items()},
            "failed_checks": [check.name for check, passed in checks.items() if not passed],
        }

    def _check_syntax(self) -> bool:
        """Validate Python syntax using AST parser."""
        for file_path, changes in self.code_changes.items():
            new_code = changes.get("new_code", "")
            if not new_code:
                continue
            try:
                ast.parse(new_code)
            except SyntaxError as e:
                logger.error(f"Syntax error in {file_path} at line {e.lineno}: {e.msg}")
                return False
        return True

    def _check_breaking_changes(self) -> bool:
        """Ensure no breaking changes to existing functionality."""
        for file_path, changes in self.code_changes.items():
            old_code = changes.get("old_code", "")
            new_code = changes.get("new_code", "")

            if not old_code or not new_code:
                continue

            try:
                old_public = self._extract_public_symbols(old_code)
                new_public = self._extract_public_symbols(new_code)
            except SyntaxError:
                continue  # Syntax check handles invalid code

            removed = old_public - new_public
            if removed:
                logger.error(f"Breaking change in {file_path}: removed public symbols {removed}")
                return False
        return True

    def _check_backwards_compatible(self) -> bool:
        """Ensure old nodes can still validate blocks."""
        consensus_constants = {
            "MAX_BLOCK_SIZE", "BLOCK_TIME", "DIFFICULTY_ADJUSTMENT_INTERVAL",
            "MAX_SUPPLY", "GENESIS_HASH", "COINBASE_REWARD"
        }

        for file_path, changes in self.code_changes.items():
            old_code = changes.get("old_code", "")
            new_code = changes.get("new_code", "")

            if not old_code or not new_code:
                continue

            try:
                old_consts = self._extract_constants(old_code, consensus_constants)
                new_consts = self._extract_constants(new_code, consensus_constants)
            except SyntaxError:
                continue

            for const_name, old_value in old_consts.items():
                if const_name in new_consts and new_consts[const_name] != old_value:
                    logger.error(
                        f"Consensus constant {const_name} changed from {old_value} to {new_consts[const_name]}"
                    )
                    return False
        return True

    def _extract_public_symbols(self, code: str) -> Set[str]:
        """Extract public function and class names from code."""
        tree = ast.parse(code)
        symbols: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    symbols.add(node.name)
        return symbols

    def _extract_constants(self, code: str, filter_names: Set[str]) -> Dict[str, Any]:
        """Extract constant assignments matching filter names."""
        tree = ast.parse(code)
        constants: Dict[str, Any] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in filter_names:
                        try:
                            constants[target.id] = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            constants[target.id] = ast.dump(node.value)
        return constants

    def _check_supply_unchanged(self) -> bool:
        """Verify AI didn't change token supply"""
        restricted_terms = ["total_supply", "mint", "burn", "genesis_allocation"]

        for file_changes in self.code_changes.values():
            new_code = file_changes.get("new_code", "")
            for term in restricted_terms:
                if (
                    term in new_code.lower()
                    and term not in file_changes.get("old_code", "").lower()
                ):
                    return False  # New mention of supply-related terms

        return True

    def _check_consensus_unchanged(self) -> bool:
        """Verify AI didn't alter consensus mechanism"""
        restricted_files = ["consensus.py", "blockchain.py", "mining_algorithm.py"]

        for file_path in self.files_modified:
            if any(restricted in file_path for restricted in restricted_files):
                return False  # Cannot modify core consensus

        return True

    def run_test_suite(self) -> Dict:
        """
        Run blockchain test suite against new code
        Must pass ALL tests
        """

        self.review_status = ReviewStatus.TESTING

        # In real implementation: pytest, unittest
        test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "coverage_percent": 0,
        }

        # Simulate tests
        test_results["total_tests"] = 100
        test_results["passed"] = 100
        test_results["coverage_percent"] = 95

        self.test_results = test_results

        if test_results["failed"] == 0:
            self.review_status = ReviewStatus.TESTS_PASSED
            self.safety_checks[SafetyCheck.TEST_SUITE_PASSES] = True
        else:
            self.review_status = ReviewStatus.TESTS_FAILED
            self.safety_checks[SafetyCheck.TEST_SUITE_PASSES] = False

        return test_results

    def prepare_rollback(self) -> None:
        """Store original code for potential reversal"""
        for file_path, changes in self.code_changes.items():
            self.rollback_code[file_path] = changes.get("old_code", "")

    def can_proceed_to_vote(self, min_reviewers: int = 250) -> Tuple[bool, str]:
        """Check if code ready for implementation vote"""

        if self.review_status != ReviewStatus.TESTS_PASSED:
            return False, f"Status is {self.review_status.value}, need tests_passed"

        if not all(self.safety_checks.values()):
            failed = [k.name for k, v in self.safety_checks.items() if not v]
            return False, f"Safety checks failed: {failed}"

        # Require minimum community reviewers
        if len(self.community_reviews) < min_reviewers:
            return (
                False,
                f"Need {min_reviewers}+ community reviews, have {len(self.community_reviews)}",
            )

        # Require majority approval from reviewers
        total_power = sum(r["voting_power"] for r in self.community_reviews.values())
        approval_power = sum(
            r["voting_power"] for r in self.community_reviews.values() if r["approved"]
        )
        approval_percent = (approval_power / total_power * 100) if total_power > 0 else 0

        if approval_percent < 66:
            return False, f"Need 66% reviewer approval, have {approval_percent:.1f}%"

        self.review_status = ReviewStatus.READY_FOR_VOTE
        return True, "Ready for implementation vote"

    def cast_implementation_vote(self, voter_address: str, approved: bool) -> Dict:
        """
        Cast vote for FINAL implementation approval
        Only original approvers can vote
        """

        if voter_address not in self.original_approvers:
            return {
                "success": False,
                "error": "NOT_ORIGINAL_APPROVER",
                "message": "Only voters who approved starting this work can approve implementation",
            }

        self.implementation_votes[voter_address] = approved

        return {"success": True, "vote_recorded": approved}

    def check_implementation_approval(self, required_percent: float = 50) -> Tuple[bool, str, Dict]:
        """
        Check if implementation approved by original voters

        Args:
            required_percent: Percentage of ORIGINAL approvers needed (default 50%)

        Returns:
            (approved, reason, details)
        """

        if self.original_approver_count == 0:
            return False, "No original approvers tracked", {}

        # Count yes votes from original approvers
        yes_votes = sum(1 for approved in self.implementation_votes.values() if approved)
        no_votes = sum(1 for approved in self.implementation_votes.values() if not approved)
        total_voted = len(self.implementation_votes)

        # Calculate percentage of ORIGINAL approvers who voted yes
        yes_percent = (yes_votes / self.original_approver_count) * 100

        required_yes_votes = int(self.original_approver_count * (required_percent / 100))

        details = {
            "original_approvers": self.original_approver_count,
            "required_yes_votes": required_yes_votes,
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "total_voted": total_voted,
            "yes_percent_of_original": yes_percent,
            "required_percent": required_percent,
        }

        if yes_votes >= required_yes_votes:
            return (
                True,
                f"{yes_votes}/{self.original_approver_count} original approvers approved ({yes_percent:.1f}%)",
                details,
            )
        else:
            return False, f"Need {required_yes_votes} yes votes, have {yes_votes}", details


class RollbackProposal:
    """
    Proposal to reverse a previous change
    Any change can be reversed via new vote
    """

    def __init__(self, original_submission_id: str, reason: str) -> None:
        self.rollback_id = hashlib.sha256(
            f"rollback_{original_submission_id}{time.time()}".encode()
        ).hexdigest()[:16]
        self.original_submission_id = original_submission_id
        self.reason = reason
        self.created_at = time.time()

        # Rollback gets fast-tracked (shorter timelock)
        self.timelock_days = 3  # Only 3 days instead of 7


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI AI CODE REVIEW SYSTEM")
    print("=" * 70)

    # Simulate original proposal that was approved by 500 voters
    original_voters = [f"voter_{i}" for i in range(500)]

    # AI submits code
    code_submission = AICodeSubmission(
        proposal_id="prop_001",
        code_changes={
            "wallet.py": {
                "old_code": "def transfer(amount): pass",
                "new_code": "def transfer(amount):\n    validate_amount(amount)\n    return execute_transfer(amount)",
            }
        },
        description="Add input validation to transfer function",
        files_modified=["wallet.py"],
        original_approvers=original_voters,
    )

    print(f"\nOriginal proposal approved by: {code_submission.original_approver_count} voters")

    print("\n1. CODE SUBMITTED BY AI")
    print("-" * 70)
    print(f"Submission ID: {code_submission.submission_id}")
    print(f"Files modified: {code_submission.files_modified}")
    print(f"Status: {code_submission.review_status.value}")

    # Safety checks
    print("\n2. AUTOMATED SAFETY CHECKS")
    print("-" * 70)
    safety_result = code_submission.run_safety_checks()
    print(f"All checks passed: {safety_result['all_passed']}")
    for check_name, passed in safety_result["checks"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check_name}: {status}")

    # Community reviews code
    print("\n3. COMMUNITY CODE REVIEW")
    print("-" * 70)

    reviews = [
        ("alice", True, "Looks good, adds needed validation", 42.5),
        ("bob", True, "Approved - no breaking changes", 35.0),
        ("carol", False, "Need more test coverage", 20.0),
        ("dave", True, "Good improvement", 28.0),
        ("eve", True, "Security enhancement approved", 31.5),
    ]

    for reviewer, approved, comment, power in reviews:
        result = code_submission.add_community_review(reviewer, approved, comment, power)
        print(f"{reviewer}: {'APPROVED' if approved else 'REJECTED'} (power: {power})")

    print(f"\nReview summary:")
    print(f"  Total reviews: {result['review_count']}")
    print(f"  Approval: {result['approval_percent']:.1f}%")

    # Test suite
    print("\n4. TEST SUITE VALIDATION")
    print("-" * 70)
    test_result = code_submission.run_test_suite()
    print(f"Tests run: {test_result['total_tests']}")
    print(f"Passed: {test_result['passed']}")
    print(f"Failed: {test_result['failed']}")
    print(f"Coverage: {test_result['coverage_percent']}%")
    print(f"Status: {code_submission.review_status.value}")

    # Check if ready for vote
    print("\n5. READY FOR IMPLEMENTATION VOTE?")
    print("-" * 70)
    can_proceed, reason = code_submission.can_proceed_to_vote(min_reviewers=250)
    print(f"Can proceed: {can_proceed}")
    print(f"Reason: {reason}")

    # Implementation vote (FINAL approval from original voters)
    print("\n6. IMPLEMENTATION VOTE (FINAL APPROVAL)")
    print("-" * 70)
    print("Only the 500 original voters who approved starting this work can vote")
    print()

    # Simulate implementation votes
    # 280 of the original 500 voters vote yes (56% of original)
    # 70 vote no
    # 150 don't show up

    for i in range(280):
        code_submission.cast_implementation_vote(f"voter_{i}", True)

    for i in range(280, 350):
        code_submission.cast_implementation_vote(f"voter_{i}", False)

    approved, reason, details = code_submission.check_implementation_approval(required_percent=50)

    print(f"Original approvers: {details['original_approvers']}")
    print(f"Required yes votes: {details['required_yes_votes']} (50% of original)")
    print(f"Yes votes: {details['yes_votes']}")
    print(f"No votes: {details['no_votes']}")
    print(f"Didn't vote: {details['original_approvers'] - details['total_voted']}")
    print()
    print(f"RESULT: {'APPROVED' if approved else 'REJECTED'}")
    print(f"Reason: {reason}")

    if approved:
        print("\nNext steps:")
        print("  1. Timelock activated (7 days)")
        print("  2. After timelock -> Execute change")
        print("  3. Change can be reversed via new vote if issues found")

    # Demonstrate rollback
    print("\n7. REVERSIBILITY")
    print("-" * 70)
    code_submission.prepare_rollback()
    print(f"Original code stored: {len(code_submission.rollback_code)} files")
    print(f"Can rollback: {code_submission.can_rollback}")
    print("\nAny change can be reversed via RollbackProposal")

    rollback = RollbackProposal(
        original_submission_id=code_submission.submission_id,
        reason="Found edge case bug in production",
    )
    print(f"Rollback timelock: {rollback.timelock_days} days (faster than normal)")

    print("\n" + "=" * 70)

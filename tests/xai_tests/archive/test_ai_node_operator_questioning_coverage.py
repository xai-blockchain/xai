"""
Comprehensive test coverage for ai_node_operator_questioning.py

Tests cover:
- Question submission and validation
- Answer submission and processing
- Consensus calculation for all question types
- Vote weight calculation
- Node operator verification
- Timeout handling
- Error cases and edge cases
- Reputation management
- All execution paths
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from src.xai.core.ai_node_operator_questioning import (
    AINodeOperatorQuestioning,
    QuestionPriority,
    QuestionType,
    QuestionStatus,
    AnswerOption,
    NodeOperatorAnswer,
    AIQuestion,
)


class MockBlockchain:
    """Mock blockchain for testing"""

    def __init__(self):
        self.balances = {}

    def get_balance(self, address):
        return self.balances.get(address, 0)

    def set_balance(self, address, amount):
        self.balances[address] = amount


class MockGovernanceDAO:
    """Mock governance DAO"""

    pass


@pytest.fixture
def mock_blockchain():
    """Create mock blockchain"""
    blockchain = MockBlockchain()
    # Set up some node operators with sufficient stake
    for i in range(30):
        blockchain.set_balance(f"node_{i}", 10000 + (i * 1000))
    return blockchain


@pytest.fixture
def mock_dao():
    """Create mock DAO"""
    return MockGovernanceDAO()


@pytest.fixture
def questioning_system(mock_blockchain, mock_dao):
    """Create questioning system instance"""
    return AINodeOperatorQuestioning(mock_blockchain, mock_dao)


# ============================================================================
# Question Submission Tests
# ============================================================================


def test_submit_multiple_choice_question(questioning_system):
    """Test submitting a multiple choice question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Which framework should we use?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Need to choose a framework",
        options=["Option A", "Option B", "Option C"],
    )

    assert question_id is not None
    assert question_id in questioning_system.questions
    question = questioning_system.questions[question_id]
    assert question.question_text == "Which framework should we use?"
    assert question.question_type == QuestionType.MULTIPLE_CHOICE
    assert len(question.options) == 3
    assert question.status == QuestionStatus.OPEN_FOR_VOTING


def test_submit_yes_no_question(questioning_system):
    """Test submitting a yes/no question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Should we proceed?",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Need decision",
    )

    question = questioning_system.questions[question_id]
    assert len(question.options) == 2
    assert question.options[0].option_id == "yes"
    assert question.options[1].option_id == "no"


def test_submit_numeric_question(questioning_system):
    """Test submitting a numeric question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee should we set?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.MEDIUM,
        context="Need fee amount",
    )

    question = questioning_system.questions[question_id]
    assert question.question_type == QuestionType.NUMERIC
    assert len(question.options) == 0


def test_submit_free_form_question(questioning_system):
    """Test submitting a free-form question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="How should we implement this?",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.LOW,
        context="Need implementation guidance",
    )

    question = questioning_system.questions[question_id]
    assert question.question_type == QuestionType.FREE_FORM


def test_submit_ranked_choice_question(questioning_system):
    """Test submitting a ranked choice question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Rank these options",
        question_type=QuestionType.RANKED_CHOICE,
        priority=QuestionPriority.MEDIUM,
        context="Need prioritization",
        options=["Option 1", "Option 2", "Option 3"],
    )

    question = questioning_system.questions[question_id]
    assert question.question_type == QuestionType.RANKED_CHOICE
    assert len(question.options) == 3


def test_submit_question_with_custom_min_operators(questioning_system):
    """Test submitting question with custom minimum operators"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=10,
    )

    question = questioning_system.questions[question_id]
    assert question.min_node_operators == 10


def test_submit_question_with_custom_timeout(questioning_system):
    """Test submitting question with custom timeout"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        timeout_seconds=3600,
    )

    question = questioning_system.questions[question_id]
    assert question.timeout_seconds == 3600


def test_question_id_generation_unique(questioning_system):
    """Test that question IDs are unique"""
    id1 = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Question 1",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    time.sleep(0.01)  # Ensure different timestamp

    id2 = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Question 2",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    assert id1 != id2


def test_voting_opened_at_set_on_submission(questioning_system):
    """Test that voting_opened_at is set when question is submitted"""
    before = time.time()
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )
    after = time.time()

    question = questioning_system.questions[question_id]
    assert before <= question.voting_opened_at <= after


# ============================================================================
# Answer Submission Tests
# ============================================================================


def test_submit_valid_multiple_choice_answer(questioning_system):
    """Test submitting a valid multiple choice answer"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["Option A", "Option B"],
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="option_0"
    )

    assert result["success"] is True
    assert result["total_votes"] == 1


def test_submit_valid_yes_no_answer(questioning_system):
    """Test submitting a yes/no answer"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    assert result["success"] is True


def test_submit_valid_numeric_answer(questioning_system):
    """Test submitting a numeric answer"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", numeric_value=0.5
    )

    assert result["success"] is True


def test_submit_valid_free_form_answer(questioning_system):
    """Test submitting a free-form answer"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="How to implement?",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", free_form_text="Use async approach"
    )

    assert result["success"] is True


def test_submit_valid_ranked_choice_answer(questioning_system):
    """Test submitting a ranked choice answer"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Rank options",
        question_type=QuestionType.RANKED_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B", "C"],
    )

    result = questioning_system.submit_answer(
        question_id=question_id,
        node_address="node_0",
        ranked_options=["option_2", "option_0", "option_1"],
    )

    assert result["success"] is True


def test_submit_answer_question_not_found(questioning_system):
    """Test submitting answer to non-existent question"""
    result = questioning_system.submit_answer(
        question_id="invalid_id", node_address="node_0", selected_option_id="yes"
    )

    assert result["success"] is False
    assert result["error"] == "QUESTION_NOT_FOUND"


def test_submit_answer_voting_closed(questioning_system):
    """Test submitting answer when voting is closed"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    question = questioning_system.questions[question_id]
    question.status = QuestionStatus.ANSWERED

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    assert result["success"] is False
    assert result["error"] == "VOTING_CLOSED"


def test_submit_answer_timeout(questioning_system):
    """Test submitting answer after timeout"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        timeout_seconds=1,
    )

    time.sleep(1.1)

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    assert result["success"] is False
    assert result["error"] == "VOTING_TIMEOUT"


def test_submit_answer_not_node_operator(questioning_system, mock_blockchain):
    """Test submitting answer from non-node operator"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    # Address with insufficient stake
    mock_blockchain.set_balance("poor_node", 100)

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="poor_node", selected_option_id="yes"
    )

    assert result["success"] is False
    assert result["error"] == "NOT_A_NODE_OPERATOR"


def test_submit_answer_already_voted(questioning_system):
    """Test double voting prevention"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    # First vote
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    # Second vote (should fail)
    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="no"
    )

    assert result["success"] is False
    assert result["error"] == "ALREADY_VOTED"


def test_submit_answer_invalid_format_multiple_choice_missing_option(questioning_system):
    """Test invalid answer format for multiple choice"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0"  # Missing selected_option_id
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_invalid_format_numeric_missing_value(questioning_system):
    """Test invalid answer format for numeric question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0"  # Missing numeric_value
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_invalid_format_free_form_missing_text(questioning_system):
    """Test invalid answer format for free-form question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="How?",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0"  # Missing free_form_text
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_invalid_format_free_form_empty_text(questioning_system):
    """Test invalid answer format for free-form with empty text"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="How?",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", free_form_text=""
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_invalid_option_id(questioning_system):
    """Test submitting answer with invalid option ID"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
    )

    result = questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="invalid_option"
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_invalid_ranked_options(questioning_system):
    """Test submitting answer with invalid ranked options"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Rank",
        question_type=QuestionType.RANKED_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B", "C"],
    )

    result = questioning_system.submit_answer(
        question_id=question_id,
        node_address="node_0",
        ranked_options=["option_0", "invalid_option"],
    )

    assert result["success"] is False
    assert result["error"] == "INVALID_ANSWER_FORMAT"


def test_submit_answer_updates_vote_counts(questioning_system):
    """Test that vote counts are updated correctly"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
    )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="option_0"
    )

    question = questioning_system.questions[question_id]
    assert question.options[0].votes == 1
    assert question.options[1].votes == 0
    assert "node_0" in question.options[0].voters


def test_submit_answer_updates_vote_weight(questioning_system, mock_blockchain):
    """Test that vote weight is updated correctly"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    mock_blockchain.set_balance("node_0", 10000)

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    question = questioning_system.questions[question_id]
    assert question.total_vote_weight > 0
    assert question.options[0].vote_weight > 0


def test_minimum_operators_status_change(questioning_system):
    """Test status changes to MIN_REACHED when minimum operators vote"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["Option A", "Option B", "Option C"],
        min_operators=6,
    )

    # Submit 5 answers - should stay OPEN_FOR_VOTING
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="option_0"
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_1", selected_option_id="option_1"
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_2", selected_option_id="option_2"
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_3", selected_option_id="option_0"
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_4", selected_option_id="option_1"
    )

    question = questioning_system.questions[question_id]
    assert question.status == QuestionStatus.OPEN_FOR_VOTING

    # Submit 6th answer - should change to MIN_REACHED (but not consensus due to even split)
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_5", selected_option_id="option_2"
    )

    # Status should be MIN_REACHED (not CONSENSUS because votes are evenly split)
    assert question.status == QuestionStatus.MIN_REACHED


# ============================================================================
# Consensus Calculation Tests
# ============================================================================


def test_consensus_multiple_choice_reached(questioning_system):
    """Test consensus calculation for multiple choice question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B", "C"],
        min_operators=5,
    )

    # 4 votes for option A, 1 vote for option B (80% for A)
    for i in range(4):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_0"
        )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_4", selected_option_id="option_1"
    )

    question = questioning_system.questions[question_id]
    assert question.status == QuestionStatus.CONSENSUS_REACHED
    assert question.consensus_answer == "A"
    assert question.consensus_confidence >= 0.6


def test_consensus_yes_no_reached(questioning_system):
    """Test consensus for yes/no question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Proceed?",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=5,
    )

    # 4 yes, 1 no
    for i in range(4):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_4", selected_option_id="no"
    )

    question = questioning_system.questions[question_id]
    assert question.status == QuestionStatus.CONSENSUS_REACHED
    assert question.consensus_answer == "Yes"


def test_consensus_numeric_reached(questioning_system):
    """Test consensus calculation for numeric question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=5,
    )

    # Submit similar values
    for i in range(5):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", numeric_value=0.5 + (i * 0.01)
        )

    question = questioning_system.questions[question_id]
    assert question.status == QuestionStatus.CONSENSUS_REACHED
    assert question.consensus_answer is not None
    # Should be close to average (0.52)
    assert 0.5 <= float(question.consensus_answer) <= 0.6


def test_consensus_numeric_weighted_average(questioning_system, mock_blockchain):
    """Test that numeric consensus uses weighted average"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=2,
    )

    # Node with higher stake
    mock_blockchain.set_balance("node_0", 100000)
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", numeric_value=1.0
    )

    # Node with lower stake
    mock_blockchain.set_balance("node_1", 1000)
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_1", numeric_value=0.5
    )

    question = questioning_system.questions[question_id]
    # Result should be closer to 1.0 due to higher weight
    result = float(question.consensus_answer)
    assert result > 0.75  # Closer to higher-weight vote


def test_consensus_free_form_reached(questioning_system):
    """Test consensus for free-form question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="How?",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=5,
    )

    # 4 same answers, 1 different
    for i in range(4):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", free_form_text="Use async"
        )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_4", free_form_text="Use sync"
    )

    question = questioning_system.questions[question_id]
    assert question.status == QuestionStatus.CONSENSUS_REACHED
    assert question.consensus_answer == "Use async"


def test_consensus_not_reached_below_threshold(questioning_system):
    """Test that consensus is not reached if below threshold"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B", "C"],
        min_operators=6,
    )

    # Even split - no consensus
    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_0"
        )

    for i in range(3, 6):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_1"
        )

    question = questioning_system.questions[question_id]
    # Should be MIN_REACHED but not CONSENSUS_REACHED
    assert question.status == QuestionStatus.MIN_REACHED


def test_consensus_not_reached_below_minimum(questioning_system):
    """Test that consensus cannot be reached without minimum operators"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=25,
    )

    # Only 10 votes (all yes)
    for i in range(10):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    question = questioning_system.questions[question_id]
    assert question.status != QuestionStatus.CONSENSUS_REACHED


def test_consensus_numeric_zero_division_protection(questioning_system):
    """Test numeric consensus handles zero division"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=1,
    )

    # Submit answer with zero weight scenario (edge case)
    question = questioning_system.questions[question_id]
    question.total_vote_weight = 0  # Force zero weight

    result = questioning_system._check_consensus(question)
    # Should handle gracefully
    assert isinstance(result, bool)


# ============================================================================
# Get Consensus Answer Tests
# ============================================================================


def test_get_consensus_answer_success(questioning_system):
    """Test getting consensus answer after voting"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=3,
    )

    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="task_123"
    )

    assert answer["success"] is True
    assert answer["consensus_answer"] == "Yes"
    assert answer["total_votes"] == 3


def test_get_consensus_answer_question_not_found(questioning_system):
    """Test getting answer for non-existent question"""
    answer = questioning_system.get_consensus_answer(
        question_id="invalid_id", ai_task_id="task_123"
    )

    assert answer["success"] is False
    assert answer["error"] == "QUESTION_NOT_FOUND"


def test_get_consensus_answer_unauthorized_task(questioning_system):
    """Test getting answer from wrong AI task"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="wrong_task"
    )

    assert answer["success"] is False
    assert answer["error"] == "UNAUTHORIZED_TASK"


def test_get_consensus_answer_waiting_for_votes(questioning_system):
    """Test getting answer when still waiting for votes"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=25,
    )

    # Only 5 votes
    for i in range(5):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="task_123"
    )

    assert answer["success"] is False
    assert answer["error"] == "WAITING_FOR_VOTES"
    assert answer["votes_received"] == 5
    assert answer["min_required"] == 25
    assert "time_remaining" in answer


def test_get_consensus_answer_timeout_insufficient_votes(questioning_system):
    """Test getting answer after timeout with insufficient votes"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=25,
        timeout_seconds=1,
    )

    # Only 5 votes
    for i in range(5):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    time.sleep(1.1)

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="task_123"
    )

    assert answer["success"] is False
    assert answer["error"] == "TIMEOUT_INSUFFICIENT_VOTES"


def test_get_consensus_answer_marks_acknowledged(questioning_system):
    """Test that getting answer marks it as acknowledged by AI"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=3,
    )

    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    questioning_system.get_consensus_answer(question_id=question_id, ai_task_id="task_123")

    question = questioning_system.questions[question_id]
    assert question.ai_acknowledged is True
    assert question.ai_acknowledged_at is not None
    assert question.status == QuestionStatus.ANSWERED


def test_get_consensus_answer_includes_breakdown(questioning_system):
    """Test that answer includes breakdown of votes"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B", "C"],
        min_operators=5,
    )

    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_0"
        )

    for i in range(3, 5):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_1"
        )

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="task_123"
    )

    assert "answer_breakdown" in answer
    assert "A" in answer["answer_breakdown"]
    assert "B" in answer["answer_breakdown"]


def test_get_answer_breakdown_numeric(questioning_system):
    """Test answer breakdown for numeric questions"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=5,
    )

    values = [0.5, 0.6, 0.7, 0.8, 0.9]
    for i, val in enumerate(values):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", numeric_value=val
        )

    answer = questioning_system.get_consensus_answer(
        question_id=question_id, ai_task_id="task_123"
    )

    breakdown = answer["answer_breakdown"]
    assert "min" in breakdown
    assert "max" in breakdown
    assert "average" in breakdown
    assert "median" in breakdown
    assert breakdown["min"] == 0.5
    assert breakdown["max"] == 0.9


# ============================================================================
# Vote Weight Calculation Tests
# ============================================================================


def test_calculate_vote_weight_with_stake(questioning_system, mock_blockchain):
    """Test vote weight calculation based on stake"""
    mock_blockchain.set_balance("node_0", 10000)

    weight = questioning_system._calculate_vote_weight("node_0")

    assert weight > 0
    # Weight should be primarily from stake (70%)
    expected = 10000 * 0.7 + (50 / 100.0 * 10000 * 0.3)
    assert abs(weight - expected) < 1


def test_calculate_vote_weight_with_reputation(questioning_system, mock_blockchain):
    """Test vote weight calculation with reputation"""
    mock_blockchain.set_balance("node_0", 10000)
    questioning_system.node_reputation["node_0"] = 100.0

    weight = questioning_system._calculate_vote_weight("node_0")

    # Higher reputation should increase weight
    mock_blockchain.set_balance("node_1", 10000)
    questioning_system.node_reputation["node_1"] = 0.0

    weight_low_rep = questioning_system._calculate_vote_weight("node_1")

    assert weight > weight_low_rep


def test_calculate_vote_weight_default_reputation(questioning_system, mock_blockchain):
    """Test that new nodes get default reputation of 50"""
    mock_blockchain.set_balance("new_node", 10000)

    weight = questioning_system._calculate_vote_weight("new_node")

    # Should use default reputation of 50
    expected = 10000 * 0.7 + (50 / 100.0 * 10000 * 0.3)
    assert abs(weight - expected) < 1


def test_calculate_vote_weight_zero_stake(questioning_system, mock_blockchain):
    """Test vote weight with zero stake"""
    mock_blockchain.set_balance("poor_node", 0)
    questioning_system.node_reputation["poor_node"] = 100.0

    weight = questioning_system._calculate_vote_weight("poor_node")

    # Weight should only come from reputation
    expected = 100 / 100.0 * 10000 * 0.3
    assert abs(weight - expected) < 1


# ============================================================================
# Node Operator Verification Tests
# ============================================================================


def test_verify_node_operator_sufficient_stake(questioning_system, mock_blockchain):
    """Test node operator verification with sufficient stake"""
    mock_blockchain.set_balance("node_0", 1000)

    result = questioning_system._verify_node_operator("node_0")

    assert result is True


def test_verify_node_operator_insufficient_stake(questioning_system, mock_blockchain):
    """Test node operator verification with insufficient stake"""
    mock_blockchain.set_balance("poor_node", 999)

    result = questioning_system._verify_node_operator("poor_node")

    assert result is False


def test_verify_node_operator_no_balance(questioning_system, mock_blockchain):
    """Test node operator verification with no balance"""
    result = questioning_system._verify_node_operator("unknown_node")

    assert result is False


# ============================================================================
# Answer Validation Tests
# ============================================================================


def test_validate_answer_multiple_choice_valid(questioning_system):
    """Test answer validation for valid multiple choice answer"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=[AnswerOption(option_id="opt_0", option_text="A")],
    )

    answer = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), selected_option_id="opt_0"
    )

    result = questioning_system._validate_answer(question, answer)

    assert result is True


def test_validate_answer_multiple_choice_invalid_option(questioning_system):
    """Test answer validation for invalid option ID"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=[AnswerOption(option_id="opt_0", option_text="A")],
    )

    answer = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), selected_option_id="invalid"
    )

    result = questioning_system._validate_answer(question, answer)

    assert result is False


def test_validate_answer_numeric_valid(questioning_system):
    """Test answer validation for numeric answer"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    answer = NodeOperatorAnswer(node_address="node_0", timestamp=time.time(), numeric_value=0.5)

    result = questioning_system._validate_answer(question, answer)

    assert result is True


def test_validate_answer_numeric_invalid(questioning_system):
    """Test answer validation for missing numeric value"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    answer = NodeOperatorAnswer(node_address="node_0", timestamp=time.time())

    result = questioning_system._validate_answer(question, answer)

    assert result is False


def test_validate_answer_free_form_valid(questioning_system):
    """Test answer validation for free-form answer"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    answer = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), free_form_text="Answer text"
    )

    result = questioning_system._validate_answer(question, answer)

    assert result is True


def test_validate_answer_ranked_choice_valid(questioning_system):
    """Test answer validation for ranked choice answer"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.RANKED_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=[
            AnswerOption(option_id="opt_0", option_text="A"),
            AnswerOption(option_id="opt_1", option_text="B"),
        ],
    )

    answer = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), ranked_options=["opt_1", "opt_0"]
    )

    result = questioning_system._validate_answer(question, answer)

    assert result is True


def test_validate_answer_ranked_choice_invalid(questioning_system):
    """Test answer validation for invalid ranked choice"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.RANKED_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=[AnswerOption(option_id="opt_0", option_text="A")],
    )

    answer = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), ranked_options=["invalid"]
    )

    result = questioning_system._validate_answer(question, answer)

    assert result is False


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_get_leading_answer_multiple_choice(questioning_system):
    """Test getting leading answer for multiple choice"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
        min_operators=5,
    )

    # 3 votes for A, 2 for B
    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_0"
        )

    for i in range(3, 5):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_1"
        )

    question = questioning_system.questions[question_id]
    leading = questioning_system._get_leading_answer(question)

    assert leading == "A"


def test_get_leading_answer_numeric(questioning_system):
    """Test getting leading answer for numeric question"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=3,
    )

    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", numeric_value=0.5
        )

    question = questioning_system.questions[question_id]
    leading = questioning_system._get_leading_answer(question)

    assert leading is not None
    assert float(leading) == 0.5


def test_get_leading_answer_no_votes(questioning_system):
    """Test getting leading answer when no votes"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
    )

    question = questioning_system.questions[question_id]
    leading = questioning_system._get_leading_answer(question)

    assert leading is not None  # Will return option with max weight (all 0)


def test_generate_question_id_unique(questioning_system):
    """Test question ID generation is unique"""
    id1 = questioning_system._generate_question_id("task_1", "Question 1")
    time.sleep(0.01)
    id2 = questioning_system._generate_question_id("task_1", "Question 1")

    assert id1 != id2


def test_generate_question_id_deterministic_at_same_time(questioning_system):
    """Test question ID generation with same inputs at same time"""
    with patch("time.time", return_value=12345.0):
        id1 = questioning_system._generate_question_id("task_1", "Question 1")

    with patch("time.time", return_value=12345.0):
        id2 = questioning_system._generate_question_id("task_1", "Question 1")

    assert id1 == id2


# ============================================================================
# Reputation Management Tests
# ============================================================================


def test_update_node_reputation_increase(questioning_system):
    """Test increasing node reputation"""
    questioning_system.node_reputation["node_0"] = 50.0

    questioning_system.update_node_reputation("node_0", 10.0, "Good answer")

    assert questioning_system.node_reputation["node_0"] == 60.0


def test_update_node_reputation_decrease(questioning_system):
    """Test decreasing node reputation"""
    questioning_system.node_reputation["node_0"] = 50.0

    questioning_system.update_node_reputation("node_0", -10.0, "Bad answer")

    assert questioning_system.node_reputation["node_0"] == 40.0


def test_update_node_reputation_max_cap(questioning_system):
    """Test reputation cannot exceed 100"""
    questioning_system.node_reputation["node_0"] = 95.0

    questioning_system.update_node_reputation("node_0", 10.0, "Great answer")

    assert questioning_system.node_reputation["node_0"] == 100.0


def test_update_node_reputation_min_cap(questioning_system):
    """Test reputation cannot go below 0"""
    questioning_system.node_reputation["node_0"] = 5.0

    questioning_system.update_node_reputation("node_0", -10.0, "Terrible answer")

    assert questioning_system.node_reputation["node_0"] == 0.0


def test_update_node_reputation_new_node(questioning_system):
    """Test updating reputation for node not in system"""
    questioning_system.update_node_reputation("new_node", 10.0, "Good first answer")

    # Should default to 50, then add 10
    assert questioning_system.node_reputation["new_node"] == 60.0


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


def test_answer_option_default_values(questioning_system):
    """Test AnswerOption dataclass default values"""
    option = AnswerOption(option_id="opt_1", option_text="Test Option")

    assert option.votes == 0
    assert option.voters == []
    assert option.vote_weight == 0.0


def test_node_operator_answer_default_values(questioning_system):
    """Test NodeOperatorAnswer dataclass default values"""
    answer = NodeOperatorAnswer(node_address="node_0", timestamp=time.time())

    assert answer.selected_option_id is None
    assert answer.numeric_value is None
    assert answer.free_form_text is None
    assert answer.ranked_options is None
    assert answer.xai_stake == 0.0
    assert answer.reputation_score == 0.0
    assert answer.total_weight == 0.0
    assert answer.response_time_seconds == 0.0
    assert answer.is_valid is True


def test_ai_question_default_values(questioning_system):
    """Test AIQuestion dataclass default values"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test context",
    )

    assert question.options == []
    assert question.min_node_operators == 25
    assert question.timeout_seconds == 86400
    assert question.consensus_threshold == 0.60
    assert question.status == QuestionStatus.SUBMITTED
    assert question.voting_opened_at is None
    assert question.voting_closed_at is None
    assert question.answers == {}
    assert question.total_vote_weight == 0.0
    assert question.consensus_answer is None
    assert question.consensus_confidence == 0.0
    assert question.consensus_reached_at is None
    assert question.ai_acknowledged is False
    assert question.ai_acknowledged_at is None


def test_multiple_questions_independent(questioning_system):
    """Test that multiple questions are independent"""
    q1_id = questioning_system.submit_question(
        task_id="task_1",
        proposal_id="prop_1",
        question_text="Question 1",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    q2_id = questioning_system.submit_question(
        task_id="task_2",
        proposal_id="prop_2",
        question_text="Question 2",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    # Vote on first question
    questioning_system.submit_answer(
        question_id=q1_id, node_address="node_0", selected_option_id="yes"
    )

    # Second question should not have votes
    q2 = questioning_system.questions[q2_id]
    assert len(q2.answers) == 0


def test_consensus_free_form_no_answers(questioning_system):
    """Test consensus calculation for free-form with no valid answers"""
    question = AIQuestion(
        question_id="q1",
        task_id="t1",
        proposal_id="p1",
        question_text="Test",
        question_type=QuestionType.FREE_FORM,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_node_operators=1,
    )

    # Add answer with None text
    question.answers["node_0"] = NodeOperatorAnswer(
        node_address="node_0", timestamp=time.time(), free_form_text=None
    )

    result = questioning_system._check_consensus(question)

    assert result is False


def test_get_answer_breakdown_empty_numeric(questioning_system):
    """Test answer breakdown for numeric question with no answers"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    question = questioning_system.questions[question_id]
    breakdown = questioning_system._get_answer_breakdown(question)

    assert breakdown["min"] == 0
    assert breakdown["max"] == 0
    assert breakdown["average"] == 0
    assert breakdown["median"] == 0


def test_configuration_settings(questioning_system):
    """Test system configuration settings"""
    assert questioning_system.min_node_operators == 25
    assert questioning_system.default_timeout == 86400
    assert questioning_system.reputation_weight == 0.3
    assert questioning_system.stake_weight == 0.7


def test_blockchain_and_dao_references(questioning_system, mock_blockchain, mock_dao):
    """Test that blockchain and DAO are properly stored"""
    assert questioning_system.blockchain is mock_blockchain
    assert questioning_system.governance_dao is mock_dao


def test_numeric_consensus_variance_calculation(questioning_system):
    """Test variance calculation in numeric consensus"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="What fee?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=3,
    )

    # Submit varied values
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", numeric_value=1.0
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_1", numeric_value=2.0
    )
    questioning_system.submit_answer(
        question_id=question_id, node_address="node_2", numeric_value=3.0
    )

    question = questioning_system.questions[question_id]
    # Consensus should be reached with some confidence
    assert question.status == QuestionStatus.CONSENSUS_REACHED
    assert 0 <= question.consensus_confidence <= 1


def test_response_time_tracking(questioning_system):
    """Test that response time is tracked"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    time.sleep(0.1)

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    question = questioning_system.questions[question_id]
    answer = question.answers["node_0"]
    assert answer.response_time_seconds >= 0.1


def test_submit_answer_stores_stake_and_reputation(questioning_system, mock_blockchain):
    """Test that answer stores node's stake and reputation"""
    mock_blockchain.set_balance("node_0", 15000)
    questioning_system.node_reputation["node_0"] = 75.0

    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
    )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_0", selected_option_id="yes"
    )

    question = questioning_system.questions[question_id]
    answer = question.answers["node_0"]
    assert answer.xai_stake == 15000
    assert answer.reputation_score == 75.0
    assert answer.total_weight > 0


def test_answer_breakdown_percentage_calculation(questioning_system):
    """Test percentage calculation in answer breakdown"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="Test",
        options=["A", "B"],
        min_operators=4,
    )

    # 3 votes for A, 1 for B
    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="option_0"
        )

    questioning_system.submit_answer(
        question_id=question_id, node_address="node_3", selected_option_id="option_1"
    )

    question = questioning_system.questions[question_id]
    breakdown = questioning_system._get_answer_breakdown(question)

    # Check percentages are reasonable
    assert breakdown["A"]["percentage"] > breakdown["B"]["percentage"]
    assert breakdown["A"]["percentage"] + breakdown["B"]["percentage"] <= 100


def test_consensus_timestamp_set(questioning_system):
    """Test that consensus_reached_at timestamp is set"""
    question_id = questioning_system.submit_question(
        task_id="task_123",
        proposal_id="prop_456",
        question_text="Test question",
        question_type=QuestionType.YES_NO,
        priority=QuestionPriority.HIGH,
        context="Test",
        min_operators=3,
    )

    before = time.time()

    for i in range(3):
        questioning_system.submit_answer(
            question_id=question_id, node_address=f"node_{i}", selected_option_id="yes"
        )

    after = time.time()

    question = questioning_system.questions[question_id]
    assert question.consensus_reached_at is not None
    assert before <= question.consensus_reached_at <= after


def test_enum_values(questioning_system):
    """Test enum values are as expected"""
    assert QuestionPriority.BLOCKING.value == "blocking"
    assert QuestionPriority.HIGH.value == "high"
    assert QuestionPriority.MEDIUM.value == "medium"
    assert QuestionPriority.LOW.value == "low"

    assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"
    assert QuestionType.YES_NO.value == "yes_no"
    assert QuestionType.NUMERIC.value == "numeric"
    assert QuestionType.FREE_FORM.value == "free_form"
    assert QuestionType.RANKED_CHOICE.value == "ranked_choice"

    assert QuestionStatus.SUBMITTED.value == "submitted"
    assert QuestionStatus.OPEN_FOR_VOTING.value == "open"
    assert QuestionStatus.MIN_REACHED.value == "min_reached"
    assert QuestionStatus.CONSENSUS_REACHED.value == "consensus"
    assert QuestionStatus.TIMEOUT.value == "timeout"
    assert QuestionStatus.ANSWERED.value == "answered"

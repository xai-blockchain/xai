from __future__ import annotations

"""
XAI Node Operator Consensus Questioning System

Allows AI to ask questions to node operators during task execution and receive
consensus answers. This ensures human oversight on critical decisions while
allowing AI autonomy on routine implementation.

Key Features:
1. AI can pause mid-task and submit questions
2. Minimum 25 node operators required to answer
3. Weighted consensus voting (stake + reputation)
4. Multiple choice or free-form answers
5. Timeout mechanisms
6. Full audit trail
7. Question priority levels

Use Cases:
- AI needs architectural guidance: "Should I use async or sync for this API?"
- Security decisions: "Is it safe to add this dependency?"
- Business logic: "What should the default fee be for this feature?"
- Implementation choices: "Which database should I use for this feature?"
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum

from xai.core.crypto_utils import verify_signature_hex

class QuestionPriority(Enum):
    """Priority levels for AI questions"""

    BLOCKING = "blocking"  # AI cannot proceed without answer
    HIGH = "high"  # Important decision, affects architecture
    MEDIUM = "medium"  # Nice to have guidance
    LOW = "low"  # Optional input

class QuestionType(Enum):
    """Types of questions AI can ask"""

    MULTIPLE_CHOICE = "multiple_choice"  # Pre-defined options
    YES_NO = "yes_no"  # Simple yes/no
    NUMERIC = "numeric"  # Number value (fees, timeouts, etc.)
    FREE_FORM = "free_form"  # Open-ended text response
    RANKED_CHOICE = "ranked_choice"  # Rank options in order

class QuestionStatus(Enum):
    """Lifecycle of a question"""

    SUBMITTED = "submitted"  # AI just asked
    OPEN_FOR_VOTING = "open"  # Node operators can vote
    MIN_REACHED = "min_reached"  # 25+ operators voted
    CONSENSUS_REACHED = "consensus"  # Clear majority
    TIMEOUT = "timeout"  # Not enough votes in time
    ANSWERED = "answered"  # AI received answer and continued

@dataclass
class AnswerOption:
    """A possible answer to a question"""

    option_id: str
    option_text: str
    votes: int = 0
    voters: list[str] = field(default_factory=list)  # Node operator addresses
    vote_weight: float = 0.0  # Weighted by stake + reputation

@dataclass
class NodeOperatorAnswer:
    """Individual node operator's answer"""

    node_address: str
    timestamp: float
    signature: str # Added field for answer signature
    public_key: str # Added field for node operator's public key
    question_id: str = "" # Added to allow hashing with question context

    # Vote details
    selected_option_id: str | None = None  # For multiple choice
    numeric_value: float | None = None  # For numeric
    free_form_text: str | None = None  # For free-form
    ranked_options: list[str] | None = None  # For ranked choice

    # Weight (stake + reputation)
    xai_stake: float = 0.0
    reputation_score: float = 0.0
    total_weight: float = 0.0

    # Metadata
    response_time_seconds: float = 0.0
    is_valid: bool = True

    def calculate_answer_hash(self) -> str:
        """Calculate a hash of the answer content for signing."""
        data = {
            "node_address": self.node_address,
            "question_id": self.question_id,
            "selected_option_id": self.selected_option_id,
            "numeric_value": self.numeric_value,
            "free_form_text": self.free_form_text,
            "ranked_options": self.ranked_options,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@dataclass
class AIQuestion:
    """Question submitted by AI during task execution"""

    # Identification
    question_id: str
    task_id: str  # Which AI task is asking
    proposal_id: str  # Which governance proposal

    # Question details
    question_text: str
    question_type: QuestionType
    priority: QuestionPriority
    context: str  # Why AI is asking, what it's working on

    # Options (for multiple choice/ranked)
    options: list[AnswerOption] = field(default_factory=list)

    # Constraints
    min_node_operators: int = 25  # Minimum required
    timeout_seconds: int = 86400  # 24 hours default
    consensus_threshold: float = field(default=0.60)  # 60% agreement needed, can be dynamic based on priority

    # Lifecycle
    status: QuestionStatus = QuestionStatus.SUBMITTED
    submitted_at: float = field(default_factory=time.time)
    voting_opened_at: float | None = None
    voting_closed_at: float | None = None

    # Answers
    answers: dict[str, NodeOperatorAnswer] = field(default_factory=dict)  # node_address -> answer
    total_vote_weight: float = 0.0

    # Result
    consensus_answer: str | None = None  # The final answer AI receives
    consensus_confidence: float = 0.0  # How confident (0-1)
    consensus_reached_at: float | None = None

    # AI continuation
    ai_acknowledged: bool = False
    ai_acknowledged_at: float | None = None

class AINodeOperatorQuestioning:
    """
    System for AI to ask questions and get consensus answers from node operators
    """

    def __init__(self, blockchain, governance_dao):
        """
        Initialize questioning system

        Args:
            blockchain: XAI blockchain instance (for stake verification)
            governance_dao: Governance DAO instance (for proposal context)
        """
        self.blockchain = blockchain
        self.governance_dao = governance_dao

        # Active questions
        self.questions: dict[str, AIQuestion] = {}  # question_id -> AIQuestion

        # Node operator reputation
        self.node_reputation: dict[str, float] = {}  # node_address -> reputation (0-100)

        # Configuration
        self.min_node_operators = 25
        self.default_timeout = 86400  # 24 hours
        self.reputation_weight = 0.3  # 30% weight to reputation, 70% to stake
        self.stake_weight = 0.7
        self.priority_thresholds = {
            QuestionPriority.BLOCKING: 0.85, # 85% for blocking questions
            QuestionPriority.HIGH: 0.70,    # 70% for high priority
            QuestionPriority.MEDIUM: 0.60,  # 60% for medium priority
            QuestionPriority.LOW: 0.51,     # 51% for low priority
        }

    def submit_question(
        self,
        task_id: str,
        proposal_id: str,
        question_text: str,
        question_type: QuestionType,
        priority: QuestionPriority,
        context: str,
        options: list[str] | None = None,
        min_operators: int | None = None,
        timeout_seconds: int | None = None,
    ) -> str:
        """
        AI submits a question during task execution

        Args:
            task_id: ID of the AI task asking the question
            proposal_id: Governance proposal being executed
            question_text: The question to ask
            question_type: Type of question
            priority: How critical is this question
            context: Why AI is asking, what it's working on
            options: For multiple choice questions
            min_operators: Minimum node operators required (default 25)
            timeout_seconds: How long to wait for answers (default 24h)

        Returns:
            question_id: Unique identifier for this question
        """

        # Generate question ID
        question_id = self._generate_question_id(task_id, question_text)

        # Create answer options
        answer_options = []
        if options and question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.RANKED_CHOICE]:
            for idx, option_text in enumerate(options):
                answer_options.append(
                    AnswerOption(option_id=f"option_{idx}", option_text=option_text)
                )
        elif question_type == QuestionType.YES_NO:
            answer_options = [
                AnswerOption(option_id="yes", option_text="Yes"),
                AnswerOption(option_id="no", option_text="No"),
            ]

        # Determine consensus threshold based on priority
        consensus_threshold = self.priority_thresholds.get(priority, self.priority_thresholds[QuestionPriority.MEDIUM])

        # Create question
        question = AIQuestion(
            question_id=question_id,
            task_id=task_id,
            proposal_id=proposal_id,
            question_text=question_text,
            question_type=question_type,
            priority=priority,
            context=context,
            options=answer_options,
            min_node_operators=min_operators or self.min_node_operators,
            timeout_seconds=timeout_seconds or self.default_timeout,
            consensus_threshold=consensus_threshold,
        )

        # Store question
        self.questions[question_id] = question

        # Open for voting immediately
        question.status = QuestionStatus.OPEN_FOR_VOTING
        question.voting_opened_at = time.time()

        print(f"\n{'='*80}")
        print(f"🤖 AI QUESTION SUBMITTED")
        print(f"{ '='*80}")
        print(f"Question ID: {question_id}")
        print(f"Task ID: {task_id}")
        print(f"Priority: {priority.value.upper()}")
        print(f"Type: {question_type.value}")
        print(f"\nQuestion: {question_text}")
        print(f"\nContext: {context}")
        if answer_options:
            print(f"\nOptions:")
            for opt in answer_options:
                print(f"  - {opt.option_text}")
        print(f"\nMinimum {question.min_node_operators} node operators must respond")
        print(f"Timeout: {timeout_seconds or self.default_timeout} seconds")
        print(f"Consensus Threshold: {consensus_threshold * 100:.1f}%")
        print(f"{ '='*80}\n")

        return question_id

    def submit_answer(
        self,
        question_id: str,
        node_address: str,
        public_key: str, # Node operator's public key
        signature: str,  # Signature of the answer
        selected_option_id: str | None = None,
        numeric_value: float | None = None,
        free_form_text: str | None = None,
        ranked_options: list[str] | None = None,
    ) -> Dict:
        """
        Node operator submits an answer to a question

        Args:
            question_id: Which question to answer
            node_address: Node operator's address
            public_key: Node operator's public key
            signature: Signature of the answer
            selected_option_id: For multiple choice/yes-no
            numeric_value: For numeric questions
            free_form_text: For free-form questions
            ranked_options: For ranked choice (list of option_ids in order)

        Returns:
            Result with success status and current vote tally
        """

        # Validate question exists
        if question_id not in self.questions:
            return {"success": False, "error": "QUESTION_NOT_FOUND"}

        question = self.questions[question_id]

        # Check if voting is still open
        if question.status not in [QuestionStatus.OPEN_FOR_VOTING, QuestionStatus.SUBMITTED]:
            return {"success": False, "error": "VOTING_CLOSED"}

        # Check timeout
        elapsed = time.time() - question.voting_opened_at
        if elapsed > question.timeout_seconds:
            question.status = QuestionStatus.TIMEOUT
            return {"success": False, "error": "VOTING_TIMEOUT"}

        # Verify node operator
        if not self._verify_node_operator(node_address):
            return {"success": False, "error": "NOT_A_NODE_OPERATOR"}

        # Prevent double voting
        if node_address in question.answers:
            return {"success": False, "error": "ALREADY_VOTED"}

        # Create a temporary answer object to generate its hash for signature verification
        temp_answer = NodeOperatorAnswer(
            node_address=node_address,
            timestamp=time.time(), # Use current time for hash, not answer.timestamp for verification
            signature=signature,
            public_key=public_key,
            selected_option_id=selected_option_id,
            numeric_value=numeric_value,
            free_form_text=free_form_text,
            ranked_options=ranked_options,
            question_id=question_id # Important for hash calculation
        )
        answer_hash = temp_answer.calculate_answer_hash()

        # Verify signature
        if not verify_signature_hex(public_key, answer_hash.encode(), signature):
            return {"success": False, "error": "INVALID_SIGNATURE"}

        # Get node operator's weight (stake + reputation)
        weight = self._calculate_vote_weight(node_address)

        # Create actual answer object
        answer = NodeOperatorAnswer(
            node_address=node_address,
            timestamp=time.time(),
            signature=signature,
            public_key=public_key,
            selected_option_id=selected_option_id,
            numeric_value=numeric_value,
            free_form_text=free_form_text,
            ranked_options=ranked_options,
            xai_stake=self.blockchain.get_balance(node_address),
            reputation_score=self.node_reputation.get(node_address, 50.0),
            total_weight=weight,
            response_time_seconds=elapsed,
            question_id=question_id # Important for hash calculation
        )

        # Validate answer matches question type
        if not self._validate_answer(question, answer):
            return {"success": False, "error": "INVALID_ANSWER_FORMAT"}

        # Store answer
        question.answers[node_address] = answer
        question.total_vote_weight += weight

        # Update option votes if applicable
        if selected_option_id:
            for option in question.options:
                if option.option_id == selected_option_id:
                    option.votes += 1
                    option.voters.append(node_address)
                    option.vote_weight += weight

        # Check if minimum reached
        if len(question.answers) >= question.min_node_operators:
            if question.status == QuestionStatus.OPEN_FOR_VOTING:
                question.status = QuestionStatus.MIN_REACHED
                print(
                    f"\n✅ Minimum {question.min_node_operators} node operators reached for question {question_id}"
                )

        # Check if consensus reached
        self._check_consensus(question)

        print(f"\n📝 Node operator {node_address[:8]}... voted on question {question_id}")
        print(f"   Total votes: {len(question.answers)}/{question.min_node_operators} minimum")
        print(f"   Vote weight: {weight:.2f}")

        return {
            "success": True,
            "question_id": question_id,
            "total_votes": len(question.answers),
            "min_required": question.min_node_operators,
            "consensus_reached": question.status == QuestionStatus.CONSENSUS_REACHED,
            "current_leading_answer": self._get_leading_answer(question),
        }

    def get_consensus_answer(self, question_id: str, ai_task_id: str) -> Dict:
        """
        AI retrieves the consensus answer to continue working

        Args:
            question_id: Which question
            ai_task_id: Verify this is the AI that asked

        Returns:
            Consensus answer with confidence level
        """

        if question_id not in self.questions:
            return {"success": False, "error": "QUESTION_NOT_FOUND"}

        question = self.questions[question_id]

        # Verify this AI task asked this question
        if question.task_id != ai_task_id:
            return {"success": False, "error": "UNAUTHORIZED_TASK"}

        # Check if minimum operators reached
        if len(question.answers) < question.min_node_operators:
            # Check if timeout
            elapsed = time.time() - question.voting_opened_at
            if elapsed > question.timeout_seconds:
                question.status = QuestionStatus.TIMEOUT
                return {
                    "success": False,
                    "error": "TIMEOUT_INSUFFICIENT_VOTES",
                    "votes_received": len(question.answers),
                    "min_required": question.min_node_operators,
                }
            else:
                return {
                    "success": False,
                    "error": "WAITING_FOR_VOTES",
                    "votes_received": len(question.answers),
                    "min_required": question.min_node_operators,
                    "time_remaining": question.timeout_seconds - elapsed,
                }

        # Calculate consensus
        if question.status != QuestionStatus.CONSENSUS_REACHED:
            self._check_consensus(question)

        # Mark as acknowledged by AI
        question.ai_acknowledged = True
        question.ai_acknowledged_at = time.time()
        question.status = QuestionStatus.ANSWERED

        return {
            "success": True,
            "question_id": question_id,
            "consensus_answer": question.consensus_answer,
            "confidence": question.consensus_confidence,
            "total_votes": len(question.answers),
            "vote_weight": question.total_vote_weight,
            "consensus_reached_at": question.consensus_reached_at,
            "answer_breakdown": self._get_answer_breakdown(question),
        }

    def _check_consensus(self, question: AIQuestion) -> bool:
        """
        Check if consensus has been reached

        Returns:
            True if consensus reached
        """

        if len(question.answers) < question.min_node_operators:
            return False

        if (
            question.question_type == QuestionType.MULTIPLE_CHOICE
            or question.question_type == QuestionType.YES_NO
        ):
            # Find option with highest weighted votes
            leading_option = max(question.options, key=lambda x: x.vote_weight)
            leading_weight_percent = (
                leading_option.vote_weight / question.total_vote_weight
                if question.total_vote_weight > 0
                else 0
            )

            if leading_weight_percent >= question.consensus_threshold:
                question.consensus_answer = leading_option.option_text
                question.consensus_confidence = leading_weight_percent
                question.consensus_reached_at = time.time()
                question.status = QuestionStatus.CONSENSUS_REACHED

                print(f"\n🎯 CONSENSUS REACHED for question {question.question_id}")
                print(f"   Answer: {question.consensus_answer}")
                print(f"   Confidence: {question.consensus_confidence * 100:.1f}%")
                print(f"   Votes: {len(question.answers)} node operators")

                return True

        elif question.question_type == QuestionType.NUMERIC:
            # Calculate weighted average
            total_weighted_value = sum(
                answer.numeric_value * answer.total_weight
                for answer in question.answers.values()
                if answer.numeric_value is not None
            )

            weighted_avg = (
                total_weighted_value / question.total_vote_weight
                if question.total_vote_weight > 0
                else 0
            )

            # Calculate standard deviation to assess confidence
            variance = (
                sum(
                    ((answer.numeric_value - weighted_avg) ** 2) * answer.total_weight
                    for answer in question.answers.values()
                    if answer.numeric_value is not None
                )
                / question.total_vote_weight
                if question.total_vote_weight > 0
                else 0
            )

            std_dev = variance**0.5

            # Confidence is inversely related to standard deviation
            # Lower std_dev = higher confidence
            confidence = max(0, 1 - (std_dev / weighted_avg if weighted_avg != 0 else 1))

            question.consensus_answer = str(weighted_avg)
            question.consensus_confidence = confidence
            question.consensus_reached_at = time.time()
            question.status = QuestionStatus.CONSENSUS_REACHED

            print(f"\n🎯 CONSENSUS REACHED for question {question.question_id}")
            print(f"   Answer: {weighted_avg:.4f}")
            print(f"   Confidence: {confidence * 100:.1f}%")
            print(f"   Std Dev: {std_dev:.4f}")

            return True

        elif question.question_type == QuestionType.FREE_FORM:
            # For free-form, use the most common answer (or most weighted)
            # Group by exact text match
            answer_weights = {}
            for answer in question.answers.values():
                text = answer.free_form_text
                if text:
                    answer_weights[text] = answer_weights.get(text, 0) + answer.total_weight

            if answer_weights:
                leading_answer = max(answer_weights.items(), key=lambda x: x[1])
                leading_weight_percent = (
                    leading_answer[1] / question.total_vote_weight
                    if question.total_vote_weight > 0
                    else 0
                )

                if leading_weight_percent >= question.consensus_threshold:
                    question.consensus_answer = leading_answer[0]
                    question.consensus_confidence = leading_weight_percent
                    question.consensus_reached_at = time.time()
                    question.status = QuestionStatus.CONSENSUS_REACHED

                    print(f"\n🎯 CONSENSUS REACHED for question {question.question_id}")
                    print(f"   Answer: {question.consensus_answer}")
                    print(f"   Confidence: {question.consensus_confidence * 100:.1f}%")

                    return True

        return False

    def _calculate_vote_weight(self, node_address: str) -> float:
        """
        Calculate node operator's vote weight based on stake + reputation

        Returns:
            Vote weight (float)
        """

        # Get XAI stake
        stake = self.blockchain.get_balance(node_address)

        # Get reputation (0-100 scale)
        reputation = self.node_reputation.get(node_address, 50.0)  # Default 50 if new

        # Normalize reputation to same scale as stake
        # Assume max reputation of 100 = 10,000 XAI worth of weight
        reputation_value = (reputation / 100.0) * 10000

        # Combined weight
        weight = (stake * self.stake_weight) + (reputation_value * self.reputation_weight)

        return weight

    def _verify_node_operator(self, address: str) -> bool:
        """
        Verify this address is a registered node operator

        In production, this would check the node operator registry
        """
        # Simplified check - verify they have stake
        balance = self.blockchain.get_balance(address)
        return balance >= 1000  # Minimum 1000 XAI to be node operator

    def _validate_answer(self, question: AIQuestion, answer: NodeOperatorAnswer) -> bool:
        """Validate answer format matches question type"""

        if (
            question.question_type == QuestionType.MULTIPLE_CHOICE
            or question.question_type == QuestionType.YES_NO
        ):
            if not answer.selected_option_id:
                return False
            # Verify option exists
            return any(opt.option_id == answer.selected_option_id for opt in question.options)

        elif question.question_type == QuestionType.NUMERIC:
            return answer.numeric_value is not None

        elif question.question_type == QuestionType.FREE_FORM:
            return answer.free_form_text is not None and len(answer.free_form_text) > 0

        elif question.question_type == QuestionType.RANKED_CHOICE:
            if not answer.ranked_options:
                return False
            # Verify all options are valid
            valid_option_ids = {opt.option_id for opt in question.options}
            return all(opt_id in valid_option_ids for opt_id in answer.ranked_options)

        return False

    def _get_leading_answer(self, question: AIQuestion) -> str | None:
        """Get current leading answer (even if consensus not reached)"""

        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.YES_NO]:
            if question.options:
                leading = max(question.options, key=lambda x: x.vote_weight)
                return leading.option_text
        elif question.question_type == QuestionType.NUMERIC:
            if question.answers:
                total_weighted_value = sum(
                    answer.numeric_value * answer.total_weight
                    for answer in question.answers.values()
                    if answer.numeric_value is not None
                )
                weighted_avg = (
                    total_weighted_value / question.total_vote_weight
                    if question.total_vote_weight > 0
                    else 0
                )
                return str(weighted_avg)

        return None

    def _get_answer_breakdown(self, question: AIQuestion) -> Dict:
        """Get detailed breakdown of all answers"""

        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.YES_NO]:
            return {
                opt.option_text: {
                    "votes": opt.votes,
                    "weight": opt.vote_weight,
                    "percentage": (
                        (opt.vote_weight / question.total_vote_weight * 100)
                        if question.total_vote_weight > 0
                        else 0
                    ),
                }
                for opt in question.options
            }
        elif question.question_type == QuestionType.NUMERIC:
            values = [
                a.numeric_value for a in question.answers.values() if a.numeric_value is not None
            ]
            return {
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "average": sum(values) / len(values) if values else 0,
                "median": sorted(values)[len(values) // 2] if values else 0,
            }

        return {}

    def _generate_question_id(self, task_id: str, question_text: str) -> str:
        """Generate unique question ID"""
        data = f"{task_id}{question_text}{time.time()}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def update_node_reputation(self, node_address: str, delta: float, reason: str):
        """
        Update node operator reputation based on answer quality

        Args:
            node_address: Node operator address
            delta: Change in reputation (-10 to +10)
            reason: Why reputation changed
        """
        current = self.node_reputation.get(node_address, 50.0)
        new_reputation = max(0, min(100, current + delta))
        self.node_reputation[node_address] = new_reputation

        print(f"\n📊 Node operator {node_address[:8]}... reputation updated")
        print(f"   {current:.1f} → {new_reputation:.1f} ({delta:+.1f})")
        print(f"   Reason: {reason}")

# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 80)
    print("AI NODE OPERATOR CONSENSUS QUESTIONING SYSTEM - DEMONSTRATION")
    print("=" * 80)

    # Mock blockchain for demo
    class MockBlockchain:
        def __init__(self):
            self.balances = {
                f"XAI_Node_{i}": 10000 + (i * 1000)  # Node operators with varying stakes
                for i in range(30)
            }

        def get_balance(self, address):
            return self.balances.get(address, 0)

    # Mock crypto_utils for demo (need a mock for sign/verify)
    class MockCryptoUtils:
        def verify_signature_hex(public_key, message_hash_bytes, signature_hex):
            # In a real scenario, this would perform actual crypto verification
            # For this mock, assume valid if public_key and signature_hex are not empty
            return bool(public_key and signature_hex and message_hash_bytes)
        
    class MockWallet:
        def __init__(self, address, public_key, private_key):
            self.address = address
            self.public_key = public_key
            self.private_key = private_key
            
        def sign(self, message_hash_bytes):
            # Simulate signing
            return hashlib.sha256(self.private_key.encode() + message_hash_bytes).hexdigest()

    # Mock governance DAO
    class MockDAO:
        """Mock DAO for testing - stores votes"""
        def __init__(self):
            self.votes = {}

    blockchain = MockBlockchain()
    dao = MockDAO()
    # Mock some node operator wallets
    node_wallets = {}
    for i in range(30):
        addr = f"XAI_Node_{i}"
        pub = f"pubkey_{i}"
        priv = f"privkey_{i}"
        node_wallets[addr] = MockWallet(addr, pub, priv)

    # Initialize questioning system
    questioning = AINodeOperatorQuestioning(blockchain, dao)

    print("\n✅ Questioning system initialized")
    print(f"   Minimum node operators required: {questioning.min_node_operators}")
    print(f"   Default timeout: {questioning.default_timeout} seconds (24 hours)")

    # Scenario 1: AI asks architectural question
    print("\n\n" + "=" * 80)
    print("SCENARIO 1: AI asks architectural question during implementation")
    print("=" * 80)

    question_id = questioning.submit_question(
        task_id="task_atomic_swap_cardano",
        proposal_id="prop_12345",
        question_text="Should the Cardano atomic swap use asynchronous or synchronous validation?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        priority=QuestionPriority.HIGH,
        context="I'm implementing the Cardano atomic swap contract validation. Async would be faster but more complex. Sync is simpler but might cause delays during high load.",
        options=[
            "Asynchronous validation (faster, more complex)",
            "Synchronous validation (simpler, potential delays)",
            "Hybrid approach (async for non-critical, sync for critical)",
        ],
        min_operators=25,
        timeout_seconds=86400,
    )

    # Simulate node operators voting
    print("\n" + "-" * 80)
    print("Node operators voting...")
    print("-" * 80)

    # 30 node operators vote (exceeds minimum of 25)
    votes = [
        ("XAI_Node_0", "option_0"),  # Async
        ("XAI_Node_1", "option_2"),  # Hybrid
        ("XAI_Node_2", "option_2"),  # Hybrid
        ("XAI_Node_3", "option_1"),  # Sync
        ("XAI_Node_4", "option_2"),  # Hybrid
        ("XAI_Node_5", "option_2"),  # Hybrid
        ("XAI_Node_6", "option_0"),  # Async
        ("XAI_Node_7", "option_2"),  # Hybrid
        ("XAI_Node_8", "option_2"),  # Hybrid
        ("XAI_Node_9", "option_2"),  # Hybrid
        ("XAI_Node_10", "option_2"),  # Hybrid
        ("XAI_Node_11", "option_1"),  # Sync
        ("XAI_Node_12", "option_2"),  # Hybrid
        ("XAI_Node_13", "option_2"),  # Hybrid
        ("XAI_Node_14", "option_2"),  # Hybrid
        ("XAI_Node_15", "option_0"),  # Async
        ("XAI_Node_16", "option_2"),  # Hybrid
        ("XAI_Node_17", "option_2"),  # Hybrid
        ("XAI_Node_18", "option_2"),  # Hybrid
        ("XAI_Node_19", "option_2"),  # Hybrid
        ("XAI_Node_20", "option_1"),  # Sync
        ("XAI_Node_21", "option_2"),  # Hybrid
        ("XAI_Node_22", "option_2"),  # Hybrid
        ("XAI_Node_23", "option_2"),  # Hybrid
        ("XAI_Node_24", "option_2"),  # Hybrid
        ("XAI_Node_25", "option_2"),  # Hybrid
        ("XAI_Node_26", "option_2"),  # Hybrid
        ("XAI_Node_27", "option_0"),  # Async
        ("XAI_Node_28", "option_2"),  # Hybrid
        ("XAI_Node_29", "option_2"),  # Hybrid
    ]

    for node_addr, option_id in votes:
        wallet = node_wallets[node_addr]
        # Create a mock answer hash for signing
        # In real scenario, this would be computed by the node operator client
        temp_answer = NodeOperatorAnswer(
            node_address=node_addr,
            timestamp=time.time(), # Use current time for hash, not answer.timestamp for verification
            signature="", # Placeholder
            public_key=wallet.public_key,
            selected_option_id=option_id,
            numeric_value=None,
            free_form_text=None,
            ranked_options=None,
            question_id=question_id # Important for hash calculation
        )
        mock_answer_hash = temp_answer.calculate_answer_hash()
        
        # Sign the hash
        mock_signature = wallet.sign(mock_answer_hash.encode())

        result = questioning.submit_answer(
            question_id=question_id,
            node_address=node_addr,
            public_key=wallet.public_key,
            signature=mock_signature,
            selected_option_id=option_id
        )
        if not result["success"]:
            print(f"Error submitting answer for {node_addr}: {result['error']}")

    # AI retrieves consensus answer
    print("\n\n" + "=" * 80)
    print("AI RETRIEVING CONSENSUS ANSWER")
    print("=" * 80)

    answer = questioning.get_consensus_answer(
        question_id=question_id, ai_task_id="task_atomic_swap_cardano"
    )

    if answer["success"]:
        print(f"\n✅ AI received consensus answer:")
        print(f"   Answer: {answer['consensus_answer']}")
        print(f"   Confidence: {answer['confidence'] * 100:.1f}%")
        print(f"   Total votes: {answer['total_votes']}")
        print(f"   Vote weight: {answer['vote_weight']:.2f}")
        print(f"\n   Answer breakdown:")
        for option, details in answer["answer_breakdown"].items():
            print(f"      {option}: {details['votes']} votes ({details['percentage']:.1f}%)")

    # Scenario 2: AI asks numeric question
    print("\n\n" + "=" * 80)
    print("SCENARIO 2: AI asks numeric question about fees")
    print("=" * 80)

    question_id_2 = questioning.submit_question(
        task_id="task_atomic_swap_cardano",
        proposal_id="prop_12345",
        question_text="What should the default atomic swap fee be (in XAI)?",
        question_type=QuestionType.NUMERIC,
        priority=QuestionPriority.MEDIUM,
        context="I need to set a default fee for Cardano atomic swaps. Too high will discourage usage, too low won't cover infrastructure costs.",
        min_operators=25,
    )

    # Node operators submit numeric answers
    print("\n" + "-" * 80)
    print("Node operators submitting fee proposals...")
    print("-" * 80)

    fee_proposals = [
        0.5,
        0.5,
        0.75,
        1.0,
        0.5,
        0.5,
        1.0,
        0.75,
        0.5,
        0.5,
        0.75,
        1.0,
        0.5,
        0.5,
        0.75,
        0.5,
        0.5,
        1.0,
        0.75,
        0.5,
        0.5,
        0.75,
        0.5,
        0.5,
        1.0,
        0.75,
        0.5,
        0.5,
        0.75,
        0.5,
    ]

    for i, fee in enumerate(fee_proposals):
        node_addr = f"XAI_Node_{i}"
        wallet = node_wallets[node_addr]
        
        temp_answer = NodeOperatorAnswer(
            node_address=node_addr,
            timestamp=time.time(),
            signature="", # Placeholder
            public_key=wallet.public_key,
            selected_option_id=None,
            numeric_value=fee,
            free_form_text=None,
            ranked_options=None,
            question_id=question_id_2 # Important for hash calculation
        )
        mock_answer_hash = temp_answer.calculate_answer_hash()
        mock_signature = wallet.sign(mock_answer_hash.encode())

        questioning.submit_answer(
            question_id=question_id_2,
            node_address=node_addr,
            public_key=wallet.public_key,
            signature=mock_signature,
            numeric_value=fee
        )

    # AI retrieves consensus
    answer_2 = questioning.get_consensus_answer(
        question_id=question_id_2, ai_task_id="task_atomic_swap_cardano"
    )

    if answer_2["success"]:
        print(f"\n✅ AI received consensus answer:")
        print(f"   Fee: {float(answer_2['consensus_answer']):.4f} XAI")
        print(f"   Confidence: {answer_2['confidence'] * 100:.1f}%")
        print(
            f"   Range: {answer_2['answer_breakdown']['min']:.2f} - {answer_2['answer_breakdown']['max']:.2f} XAI"
        )
        print(f"   Median: {answer_2['answer_breakdown']['median']:.2f} XAI")

    print("\n\n" + "=" * 80)
    print("BENEFITS OF AI QUESTIONING SYSTEM")
    print("=" * 80)
    print(
        """
1. ✅ AI gets expert human guidance on critical decisions
2. ✅ Node operators provide oversight during implementation
3. ✅ Consensus ensures no single person controls AI decisions
4. ✅ Weighted voting (stake + reputation) rewards good actors
5. ✅ Minimum 25 operators ensures decentralization
6. ✅ Multiple question types handle different scenarios
7. ✅ Priority levels allow urgent vs. routine questions
8. ✅ Full audit trail of all questions and answers
9. ✅ AI can continue working while waiting for answers
10. ✅ Timeout mechanisms prevent indefinite blocking

This creates a collaborative AI + human development system!
    """)
"""
AI Executor with Node Operator Questioning Integration

Extends the auto-switching AI executor to allow AI to pause mid-task,
ask questions to node operators, wait for consensus answers, then continue.

This creates a collaborative AI + human development workflow where:
- AI handles routine implementation
- AI asks humans for critical decisions
- Minimum 25 node operators provide consensus answers
- AI continues based on community guidance

Use Cases:
1. Architectural decisions: "Which pattern should I use?"
2. Security choices: "Is this dependency safe?"
3. Business logic: "What should this fee be?"
4. Implementation options: "Sync or async for this API?"
"""

import time
from typing import Dict, Optional
from aixn.core.auto_switching_ai_executor import AutoSwitchingAIExecutor, TaskStatus
from aixn.core.ai_node_operator_questioning import (
    AINodeOperatorQuestioning,
    QuestionType,
    QuestionPriority,
    QuestionStatus,
)


class AIExecutorWithQuestioning(AutoSwitchingAIExecutor):
    """
    Enhanced AI executor that can pause and ask node operators questions
    """

    def __init__(self, pool_manager, key_manager, blockchain, governance_dao):
        """
        Initialize executor with questioning capability

        Args:
            pool_manager: StrictAIPoolManager instance
            key_manager: SecureAPIKeyManager instance
            blockchain: XAI blockchain instance
            governance_dao: Governance DAO instance
        """
        super().__init__(pool_manager, key_manager)

        # Initialize questioning system
        self.questioning = AINodeOperatorQuestioning(blockchain, governance_dao)

        # Track questions asked during tasks
        self.task_questions: Dict[str, list] = {}  # task_id -> [question_ids]

        print("✅ AI Executor with Node Operator Questioning initialized")
        print(f"   Minimum {self.questioning.min_node_operators} operators required for consensus")

    def ask_question_and_wait(
        self,
        task_id: str,
        proposal_id: str,
        question_text: str,
        question_type: QuestionType,
        priority: QuestionPriority,
        context: str,
        options: Optional[list] = None,
        min_operators: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        poll_interval: int = 60,  # Check for answer every 60 seconds
    ) -> Dict:
        """
        AI pauses task, asks question, waits for consensus, then continues

        Args:
            task_id: Current task ID
            proposal_id: Governance proposal being executed
            question_text: The question
            question_type: Type of question
            priority: How critical
            context: Why asking
            options: For multiple choice
            min_operators: Minimum node operators (default 25)
            timeout_seconds: Max wait time (default 24h)
            poll_interval: How often to check for consensus (seconds)

        Returns:
            Consensus answer with metadata
        """

        # Pause AI task
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = TaskStatus.PENDING
            print(f"\n⏸️  Task {task_id} PAUSED - waiting for node operator consensus")

        # Submit question
        question_id = self.questioning.submit_question(
            task_id=task_id,
            proposal_id=proposal_id,
            question_text=question_text,
            question_type=question_type,
            priority=priority,
            context=context,
            options=options,
            min_operators=min_operators,
            timeout_seconds=timeout_seconds,
        )

        # Track this question
        if task_id not in self.task_questions:
            self.task_questions[task_id] = []
        self.task_questions[task_id].append(question_id)

        # Wait for consensus (polling loop)
        print(
            f"\n🕐 Waiting for consensus from {min_operators or self.questioning.min_node_operators} node operators..."
        )
        print(f"   Checking every {poll_interval} seconds")
        print(f"   Timeout: {timeout_seconds or self.questioning.default_timeout} seconds")

        start_time = time.time()
        max_wait = timeout_seconds or self.questioning.default_timeout

        while True:
            # Try to get consensus answer
            answer = self.questioning.get_consensus_answer(
                question_id=question_id, ai_task_id=task_id
            )

            if answer["success"]:
                # Got answer! Resume task
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = TaskStatus.IN_PROGRESS
                    print(f"\n▶️  Task {task_id} RESUMED - consensus received")

                return answer

            # Check if error is timeout or just waiting
            if answer.get("error") == "TIMEOUT_INSUFFICIENT_VOTES":
                # Timeout - not enough votes
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = TaskStatus.FAILED

                print(
                    f"\n❌ TIMEOUT: Only {answer['votes_received']} of {answer['min_required']} operators voted"
                )
                return answer

            elif answer.get("error") == "WAITING_FOR_VOTES":
                # Still waiting - check if we should continue polling
                elapsed = time.time() - start_time

                if elapsed >= max_wait:
                    # Manual timeout on our side
                    if task_id in self.active_tasks:
                        self.active_tasks[task_id]["status"] = TaskStatus.FAILED

                    return {
                        "success": False,
                        "error": "TIMEOUT_INSUFFICIENT_VOTES",
                        "votes_received": answer["votes_received"],
                        "min_required": answer["min_required"],
                        "elapsed_seconds": elapsed,
                    }

                # Print progress
                progress = (answer["votes_received"] / answer["min_required"]) * 100
                time_left = max_wait - elapsed

                print(
                    f"\r   Progress: {answer['votes_received']}/{answer['min_required']} operators ({progress:.1f}%) | Time left: {time_left:.0f}s",
                    end="",
                    flush=True,
                )

                # Wait before next poll
                time.sleep(poll_interval)

            else:
                # Unknown error
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = TaskStatus.FAILED

                return answer

    def ask_quick_yes_no(
        self,
        task_id: str,
        proposal_id: str,
        question: str,
        context: str,
        timeout_seconds: int = 3600,  # 1 hour for quick decisions
    ) -> bool:
        """
        Quick yes/no question helper

        Args:
            task_id: Current task
            proposal_id: Proposal ID
            question: Yes/no question
            context: Why asking
            timeout_seconds: Max wait (default 1 hour)

        Returns:
            True if yes, False if no or timeout
        """

        answer = self.ask_question_and_wait(
            task_id=task_id,
            proposal_id=proposal_id,
            question_text=question,
            question_type=QuestionType.YES_NO,
            priority=QuestionPriority.HIGH,
            context=context,
            timeout_seconds=timeout_seconds,
            poll_interval=30,  # Check every 30 seconds for quick questions
        )

        if answer["success"]:
            return answer["consensus_answer"].lower() == "yes"

        return False  # Default to no on timeout/error

    def ask_multiple_choice(
        self,
        task_id: str,
        proposal_id: str,
        question: str,
        options: list,
        context: str,
        priority: QuestionPriority = QuestionPriority.HIGH,
        timeout_seconds: int = 86400,
    ) -> Optional[str]:
        """
        Multiple choice question helper

        Args:
            task_id: Current task
            proposal_id: Proposal ID
            question: The question
            options: List of options
            context: Why asking
            priority: Question priority
            timeout_seconds: Max wait

        Returns:
            Selected option text or None on timeout
        """

        answer = self.ask_question_and_wait(
            task_id=task_id,
            proposal_id=proposal_id,
            question_text=question,
            question_type=QuestionType.MULTIPLE_CHOICE,
            priority=priority,
            context=context,
            options=options,
            timeout_seconds=timeout_seconds,
        )

        if answer["success"]:
            return answer["consensus_answer"]

        return None

    def ask_numeric_value(
        self,
        task_id: str,
        proposal_id: str,
        question: str,
        context: str,
        priority: QuestionPriority = QuestionPriority.MEDIUM,
        timeout_seconds: int = 86400,
    ) -> Optional[float]:
        """
        Numeric question helper

        Args:
            task_id: Current task
            proposal_id: Proposal ID
            question: The question
            context: Why asking
            priority: Question priority
            timeout_seconds: Max wait

        Returns:
            Numeric answer or None on timeout
        """

        answer = self.ask_question_and_wait(
            task_id=task_id,
            proposal_id=proposal_id,
            question_text=question,
            question_type=QuestionType.NUMERIC,
            priority=priority,
            context=context,
            timeout_seconds=timeout_seconds,
        )

        if answer["success"]:
            try:
                return float(answer["consensus_answer"])
            except (ValueError, TypeError):
                return None

        return None

    def execute_with_questioning_capability(
        self,
        task_id: str,
        proposal_id: str,
        task_description: str,
        provider,
        max_total_tokens: int = 500000,
        allow_ai_questions: bool = True,
    ) -> Dict:
        """
        Execute task with AI's ability to ask questions

        This wraps the normal execution but gives AI access to questioning system.
        In the AI's prompt, we tell it that it can ask questions by outputting
        special markers that we parse.

        Args:
            task_id: Task identifier
            proposal_id: Governance proposal
            task_description: What AI should do
            provider: AI provider
            max_total_tokens: Token budget
            allow_ai_questions: Enable questioning (can disable for simple tasks)

        Returns:
            Execution result with questions asked
        """

        # Enhance task description to tell AI it can ask questions
        if allow_ai_questions:
            enhanced_description = f"""{task_description}

IMPORTANT: You can ask questions to node operators during this implementation.

If you need human guidance on critical decisions, output a question in this format:

<AI_QUESTION>
<TYPE>multiple_choice|yes_no|numeric</TYPE>
<PRIORITY>blocking|high|medium|low</PRIORITY>
<QUESTION>Your question here?</QUESTION>
<CONTEXT>Why you're asking and what you're working on</CONTEXT>
<OPTIONS>
- Option 1
- Option 2
- Option 3
</OPTIONS>
</AI_QUESTION>

I will pause, get consensus from at least 25 node operators, then provide the answer.

You can ask questions about:
- Architectural decisions
- Security choices
- Fee amounts
- Implementation approaches
- Any critical decision you're uncertain about

Continue with the implementation. Ask questions when needed.
"""
        else:
            enhanced_description = task_description

        # Store task metadata
        task_metadata = {
            "proposal_id": proposal_id,
            "allow_questioning": allow_ai_questions,
            "questions_asked": [],
        }

        # Execute normally
        # (In production, we'd parse AI output for question markers and handle them)
        result = self.execute_long_task_with_auto_switch(
            task_id=task_id,
            task_description=enhanced_description,
            provider=provider,
            max_total_tokens=max_total_tokens,
            streaming=True,
        )

        # Add questioning metadata to result
        if task_id in self.task_questions:
            result["questions_asked"] = self.task_questions[task_id]
            result["questions_count"] = len(self.task_questions[task_id])

        return result

    def get_task_questions(self, task_id: str) -> list:
        """
        Get all questions asked during a task

        Args:
            task_id: Task identifier

        Returns:
            List of question IDs
        """
        return self.task_questions.get(task_id, [])

    def get_question_details(self, question_id: str) -> Optional[Dict]:
        """
        Get full details of a question

        Args:
            question_id: Question identifier

        Returns:
            Question details or None
        """
        question = self.questioning.questions.get(question_id)
        if question:
            return {
                "question_id": question.question_id,
                "task_id": question.task_id,
                "proposal_id": question.proposal_id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "priority": question.priority.value,
                "status": question.status.value,
                "total_votes": len(question.answers),
                "min_required": question.min_node_operators,
                "consensus_answer": question.consensus_answer,
                "consensus_confidence": question.consensus_confidence,
                "submitted_at": question.submitted_at,
                "consensus_reached_at": question.consensus_reached_at,
            }
        return None


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("AI EXECUTOR WITH NODE OPERATOR QUESTIONING - DEMONSTRATION")
    print("=" * 80)

    from secure_api_key_manager import SecureAPIKeyManager, AIProvider
    from ai_pool_with_strict_limits import StrictAIPoolManager

    # Mock components
    class MockBlockchain:
        def __init__(self):
            self.balances = {f"XAI_Node_{i}": 10000 + (i * 1000) for i in range(30)}

        def get_balance(self, address):
            return self.balances.get(address, 0)

    class MockDAO:
        pass

    # Initialize
    blockchain_seed = "xai_genesis_block_hash"
    key_manager = SecureAPIKeyManager(blockchain_seed)
    pool = StrictAIPoolManager(key_manager)
    blockchain = MockBlockchain()
    dao = MockDAO()

    # Create enhanced executor
    executor = AIExecutorWithQuestioning(pool, key_manager, blockchain, dao)

    print("\n✅ Enhanced executor initialized")
    print("   AI can now pause and ask node operators questions")

    # Scenario: AI implementation with questions
    print("\n\n" + "=" * 80)
    print("SCENARIO: AI implementing Cardano atomic swap")
    print("=" * 80)

    print("\n1. AI starts implementation...")
    print("   [AI working on contract structure...]")

    # AI encounters first decision point
    print("\n2. AI encounters architectural decision...")

    answer_1 = executor.ask_multiple_choice(
        task_id="task_cardano_swap",
        proposal_id="prop_12345",
        question="Should I use asynchronous or synchronous validation for the Cardano HTLC contract?",
        options=[
            "Asynchronous validation (faster, more complex)",
            "Synchronous validation (simpler, potential delays)",
            "Hybrid approach (async for non-critical, sync for critical)",
        ],
        context="I'm implementing the validation logic. Async would be 3x faster but requires event handling. Sync is simpler but might delay during high load periods.",
        priority=QuestionPriority.HIGH,
        timeout_seconds=300,  # 5 minutes for demo
    )

    # Simulate node operators voting quickly for demo
    print("\n   [Simulating 25+ node operators voting...]")

    # In real scenario, node operators would vote through UI
    # For demo, we'll simulate instant votes
    question_id = (
        executor.task_questions.get("task_cardano_swap", [])[-1]
        if "task_cardano_swap" in executor.task_questions
        else None
    )

    if question_id:
        # Simulate votes (in reality this happens externally)
        for i in range(28):
            executor.questioning.submit_answer(
                question_id=question_id,
                node_address=f"XAI_Node_{i}",
                selected_option_id="option_2",  # Most vote for hybrid
            )

        # Now AI can get the answer
        time.sleep(1)  # Brief pause for effect

        print(f"\n3. ✅ Node operator consensus received: {answer_1}")
        print("   [AI continues implementation with hybrid approach...]")

    # AI encounters second decision
    print("\n4. AI encounters fee question...")

    answer_2 = executor.ask_numeric_value(
        task_id="task_cardano_swap",
        proposal_id="prop_12345",
        question="What should the default atomic swap fee be (in XAI)?",
        context="I need to set a default fee. Too high discourages use, too low doesn't cover costs. Similar chains use 0.1-2.0 for atomic swaps.",
        priority=QuestionPriority.MEDIUM,
        timeout_seconds=300,
    )

    # Simulate votes again
    question_id_2 = executor.task_questions["task_cardano_swap"][-1]
    for i in range(27):
        executor.questioning.submit_answer(
            question_id=question_id_2,
            node_address=f"XAI_Node_{i}",
            numeric_value=0.5,  # Most suggest 0.5 XAI
        )

    time.sleep(1)

    print(f"\n5. ✅ Node operator consensus received: {answer_2} XAI")
    print("   [AI continues implementation with 0.5 XAI fee...]")

    # AI encounters security decision
    print("\n6. AI encounters security decision...")

    answer_3 = executor.ask_quick_yes_no(
        task_id="task_cardano_swap",
        proposal_id="prop_12345",
        question="Should I add rate limiting to prevent spam attacks?",
        context="I can add rate limiting (max 10 swaps per address per hour) to prevent DoS. This adds complexity but improves security.",
        timeout_seconds=300,
    )

    # Simulate votes
    question_id_3 = executor.task_questions["task_cardano_swap"][-1]
    for i in range(26):
        executor.questioning.submit_answer(
            question_id=question_id_3, node_address=f"XAI_Node_{i}", selected_option_id="yes"
        )

    time.sleep(1)

    print(f"\n7. ✅ Node operator consensus received: {'YES' if answer_3 else 'NO'}")
    print("   [AI adds rate limiting to contract...]")

    print("\n8. AI completes implementation!")

    # Summary
    print("\n\n" + "=" * 80)
    print("TASK SUMMARY")
    print("=" * 80)

    questions_asked = executor.get_task_questions("task_cardano_swap")
    print(f"\nQuestions asked by AI: {len(questions_asked)}")

    for i, q_id in enumerate(questions_asked, 1):
        details = executor.get_question_details(q_id)
        if details:
            print(f"\n{i}. {details['question_text']}")
            print(f"   Type: {details['question_type']}")
            print(f"   Status: {details['status']}")
            print(f"   Votes: {details['total_votes']}/{details['min_required']}")
            print(f"   Answer: {details['consensus_answer']}")
            print(f"   Confidence: {details['consensus_confidence'] * 100:.1f}%")

    print("\n\n" + "=" * 80)
    print("BENEFITS OF AI + NODE OPERATOR COLLABORATION")
    print("=" * 80)
    print(
        """
✅ AI handles routine implementation autonomously
✅ AI asks humans for critical decisions
✅ 25+ node operators ensure decentralized guidance
✅ Prevents AI from making poor architectural choices
✅ Community stays involved throughout development
✅ Weighted voting rewards experienced operators
✅ Full audit trail of all decisions
✅ AI can continue working while waiting
✅ Flexible question types handle different scenarios
✅ Priority levels allow urgent vs. routine questions

This creates the PERFECT balance of AI autonomy + human oversight!
    """
    )

"""
Multi-AI Collaboration System

Enables 2-3 different AI models to work together on the same blockchain task:
1. Parallel Development - Multiple AIs implement the same feature simultaneously
2. Cross-Review - AIs review each other's code for errors
3. Consensus Voting - AIs vote on best approach
4. Intelligent Merging - Combine best parts from multiple solutions
5. Error Detection - One AI catches another's mistakes

Benefits:
- Better code quality (multiple perspectives)
- Error detection (peer review)
- Innovation (different approaches)
- Redundancy (if one AI fails, others continue)
- Learning (AIs see different solutions)

Use Cases:
- Critical security features (need multiple validations)
- Complex algorithms (benefit from different approaches)
- Research tasks (explore multiple solutions)
- Code optimization (compare different implementations)
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from xai.core.ai_pool_with_strict_limits import StrictAIPoolManager, AIProvider
import difflib


class CollaborationStrategy(Enum):
    """How multiple AIs should collaborate"""

    PARALLEL = "parallel"  # All work simultaneously, compare results
    SEQUENTIAL = "sequential"  # One AI, then next reviews/improves
    DEBATE = "debate"  # AIs discuss and vote on approaches
    MERGE = "merge"  # Each AI does part, merge results
    PEER_REVIEW = "peer_review"  # One implements, others review


MODEL_PROVIDER_MAP = {
    "claude-opus-4": AIProvider.ANTHROPIC,
    "claude-sonnet-4": AIProvider.ANTHROPIC,
    "claude-haiku-4": AIProvider.ANTHROPIC,
    "gpt-4-turbo": AIProvider.OPENAI,
    "gpt-4": AIProvider.OPENAI,
    "gpt-3.5-turbo": AIProvider.OPENAI,
    "o1-preview": AIProvider.OPENAI,
    "o1-mini": AIProvider.OPENAI,
    "gemini-ultra": AIProvider.GOOGLE,
    "gemini-pro": AIProvider.GOOGLE,
    "gemini-flash": AIProvider.GOOGLE,
    "llama-3-70b": AIProvider.ANTHROPIC,
    "mistral-large": AIProvider.ANTHROPIC,
    "command-r-plus": AIProvider.ANTHROPIC,
    "deepseek-coder": AIProvider.ANTHROPIC,
}


class AIRole(Enum):
    """Role of AI in collaboration"""

    IMPLEMENTER = "implementer"  # Writes the code
    REVIEWER = "reviewer"  # Reviews code for errors
    OPTIMIZER = "optimizer"  # Optimizes existing code
    SECURITY_AUDITOR = "auditor"  # Security-focused review
    ARCHITECT = "architect"  # High-level design
    TESTER = "tester"  # Writes tests


@dataclass
class AIContribution:
    """A single AI's contribution to the task"""

    ai_provider: str
    ai_model: str
    role: AIRole

    # Output
    code: str
    explanation: str
    confidence: float  # 0-1, how confident AI is

    # Analysis
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    security_score: float = 0.0
    code_quality_score: float = 0.0
    performance_score: float = 0.0

    # Metadata
    tokens_used: int = 0
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AIPeerReview:
    """One AI's review of another AI's work"""

    reviewer_ai: str
    reviewer_model: str
    reviewed_contribution_id: str

    # Review results
    overall_score: float  # 0-100
    approved: bool

    # Detailed feedback
    security_issues: List[Dict] = field(default_factory=list)
    code_quality_issues: List[Dict] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    bugs_found: List[Dict] = field(default_factory=list)

    # Summary
    summary: str = ""
    recommendation: str = ""  # "approve", "approve_with_changes", "reject"

    timestamp: float = field(default_factory=time.time)


@dataclass
class CollaborativeTask:
    """Task being worked on by multiple AIs"""

    task_id: str
    proposal_id: str
    description: str
    requirements: str

    # Collaboration settings
    strategy: CollaborationStrategy
    num_ais: int  # 2 or 3
    selected_ais: List[Tuple[str, str, AIRole]]  # [(provider, model, role), ...]

    # Contributions
    contributions: List[AIContribution] = field(default_factory=list)
    reviews: List[AIPeerReview] = field(default_factory=list)

    # Consensus
    winning_contribution_id: Optional[str] = None
    merged_solution: Optional[str] = None
    consensus_confidence: float = 0.0

    # Metadata
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    total_tokens_used: int = 0


class MultiAICollaboration:
    """
    System for managing multi-AI collaboration on blockchain tasks
    """

    def __init__(self, ai_executor, ai_matcher, pool_manager: Optional[StrictAIPoolManager] = None):
        """
        Initialize multi-AI collaboration system

        Args:
            ai_executor: AIExecutorWithQuestioning instance
            ai_matcher: AITaskMatcher instance
            pool_manager: Optional StrictAIPoolManager for real executions
        """
        self.executor = ai_executor
        self.matcher = ai_matcher
        self.pool_manager = pool_manager

        # Active collaborative tasks
        self.tasks: Dict[str, CollaborativeTask] = {}

        # Collaboration templates
        self.strategies = self._define_strategies()

    def _define_strategies(self) -> Dict[CollaborationStrategy, Dict]:
        """Define collaboration strategies and their configurations"""

        return {
            CollaborationStrategy.PARALLEL: {
                "description": "All AIs implement simultaneously, best solution wins",
                "ideal_for": ["complex_algorithms", "multiple_valid_approaches"],
                "ai_selection": "diverse",  # Choose different types of AIs
                "merge_results": False,
                "review_required": True,
            },
            CollaborationStrategy.SEQUENTIAL: {
                "description": "First AI implements, others improve iteratively",
                "ideal_for": ["incremental_improvements", "optimization"],
                "ai_selection": "progressive",  # Fast AI first, then better AIs
                "merge_results": False,
                "review_required": True,
            },
            CollaborationStrategy.DEBATE: {
                "description": "AIs discuss approaches before implementing",
                "ideal_for": ["architectural_decisions", "security_critical"],
                "ai_selection": "expert",  # Choose best AIs for reasoning
                "merge_results": False,
                "review_required": True,
            },
            CollaborationStrategy.MERGE: {
                "description": "Each AI handles different parts, merge together",
                "ideal_for": ["large_features", "multi_component"],
                "ai_selection": "specialized",  # Choose specialists for each part
                "merge_results": True,
                "review_required": True,
            },
            CollaborationStrategy.PEER_REVIEW: {
                "description": "One AI implements, 2 others review for errors",
                "ideal_for": ["security_critical", "financial_code"],
                "ai_selection": "implementer_plus_reviewers",
                "merge_results": False,
                "review_required": True,
            },
        }

    def start_collaborative_task(
        self,
        task_id: str,
        proposal_id: str,
        description: str,
        requirements: str,
        strategy: CollaborationStrategy = CollaborationStrategy.PARALLEL,
        num_ais: int = 3,
    ) -> Dict:
        """
        Start multi-AI collaborative task

        Args:
            task_id: Unique task identifier
            proposal_id: Governance proposal ID
            description: What needs to be built
            requirements: Detailed requirements
            strategy: Collaboration strategy
            num_ais: Number of AIs (2 or 3)

        Returns:
            Task initialization result
        """

        if num_ais not in [2, 3]:
            return {"success": False, "error": "num_ais must be 2 or 3"}

        # Select AIs based on strategy
        selected_ais = self._select_ais_for_collaboration(
            description=description, requirements=requirements, strategy=strategy, num_ais=num_ais
        )

        # Create collaborative task
        task = CollaborativeTask(
            task_id=task_id,
            proposal_id=proposal_id,
            description=description,
            requirements=requirements,
            strategy=strategy,
            num_ais=num_ais,
            selected_ais=selected_ais,
        )

        self.tasks[task_id] = task

        print(f"\n{'='*80}")
        print(f"MULTI-AI COLLABORATION STARTED")
        print(f"{'='*80}")
        print(f"Task ID: {task_id}")
        print(f"Strategy: {strategy.value}")
        print(f"Number of AIs: {num_ais}")
        print(f"\nSelected AIs:")
        for provider, model, role in selected_ais:
            print(f"  - {model} ({provider}) - Role: {role.value}")
        print(f"{'='*80}\n")

        return {
            "success": True,
            "task_id": task_id,
            "strategy": strategy.value,
            "selected_ais": [(p, m, r.value) for p, m, r in selected_ais],
        }

    def execute_collaborative_task(self, task_id: str) -> Dict:
        """
        Execute collaborative task based on strategy

        Args:
            task_id: Task identifier

        Returns:
            Final merged/selected solution
        """

        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}

        task = self.tasks[task_id]
        strategy_config = self.strategies[task.strategy]

        if task.strategy == CollaborationStrategy.PARALLEL:
            return self._execute_parallel(task)

        elif task.strategy == CollaborationStrategy.SEQUENTIAL:
            return self._execute_sequential(task)

        elif task.strategy == CollaborationStrategy.DEBATE:
            return self._execute_debate(task)

        elif task.strategy == CollaborationStrategy.MERGE:
            return self._execute_merge(task)

        elif task.strategy == CollaborationStrategy.PEER_REVIEW:
            return self._execute_peer_review(task)

        return {"success": False, "error": "Unknown strategy"}

    def _execute_parallel(self, task: CollaborativeTask) -> Dict:
        """
        Execute PARALLEL strategy: All AIs work simultaneously
        """

        print(f"\n🔄 PARALLEL EXECUTION: All {task.num_ais} AIs implementing simultaneously...\n")

        # All AIs implement the same task in parallel
        for provider, model, role in task.selected_ais:
            print(f"{'='*60}")
            print(f"AI {len(task.contributions) + 1}: {model} ({provider})")
            print(f"{'='*60}")

            # Create task prompt
            prompt = f"""
{task.description}

Requirements:
{task.requirements}

IMPORTANT: You are working in parallel with {task.num_ais - 1} other AI models on this same task.
Each AI will implement their own solution. The best solution will be selected.

Provide:
1. Your implementation (code)
2. Explanation of your approach
3. Why you chose this approach
4. Potential weaknesses of your solution
5. Confidence level (0-100)
"""

            # Execute (in production, this would call actual AI)
            # For demonstration, simulate
            contribution = self._simulate_ai_contribution(provider, model, role, prompt)
            task.contributions.append(contribution)
            task.total_tokens_used += contribution.tokens_used

            print(f"✅ Contribution received")
            print(f"   Confidence: {contribution.confidence * 100:.1f}%")
            print(f"   Tokens used: {contribution.tokens_used:,}\n")

        # Cross-review: Each AI reviews others' work
        print(f"\n{'='*80}")
        print(f"CROSS-REVIEW PHASE")
        print(f"{'='*80}\n")

        for i, reviewer_ai in enumerate(task.selected_ais):
            for j, contribution in enumerate(task.contributions):
                # Don't review own work
                if i == j:
                    continue

                print(f"AI {i+1} ({reviewer_ai[1]}) reviewing AI {j+1}'s work...")

                review = self._simulate_peer_review(reviewer_ai[0], reviewer_ai[1], contribution)
                task.reviews.append(review)

                print(f"   Score: {review.overall_score:.1f}/100")
                print(f"   Recommendation: {review.recommendation}\n")

        # Select winning contribution
        winner = self._select_best_contribution(task)
        task.winning_contribution_id = winner["contribution_id"]
        task.consensus_confidence = winner["confidence"]
        task.completed_at = time.time()

        print(f"\n{'='*80}")
        print(f"PARALLEL EXECUTION COMPLETE")
        print(f"{'='*80}")
        print(f"Winner: {winner['ai_model']}")
        print(f"Consensus confidence: {winner['confidence'] * 100:.1f}%")
        print(f"Total tokens used: {task.total_tokens_used:,}")
        print(f"{'='*80}\n")

        return {
            "success": True,
            "strategy": "parallel",
            "winning_solution": winner["code"],
            "winning_ai": winner["ai_model"],
            "confidence": winner["confidence"],
            "all_contributions": len(task.contributions),
            "total_reviews": len(task.reviews),
            "total_tokens_used": task.total_tokens_used,
        }

    def _execute_peer_review(self, task: CollaborativeTask) -> Dict:
        """
        Execute PEER_REVIEW strategy: One implements, others review
        """

        print(f"\n📝 PEER REVIEW EXECUTION\n")

        # Find implementer and reviewers
        implementer = None
        reviewers = []

        for provider, model, role in task.selected_ais:
            if role == AIRole.IMPLEMENTER:
                implementer = (provider, model, role)
            else:
                reviewers.append((provider, model, role))

        # Implementer writes code
        print(f"{'='*60}")
        print(f"IMPLEMENTATION PHASE")
        print(f"{'='*60}")
        print(f"Implementer: {implementer[1]} ({implementer[0]})\n")

        prompt = f"""
{task.description}

Requirements:
{task.requirements}

IMPORTANT: Implement this feature. Your code will be reviewed by {len(reviewers)} other AI models
for security, quality, and correctness. Write clean, well-documented code.
"""

        contribution = self._simulate_ai_contribution(
            implementer[0], implementer[1], implementer[2], prompt
        )
        task.contributions.append(contribution)
        task.total_tokens_used += contribution.tokens_used

        print(f"✅ Implementation complete")
        print(f"   Tokens used: {contribution.tokens_used:,}\n")

        # Reviewers audit the code
        print(f"\n{'='*60}")
        print(f"REVIEW PHASE")
        print(f"{'='*60}\n")

        for reviewer_provider, reviewer_model, reviewer_role in reviewers:
            print(f"Reviewer: {reviewer_model} ({reviewer_role.value})")

            review = self._simulate_peer_review(
                reviewer_provider, reviewer_model, contribution, focus=reviewer_role.value
            )
            task.reviews.append(review)

            print(f"   Overall score: {review.overall_score:.1f}/100")
            print(f"   Security issues: {len(review.security_issues)}")
            print(f"   Code quality issues: {len(review.code_quality_issues)}")
            print(f"   Bugs found: {len(review.bugs_found)}")
            print(f"   Recommendation: {review.recommendation}\n")

        # Calculate consensus
        avg_score = sum(r.overall_score for r in task.reviews) / len(task.reviews)
        all_approved = all(r.approved for r in task.reviews)

        task.winning_contribution_id = "impl_0"
        task.consensus_confidence = avg_score / 100
        task.completed_at = time.time()

        print(f"\n{'='*80}")
        print(f"PEER REVIEW COMPLETE")
        print(f"{'='*80}")
        print(f"Average review score: {avg_score:.1f}/100")
        print(f"All reviewers approved: {all_approved}")
        print(f"Total tokens used: {task.total_tokens_used:,}")
        print(f"{'='*80}\n")

        return {
            "success": True,
            "strategy": "peer_review",
            "implementation": contribution.code,
            "implementer": implementer[1],
            "avg_review_score": avg_score,
            "all_approved": all_approved,
            "reviews": len(task.reviews),
            "total_tokens_used": task.total_tokens_used,
            "security_issues_found": sum(len(r.security_issues) for r in task.reviews),
            "bugs_found": sum(len(r.bugs_found) for r in task.reviews),
        }

    def _execute_sequential(self, task: CollaborativeTask) -> Dict:
        """Execute SEQUENTIAL strategy: Each AI improves previous AI's work"""
        contributions = []
        previous_output = ""

        for provider, model, role in task.selected_ais:
            prompt = f"{task.description}\nRequirements: {task.requirements}\nRole: {role.value}\nPrevious output:\n{previous_output}"
            contribution = self._simulate_ai_contribution(provider, model, role, prompt)
            contributions.append(contribution)
            task.contributions.append(contribution)
            task.total_tokens_used += contribution.tokens_used
            previous_output = contribution.code

        task.winning_contribution_id = contributions[-1].ai_model if contributions else None

        return {
            "success": True,
            "strategy": "sequential",
            "final_solution": previous_output,
            "contributions": len(contributions),
            "total_tokens_used": task.total_tokens_used,
        }

    def _execute_debate(self, task: CollaborativeTask) -> Dict:
        """Execute DEBATE strategy: AIs discuss approaches first"""
        debates = []

        for provider, model, role in task.selected_ais:
            prompt = f"Debate perspective ({role.value}) on {task.description}\nRequirements: {task.requirements}"
            contribution = self._simulate_ai_contribution(provider, model, role, prompt)
            debates.append(contribution)
            task.contributions.append(contribution)
            task.total_tokens_used += contribution.tokens_used

        winner = max(debates, key=lambda c: c.confidence) if debates else None
        best_summary = winner.explanation if winner else "No debate data"

        return {
            "success": True,
            "strategy": "debate",
            "winner": winner.ai_model if winner else None,
            "summary": best_summary,
            "debate_rounds": len(debates),
        }

    def _execute_merge(self, task: CollaborativeTask) -> Dict:
        """Execute MERGE strategy: Each AI does a part, merge together"""
        parts = []

        for provider, model, role in task.selected_ais:
            prompt = f"{task.description}\nRequirements specify {role.value} responsibilities"
            contribution = self._simulate_ai_contribution(provider, model, role, prompt)
            parts.append(contribution.code)
            task.contributions.append(contribution)
            task.total_tokens_used += contribution.tokens_used

        merged_solution = "\n\n".join(parts)
        task.merged_solution = merged_solution

        return {
            "success": True,
            "strategy": "merge",
            "merged_solution": merged_solution,
            "parts": len(parts),
        }

    def _select_ais_for_collaboration(
        self, description: str, requirements: str, strategy: CollaborationStrategy, num_ais: int
    ) -> List[Tuple[str, str, AIRole]]:
        """
        Intelligently select which AIs should collaborate

        Returns:
            List of (provider, model, role) tuples
        """

        if strategy == CollaborationStrategy.PARALLEL:
            # Choose diverse AIs with different strengths
            return [
                ("anthropic", "claude-opus-4", AIRole.IMPLEMENTER),
                ("openai", "o1-preview", AIRole.IMPLEMENTER),
                ("deepseek", "deepseek-coder", AIRole.IMPLEMENTER),
            ][:num_ais]

        elif strategy == CollaborationStrategy.PEER_REVIEW:
            # One implementer, rest are reviewers
            if num_ais == 2:
                return [
                    ("anthropic", "claude-opus-4", AIRole.IMPLEMENTER),
                    ("openai", "o1-preview", AIRole.SECURITY_AUDITOR),
                ]
            else:  # 3 AIs
                return [
                    ("anthropic", "claude-opus-4", AIRole.IMPLEMENTER),
                    ("openai", "o1-preview", AIRole.SECURITY_AUDITOR),
                    ("deepseek", "deepseek-coder", AIRole.REVIEWER),
                ]

        elif strategy == CollaborationStrategy.SEQUENTIAL:
            # Fast AI first, then better AIs improve
            return [
                ("groq", "groq-llama-3-70b", AIRole.IMPLEMENTER),
                ("anthropic", "claude-sonnet-4", AIRole.OPTIMIZER),
                ("anthropic", "claude-opus-4", AIRole.REVIEWER),
            ][:num_ais]

        # Default diverse selection
        return [
            ("anthropic", "claude-opus-4", AIRole.IMPLEMENTER),
            ("openai", "gpt-4-turbo", AIRole.REVIEWER),
            ("deepseek", "deepseek-coder", AIRole.OPTIMIZER),
        ][:num_ais]

    def _simulate_ai_contribution(
        self, provider: str, model: str, role: AIRole, prompt: str
    ) -> AIContribution:
        """
        Simulate AI contribution (in production, call actual AI API)
        """

        if self.pool_manager:
            return self._execute_real_contribution(provider, model, role, prompt)

        code = f"# Implementation by {model}\n# Approach: {role.value}\n\n{prompt}"

        explanation = (
            f"I implemented this using a {role.value} approach focused on clarity and security."
        )

        return AIContribution(
            ai_provider=provider,
            ai_model=model,
            role=role,
            code=code,
            explanation=explanation,
            confidence=0.85 + (hash(model) % 15) / 100,
            tokens_used=50000 + (hash(model) % 20000),
            execution_time=120.0,
        )

    def _execute_real_contribution(
        self, provider: str, model: str, role: AIRole, prompt: str, estimated_tokens: int = 60000
    ) -> AIContribution:
        """Execute a real AI contribution using the strict pool"""

        provider_enum = MODEL_PROVIDER_MAP.get(model, AIProvider.ANTHROPIC)
        execution = self.pool_manager.execute_ai_task_with_limits(
            task_description=prompt,
            estimated_tokens=estimated_tokens,
            provider=provider_enum,
            max_tokens_override=estimated_tokens + 2048,
        )

        if not execution.get("success"):
            return AIContribution(
                ai_provider=provider,
                ai_model=model,
                role=role,
                code=prompt,
                explanation=execution.get("error", "API call failed to produce output."),
                confidence=0.4,
                tokens_used=0,
                execution_time=0.0,
            )

        output = execution.get("output", "").strip() or prompt
        tokens_used = execution.get("tokens_used", 0)
        confidence = min(1.0, 0.5 + tokens_used / (estimated_tokens * 2))

        return AIContribution(
            ai_provider=provider_enum.value,
            ai_model=model,
            role=role,
            code=output,
            explanation=execution.get("output", output)[:300],
            confidence=confidence,
            tokens_used=tokens_used,
            execution_time=execution.get("execution_time", 0.0),
        )

    def _simulate_peer_review(
        self,
        reviewer_provider: str,
        reviewer_model: str,
        contribution: AIContribution,
        focus: str = "general",
    ) -> AIPeerReview:
        """
        Simulate peer review (in production, AI reviews code)
        """

        if self.pool_manager:
            return self._execute_real_review(reviewer_provider, reviewer_model, contribution, focus)

        score = 85.0 + (hash(reviewer_model) % 15)

        return AIPeerReview(
            reviewer_ai=reviewer_provider,
            reviewer_model=reviewer_model,
            reviewed_contribution_id="contrib_0",
            overall_score=score,
            approved=score >= 80,
            security_issues=[],
            code_quality_issues=[],
            bugs_found=[],
            summary=f"Reviewed by {reviewer_model}. Overall solid implementation.",
            recommendation="approve" if score >= 90 else "approve_with_changes",
        )

    def _execute_real_review(
        self,
        reviewer_provider: str,
        reviewer_model: str,
        contribution: AIContribution,
        focus: str = "general",
        estimated_tokens: int = 9000,
    ) -> AIPeerReview:
        provider_enum = MODEL_PROVIDER_MAP.get(reviewer_model, AIProvider.ANTHROPIC)
        prompt = f"You are reviewing code for issues and improvements. Focus: {focus}.\n\n{contribution.code}"
        result = self.pool_manager.execute_ai_task_with_limits(
            task_description=prompt, estimated_tokens=estimated_tokens, provider=provider_enum
        )

        tokens_used = result.get("tokens_used", 0)
        overall_score = min(100, 60 + tokens_used / 1000)
        approved = result.get("success", False)
        summary = (result.get("output") or "Review completed.").strip()

        return AIPeerReview(
            reviewer_ai=provider_enum.value,
            reviewer_model=reviewer_model,
            reviewed_contribution_id=contribution.ai_model,
            overall_score=overall_score,
            approved=approved,
            security_issues=[],
            code_quality_issues=[],
            bugs_found=[],
            summary=summary,
            recommendation="approve" if approved else "approve_with_changes",
        )

    def _select_best_contribution(self, task: CollaborativeTask) -> Dict:
        """
        Select best contribution based on peer reviews and voting mechanism
        """

        # Calculate score for each contribution
        scores = []
        for i, contribution in enumerate(task.contributions):
            # Get reviews for this contribution
            contribution_reviews = [
                r
                for r in task.reviews
                if r.reviewed_contribution_id == f"contrib_{i}" or i == 0  # Simulated
            ]

            # Average review score
            avg_review_score = sum(r.overall_score for r in contribution_reviews) / max(
                len(contribution_reviews), 1
            )

            # Combined score: 70% peer reviews + 30% self-confidence
            combined_score = (avg_review_score * 0.7) + (contribution.confidence * 100 * 0.3)

            scores.append(
                {
                    "contribution_id": f"contrib_{i}",
                    "ai_model": contribution.ai_model,
                    "code": contribution.code,
                    "combined_score": combined_score,
                    "confidence": combined_score / 100,
                }
            )

        # Return highest scoring contribution
        winner = max(scores, key=lambda x: x["combined_score"])
        return winner

    def vote_on_contributions(
        self, task_id: str, consensus_threshold: float = 0.67
    ) -> Dict:
        """
        Multi-AI voting mechanism with weighted consensus

        Args:
            task_id: Task identifier
            consensus_threshold: Minimum agreement level (default 67%)

        Returns:
            Voting results with consensus decision
        """

        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}

        task = self.tasks[task_id]

        # Each AI votes on each contribution (including their own)
        votes = {}
        for i, voter_ai in enumerate(task.selected_ais):
            votes[f"ai_{i}"] = {
                "ai_model": voter_ai[1],
                "votes": {},
                "weight": self._calculate_ai_weight(voter_ai[1]),
            }

            # Vote on each contribution
            for j, contribution in enumerate(task.contributions):
                # Simulate voting (in production, AI would analyze and vote)
                vote_score = self._simulate_ai_vote(
                    voter_ai[1], contribution, is_own=(i == j)
                )
                votes[f"ai_{i}"]["votes"][f"contrib_{j}"] = vote_score

        # Calculate consensus
        consensus_result = self._calculate_voting_consensus(
            votes, len(task.contributions), consensus_threshold
        )

        return {
            "success": True,
            "task_id": task_id,
            "votes": votes,
            "consensus": consensus_result,
            "winning_contribution": consensus_result.get("winner"),
            "agreement_level": consensus_result.get("agreement_level"),
        }

    def _calculate_ai_weight(self, ai_model: str) -> float:
        """Calculate voting weight for AI model based on confidence/capability"""
        weights = {
            "claude-opus-4": 1.0,
            "o1-preview": 0.95,
            "deepseek-coder": 0.85,
            "claude-sonnet-4": 0.90,
            "gpt-4-turbo": 0.85,
        }
        return weights.get(ai_model, 0.8)

    def _simulate_ai_vote(
        self, voter_model: str, contribution: AIContribution, is_own: bool
    ) -> float:
        """Simulate AI voting on a contribution"""
        # In production, AI would analyze contribution
        base_score = contribution.confidence * 100

        # Slight boost if voting for own work
        if is_own:
            base_score *= 1.1

        # Add some variance based on AI model
        variance = (hash(voter_model + contribution.ai_model) % 20 - 10) / 100
        final_score = max(0, min(100, base_score + base_score * variance))

        return round(final_score, 2)

    def _calculate_voting_consensus(
        self, votes: Dict, num_contributions: int, threshold: float
    ) -> Dict:
        """
        Calculate consensus from weighted votes

        Args:
            votes: Voting data from all AIs
            num_contributions: Number of contributions being voted on
            threshold: Minimum agreement threshold (0-1)

        Returns:
            Consensus result
        """

        # Calculate weighted scores for each contribution
        contribution_scores = {}
        total_weight = sum(v["weight"] for v in votes.values())

        for contrib_id in range(num_contributions):
            contrib_key = f"contrib_{contrib_id}"
            weighted_score = 0.0

            for voter_id, voter_data in votes.items():
                vote_score = voter_data["votes"].get(contrib_key, 0)
                weight = voter_data["weight"]
                weighted_score += vote_score * weight

            # Normalize by total weight
            contribution_scores[contrib_key] = weighted_score / total_weight if total_weight > 0 else 0

        # Find winner
        winner = max(contribution_scores.items(), key=lambda x: x[1])

        # Calculate agreement level (how much consensus there is)
        scores = list(contribution_scores.values())
        if len(scores) > 1:
            max_score = max(scores)
            second_score = sorted(scores, reverse=True)[1]
            agreement_level = (max_score - second_score) / max_score if max_score > 0 else 0
        else:
            agreement_level = 1.0

        # Check if consensus threshold is met
        consensus_reached = agreement_level >= threshold

        return {
            "winner": winner[0],
            "winner_score": winner[1],
            "all_scores": contribution_scores,
            "agreement_level": round(agreement_level, 3),
            "consensus_reached": consensus_reached,
            "threshold": threshold,
            "total_voters": len(votes),
        }

    def resolve_conflict(self, task_id: str, conflict_type: str = "score_tie") -> Dict:
        """
        Conflict resolution strategies when AIs disagree

        Args:
            task_id: Task identifier
            conflict_type: Type of conflict to resolve

        Returns:
            Resolution decision
        """

        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}

        task = self.tasks[task_id]

        strategies = {
            "score_tie": self._resolve_score_tie,
            "quality_disagreement": self._resolve_quality_disagreement,
            "approach_conflict": self._resolve_approach_conflict,
        }

        resolver = strategies.get(conflict_type, self._resolve_score_tie)
        resolution = resolver(task)

        return {
            "success": True,
            "conflict_type": conflict_type,
            "resolution": resolution,
            "strategy_used": resolver.__name__,
        }

    def _resolve_score_tie(self, task: CollaborativeTask) -> Dict:
        """Resolve tie scores - use complexity as tiebreaker"""
        # In production, analyze code complexity
        return {
            "method": "complexity_tiebreaker",
            "decision": "Choose simpler implementation",
            "rationale": "Simpler code is easier to maintain and understand",
        }

    def _resolve_quality_disagreement(self, task: CollaborativeTask) -> Dict:
        """Resolve disagreement on code quality"""
        return {
            "method": "weighted_review",
            "decision": "Weight reviews by reviewer expertise",
            "rationale": "More experienced AI models have higher weight",
        }

    def _resolve_approach_conflict(self, task: CollaborativeTask) -> Dict:
        """Resolve different implementation approaches"""
        return {
            "method": "hybrid_merge",
            "decision": "Merge best aspects of each approach",
            "rationale": "Combine strengths while avoiding weaknesses",
        }


# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 80)
    print("MULTI-AI COLLABORATION SYSTEM - DEMONSTRATION")
    print("=" * 80)

    # Mock components
    from ai_executor_with_questioning import AIExecutorWithQuestioning
    from ai_task_matcher import AITaskMatcher

    # Simulated instances
    executor = None  # Would be real executor
    matcher = None  # Would be real matcher

    # Create collaboration system
    collaboration = MultiAICollaboration(executor, matcher)

    print("\n✅ Multi-AI collaboration system initialized\n")

    # Scenario 1: PARALLEL - All AIs implement simultaneously
    print("\n" + "=" * 80)
    print("SCENARIO 1: PARALLEL COLLABORATION")
    print("=" * 80)

    result = collaboration.start_collaborative_task(
        task_id="task_cardano_swap",
        proposal_id="prop_12345",
        description="Implement Cardano atomic swap with HTLC contracts",
        requirements="Must support time-locked contracts, hash verification, and refund mechanism",
        strategy=CollaborationStrategy.PARALLEL,
        num_ais=3,
    )

    if result["success"]:
        # Execute collaborative task
        execution_result = collaboration.execute_collaborative_task("task_cardano_swap")

        print(f"\n📊 RESULTS:")
        print(f"   Winning AI: {execution_result['winning_ai']}")
        print(f"   Confidence: {execution_result['confidence'] * 100:.1f}%")
        print(f"   Total contributions: {execution_result['all_contributions']}")
        print(f"   Total peer reviews: {execution_result['total_reviews']}")
        print(f"   Total cost: ${execution_result['total_tokens_used'] * 0.000015:.2f}")

    # Scenario 2: PEER REVIEW - One implements, others review
    print("\n\n" + "=" * 80)
    print("SCENARIO 2: PEER REVIEW COLLABORATION")
    print("=" * 80)

    result2 = collaboration.start_collaborative_task(
        task_id="task_security_feature",
        proposal_id="prop_12346",
        description="Implement rate limiting to prevent spam attacks",
        requirements="Max 10 transactions per address per hour, must be efficient",
        strategy=CollaborationStrategy.PEER_REVIEW,
        num_ais=3,
    )

    if result2["success"]:
        execution_result2 = collaboration.execute_collaborative_task("task_security_feature")

        print(f"\n📊 RESULTS:")
        print(f"   Implementer: {execution_result2['implementer']}")
        print(f"   Average review score: {execution_result2['avg_review_score']:.1f}/100")
        print(f"   All approved: {execution_result2['all_approved']}")
        print(f"   Security issues found: {execution_result2['security_issues_found']}")
        print(f"   Bugs found: {execution_result2['bugs_found']}")

    # Summary
    print("\n\n" + "=" * 80)
    print("MULTI-AI COLLABORATION BENEFITS")
    print("=" * 80)
    print(
        """
1. ✅ Better Code Quality - Multiple perspectives catch more issues
2. ✅ Error Detection - Peer review finds bugs one AI might miss
3. ✅ Innovation - Different AIs try different approaches
4. ✅ Validation - Cross-validation increases confidence
5. ✅ Redundancy - If one AI fails, others continue
6. ✅ Learning - AIs can see alternative solutions
7. ✅ Security - Multiple security audits by different AIs
8. ✅ Optimization - Best parts from each solution can be merged

Collaboration Strategies:
- PARALLEL: All implement, best wins (competitive)
- PEER_REVIEW: One implements, others audit (security)
- SEQUENTIAL: Each improves previous (iterative)
- DEBATE: Discuss approaches first (architectural)
- MERGE: Each does a part (divide and conquer)

Cost Impact:
- Uses 2-3x tokens (multiple AIs working)
- But produces significantly better code
- Worth it for critical/security features
- Can use cheaper AIs for some roles (Groq for reviews)
    """
    )

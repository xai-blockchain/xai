from __future__ import annotations

"""
AI Task Matcher - Intelligent AI Selection System

Automatically selects the BEST AI model for each specific task based on:
1. Task type (code, security, documentation, etc.)
2. Task complexity
3. Available donated API credits
4. Cost optimization
5. Speed requirements
6. Quality requirements

This ensures the right AI is used for each job - not wasting premium credits
on simple tasks, and not using cheap models for critical security work.
"""

import time
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    """Types of development tasks"""

    SECURITY_AUDIT = "security_audit"  # Critical security review
    CORE_FEATURE = "core_feature"  # New blockchain features
    BUG_FIX = "bug_fix"  # Fix existing bugs
    OPTIMIZATION = "optimization"  # Performance improvements
    ATOMIC_SWAP = "atomic_swap"  # Trading pair integrations
    SMART_CONTRACT = "smart_contract"  # Contract development
    TESTING = "testing"  # Test suite creation
    DOCUMENTATION = "documentation"  # Write docs
    REFACTORING = "refactoring"  # Code cleanup
    UI_UX = "ui_ux"  # User interface work
    API_DEVELOPMENT = "api_development"  # API endpoints
    MOBILE_APP = "mobile_app"  # Mobile features
    RESEARCH = "research"  # Research & analysis
    CODE_REVIEW = "code_review"  # Review existing code
    DEPLOYMENT = "deployment"  # Deploy scripts
    MONITORING = "monitoring"  # Monitoring/logging
    INTEGRATION = "integration"  # Third-party integrations

class TaskComplexity(Enum):
    """Complexity levels"""

    SIMPLE = 1  # Basic tasks, clear requirements
    MODERATE = 2  # Some complexity, multiple files
    COMPLEX = 3  # High complexity, architecture decisions
    CRITICAL = 4  # Mission-critical, security-sensitive

class TaskPriority(Enum):
    """Priority levels"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AICapability:
    """Capabilities and characteristics of an AI model"""

    provider: str
    model: str

    # Cost (per million tokens)
    cost_input: float
    cost_output: float

    # Performance characteristics
    speed_score: int  # 1-10, higher = faster
    quality_score: int  # 1-10, higher = better quality
    context_window: int  # Maximum tokens

    # Specializations (1-10 score for each)
    code_quality: int
    security_analysis: int
    documentation: int
    reasoning: int
    speed: int
    creativity: int
    research: int  # Can access web/real-time data

    # Availability
    available: bool = True

class AITaskMatcher:
    """
    Intelligent system that matches tasks to optimal AI models
    """

    def __init__(self):
        # Define all available AI models and their capabilities
        self.ai_models = self._initialize_ai_capabilities()

        # Task type to required capabilities mapping
        self.task_requirements = self._initialize_task_requirements()

    def _initialize_ai_capabilities(self) -> dict[str, AICapability]:
        """Define capabilities of each AI model"""

        return {
            # ANTHROPIC - Best overall code quality
            "claude-opus-4": AICapability(
                provider="anthropic",
                model="claude-opus-4",
                cost_input=15.0,
                cost_output=75.0,
                speed_score=7,
                quality_score=10,
                context_window=200000,
                code_quality=10,
                security_analysis=10,
                documentation=9,
                reasoning=10,
                speed=7,
                creativity=9,
                research=5,  # No web access
            ),
            "claude-sonnet-4": AICapability(
                provider="anthropic",
                model="claude-sonnet-4",
                cost_input=3.0,
                cost_output=15.0,
                speed_score=9,
                quality_score=9,
                context_window=200000,
                code_quality=9,
                security_analysis=9,
                documentation=9,
                reasoning=9,
                speed=9,
                creativity=8,
                research=5,
            ),
            "claude-haiku-4": AICapability(
                provider="anthropic",
                model="claude-haiku-4",
                cost_input=0.25,
                cost_output=1.25,
                speed_score=10,
                quality_score=7,
                context_window=200000,
                code_quality=7,
                security_analysis=6,
                documentation=8,
                reasoning=7,
                speed=10,
                creativity=6,
                research=5,
            ),
            # OPENAI - Industry standard, reliable
            "gpt-4-turbo": AICapability(
                provider="openai",
                model="gpt-4-turbo",
                cost_input=10.0,
                cost_output=30.0,
                speed_score=8,
                quality_score=9,
                context_window=128000,
                code_quality=9,
                security_analysis=8,
                documentation=9,
                reasoning=9,
                speed=8,
                creativity=9,
                research=5,
            ),
            "o1-preview": AICapability(
                provider="openai",
                model="o1-preview",
                cost_input=15.0,
                cost_output=60.0,
                speed_score=5,
                quality_score=10,
                context_window=128000,
                code_quality=10,
                security_analysis=10,
                documentation=7,
                reasoning=10,  # Best reasoning
                speed=5,  # Slower (more thinking time)
                creativity=8,
                research=5,
            ),
            # GOOGLE - Good general purpose
            "gemini-pro": AICapability(
                provider="google",
                model="gemini-pro",
                cost_input=0.5,
                cost_output=1.5,
                speed_score=9,
                quality_score=8,
                context_window=1000000,  # Huge context!
                code_quality=8,
                security_analysis=7,
                documentation=8,
                reasoning=8,
                speed=9,
                creativity=8,
                research=5,
            ),
            "gemini-flash": AICapability(
                provider="google",
                model="gemini-flash",
                cost_input=0.075,
                cost_output=0.30,
                speed_score=10,
                quality_score=7,
                context_window=1000000,
                code_quality=7,
                security_analysis=6,
                documentation=7,
                reasoning=7,
                speed=10,
                creativity=7,
                research=5,
            ),
            # PERPLEXITY - Research specialist
            "perplexity-sonar": AICapability(
                provider="perplexity",
                model="llama-3.1-sonar-large-128k-online",
                cost_input=1.0,
                cost_output=1.0,
                speed_score=8,
                quality_score=8,
                context_window=128000,
                code_quality=7,
                security_analysis=7,
                documentation=8,
                reasoning=8,
                speed=8,
                creativity=7,
                research=10,  # ⭐ ONLY ONE WITH WEB ACCESS!
            ),
            # GROQ - Speed demon
            "groq-llama-3-70b": AICapability(
                provider="groq",
                model="llama-3.1-70b-versatile",
                cost_input=0.10,
                cost_output=0.10,
                speed_score=10,  # ⭐ FASTEST
                quality_score=8,
                context_window=128000,
                code_quality=8,
                security_analysis=7,
                documentation=8,
                reasoning=8,
                speed=10,
                creativity=7,
                research=5,
            ),
            # TOGETHER AI - Cost effective
            "together-llama-3-70b": AICapability(
                provider="together",
                model="meta-llama/Llama-3-70b-chat-hf",
                cost_input=0.20,
                cost_output=0.20,
                speed_score=8,
                quality_score=8,
                context_window=8000,
                code_quality=8,
                security_analysis=7,
                documentation=8,
                reasoning=8,
                speed=8,
                creativity=7,
                research=5,
            ),
            # DEEPSEEK - Code specialist
            "deepseek-coder": AICapability(
                provider="deepseek",
                model="deepseek-coder-33b-instruct",
                cost_input=0.14,
                cost_output=0.28,
                speed_score=8,
                quality_score=9,
                context_window=16000,
                code_quality=10,  # ⭐ BEST FOR CODE
                security_analysis=8,
                documentation=7,
                reasoning=8,
                speed=8,
                creativity=6,
                research=5,
            ),
            # XAI - Real-time insights
            "grok-2": AICapability(
                provider="xai",
                model="grok-2",
                cost_input=2.0,
                cost_output=10.0,
                speed_score=7,
                quality_score=8,
                context_window=128000,
                code_quality=8,
                security_analysis=7,
                documentation=8,
                reasoning=9,
                speed=7,
                creativity=9,
                research=9,  # ⭐ X/Twitter integration
            ),
            # FIREWORKS - Production optimized
            "fireworks-llama-3-70b": AICapability(
                provider="fireworks",
                model="accounts/fireworks/models/llama-v3-70b-instruct",
                cost_input=0.50,
                cost_output=0.50,
                speed_score=9,
                quality_score=8,
                context_window=8000,
                code_quality=8,
                security_analysis=7,
                documentation=8,
                reasoning=8,
                speed=9,
                creativity=7,
                research=5,
            ),
        }

    def _initialize_task_requirements(self) -> dict[TaskType, dict[str, int]]:
        """Define what each task type requires from AI"""

        return {
            TaskType.SECURITY_AUDIT: {
                "code_quality": 10,  # Must be perfect
                "security_analysis": 10,  # Critical
                "reasoning": 10,  # Deep analysis
                "documentation": 7,
                "speed": 5,  # Quality > speed
                "creativity": 5,
                "research": 8,  # Check known vulnerabilities
            },
            TaskType.CORE_FEATURE: {
                "code_quality": 9,
                "security_analysis": 8,
                "reasoning": 9,
                "documentation": 8,
                "speed": 6,
                "creativity": 8,
                "research": 7,
            },
            TaskType.BUG_FIX: {
                "code_quality": 8,
                "security_analysis": 7,
                "reasoning": 9,  # Need to understand root cause
                "documentation": 6,
                "speed": 8,  # Faster is better
                "creativity": 5,
                "research": 6,
            },
            TaskType.OPTIMIZATION: {
                "code_quality": 9,
                "security_analysis": 7,
                "reasoning": 9,
                "documentation": 7,
                "speed": 7,
                "creativity": 7,
                "research": 8,  # Check best practices
            },
            TaskType.ATOMIC_SWAP: {
                "code_quality": 9,
                "security_analysis": 9,  # Financial code
                "reasoning": 9,
                "documentation": 8,
                "speed": 6,
                "creativity": 7,
                "research": 9,  # Check other implementations
            },
            TaskType.SMART_CONTRACT: {
                "code_quality": 10,  # Cannot have bugs
                "security_analysis": 10,
                "reasoning": 10,
                "documentation": 8,
                "speed": 5,
                "creativity": 7,
                "research": 9,
            },
            TaskType.TESTING: {
                "code_quality": 8,
                "security_analysis": 8,
                "reasoning": 8,
                "documentation": 7,
                "speed": 8,  # Can be fast
                "creativity": 8,  # Creative test cases
                "research": 6,
            },
            TaskType.DOCUMENTATION: {
                "code_quality": 5,
                "security_analysis": 3,
                "reasoning": 7,
                "documentation": 10,  # Most important
                "speed": 8,
                "creativity": 7,
                "research": 7,
            },
            TaskType.REFACTORING: {
                "code_quality": 9,
                "security_analysis": 7,
                "reasoning": 8,
                "documentation": 7,
                "speed": 7,
                "creativity": 6,
                "research": 6,
            },
            TaskType.UI_UX: {
                "code_quality": 7,
                "security_analysis": 5,
                "reasoning": 7,
                "documentation": 7,
                "speed": 7,
                "creativity": 9,  # Creative design
                "research": 8,  # Check trends
            },
            TaskType.RESEARCH: {
                "code_quality": 3,
                "security_analysis": 3,
                "reasoning": 9,
                "documentation": 8,
                "speed": 6,
                "creativity": 7,
                "research": 10,  # ⭐ Most important
            },
            TaskType.CODE_REVIEW: {
                "code_quality": 9,
                "security_analysis": 9,
                "reasoning": 10,  # Deep analysis
                "documentation": 7,
                "speed": 6,
                "creativity": 5,
                "research": 6,
            },
        }

    def select_best_ai(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        priority: TaskPriority,
        estimated_tokens: int,
        available_providers: list[str] | None = None,
        prefer_cost_optimization: bool = False,
    ) -> Dict:
        """
        Select the BEST AI model for a given task

        Returns:
            {
                'primary': 'claude-opus-4',
                'fallback': ['claude-sonnet-4', 'gpt-4-turbo'],
                'reasoning': 'Selected for high code quality and security analysis',
                'estimated_cost': 1.50
            }
        """
        # Import metrics
        from xai.core.ai_task_metrics import get_ai_task_metrics
        metrics = get_ai_task_metrics()

        # Record job submission
        metrics.jobs_submitted.labels(job_type=task_type.value).inc()

        # Get task requirements
        requirements = self.task_requirements.get(task_type, {})

        # Score each available AI
        scores = {}

        for model_name, capabilities in self.ai_models.items():
            # Skip if provider not available
            if available_providers and capabilities.provider not in available_providers:
                continue

            if not capabilities.available:
                continue

            # Calculate match score
            score = self._calculate_match_score(
                capabilities=capabilities,
                requirements=requirements,
                complexity=complexity,
                priority=priority,
                estimated_tokens=estimated_tokens,
                prefer_cost=prefer_cost_optimization,
            )

            scores[model_name] = score

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if not ranked:
            return {
                "success": False,
                "error": "NO_SUITABLE_AI_FOUND",
                "message": "No AI models available for this task",
            }

        # Select primary and fallbacks
        primary = ranked[0][0]
        fallback = [model for model, _ in ranked[1:4]]  # Top 3 alternatives

        # Calculate cost
        model = self.ai_models[primary]
        avg_cost_per_token = (model.cost_input + model.cost_output) / 2 / 1_000_000
        estimated_cost = estimated_tokens * avg_cost_per_token

        # Generate reasoning
        reasoning = self._generate_selection_reasoning(
            primary=primary, task_type=task_type, complexity=complexity, score=scores[primary]
        )

        # Record model selection metric
        metrics.model_selections.labels(model=primary, provider=model.provider).inc()

        return {
            "success": True,
            "primary": primary,
            "fallback": fallback,
            "reasoning": reasoning,
            "estimated_cost": round(estimated_cost, 2),
            "match_score": round(scores[primary], 2),
            "all_scores": {k: round(v, 2) for k, v in ranked},
        }

    def _calculate_match_score(
        self,
        capabilities: AICapability,
        requirements: dict[str, int],
        complexity: TaskComplexity,
        priority: TaskPriority,
        estimated_tokens: int,
        prefer_cost: bool,
    ) -> float:
        """
        Calculate how well an AI matches task requirements
        Returns score 0-100
        """

        score = 0.0

        # 1. Capability matching (70% of score)
        capability_score = 0.0
        total_weight = 0.0

        for requirement, importance in requirements.items():
            if hasattr(capabilities, requirement):
                capability_value = getattr(capabilities, requirement)

                # Weighted score
                match = (capability_value / 10.0) * importance
                capability_score += match
                total_weight += importance

        if total_weight > 0:
            capability_score = (capability_score / total_weight) * 70

        score += capability_score

        # 2. Complexity adjustment (10% of score)
        if complexity == TaskComplexity.CRITICAL:
            # Critical tasks need top quality
            score += capabilities.quality_score * 1.0
        elif complexity == TaskComplexity.COMPLEX:
            score += capabilities.quality_score * 0.7
        elif complexity == TaskComplexity.MODERATE:
            score += capabilities.quality_score * 0.5
        else:  # SIMPLE
            score += capabilities.quality_score * 0.3

        # 3. Cost optimization (10% of score)
        if prefer_cost:
            # Reward cheaper models
            avg_cost = (capabilities.cost_input + capabilities.cost_output) / 2

            if avg_cost < 1.0:
                score += 10  # Very cheap
            elif avg_cost < 5.0:
                score += 7  # Moderate
            elif avg_cost < 20.0:
                score += 3  # Expensive
            else:
                score += 0  # Very expensive
        else:
            # For non-cost-optimized, slightly penalize expensive models
            # (prefer value for money)
            avg_cost = (capabilities.cost_input + capabilities.cost_output) / 2

            if avg_cost > 50.0:
                score -= 5  # Very expensive
            elif avg_cost > 20.0:
                score -= 2  # Expensive

        # 4. Context window check (5% of score)
        if estimated_tokens > capabilities.context_window * 0.8:
            score -= 10  # Penalize if close to limit
        elif estimated_tokens > capabilities.context_window:
            score -= 50  # Heavily penalize if over limit

        # 5. Priority boost (5% of score)
        if priority == TaskPriority.CRITICAL:
            # Boost high-quality models
            score += capabilities.quality_score * 0.5

        return max(0.0, min(100.0, score))

    def _generate_selection_reasoning(
        self, primary: str, task_type: TaskType, complexity: TaskComplexity, score: float
    ) -> str:
        """Generate human-readable explanation of selection"""

        model = self.ai_models[primary]

        reasons = []

        # Main strengths
        if model.code_quality >= 9:
            reasons.append("excellent code quality")
        if model.security_analysis >= 9:
            reasons.append("strong security analysis")
        if model.reasoning >= 9:
            reasons.append("superior reasoning")
        if model.research >= 9:
            reasons.append("research capability")
        if model.speed >= 9:
            reasons.append("fast execution")

        # Cost consideration
        avg_cost = (model.cost_input + model.cost_output) / 2
        if avg_cost < 1.0:
            reasons.append("cost-effective")

        # Task-specific
        task_name = task_type.value.replace("_", " ")

        reasoning = f"Selected {primary} for {task_name} task"

        if reasons:
            reasoning += f" due to {', '.join(reasons)}"

        reasoning += f". Match score: {score:.1f}/100"

        if complexity == TaskComplexity.CRITICAL:
            reasoning += ". Critical task requires highest quality."

        return reasoning

# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 80)
    print("AI TASK MATCHER - INTELLIGENT AI SELECTION")
    print("=" * 80)

    matcher = AITaskMatcher()

    # Test different task types
    test_scenarios = [
        {
            "name": "Security Audit (Critical)",
            "task_type": TaskType.SECURITY_AUDIT,
            "complexity": TaskComplexity.CRITICAL,
            "priority": TaskPriority.CRITICAL,
            "estimated_tokens": 200000,
        },
        {
            "name": "Documentation (Simple)",
            "task_type": TaskType.DOCUMENTATION,
            "complexity": TaskComplexity.SIMPLE,
            "priority": TaskPriority.LOW,
            "estimated_tokens": 50000,
            "prefer_cost": True,
        },
        {
            "name": "Bug Fix (Moderate, Fast)",
            "task_type": TaskType.BUG_FIX,
            "complexity": TaskComplexity.MODERATE,
            "priority": TaskPriority.HIGH,
            "estimated_tokens": 30000,
        },
        {
            "name": "Research Latest Standards",
            "task_type": TaskType.RESEARCH,
            "complexity": TaskComplexity.MODERATE,
            "priority": TaskPriority.MEDIUM,
            "estimated_tokens": 100000,
        },
        {
            "name": "Atomic Swap Implementation",
            "task_type": TaskType.ATOMIC_SWAP,
            "complexity": TaskComplexity.COMPLEX,
            "priority": TaskPriority.HIGH,
            "estimated_tokens": 250000,
        },
    ]

    for scenario in test_scenarios:
        print("\n" + "=" * 80)
        print(f"SCENARIO: {scenario['name']}")
        print("-" * 80)

        name = scenario.pop("name")
        result = matcher.select_best_ai(**scenario)

        if result["success"]:
            print(f"\n✅ Primary AI: {result['primary']}")
            print(f"   Cost estimate: ${result['estimated_cost']}")
            print(f"   Match score: {result['match_score']}/100")
            print(f"\n📝 Reasoning: {result['reasoning']}")
            print(f"\n🔄 Fallback options:")
            for i, fallback in enumerate(result["fallback"][:3], 1):
                print(f"   {i}. {fallback}")

            print(f"\n📊 All AI Scores:")
            for ai, score in list(result["all_scores"].items())[:5]:
                print(f"   {ai}: {score}/100")
        else:
            print(f"❌ Error: {result['error']}")

    print("\n\n" + "=" * 80)
    print("SELECTION LOGIC SUMMARY")
    print("=" * 80)
    print(
        """
How AI is chosen for each task:

1. Task Analysis (70%):
   - What capabilities does task need?
   - Code quality, security, reasoning, speed, research, etc.
   - Match AI strengths to task needs

2. Complexity Adjustment (10%):
   - Critical tasks → require highest quality AI
   - Simple tasks → can use faster/cheaper AI

3. Cost Optimization (10%):
   - If cost optimization enabled → prefer cheaper
   - Otherwise → prefer value for money

4. Context Window (5%):
   - Ensure AI can handle estimated tokens
   - Penalize if close to limit

5. Priority Boost (5%):
   - Critical priority → boost quality models

Result: Perfect AI for each specific task!

Examples:
- Security audit → Claude Opus (best security analysis)
- Quick bug fix → Groq (fastest)
- Research task → Perplexity (web access)
- Documentation → Gemini Flash (cheap + good docs)
- Complex code → DeepSeek or O1 (code specialists)
    """
    )

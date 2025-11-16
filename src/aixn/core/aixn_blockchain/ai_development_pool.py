"""
XAI AI Development Pool - Autonomous Blockchain Development
Miners donate AI API credits to fund autonomous development
Multiple AI models compete to contribute the most

Revolutionary Concept:
1. Miners donate API minutes from Claude, GPT-4, Gemini, etc.
2. Credits pooled on-chain with encrypted API keys
3. When threshold reached, AI autonomously works on tasks
4. Public leaderboard shows which AI/users contributed most
5. Gamified competition drives sustainable development
"""

import hashlib
import os
import sys
import time
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum
import secrets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "core"))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from src.aixn.core.ai_pool_with_strict_limits import StrictAIPoolManager, AIProvider
from src.aixn.core.secure_api_key_manager import SecureAPIKeyManager


class AIModel(Enum):
    """Supported AI models for development"""

    # Anthropic
    CLAUDE_OPUS = "claude-opus-4"
    CLAUDE_SONNET = "claude-sonnet-4"
    CLAUDE_HAIKU = "claude-haiku-4"

    # OpenAI
    GPT4_TURBO = "gpt-4-turbo"
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"

    # Google
    GEMINI_ULTRA = "gemini-ultra"
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH = "gemini-flash"

    # Other
    LLAMA_70B = "llama-3-70b"
    MISTRAL_LARGE = "mistral-large"
    COHERE_COMMAND = "command-r-plus"
    DEEPSEEK_CODER = "deepseek-coder"


# Cost per million tokens (approximate USD)
MODEL_COSTS = {
    AIModel.CLAUDE_OPUS: {"input": 15.0, "output": 75.0},
    AIModel.CLAUDE_SONNET: {"input": 3.0, "output": 15.0},
    AIModel.CLAUDE_HAIKU: {"input": 0.25, "output": 1.25},
    AIModel.GPT4_TURBO: {"input": 10.0, "output": 30.0},
    AIModel.GPT4: {"input": 30.0, "output": 60.0},
    AIModel.GPT35_TURBO: {"input": 0.5, "output": 1.5},
    AIModel.O1_PREVIEW: {"input": 15.0, "output": 60.0},
    AIModel.O1_MINI: {"input": 3.0, "output": 12.0},
    AIModel.GEMINI_ULTRA: {"input": 12.5, "output": 37.5},
    AIModel.GEMINI_PRO: {"input": 0.5, "output": 1.5},
    AIModel.GEMINI_FLASH: {"input": 0.075, "output": 0.30},
    AIModel.LLAMA_70B: {"input": 0.9, "output": 0.9},
    AIModel.MISTRAL_LARGE: {"input": 4.0, "output": 12.0},
    AIModel.COHERE_COMMAND: {"input": 3.0, "output": 15.0},
    AIModel.DEEPSEEK_CODER: {"input": 0.14, "output": 0.28},
}

# Best models for different task types
MODEL_SPECIALIZATIONS = {
    "code_generation": [AIModel.CLAUDE_SONNET, AIModel.GPT4_TURBO, AIModel.DEEPSEEK_CODER],
    "bug_fixing": [AIModel.CLAUDE_OPUS, AIModel.O1_PREVIEW, AIModel.GPT4],
    "documentation": [AIModel.CLAUDE_SONNET, AIModel.GPT4_TURBO, AIModel.GEMINI_PRO],
    "optimization": [AIModel.O1_PREVIEW, AIModel.CLAUDE_OPUS, AIModel.DEEPSEEK_CODER],
    "security_audit": [AIModel.CLAUDE_OPUS, AIModel.GPT4, AIModel.O1_PREVIEW],
    "testing": [AIModel.CLAUDE_SONNET, AIModel.GPT4_TURBO, AIModel.DEEPSEEK_CODER],
}


MODEL_PROVIDER_MAP = {
    AIModel.CLAUDE_OPUS: AIProvider.ANTHROPIC,
    AIModel.CLAUDE_SONNET: AIProvider.ANTHROPIC,
    AIModel.CLAUDE_HAIKU: AIProvider.ANTHROPIC,
    AIModel.GPT4_TURBO: AIProvider.OPENAI,
    AIModel.GPT4: AIProvider.OPENAI,
    AIModel.GPT35_TURBO: AIProvider.OPENAI,
    AIModel.O1_PREVIEW: AIProvider.OPENAI,
    AIModel.O1_MINI: AIProvider.OPENAI,
    AIModel.GEMINI_ULTRA: AIProvider.GOOGLE,
    AIModel.GEMINI_PRO: AIProvider.GOOGLE,
    AIModel.GEMINI_FLASH: AIProvider.GOOGLE,
    AIModel.LLAMA_70B: AIProvider.ANTHROPIC,
    AIModel.MISTRAL_LARGE: AIProvider.ANTHROPIC,
    AIModel.COHERE_COMMAND: AIProvider.ANTHROPIC,
    AIModel.DEEPSEEK_CODER: AIProvider.ANTHROPIC,
}


class AIDonation:
    """Represents a single AI credit donation"""

    def __init__(
        self,
        donor_address: str,
        ai_model: AIModel,
        api_key_encrypted: str,
        donated_tokens: int,
        usd_value: float,
    ):

        self.donor_address = donor_address
        self.ai_model = ai_model
        self.api_key_encrypted = api_key_encrypted
        self.donated_tokens = donated_tokens
        self.usd_value = usd_value
        self.timestamp = time.time()
        self.donation_id = self._generate_id()
        self.used_tokens = 0
        self.tasks_completed = 0

    def _generate_id(self) -> str:
        """Generate unique donation ID"""
        data = f"{self.donor_address}{self.timestamp}{self.donated_tokens}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        """Convert to dictionary for blockchain storage"""
        return {
            "donation_id": self.donation_id,
            "donor_address": self.donor_address,
            "ai_model": self.ai_model.value,
            "api_key_encrypted": self.api_key_encrypted,
            "donated_tokens": self.donated_tokens,
            "usd_value": self.usd_value,
            "timestamp": self.timestamp,
            "used_tokens": self.used_tokens,
            "tasks_completed": self.tasks_completed,
        }


class DevelopmentTask:
    """A task that AI will autonomously complete"""

    def __init__(self, task_type: str, description: str, estimated_tokens: int, priority: int = 5):

        self.task_id = secrets.token_hex(8)
        self.task_type = task_type
        self.description = description
        self.estimated_tokens = estimated_tokens
        self.priority = priority  # 1-10, higher = more important
        self.status = "pending"
        self.assigned_model = None
        self.created_at = time.time()
        self.completed_at = None
        self.tokens_used = 0
        self.result = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "estimated_tokens": self.estimated_tokens,
            "priority": self.priority,
            "status": self.status,
            "assigned_model": self.assigned_model.value if self.assigned_model else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tokens_used": self.tokens_used,
        }


class AIDevelopmentPool:
    """
    Manages AI credit donations and autonomous development
    """

    def __init__(self, blockchain_seed: str = "xai_genesis_block_hash"):
        self.donations: List[AIDonation] = []
        self.task_queue: List[DevelopmentTask] = []
        self.completed_tasks: List[DevelopmentTask] = []
        self.key_manager = SecureAPIKeyManager(blockchain_seed)
        self.strict_pool = StrictAIPoolManager(self.key_manager)

        # Leaderboards
        self.donor_leaderboard: Dict[str, int] = {}  # address -> total tokens
        self.model_leaderboard: Dict[AIModel, int] = {}  # model -> total tokens
        self.model_task_count: Dict[AIModel, int] = {}  # model -> tasks completed

    def donate_ai_credits(
        self, donor_address: str, ai_model: AIModel, api_key: str, token_amount: int
    ) -> Dict:
        """
        Donate AI API credits to the development pool

        Args:
            donor_address: XAI wallet address of donor
            ai_model: Which AI model (Claude, GPT-4, etc.)
            api_key: API key for the model
            token_amount: Number of tokens to donate

        Returns:
            dict: Donation receipt
        """

        provider = self._provider_for_model(ai_model)
        submission = self.strict_pool.submit_api_key_donation(
            donor_address=donor_address,
            provider=provider,
            api_key=api_key,
            donated_tokens=token_amount,
            donated_minutes=None,
        )

        if not submission.get("success"):
            return submission

        key_id = submission["key_id"]

        # Calculate USD value for leaderboard
        model_cost = MODEL_COSTS[ai_model]
        avg_cost_per_token = (model_cost["input"] + model_cost["output"]) / 2 / 1_000_000
        usd_value = token_amount * avg_cost_per_token

        donation = AIDonation(
            donor_address=donor_address,
            ai_model=ai_model,
            api_key_encrypted=key_id,
            donated_tokens=token_amount,
            usd_value=usd_value,
        )

        self.donations.append(donation)

        self.donor_leaderboard[donor_address] = (
            self.donor_leaderboard.get(donor_address, 0) + token_amount
        )

        self.model_leaderboard[ai_model] = self.model_leaderboard.get(ai_model, 0) + token_amount

        self._process_task_queue()

        return {
            "success": True,
            "donation_id": donation.donation_id,
            "donor_address": donor_address,
            "ai_model": ai_model.value,
            "key_reference": key_id,
            "donated_tokens": token_amount,
            "usd_value": round(usd_value, 2),
            "your_total_donated": self.donor_leaderboard[donor_address],
            "your_rank": self.get_donor_rank(donor_address),
            "model_total": self.model_leaderboard[ai_model],
            "model_rank": self.get_model_rank(ai_model),
        }

    def create_development_task(
        self, task_type: str, description: str, estimated_tokens: int, priority: int = 5
    ) -> Dict:
        """
        Create a new development task for AI to complete

        Args:
            task_type: Type of task (code_generation, bug_fixing, etc.)
            description: What needs to be done
            estimated_tokens: Estimated token cost
            priority: 1-10, higher = more urgent

        Returns:
            dict: Task details
        """

        task = DevelopmentTask(
            task_type=task_type,
            description=description,
            estimated_tokens=estimated_tokens,
            priority=priority,
        )

        self.task_queue.append(task)

        # Sort queue by priority
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)

        # Try to process immediately
        self._process_task_queue()

        return {
            "success": True,
            "task_id": task.task_id,
            "task_type": task_type,
            "estimated_tokens": estimated_tokens,
            "queue_position": self.task_queue.index(task) + 1,
            "total_queued_tasks": len(self.task_queue),
            "status": "Will execute when sufficient credits available",
        }

    def _process_task_queue(self):
        """
        Process pending tasks if sufficient credits available
        This would be called periodically by the blockchain
        """

        for task in self.task_queue[:]:
            # Find best model for this task type
            suitable_models = MODEL_SPECIALIZATIONS.get(
                task.task_type, [AIModel.CLAUDE_SONNET]  # Default
            )

            # Check if we have credits for any suitable model
            for model in suitable_models:
                available_tokens = self._get_available_tokens(model)

                if available_tokens >= task.estimated_tokens:
                    # Enough credits! Execute task
                    self._execute_task(task, model)
                    self.task_queue.remove(task)
                    break

    def _get_available_tokens(self, model: AIModel) -> int:
        """Get total available tokens for a model"""
        total = 0
        for donation in self.donations:
            if donation.ai_model == model:
                remaining = donation.donated_tokens - donation.used_tokens
                total += remaining
        return total

    def _provider_for_model(self, model: AIModel) -> AIProvider:
        "Map AI models to providers for strict execution"
        return MODEL_PROVIDER_MAP.get(model, AIProvider.ANTHROPIC)

    def _apply_token_usage(self, model: AIModel, tokens_used: int):
        """Apply token usage across donations for reporting"""
        remaining = tokens_used
        for donation in self.donations:
            if donation.ai_model != model:
                continue
            available = donation.donated_tokens - donation.used_tokens
            if available <= 0:
                continue
            delta = min(available, remaining)
            donation.used_tokens += delta
            if delta > 0:
                donation.tasks_completed += 1
            remaining -= delta
            if remaining <= 0:
                break

    def _execute_task(self, task: DevelopmentTask, model: AIModel):
        """
        Execute a development task using AI providers via the strict pool
        """

        provider = self._provider_for_model(model)
        prompt = (
            f"Task Type: {task.task_type}\n"
            f"Priority: {task.priority}\n"
            f"Description: {task.description}"
        )

        execution_result = self.strict_pool.execute_ai_task_with_limits(
            task_description=prompt,
            estimated_tokens=task.estimated_tokens,
            provider=provider,
            max_tokens_override=task.estimated_tokens + 2048,
        )

        execution_result.setdefault("provider", provider.value)
        task.assigned_model = model
        task.tokens_used = execution_result.get("tokens_used", 0)
        task.result = execution_result
        task.completed_at = time.time()

        if execution_result.get("success"):
            task.status = "completed"
            self.completed_tasks.append(task)
            self.model_task_count[model] = self.model_task_count.get(model, 0) + 1
            self._apply_token_usage(model, task.tokens_used)
        else:
            task.status = "failed"

    def _simulate_ai_task(self, task: DevelopmentTask, model: AIModel, api_key: str) -> Dict:
        """
        Simulate AI task execution
        In production, this would call actual AI APIs
        """

        return {
            "task_type": task.task_type,
            "model_used": model.value,
            "execution_time": round(time.time() - task.created_at, 2),
            "tokens_used": task.estimated_tokens,
            "status": "completed",
            "output": f"Task {task.task_id} completed by {model.value}",
        }

    def get_donor_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """Get top donors by tokens contributed"""

        sorted_donors = sorted(self.donor_leaderboard.items(), key=lambda x: x[1], reverse=True)[
            :top_n
        ]

        leaderboard = []
        for rank, (address, tokens) in enumerate(sorted_donors, 1):
            # Calculate USD value across all their donations
            usd_value = sum(d.usd_value for d in self.donations if d.donor_address == address)

            leaderboard.append(
                {
                    "rank": rank,
                    "address": address,
                    "total_tokens": tokens,
                    "usd_value": round(usd_value, 2),
                    "donations_count": sum(1 for d in self.donations if d.donor_address == address),
                }
            )

        return leaderboard

    def get_model_leaderboard(self) -> List[Dict]:
        """Get AI model competition leaderboard"""

        sorted_models = sorted(self.model_leaderboard.items(), key=lambda x: x[1], reverse=True)

        leaderboard = []
        for rank, (model, tokens) in enumerate(sorted_models, 1):
            tasks_completed = self.model_task_count.get(model, 0)
            available_tokens = self._get_available_tokens(model)

            leaderboard.append(
                {
                    "rank": rank,
                    "model": model.value,
                    "total_donated_tokens": tokens,
                    "available_tokens": available_tokens,
                    "used_tokens": tokens - available_tokens,
                    "tasks_completed": tasks_completed,
                    "efficiency": round(tasks_completed / tokens * 1000, 2) if tokens > 0 else 0,
                }
            )

        return leaderboard

    def get_donor_rank(self, address: str) -> int:
        """Get rank of specific donor"""
        sorted_donors = sorted(self.donor_leaderboard.items(), key=lambda x: x[1], reverse=True)

        for rank, (addr, _) in enumerate(sorted_donors, 1):
            if addr == address:
                return rank

        return 0

    def get_model_rank(self, model: AIModel) -> int:
        """Get rank of specific AI model"""
        sorted_models = sorted(self.model_leaderboard.items(), key=lambda x: x[1], reverse=True)

        for rank, (m, _) in enumerate(sorted_models, 1):
            if m == model:
                return rank

        return 0

    def get_pool_stats(self) -> Dict:
        """Get overall pool statistics"""

        total_donated_tokens = sum(d.donated_tokens for d in self.donations)
        total_used_tokens = sum(d.used_tokens for d in self.donations)
        total_usd_value = sum(d.usd_value for d in self.donations)

        return {
            "total_donations": len(self.donations),
            "unique_donors": len(self.donor_leaderboard),
            "total_donated_tokens": total_donated_tokens,
            "total_used_tokens": total_used_tokens,
            "available_tokens": total_donated_tokens - total_used_tokens,
            "total_usd_value": round(total_usd_value, 2),
            "tasks_completed": len(self.completed_tasks),
            "tasks_pending": len(self.task_queue),
            "models_active": len(self.model_leaderboard),
            "top_donor": (
                max(self.donor_leaderboard.items(), key=lambda x: x[1])[0]
                if self.donor_leaderboard
                else None
            ),
            "top_model": (
                max(self.model_leaderboard.items(), key=lambda x: x[1])[0].value
                if self.model_leaderboard
                else None
            ),
        }


# Integration with blockchain transaction
class AIDonationTransaction:
    """Special transaction type for AI donations"""

    def __init__(
        self,
        sender: str,
        ai_model: str,
        api_key_encrypted: str,
        token_amount: int,
        usd_value: float,
    ):

        self.sender = sender
        self.tx_type = "ai_donation"
        self.ai_model = ai_model
        self.api_key_encrypted = api_key_encrypted
        self.token_amount = token_amount
        self.usd_value = usd_value
        self.timestamp = time.time()
        self.txid = self._generate_txid()

    def _generate_txid(self) -> str:
        data = f"{self.sender}{self.ai_model}{self.timestamp}{self.token_amount}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "txid": self.txid,
            "sender": self.sender,
            "tx_type": self.tx_type,
            "ai_model": self.ai_model,
            "api_key_encrypted": self.api_key_encrypted,
            "token_amount": self.token_amount,
            "usd_value": self.usd_value,
            "timestamp": self.timestamp,
        }


# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 80)
    print("XAI AI Development Pool - Gamified Autonomous Development")
    print("=" * 80)

    # Initialize pool
    pool = AIDevelopmentPool()

    # Simulate donations from different users with different AI models
    print("\n📊 SIMULATING AI CREDIT DONATIONS...")
    print("-" * 80)

    donations_data = [
        ("XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b", AIModel.CLAUDE_OPUS, "sk-ant-xxxxx", 500000),
        ("XAI4b8f2d9a6c3e1f7b4d9a2c8f1e6b3d7a9c2e", AIModel.GPT4_TURBO, "sk-xxxxx", 750000),
        ("XAI9e2f1b4d7a3c6e8f2b4d9a1c7e3f6b8d2a9c", AIModel.CLAUDE_SONNET, "sk-ant-xxxxx", 1000000),
        ("XAI3c6e8f1b4d7a2c9e4f2b8d1a6c3e7f9b2d4a", AIModel.GEMINI_PRO, "xxxxx", 2000000),
        ("XAI8d2a9c4e6f1b3d7a2c9e8f4b1d6a3c7e2f9b", AIModel.DEEPSEEK_CODER, "xxxxx", 3000000),
        (
            "XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
            AIModel.CLAUDE_OPUS,
            "sk-ant-xxxxx",
            300000,
        ),  # Same donor again!
        ("XAI2f9b4d6a1c8e3f7b2d9a4c6e1f8b3d7a2c9e", AIModel.O1_PREVIEW, "sk-xxxxx", 400000),
    ]

    for donor, model, api_key, tokens in donations_data:
        result = pool.donate_ai_credits(donor, model, api_key, tokens)
        print(f"\n✅ Donation #{len(pool.donations)}")
        print(f"   Donor: {donor[:20]}...")
        print(f"   Model: {result['ai_model']}")
        print(f"   Tokens: {result['donated_tokens']:,}")
        print(f"   USD Value: ${result['usd_value']}")
        print(f"   Donor Rank: #{result['your_rank']}")
        print(f"   Model Rank: #{result['model_rank']}")

    # Create development tasks
    print("\n\n📋 CREATING DEVELOPMENT TASKS...")
    print("-" * 80)

    tasks_data = [
        ("bug_fixing", "Fix memory leak in blockchain sync", 150000, 10),
        ("code_generation", "Implement new atomic swap protocol for Monero", 300000, 8),
        ("security_audit", "Audit smart contract vesting system", 200000, 9),
        ("documentation", "Write API documentation for Mesh-DEX", 100000, 5),
        ("optimization", "Optimize block validation algorithm", 250000, 7),
        ("testing", "Create integration tests for 11-coin atomic swaps", 180000, 6),
    ]

    for task_type, description, tokens, priority in tasks_data:
        result = pool.create_development_task(task_type, description, tokens, priority)
        print(f"\n📝 Task: {description}")
        print(f"   Type: {task_type}")
        print(f"   Estimated Tokens: {tokens:,}")
        print(f"   Priority: {priority}/10")
        print(f"   Status: {result['status']}")

    # Show donor leaderboard
    print("\n\n🏆 DONOR LEADERBOARD (Top Contributors)")
    print("=" * 80)

    donor_board = pool.get_donor_leaderboard(top_n=10)
    for entry in donor_board:
        print(f"\n#{entry['rank']} | {entry['address'][:25]}...")
        print(f"     Tokens Donated: {entry['total_tokens']:,}")
        print(f"     USD Value: ${entry['usd_value']}")
        print(f"     Donations: {entry['donations_count']}")

    # Show model competition leaderboard
    print("\n\n🤖 AI MODEL COMPETITION LEADERBOARD")
    print("=" * 80)

    model_board = pool.get_model_leaderboard()
    for entry in model_board:
        print(f"\n#{entry['rank']} | {entry['model']}")
        print(f"     Total Donated: {entry['total_donated_tokens']:,} tokens")
        print(f"     Available: {entry['available_tokens']:,} tokens")
        print(f"     Used: {entry['used_tokens']:,} tokens")
        print(f"     Tasks Completed: {entry['tasks_completed']}")
        print(f"     Efficiency: {entry['efficiency']} tasks/1k tokens")

    # Show pool statistics
    print("\n\n📈 POOL STATISTICS")
    print("=" * 80)

    stats = pool.get_pool_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    print("\n\n🎯 COMPETITIVE DYNAMICS")
    print("=" * 80)
    print(
        """
The AI Development Pool creates natural competition:

1. DONOR COMPETITION:
   - Miners compete to be #1 contributor
   - Leaderboard visible on-chain
   - Public recognition for top donors
   - Community status

2. MODEL COMPETITION:
   - Claude vs GPT-4 vs Gemini
   - Which AI completes most tasks?
   - Which is most efficient?
   - Community chooses winners

3. AUTONOMOUS DEVELOPMENT:
   - AI fixes bugs automatically
   - AI writes new features
   - AI optimizes code
   - AI creates documentation

4. SUSTAINABLE FUNDING:
   - No need for ICO or VC funding
   - Community donates spare AI credits
   - Development runs on donated compute
   - Fully decentralized dev team

This has NEVER been done before!
    """
    )

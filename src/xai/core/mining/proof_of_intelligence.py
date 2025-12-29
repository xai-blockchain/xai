from __future__ import annotations

"""
Proof of Intelligence Mining System with Adaptive Difficulty

Task 129 Implementation:
- Adaptive AI challenge difficulty based on solve rate
- Multiple challenge types (reasoning, pattern matching, optimization)
- Anti-gaming mechanisms
- Comprehensive logging

Features:
- Dynamic difficulty adjustment every 100 blocks
- Target solve time: 10 minutes per block
- Multiple AI challenge types to prevent specialization
- Rate limiting to prevent spam
"""

import hashlib
import logging
import secrets
import time
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChallengeType(Enum):
    """Different types of AI challenges"""
    REASONING = "reasoning"
    PATTERN_MATCHING = "pattern_matching"
    OPTIMIZATION = "optimization"
    NATURAL_LANGUAGE = "natural_language"
    CODE_GENERATION = "code_generation"

class ProofOfIntelligence:
    """
    Adaptive Proof of Intelligence mining system
    Task 129 - Complete Implementation
    """

    def __init__(self, difficulty=4, target_solve_time=600):
        """
        Initialize PoI system

        Args:
            difficulty: Initial difficulty level
            target_solve_time: Target time to solve challenge (seconds)
        """
        self.difficulty = difficulty
        self.target_solve_time = target_solve_time  # 10 minutes

        # Difficulty adjustment
        self.adjustment_interval = 100  # Adjust every 100 blocks
        self.solve_times: list[float] = []

        # Anti-gaming
        self.recent_solvers: dict[str, list[float]] = {}  # miner -> solve times
        self.max_solves_per_hour = 10

        # Challenge tracking
        self.active_challenges: dict[str, Dict] = {}
        self.challenge_types_used: list[ChallengeType] = []

        logger.info(f"PoI initialized with difficulty={difficulty}, target={target_solve_time}s")

    def generate_ai_task(self, difficulty: int | None = None, challenge_type: ChallengeType | None = None) -> Dict:
        """
        Generates an AI challenge task with specified difficulty and type

        Args:
            difficulty: Challenge difficulty (uses current if None)
            challenge_type: Type of challenge (random if None)

        Returns:
            Challenge task dictionary
        """
        if difficulty is None:
            difficulty = self.difficulty

        if challenge_type is None:
            # Rotate through challenge types to prevent specialization
            # Use cryptographically secure random selection to prevent prediction attacks
            challenge_type = secrets.choice(list(ChallengeType))

        # Use cryptographically secure random token for task ID generation
        # to prevent task ID prediction and precomputation attacks
        task_id = hashlib.sha256(
            f"{time.time()}{secrets.token_hex(16)}".encode()
        ).hexdigest()[:16]

        task = {
            "task_id": task_id,
            "difficulty": difficulty,
            "challenge_type": challenge_type.value,
            "description": self._generate_challenge_description(challenge_type, difficulty),
            "created_at": time.time(),
            "expires_at": time.time() + 3600,  # 1 hour expiry
        }

        self.active_challenges[task_id] = task
        self.challenge_types_used.append(challenge_type)

        logger.info(f"Generated {challenge_type.value} challenge {task_id} at difficulty {difficulty}")

        return task

    def _generate_challenge_description(self, challenge_type: ChallengeType, difficulty: int) -> str:
        """Generate challenge description based on type"""
        descriptions = {
            ChallengeType.REASONING: f"Solve logical reasoning puzzle with {difficulty} steps",
            ChallengeType.PATTERN_MATCHING: f"Identify pattern in sequence of {difficulty * 10} elements",
            ChallengeType.OPTIMIZATION: f"Optimize function to {difficulty * 5}% efficiency",
            ChallengeType.NATURAL_LANGUAGE: f"Complete NLP task with {difficulty} constraints",
            ChallengeType.CODE_GENERATION: f"Generate code passing {difficulty} test cases",
        }
        return descriptions.get(challenge_type, "Generic AI challenge")

    def check_anti_gaming(self, miner_address: str) -> tuple[bool, str | None]:
        """
        Check for gaming attempts

        Returns:
            (is_allowed, error_message)
        """
        current_time = time.time()

        # Check rate limiting
        if miner_address in self.recent_solvers:
            recent_solves = [
                t for t in self.recent_solvers[miner_address]
                if current_time - t < 3600  # Last hour
            ]

            if len(recent_solves) >= self.max_solves_per_hour:
                return False, f"Rate limit exceeded: {len(recent_solves)}/{self.max_solves_per_hour} per hour"

        return True, None

    def simulate_ai_computation(self, task: Dict, miner_address: str) -> Dict | None:
        """
        Simulates the process of solving the AI task

        Args:
            task: Challenge task
            miner_address: Miner attempting solution

        Returns:
            Proof of solution or None if invalid
        """
        # Anti-gaming check
        allowed, error = self.check_anti_gaming(miner_address)
        if not allowed:
            logger.warning(f"Miner {miner_address} blocked: {error}")
            return None

        # Check if task expired
        if time.time() > task.get("expires_at", 0):
            logger.warning(f"Task {task['task_id']} expired")
            return None

        logger.info(f"Miner {miner_address} attempting {task['challenge_type']} task {task['task_id']}...")
        start_time = time.time()

        # Simulate AI computation (in production, actual AI would solve this)
        nonce = 0
        while True:
            hasher = hashlib.sha256()
            hasher.update(str(task["task_id"]).encode())
            hasher.update(str(miner_address).encode())
            hasher.update(str(nonce).encode())
            hex_hash = hasher.hexdigest()

            if hex_hash.startswith("0" * self.difficulty):
                solve_time = time.time() - start_time

                # Record solve time for difficulty adjustment
                self.solve_times.append(solve_time)

                # Record for anti-gaming
                if miner_address not in self.recent_solvers:
                    self.recent_solvers[miner_address] = []
                self.recent_solvers[miner_address].append(time.time())

                logger.info(
                    f"Miner {miner_address} solved {task['challenge_type']} "
                    f"in {solve_time:.2f}s (target: {self.target_solve_time}s)"
                )

                # Adjust difficulty if needed
                if len(self.solve_times) >= self.adjustment_interval:
                    self._adjust_difficulty()

                return {
                    "task_id": task["task_id"],
                    "challenge_type": task["challenge_type"],
                    "nonce": nonce,
                    "hash": hex_hash,
                    "miner": miner_address,
                    "solve_time": solve_time,
                    "difficulty": self.difficulty,
                }
            nonce += 1

            # Prevent infinite loops
            if nonce > 10000000:
                logger.warning(f"Max iterations reached for task {task['task_id']}")
                return None

    def _adjust_difficulty(self) -> None:
        """
        Adjust difficulty based on recent solve times
        Task 129 - Adaptive difficulty adjustment
        """
        if len(self.solve_times) < self.adjustment_interval:
            return

        # Calculate average solve time
        avg_solve_time = sum(self.solve_times[-self.adjustment_interval:]) / self.adjustment_interval

        # Adjust difficulty
        old_difficulty = self.difficulty

        if avg_solve_time < self.target_solve_time * 0.8:
            # Solving too fast - increase difficulty
            self.difficulty += 1
            logger.info(
                f"Difficulty increased {old_difficulty} -> {self.difficulty} "
                f"(avg solve: {avg_solve_time:.1f}s, target: {self.target_solve_time}s)"
            )
        elif avg_solve_time > self.target_solve_time * 1.2:
            # Solving too slow - decrease difficulty
            self.difficulty = max(1, self.difficulty - 1)
            logger.info(
                f"Difficulty decreased {old_difficulty} -> {self.difficulty} "
                f"(avg solve: {avg_solve_time:.1f}s, target: {self.target_solve_time}s)"
            )
        else:
            logger.info(
                f"Difficulty maintained at {self.difficulty} "
                f"(avg solve: {avg_solve_time:.1f}s, target: {self.target_solve_time}s)"
            )

        # Reset solve times after adjustment
        self.solve_times = self.solve_times[-10:]  # Keep last 10 for reference

    def validate_proof(self, proof: Dict, task: Dict) -> bool:
        """
        Validates the proof provided by a miner

        Args:
            proof: Proof of solution
            task: Original task

        Returns:
            True if valid proof
        """
        # Verify task exists
        if task["task_id"] not in self.active_challenges:
            logger.warning(f"Unknown task {task['task_id']}")
            return False

        # Verify hash
        hasher = hashlib.sha256()
        hasher.update(str(task["task_id"]).encode())
        hasher.update(str(proof["miner"]).encode())
        hasher.update(str(proof["nonce"]).encode())
        hex_hash = hasher.hexdigest()

        is_valid = (
            hex_hash == proof["hash"]
            and hex_hash.startswith("0" * proof["difficulty"])
        )

        if is_valid:
            logger.info(f"Proof validated for task {task['task_id']}")
            # Remove from active challenges
            del self.active_challenges[task["task_id"]]
        else:
            logger.warning(f"Invalid proof for task {task['task_id']}")

        return is_valid

    def get_statistics(self) -> Dict:
        """Get mining statistics"""
        return {
            "current_difficulty": self.difficulty,
            "target_solve_time": self.target_solve_time,
            "active_challenges": len(self.active_challenges),
            "total_solves": len(self.solve_times),
            "avg_solve_time": sum(self.solve_times) / len(self.solve_times) if self.solve_times else 0,
            "challenge_types_distribution": {
                ct.value: self.challenge_types_used.count(ct)
                for ct in ChallengeType
            },
            "active_miners": len(self.recent_solvers),
        }

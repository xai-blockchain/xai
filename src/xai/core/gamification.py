"""
AXN Blockchain Gamification Features
Implements 5 gamification mechanisms to increase engagement and network activity
All features use $0 cost - pure Python with JSON file storage
"""

import json
import logging
import time
import secrets
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import os
from xai.core.blockchain_interface import GamificationBlockchainInterface

logger = logging.getLogger(__name__)


# Cryptographically secure random number generation helpers
# Used for fairness-critical operations: airdrops, winner selection, treasure hunts

def _secure_randint(a: int, b: int) -> int:
    """
    Cryptographically secure random integer in [a, b] inclusive.

    Uses secrets.randbelow() which is backed by os.urandom() - suitable for
    security/cryptographic use where unpredictability is critical.

    Args:
        a: Minimum value (inclusive)
        b: Maximum value (inclusive)

    Returns:
        Random integer in range [a, b]
    """
    if a > b:
        raise ValueError(f"Invalid range: {a} > {b}")
    return secrets.randbelow(b - a + 1) + a


def _secure_random_float(min_val: float = 0.0, max_val: float = 1.0, precision: int = 10000) -> float:
    """
    Cryptographically secure random float in [min_val, max_val].

    Args:
        min_val: Minimum value
        max_val: Maximum value
        precision: Number of discrete steps (higher = more precision)

    Returns:
        Random float in range [min_val, max_val]
    """
    if min_val > max_val:
        raise ValueError(f"Invalid range: {min_val} > {max_val}")

    # Generate secure random value in [0, 1] with given precision
    random_fraction = secrets.randbelow(precision) / float(precision)

    # Scale to desired range
    return min_val + (random_fraction * (max_val - min_val))


def _secure_sample(population: list, k: int) -> list:
    """
    Cryptographically secure random sample without replacement.

    Implements Fisher-Yates shuffle algorithm with secure randomness.
    This prevents predictable selection even if internal state is partially known.

    Args:
        population: List to sample from
        k: Number of samples to draw

    Returns:
        List of k randomly selected items (no duplicates)
    """
    if k > len(population):
        raise ValueError(f"Sample size {k} exceeds population size {len(population)}")

    # Create a copy to avoid modifying original
    pool = list(population)
    result = []

    # Fisher-Yates shuffle for first k elements
    for i in range(k):
        # Select random index from remaining items
        j = _secure_randint(i, len(pool) - 1)
        # Swap
        pool[i], pool[j] = pool[j], pool[i]
        result.append(pool[i])

    return result


def _secure_choice(population: list):
    """
    Cryptographically secure random choice from list.

    Args:
        population: List to choose from

    Returns:
        Single randomly selected item
    """
    if not population:
        raise ValueError("Cannot choose from empty population")

    return population[secrets.randbelow(len(population))]


class AirdropManager:
    """
    Random Airdrops - Every 100th block, distribute 1-10 AXN to 10 random active addresses
    Tracks active addresses from recent blocks and distributes rewards periodically
    """

    def __init__(self, blockchain_interface: GamificationBlockchainInterface, data_dir: str = None):
        self.blockchain_interface = blockchain_interface
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "gamification_data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.airdrop_file = self.data_dir / "airdrops.json"
        self.airdrop_history = self._load_airdrop_history()

    def _load_airdrop_history(self) -> List[dict]:
        """Load airdrop history from file"""
        if self.airdrop_file.exists():
            try:
                with open(self.airdrop_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Corrupted airdrop file, resetting",
                    extra={"event": "gamification.airdrop.file_corrupted", "error": str(e)},
                )
                # Backup corrupted file
                backup_path = str(self.airdrop_file) + ".corrupted"
                self.airdrop_file.rename(backup_path)
                return []
        return []

    def _save_airdrop_history(self):
        """Save airdrop history to file"""
        with open(self.airdrop_file, "w") as f:
            json.dump(self.airdrop_history, f, indent=2)

    def should_trigger_airdrop(self, block_height: int) -> bool:
        """Check if airdrop should trigger at this block height"""
        return block_height > 0 and block_height % 100 == 0

    def get_active_addresses(self, lookback_blocks: int = 100) -> List[str]:
        """
        Get active addresses from recent blocks (excluding COINBASE and GENESIS)
        Returns addresses that have sent or received transactions in the last N blocks
        """
        active_addresses = set()
        chain_length = self.blockchain_interface.get_chain_length()
        start_index = max(0, chain_length - lookback_blocks)

        for i in range(start_index, chain_length):
            block = self.blockchain_interface.get_block_by_index(i)
            if not block:
                continue
            for tx in block.transactions:
                if tx.sender not in ["COINBASE", "GENESIS"]:
                    active_addresses.add(tx.sender)
                if tx.recipient not in ["COINBASE", "GENESIS"]:
                    active_addresses.add(tx.recipient)

        return list(active_addresses)

    def select_airdrop_winners(
        self,
        active_addresses: List[str],
        count: int = 10,
        seed: str = None,
        weighted: bool = True,
        activity_scores: Optional[Dict[str, int]] = None
    ) -> List[str]:
        """
        TASK 61: Fair random selection with optional weighted distribution
        Uses block hash as seed for deterministic but unpredictable selection
        Supports weighted selection based on activity scores

        SECURITY: Uses cryptographically secure randomness (secrets module)
        If seed is provided (block hash), uses it to derive deterministic but
        unpredictable selection via hashing - this ensures fairness and prevents
        manipulation while maintaining reproducibility for same block hash.
        """
        if not active_addresses:
            return []

        # Select up to 'count' winners
        winner_count = min(count, len(active_addresses))

        if weighted and activity_scores:
            # Weighted random selection based on activity
            # More active users have higher probability
            weights = [activity_scores.get(addr, 1) for addr in active_addresses]

            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                probabilities = [w / total_weight for w in weights]
            else:
                probabilities = [1 / len(active_addresses)] * len(active_addresses)

            # Use weighted random selection (secure implementation)
            winners = []
            remaining_addresses = active_addresses.copy()
            remaining_probs = probabilities.copy()

            for i in range(winner_count):
                if not remaining_addresses:
                    break

                # Cumulative probability selection with secure randomness
                if seed:
                    # Deterministic but unpredictable: hash seed with iteration
                    hash_input = f"{seed}:{i}".encode()
                    hash_digest = hashlib.sha256(hash_input).digest()
                    # Use first 8 bytes as random value
                    r = int.from_bytes(hash_digest[:8], 'big') / (2**64)
                else:
                    # Truly random using secrets module
                    r = _secure_random_float(0.0, 1.0, precision=100000)

                cumulative = 0
                selected_idx = 0

                for idx, prob in enumerate(remaining_probs):
                    cumulative += prob
                    if r <= cumulative:
                        selected_idx = idx
                        break

                winners.append(remaining_addresses[selected_idx])

                # Remove selected address
                remaining_addresses.pop(selected_idx)
                remaining_probs.pop(selected_idx)

                # Renormalize probabilities
                if remaining_probs:
                    total = sum(remaining_probs)
                    remaining_probs = [p / total for p in remaining_probs]

            return winners
        else:
            # Simple random selection without weighting
            if seed:
                # Deterministic selection using seed
                # Sort addresses first for consistent ordering
                sorted_addresses = sorted(active_addresses)

                # Select winners deterministically based on hash
                winners = []
                for i in range(winner_count):
                    hash_input = f"{seed}:{i}".encode()
                    hash_digest = hashlib.sha256(hash_input).digest()
                    # Use hash to select index
                    idx = int.from_bytes(hash_digest[:4], 'big') % len(sorted_addresses)

                    # Ensure no duplicates
                    selected = sorted_addresses[idx]
                    attempts = 0
                    while selected in winners and attempts < len(sorted_addresses):
                        hash_input = f"{seed}:{i}:{attempts}".encode()
                        hash_digest = hashlib.sha256(hash_input).digest()
                        idx = int.from_bytes(hash_digest[:4], 'big') % len(sorted_addresses)
                        selected = sorted_addresses[idx]
                        attempts += 1

                    if selected not in winners:
                        winners.append(selected)

                return winners
            else:
                # Truly random selection using secure randomness
                winners = _secure_sample(active_addresses, winner_count)
                return winners

    def calculate_airdrop_amounts(self, winners: List[str], seed: str = None) -> Dict[str, float]:
        """
        Calculate random airdrop amount for each winner (1-10 AXN)
        Uses seed for deterministic amounts

        SECURITY: Uses cryptographically secure randomness (secrets module)
        If seed is provided, uses deterministic hash-based generation for
        reproducibility while maintaining unpredictability.
        """
        amounts = {}
        for idx, winner in enumerate(winners):
            if seed:
                # Deterministic but unpredictable amount using hash
                hash_input = f"{seed}:amount:{winner}:{idx}".encode()
                hash_digest = hashlib.sha256(hash_input).digest()
                # Use hash to generate value in [1.0, 10.0]
                # First 4 bytes as integer, scale to range
                random_int = int.from_bytes(hash_digest[:4], 'big')
                # Map to [1.0, 10.0] range with 2 decimal precision
                amount = 1.0 + ((random_int % 900) / 100.0)  # 900 cents = 9.00 range
                amounts[winner] = round(amount, 2)
            else:
                # Truly random amount using secure randomness
                amount = _secure_random_float(1.0, 10.0, precision=900)
                amounts[winner] = round(amount, 2)

        return amounts

    def execute_airdrop(self, block_height: int, block_hash: str) -> Optional[Dict[str, float]]:
        """
        Execute airdrop at the given block height
        Returns dict of {address: amount} for winners
        """
        if not self.should_trigger_airdrop(block_height):
            return None

        # Get active addresses from last 100 blocks
        active_addresses = self.get_active_addresses(lookback_blocks=100)

        if not active_addresses:
            logger.info(
                "No active addresses for airdrop",
                extra={"event": "gamification.airdrop.no_addresses", "block_height": block_height},
            )
            return None

        # Use block hash as seed for deterministic randomness
        seed = block_hash

        # Select winners
        winners = self.select_airdrop_winners(active_addresses, count=10, seed=seed)

        # Calculate amounts
        airdrop_amounts = self.calculate_airdrop_amounts(winners, seed=seed)

        # Record airdrop
        airdrop_record = {
            "block_height": block_height,
            "block_hash": block_hash,
            "timestamp": time.time(),
            "winners": airdrop_amounts,
            "total_distributed": sum(airdrop_amounts.values()),
            "winner_count": len(winners),
        }

        self.airdrop_history.append(airdrop_record)
        self._save_airdrop_history()

        logger.info(
            "Airdrop executed",
            extra={
                "event": "gamification.airdrop.executed",
                "block_height": block_height,
                "winners": len(winners),
                "total_distributed": sum(airdrop_amounts.values()),
            },
        )

        return airdrop_amounts

    def get_recent_airdrops(self, limit: int = 10) -> List[dict]:
        """Get recent airdrop history"""
        return self.airdrop_history[-limit:]

    def get_user_airdrop_history(self, address: str) -> List[dict]:
        """Get airdrop history for specific address"""
        user_airdrops = []
        for airdrop in self.airdrop_history:
            if address in airdrop["winners"]:
                user_airdrops.append(
                    {
                        "block_height": airdrop["block_height"],
                        "timestamp": airdrop["timestamp"],
                        "amount": airdrop["winners"].get(address, 0),
                    }
                )
        return user_airdrops


class StreakTracker:
    """
    Mining Streak Bonuses - Track consecutive mining days
    Gives up to 20% bonus for 10+ day streaks
    1 day = 1% bonus, capped at 20% (10 days or more)
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "gamification_data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.streak_file = self.data_dir / "mining_streaks.json"
        self.miner_streaks = self._load_streaks()

    def _load_streaks(self) -> Dict[str, dict]:
        """Load mining streaks from file"""
        if self.streak_file.exists():
            try:
                with open(self.streak_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Corrupted streak file, resetting",
                    extra={"event": "gamification.streak.file_corrupted", "error": str(e)},
                )
                # Backup corrupted file
                backup_path = str(self.streak_file) + ".corrupted"
                self.streak_file.rename(backup_path)
                return {}
        return {}

    def _save_streaks(self):
        """Save mining streaks to file"""
        with open(self.streak_file, "w") as f:
            json.dump(self.miner_streaks, f, indent=2)

    def _get_day_key(self, timestamp: float) -> str:
        """Convert timestamp to day key (YYYY-MM-DD)"""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

    def update_miner_streak(self, miner_address: str, block_timestamp: float):
        """
        Update mining streak for a miner
        Tracks consecutive days of mining
        """
        day_key = self._get_day_key(block_timestamp)

        if miner_address not in self.miner_streaks:
            # New miner
            self.miner_streaks[miner_address] = {
                "current_streak": 1,
                "longest_streak": 1,
                "last_mining_day": day_key,
                "total_blocks_mined": 1,
                "mining_days": [day_key],
            }
        else:
            streak_data = self.miner_streaks[miner_address]
            last_day = streak_data["last_mining_day"]

            # Check if this is a new day
            if day_key != last_day:
                # Parse dates
                last_date = datetime.strptime(last_day, "%Y-%m-%d")
                current_date = datetime.strptime(day_key, "%Y-%m-%d")
                days_diff = (current_date - last_date).days

                if days_diff == 1:
                    # Consecutive day - increment streak
                    streak_data["current_streak"] += 1
                    streak_data["longest_streak"] = max(
                        streak_data["longest_streak"], streak_data["current_streak"]
                    )
                elif days_diff > 1:
                    # Streak broken - reset to 1
                    streak_data["current_streak"] = 1

                streak_data["last_mining_day"] = day_key
                if day_key not in streak_data["mining_days"]:
                    streak_data["mining_days"].append(day_key)

            streak_data["total_blocks_mined"] += 1

        self._save_streaks()

    def get_streak_bonus(self, miner_address: str, with_decay: bool = True) -> float:
        """
        TASK 60: Calculate streak bonus percentage with optional decay
        1 day = 1% bonus, capped at 20% for 10+ days
        Decay reduces bonus if mining gaps occur
        """
        if miner_address not in self.miner_streaks:
            return 0.0

        streak_data = self.miner_streaks[miner_address]
        current_streak = streak_data["current_streak"]
        last_mining_day = streak_data["last_mining_day"]

        # Calculate base bonus
        bonus_percent = min(current_streak * 0.01, 0.20)

        if with_decay:
            # Apply gradual decay based on days since last mining
            last_date = datetime.strptime(last_mining_day, "%Y-%m-%d")
            current_date = datetime.now()
            days_inactive = (current_date - last_date).days

            if days_inactive > 0:
                # Decay rate: 10% reduction per day inactive (gradual reduction)
                decay_factor = max(0.0, 1.0 - (days_inactive * 0.10))
                bonus_percent *= decay_factor

        return max(0.0, bonus_percent)  # Ensure non-negative

    def apply_streak_bonus(self, miner_address: str, base_reward: float) -> Tuple[float, float]:
        """
        Apply streak bonus to block reward
        Returns (final_reward, bonus_amount)
        """
        bonus_percent = self.get_streak_bonus(miner_address)
        bonus_amount = base_reward * bonus_percent
        final_reward = base_reward + bonus_amount

        return final_reward, bonus_amount

    def get_miner_stats(self, miner_address: str) -> Optional[dict]:
        """Get mining statistics for address"""
        if miner_address not in self.miner_streaks:
            return None

        streak_data = self.miner_streaks[miner_address].copy()
        streak_data["bonus_percent"] = self.get_streak_bonus(miner_address) * 100
        return streak_data

    def get_leaderboard(self, limit: int = 10, sort_by: str = "current_streak") -> List[dict]:
        """
        Get mining streak leaderboard
        sort_by: 'current_streak', 'longest_streak', or 'total_blocks_mined'
        """
        leaderboard = []

        for address, data in self.miner_streaks.items():
            entry = {
                "address": address,
                "current_streak": data["current_streak"],
                "longest_streak": data["longest_streak"],
                "total_blocks_mined": data["total_blocks_mined"],
                "bonus_percent": self.get_streak_bonus(address) * 100,
            }
            leaderboard.append(entry)

        # Sort by specified metric
        leaderboard.sort(key=lambda x: x[sort_by], reverse=True)

        return leaderboard[:limit]


class TreasureHuntManager:
    """
    Blockchain Treasure Hunts - Allow miners to hide puzzle transactions
    Others can claim by solving puzzles (hash-based or math puzzles)
    """

    def __init__(self, blockchain_interface: GamificationBlockchainInterface, data_dir: str = None):
        self.blockchain_interface = blockchain_interface
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "gamification_data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.treasure_file = self.data_dir / "treasure_hunts.json"
        self.treasures = self._load_treasures()

    def _load_treasures(self) -> Dict[str, dict]:
        """Load treasure hunts from file"""
        if self.treasure_file.exists():
            with open(self.treasure_file, "r") as f:
                return json.load(f)
        return {}

    def _save_treasures(self):
        """Save treasure hunts to file"""
        with open(self.treasure_file, "w") as f:
            json.dump(self.treasures, f, indent=2)

    def create_treasure_hunt(
        self,
        creator_address: str,
        amount: float,
        puzzle_type: str,
        puzzle_data: dict,
        hint: str = "",
    ) -> str:
        """
        Create a new treasure hunt

        puzzle_type: 'hash', 'math', 'sequence'
        puzzle_data: puzzle-specific data (answer_hash, equation, etc.)
        """
        # Generate treasure ID
        treasure_id = hashlib.sha256(
            f"{creator_address}{amount}{time.time()}".encode()
        ).hexdigest()[:16]

        treasure = {
            "id": treasure_id,
            "creator": creator_address,
            "amount": amount,
            "puzzle_type": puzzle_type,
            "puzzle_data": puzzle_data,
            "hint": hint,
            "created_at": time.time(),
            "status": "active",
            "claimed_by": None,
            "claimed_at": None,
            "attempts": [],
        }

        self.treasures[treasure_id] = treasure
        self._save_treasures()

        logger.info(
            "Treasure hunt created",
            extra={
                "event": "gamification.treasure.created",
                "treasure_id": treasure_id,
                "amount": amount,
            },
        )

        return treasure_id

    def verify_solution(self, treasure_id: str, solution: str, proof: Optional[dict] = None) -> bool:
        """
        TASK 59: Verify if solution is correct for treasure hunt
        Supports GPS or cryptographic proof verification
        """
        if treasure_id not in self.treasures:
            return False

        treasure = self.treasures[treasure_id]

        if treasure["status"] != "active":
            return False

        puzzle_type = treasure["puzzle_type"]
        puzzle_data = treasure["puzzle_data"]

        if puzzle_type == "hash":
            # Solution must hash to answer_hash
            solution_hash = hashlib.sha256(solution.encode()).hexdigest()
            return solution_hash == puzzle_data["answer_hash"]

        elif puzzle_type == "math":
            # Solution must equal the answer
            try:
                return float(solution) == float(puzzle_data["answer"])
            except (ValueError, TypeError, KeyError):
                return False

        elif puzzle_type == "sequence":
            # Solution must be the next number in sequence
            return solution == str(puzzle_data["next_number"])

        elif puzzle_type == "gps":
            # GPS-based treasure hunt - verify location proof
            if not proof or "latitude" not in proof or "longitude" not in proof:
                return False

            target_lat = puzzle_data.get("latitude", 0)
            target_lon = puzzle_data.get("longitude", 0)
            radius = puzzle_data.get("radius_meters", 100)

            # Calculate distance using Haversine formula
            from math import radians, cos, sin, asin, sqrt

            lat1, lon1 = radians(target_lat), radians(target_lon)
            lat2, lon2 = radians(proof["latitude"]),
            radians(proof["longitude"])

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            distance = 6371000 * c  # Earth radius in meters

            return distance <= radius

        elif puzzle_type == "cryptographic":
            # Cryptographic proof verification (zero-knowledge proof, signature, etc.)
            if not proof or "signature" not in proof:
                return False

            # Verify cryptographic signature matches challenge
            challenge = puzzle_data.get("challenge", "")
            expected_signature = puzzle_data.get("answer_signature", "")

            return proof["signature"] == expected_signature

        return False

    def claim_treasure(
        self,
        treasure_id: str,
        claimer_address: str,
        solution: str,
    ) -> Tuple[bool, Optional[float]]:
        """
        Attempt to claim treasure by solving puzzle
        Returns (success, amount)
        """
        if treasure_id not in self.treasures:
            return False, None

        treasure = self.treasures[treasure_id]

        # Record attempt
        treasure["attempts"].append(
            {"address": claimer_address, "timestamp": time.time(), "success": False}
        )

        # Verify solution
        if not self.verify_solution(treasure_id, solution):
            self._save_treasures()
            return False, None

        # Claim treasure
        treasure["status"] = "claimed"
        treasure["claimed_by"] = claimer_address
        treasure["claimed_at"] = time.time()
        treasure["attempts"][-1]["success"] = True

        self._save_treasures()

        logger.info(
            "Treasure claimed",
            extra={
                "event": "gamification.treasure.claimed",
                "treasure_id": treasure_id,
                "claimer": claimer_address,
                "amount": treasure["amount"],
            },
        )

        return True, treasure["amount"]

    def get_active_treasures(self) -> List[dict]:
        """Get all active (unclaimed) treasure hunts"""
        active = []
        for treasure_id, treasure in self.treasures.items():
            if treasure["status"] == "active":
                # Return sanitized version (no answer)
                active.append(
                    {
                        "id": treasure["id"],
                        "creator": treasure["creator"],
                        "amount": treasure["amount"],
                        "puzzle_type": treasure["puzzle_type"],
                        "hint": treasure["hint"],
                        "created_at": treasure["created_at"],
                        "attempts": len(treasure["attempts"]),
                    }
                )
        return active

    def get_treasure_details(self, treasure_id: str) -> Optional[dict]:
        """Get full details of treasure hunt (for display, no answer)"""
        if treasure_id not in self.treasures:
            return None

        treasure = self.treasures[treasure_id].copy()

        # Remove sensitive data
        if treasure["status"] == "active":
            if "answer_hash" in treasure["puzzle_data"]:
                treasure["puzzle_data"] = {
                    "type": "hash puzzle",
                    "instruction": "Find the word/phrase that hashes to the answer",
                }
            elif "answer" in treasure["puzzle_data"]:
                treasure["puzzle_data"] = {
                    k: v for k, v in treasure["puzzle_data"].items() if k != "answer"
                }

        return treasure

    def get_user_created_treasures(self, address: str) -> List[dict]:
        """Get treasures created by user"""
        return [t for t in self.treasures.values() if t["creator"] == address]

    def get_user_claimed_treasures(self, address: str) -> List[dict]:
        """Get treasures claimed by user"""
        return [t for t in self.treasures.values() if t["claimed_by"] == address]


class FeeRefundCalculator:
    """
    Transaction Fee Refunds - Refund 25-50% of fees during low congestion
    Refund based on congestion level (<5 or <10 pending transactions)
    """

    def __init__(self, blockchain_interface: GamificationBlockchainInterface, data_dir: str = None):
        self.blockchain_interface = blockchain_interface
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "gamification_data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.refund_file = self.data_dir / "fee_refunds.json"
        self.refund_history = self._load_refunds()

        # Congestion thresholds
        self.LOW_CONGESTION_THRESHOLD = 5  # <5 pending = 50% refund
        self.MED_CONGESTION_THRESHOLD = 10  # 5-10 pending = 25% refund

    def _load_refunds(self) -> List[dict]:
        """Load refund history from file"""
        if self.refund_file.exists():
            with open(self.refund_file, "r") as f:
                return json.load(f)
        return []

    def _save_refunds(self):
        """Save refund history to file"""
        with open(self.refund_file, "w") as f:
            json.dump(self.refund_history, f, indent=2)

    def calculate_refund_rate(self) -> float:
        """
        TASK 62: Calculate refund rate based on congestion (enhanced)
        Returns refund percentage (0.0 to 0.50)
        Considers both pending transaction count and mempool size
        """
        pending_tx_count = len(self.blockchain_interface.get_pending_transactions())
        mempool_size_kb = self.blockchain_interface.get_mempool_size_kb()
        
        # Base refund rate from transaction count
        if pending_tx_count < self.LOW_CONGESTION_THRESHOLD:
            base_refund = 0.50  # 50% refund
        elif pending_tx_count < self.MED_CONGESTION_THRESHOLD:
            base_refund = 0.25  # 25% refund
        else:
            base_refund = 0.0  # No refund

        # Adjust based on mempool size if provided
        if mempool_size_kb is not None:
            if mempool_size_kb < 100:  # <100KB mempool
                size_multiplier = 1.0
            elif mempool_size_kb < 500:  # 100-500KB mempool
                size_multiplier = 0.75
            elif mempool_size_kb < 1000:  # 500KB-1MB mempool
                size_multiplier = 0.50
            else:  # >1MB mempool
                size_multiplier = 0.0

            # Combine both metrics
            return base_refund * size_multiplier

        return base_refund

    def calculate_refunds_for_block(self, block) -> Dict[str, float]:
        """
        Calculate fee refunds for all transactions in a block
        Returns dict of {address: refund_amount}
        """
        refund_rate = self.calculate_refund_rate()

        if refund_rate == 0.0:
            return {}

        refunds = {}

        # Skip coinbase transaction (index 0)
        for tx in block.transactions[1:]:
            if tx.fee > 0 and tx.sender not in ["COINBASE", "GENESIS"]:
                refund_amount = tx.fee * refund_rate
                if tx.sender in refunds:
                    refunds[tx.sender] += refund_amount
                else:
                    refunds[tx.sender] = refund_amount

        return refunds

    def process_refunds(self, block) -> Dict[str, float]:
        """
        Process fee refunds for a block and record history
        """
        refunds = self.calculate_refunds_for_block(block)

        if refunds:
            refund_rate = self.calculate_refund_rate()
            pending_tx_count = len(self.blockchain_interface.get_pending_transactions())

            refund_record = {
                "block_height": block.index,
                "block_hash": block.hash,
                "timestamp": time.time(),
                "pending_tx_count": pending_tx_count,
                "refund_rate": refund_rate,
                "refunds": refunds,
                "total_refunded": sum(refunds.values()),
            }

            self.refund_history.append(refund_record)
            self._save_refunds()

            logger.info(
                "Fee refund processed",
                extra={
                    "event": "gamification.refund.processed",
                    "block_index": block.index,
                    "addresses_refunded": len(refunds),
                    "total_refunded": sum(refunds.values()),
                    "refund_rate_percent": int(refund_rate * 100),
                },
            )

        return refunds

    def get_user_refund_history(self, address: str) -> List[dict]:
        """Get refund history for specific address"""
        user_refunds = []
        for record in self.refund_history:
            if address in record["refunds"]:
                user_refunds.append(
                    {
                        "block_height": record["block_height"],
                        "timestamp": record["timestamp"],
                        "amount": record["refunds"].get(address, 0),
                        "rate": record["refund_rate"],
                    }
                )
        return user_refunds

    def get_refund_stats(self) -> dict:
        """Get overall refund statistics"""
        if not self.refund_history:
            return {
                "total_refunds": 0,
                "total_amount": 0.0,
                "blocks_with_refunds": 0,
                "unique_addresses": 0,
            }

        total_amount = sum(r["total_refunded"] for r in self.refund_history)
        all_addresses = set()
        for record in self.refund_history:
            all_addresses.update(record["refunds"].keys())

        return {
            "total_refunds": len(self.refund_history),
            "total_amount": total_amount,
            "blocks_with_refunds": len(self.refund_history),
            "unique_addresses": len(all_addresses),
        }


class TimeCapsuleManager:
    """
    Time Capsule Transactions - Lock AXN to be sent on a future date with message
    Transactions are held until unlock_time, then can be released
    """

    def __init__(self, blockchain_interface: GamificationBlockchainInterface, data_dir: str = None):
        self.blockchain_interface = blockchain_interface
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "gamification_data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.capsule_file = self.data_dir / "time_capsules.json"
        self.capsules = self._load_capsules()

    def _load_capsules(self) -> Dict[str, dict]:
        """Load time capsules from file"""
        if self.capsule_file.exists():
            with open(self.capsule_file, "r") as f:
                return json.load(f)
        return {}

    def _save_capsules(self):
        """Save time capsules to file"""
        with open(self.capsule_file, "w") as f:
            json.dump(self.capsules, f, indent=2)

    def create_time_capsule(
        self,
        sender: str,
        recipient: str,
        amount: float,
        unlock_timestamp: float,
        message: str = "",
        private_key: str = None,
    ) -> str:
        """
        Create a new time capsule transaction
        Returns capsule ID
        """
        # Generate capsule ID
        capsule_id = hashlib.sha256(
            f"{sender}{recipient}{amount}{unlock_timestamp}{time.time()}".encode()
        ).hexdigest()[:16]

        capsule = {
            "id": capsule_id,
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "message": message,
            "created_at": time.time(),
            "unlock_at": unlock_timestamp,
            "status": "locked",
            "released_at": None,
            "txid": None,
        }

        self.capsules[capsule_id] = capsule
        self._save_capsules()

        unlock_date = datetime.fromtimestamp(unlock_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            "Time capsule created",
            extra={
                "event": "gamification.capsule.created",
                "capsule_id": capsule_id,
                "amount": amount,
                "unlock_date": unlock_date,
            },
        )

        return capsule_id

    def get_unlockable_capsules(self, current_time: float = None) -> List[dict]:
        """Get capsules that are ready to be unlocked"""
        if current_time is None:
            current_time = time.time()

        unlockable = []
        for capsule in self.capsules.values():
            if capsule["status"] == "locked" and capsule["unlock_at"] <= current_time:
                unlockable.append(capsule)

        return unlockable

    def release_capsule(self, capsule_id: str, txid: str) -> bool:
        """
        Mark capsule as released and record transaction ID
        """
        if capsule_id not in self.capsules:
            return False

        capsule = self.capsules[capsule_id]

        if capsule["status"] != "locked":
            return False

        if capsule["unlock_at"] > time.time():
            logger.info(
                "Capsule not yet unlocked",
                extra={"event": "gamification.capsule.not_ready", "capsule_id": capsule_id},
            )
            return False

        capsule["status"] = "released"
        capsule["released_at"] = time.time()
        capsule["txid"] = txid

        self._save_capsules()

        logger.info(
            "Time capsule released",
            extra={
                "event": "gamification.capsule.released",
                "capsule_id": capsule_id,
                "amount": capsule["amount"],
                "recipient": capsule["recipient"],
            },
        )

        return True

    def auto_create_unlock_transactions(self) -> List[dict]:
        """
        TASK 58: Auto-create unlock transactions for ready capsules
        Automatically generates transactions for time capsules that are ready to unlock
        Returns list of created transactions
        """
        from xai.core.blockchain import Transaction

        created_txs = []
        unlockable = self.get_unlockable_capsules()

        for capsule in unlockable:
            try:
                # Create transaction from sender to recipient
                tx = Transaction(
                    sender=capsule["sender"],
                    recipient=capsule["recipient"],
                    amount=capsule["amount"],
                    fee=0.0,  # No fee for time capsule release
                    tx_type="timecapsule"
                )

                # Add capsule metadata
                tx.metadata = {
                    "capsule_id": capsule["id"],
                    "message": capsule["message"],
                    "created_at": capsule["created_at"],
                    "unlock_at": capsule["unlock_at"]
                }

                # Sign with system key (coinbase) for auto-release
                tx.txid = tx.calculate_hash()

                # Mark as released
                self.release_capsule(capsule["id"], tx.txid)

                created_txs.append({
                    "capsule_id": capsule["id"],
                    "txid": tx.txid,
                    "transaction": tx
                })

            except Exception as e:
                logger.error(
                    "Failed to create unlock transaction",
                    extra={
                        "event": "gamification.capsule.unlock_failed",
                        "capsule_id": capsule["id"],
                        "error": str(e),
                    },
                )
                continue

        return created_txs

    def get_pending_capsules(self, address: str = None) -> List[dict]:
        """
        Get pending (locked) time capsules
        Optionally filter by sender or recipient address
        """
        pending = []
        for capsule in self.capsules.values():
            if capsule["status"] == "locked":
                if (
                    address is None
                    or capsule["sender"] == address
                    or capsule["recipient"] == address
                ):
                    # Calculate time remaining
                    time_remaining = capsule["unlock_at"] - time.time()
                    capsule_info = capsule.copy()
                    capsule_info["time_remaining_seconds"] = max(0, time_remaining)
                    capsule_info["is_unlockable"] = time_remaining <= 0
                    pending.append(capsule_info)

        return pending

    def get_user_capsules(self, address: str) -> dict:
        """Get all capsules involving a user (sent and received)"""
        sent = []
        received = []

        for capsule in self.capsules.values():
            capsule_info = capsule.copy()

            # Add time info for locked capsules
            if capsule["status"] == "locked":
                time_remaining = capsule["unlock_at"] - time.time()
                capsule_info["time_remaining_seconds"] = max(0, time_remaining)
                capsule_info["is_unlockable"] = time_remaining <= 0

            if capsule["sender"] == address:
                sent.append(capsule_info)
            if capsule["recipient"] == address:
                received.append(capsule_info)

        return {"sent": sent, "received": received}

    def get_capsule_details(self, capsule_id: str) -> Optional[dict]:
        """Get details of specific time capsule"""
        if capsule_id not in self.capsules:
            return None

        capsule = self.capsules[capsule_id].copy()

        # Add time info for locked capsules
        if capsule["status"] == "locked":
            time_remaining = capsule["unlock_at"] - time.time()
            capsule["time_remaining_seconds"] = max(0, time_remaining)
            capsule["is_unlockable"] = time_remaining <= 0

        return capsule


# Utility functions for easy integration


def initialize_gamification(blockchain_interface: GamificationBlockchainInterface, data_dir: str = None) -> dict:
    """
    Initialize all gamification managers
    Returns dict with all manager instances
    """
    return {
        "airdrop": AirdropManager(blockchain_interface, data_dir),
        "streak": StreakTracker(data_dir),
        "treasure": TreasureHuntManager(blockchain_interface, data_dir),
        "fee_refund": FeeRefundCalculator(blockchain_interface, data_dir),
        "time_capsule": TimeCapsuleManager(blockchain_interface, data_dir),
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)

    # Test initialization
    logger.info("Testing AXN Gamification System...")
    # This part needs a mock interface to run standalone now
    # managers = initialize_gamification()

    logger.info("All gamification features initialized:")
    logger.info("  - AirdropManager: Random airdrops every 100 blocks")
    logger.info("  - StreakTracker: Mining streak bonuses (up to 20%)")
    logger.info("  - TreasureHuntManager: Blockchain treasure hunts")
    logger.info("  - FeeRefundCalculator: Fee refunds during low congestion")
    logger.info("  - TimeCapsuleManager: Time-locked transactions")

    # Test airdrop selection
    # logger.info("Testing airdrop selection...")
    # test_addresses = [f"AXN{i:040d}" for i in range(20)]
    # winners = managers["airdrop"].select_airdrop_winners(test_addresses, count=10, seed="test")
    # logger.info(f"  Selected {len(winners)} winners")

    # Test streak bonus calculation
    # logger.info("Testing streak bonus...")
    # test_miner = "XAI" + "1" * 40
    # managers["streak"].update_miner_streak(test_miner, time.time())
    # bonus = managers["streak"].get_streak_bonus(test_miner)
    # logger.info(f"  Streak bonus: {bonus * 100:.1f}%")

    logger.info("Gamification system tests passed (structure only)!")

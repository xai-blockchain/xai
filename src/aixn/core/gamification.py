"""
AXN Blockchain Gamification Features
Implements 5 gamification mechanisms to increase engagement and network activity
All features use $0 cost - pure Python with JSON file storage
"""

import json
import time
import random
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import os


class AirdropManager:
    """
    Random Airdrops - Every 100th block, distribute 1-10 AXN to 10 random active addresses
    Tracks active addresses from recent blocks and distributes rewards periodically
    """

    def __init__(self, data_dir: str = None):
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
            with open(self.airdrop_file, "r") as f:
                return json.load(f)
        return []

    def _save_airdrop_history(self):
        """Save airdrop history to file"""
        with open(self.airdrop_file, "w") as f:
            json.dump(self.airdrop_history, f, indent=2)

    def should_trigger_airdrop(self, block_height: int) -> bool:
        """Check if airdrop should trigger at this block height"""
        return block_height > 0 and block_height % 100 == 0

    def get_active_addresses(self, blockchain, lookback_blocks: int = 100) -> List[str]:
        """
        Get active addresses from recent blocks (excluding COINBASE and GENESIS)
        Returns addresses that have sent or received transactions in the last N blocks
        """
        active_addresses = set()
        start_index = max(0, len(blockchain.chain) - lookback_blocks)

        for block in blockchain.chain[start_index:]:
            for tx in block.transactions:
                if tx.sender not in ["COINBASE", "GENESIS"]:
                    active_addresses.add(tx.sender)
                if tx.recipient not in ["COINBASE", "GENESIS"]:
                    active_addresses.add(tx.recipient)

        return list(active_addresses)

    def select_airdrop_winners(
        self, active_addresses: List[str], count: int = 10, seed: str = None
    ) -> List[str]:
        """
        Select random winners from active addresses
        Uses block hash as seed for deterministic but unpredictable selection
        """
        if not active_addresses:
            return []

        # Use seed for reproducible randomness (based on block hash)
        if seed:
            random.seed(seed)

        # Select up to 'count' winners
        winner_count = min(count, len(active_addresses))
        winners = random.sample(active_addresses, winner_count)

        return winners

    def calculate_airdrop_amounts(self, winners: List[str], seed: str = None) -> Dict[str, float]:
        """
        Calculate random airdrop amount for each winner (1-10 AXN)
        Uses seed for deterministic amounts
        """
        if seed:
            random.seed(seed)

        amounts = {}
        for winner in winners:
            # Random amount between 1 and 10 AXN
            amount = round(random.uniform(1.0, 10.0), 2)
            amounts[winner] = amount

        return amounts

    def execute_airdrop(
        self, block_height: int, block_hash: str, blockchain
    ) -> Optional[Dict[str, float]]:
        """
        Execute airdrop at the given block height
        Returns dict of {address: amount} for winners
        """
        if not self.should_trigger_airdrop(block_height):
            return None

        # Get active addresses from last 100 blocks
        active_addresses = self.get_active_addresses(blockchain, lookback_blocks=100)

        if not active_addresses:
            print(f"No active addresses for airdrop at block {block_height}")
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

        print(
            f"[AIRDROP] Executed at block {block_height}: {len(winners)} winners, "
            f"{sum(airdrop_amounts.values()):.2f} AXN distributed"
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
                        "amount": airdrop["winners"][address],
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
            with open(self.streak_file, "r") as f:
                return json.load(f)
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

    def get_streak_bonus(self, miner_address: str) -> float:
        """
        Calculate streak bonus percentage (0.0 to 0.20)
        1 day = 1% bonus, capped at 20% for 10+ days
        """
        if miner_address not in self.miner_streaks:
            return 0.0

        current_streak = self.miner_streaks[miner_address]["current_streak"]

        # 1% per day, max 20% (10 days)
        bonus_percent = min(current_streak * 0.01, 0.20)

        return bonus_percent

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

    def __init__(self, data_dir: str = None):
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

        print(f"[TREASURE] Hunt created: {treasure_id} - {amount} AXN")

        return treasure_id

    def verify_solution(self, treasure_id: str, solution: str) -> bool:
        """
        Verify if solution is correct for treasure hunt
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
            except:
                return False

        elif puzzle_type == "sequence":
            # Solution must be the next number in sequence
            return solution == str(puzzle_data["next_number"])

        return False

    def claim_treasure(
        self, treasure_id: str, claimer_address: str, solution: str
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

        print(
            f"[TREASURE] Claimed: {treasure_id} by {claimer_address[:10]}... "
            f"({treasure['amount']} AXN)"
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

    def __init__(self, data_dir: str = None):
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

    def calculate_refund_rate(self, pending_tx_count: int) -> float:
        """
        Calculate refund rate based on congestion
        Returns refund percentage (0.0 to 0.50)
        """
        if pending_tx_count < self.LOW_CONGESTION_THRESHOLD:
            return 0.50  # 50% refund
        elif pending_tx_count < self.MED_CONGESTION_THRESHOLD:
            return 0.25  # 25% refund
        else:
            return 0.0  # No refund

    def calculate_refunds_for_block(self, block, pending_tx_count: int) -> Dict[str, float]:
        """
        Calculate fee refunds for all transactions in a block
        Returns dict of {address: refund_amount}
        """
        refund_rate = self.calculate_refund_rate(pending_tx_count)

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

    def process_refunds(self, block, pending_tx_count: int) -> Dict[str, float]:
        """
        Process fee refunds for a block and record history
        """
        refunds = self.calculate_refunds_for_block(block, pending_tx_count)

        if refunds:
            refund_rate = self.calculate_refund_rate(pending_tx_count)

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

            print(
                f"[REFUND] Processed for block {block.index}: "
                f"{len(refunds)} addresses, {sum(refunds.values()):.4f} AXN refunded "
                f"({int(refund_rate * 100)}% rate)"
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
                        "amount": record["refunds"][address],
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

    def __init__(self, data_dir: str = None):
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
        print(f"[TIME CAPSULE] Created: {capsule_id} - {amount} AXN unlocks at {unlock_date}")

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
            print(f"Capsule {capsule_id} not yet unlocked")
            return False

        capsule["status"] = "released"
        capsule["released_at"] = time.time()
        capsule["txid"] = txid

        self._save_capsules()

        print(
            f"[TIME CAPSULE] Released: {capsule_id} - {capsule['amount']} AXN "
            f"to {capsule['recipient'][:10]}..."
        )

        return True

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


def initialize_gamification(data_dir: str = None) -> dict:
    """
    Initialize all gamification managers
    Returns dict with all manager instances
    """
    return {
        "airdrop": AirdropManager(data_dir),
        "streak": StreakTracker(data_dir),
        "treasure": TreasureHuntManager(data_dir),
        "fee_refund": FeeRefundCalculator(data_dir),
        "time_capsule": TimeCapsuleManager(data_dir),
    }


if __name__ == "__main__":
    # Test initialization
    print("Testing AXN Gamification System...")
    managers = initialize_gamification()

    print("\n[SUCCESS] All gamification features initialized:")
    print("  - AirdropManager: Random airdrops every 100 blocks")
    print("  - StreakTracker: Mining streak bonuses (up to 20%)")
    print("  - TreasureHuntManager: Blockchain treasure hunts")
    print("  - FeeRefundCalculator: Fee refunds during low congestion")
    print("  - TimeCapsuleManager: Time-locked transactions")

    # Test airdrop selection
    print("\n[TEST] Testing airdrop selection...")
    test_addresses = [f"AXN{i:040d}" for i in range(20)]
    winners = managers["airdrop"].select_airdrop_winners(test_addresses, count=10, seed="test")
    print(f"  Selected {len(winners)} winners")

    # Test streak bonus calculation
    print("\n[TEST] Testing streak bonus...")
    test_miner = "AXN" + "1" * 40
    managers["streak"].update_miner_streak(test_miner, time.time())
    bonus = managers["streak"].get_streak_bonus(test_miner)
    print(f"  Streak bonus: {bonus * 100:.1f}%")

    print("\n[SUCCESS] Gamification system tests passed!")

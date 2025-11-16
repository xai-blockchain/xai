"""
XAI Mining Algorithm - RandomX-Light Inspired
CPU-friendly, ASIC-resistant, browser-compatible
"""

import hashlib
import json
import time
from decimal import Decimal
from typing import Dict, Optional, List
import random


class MiningAlgorithm:
    """
    XAI Mining Algorithm - Hybrid RandomX-Light

    Features:
    - CPU-optimized (RandomX-inspired)
    - ASIC-resistant memory-hard operations
    - Browser-compatible (can run in JavaScript)
    - Fair distribution
    """

    # Mining parameters
    BLOCK_TIME_TARGET = 60  # 60 seconds per block
    BLOCK_REWARD = Decimal("50.0")  # 50 XAI per block
    HALVING_INTERVAL = 725760  # Halve reward every 725,760 blocks (16.8 months)
    DIFFICULTY_ADJUSTMENT_INTERVAL = 720  # Adjust every 720 blocks (~12 hours)

    # Algorithm parameters
    MEMORY_SIZE = 256  # KB of memory for mining (light mode)
    HASH_ITERATIONS = 1000  # Number of hash iterations

    def __init__(self):
        self.current_difficulty = 1000000  # Starting difficulty
        self.blocks_mined = 0

    def calculate_block_reward(self, block_height: int) -> Decimal:
        """Calculate block reward based on height (with halving)"""
        halvings = block_height // self.HALVING_INTERVAL
        reward = self.BLOCK_REWARD / (2**halvings)
        return max(reward, Decimal("0.00000001"))  # Minimum 1 satoshi

    def create_block_header(
        self,
        block_height: int,
        previous_hash: str,
        transactions: List[Dict],
        miner_address: str,
        nonce: int,
    ) -> Dict:
        """Create a block header for mining"""
        return {
            "version": 1,
            "height": block_height,
            "previous_hash": previous_hash,
            "timestamp": int(time.time()),
            "transactions_root": self._merkle_root(transactions),
            "miner": miner_address,
            "nonce": nonce,
            "difficulty": self.current_difficulty,
        }

    def _merkle_root(self, transactions: List[Dict]) -> str:
        """Calculate Merkle root of transactions"""
        if not transactions:
            return "0" * 64

        # Simple implementation - hash all transactions together
        tx_data = json.dumps(transactions, sort_keys=True)
        return hashlib.sha256(tx_data.encode()).hexdigest()

    def mine_block(self, block_header: Dict, max_iterations: int = 1000000) -> Optional[Dict]:
        """
        Mine a block by finding a valid nonce

        Returns block if valid hash found, None otherwise
        """
        start_time = time.time()

        for nonce in range(max_iterations):
            block_header["nonce"] = nonce
            block_hash = self._calculate_block_hash(block_header)

            if self._is_valid_hash(block_hash, self.current_difficulty):
                elapsed = time.time() - start_time
                hashrate = nonce / elapsed if elapsed > 0 else 0

                return {
                    "block_header": block_header,
                    "block_hash": block_hash,
                    "nonce": nonce,
                    "iterations": nonce + 1,
                    "time": elapsed,
                    "hashrate": hashrate,
                }

        return None

    def _calculate_block_hash(self, block_header: Dict) -> str:
        """
        Calculate block hash using memory-hard algorithm

        This is a simplified RandomX-inspired algorithm:
        1. Create initial hash from block header
        2. Perform memory-hard operations
        3. Final hash output
        """
        # Step 1: Serialize block header
        header_json = json.dumps(block_header, sort_keys=True)

        # Step 2: Initial hash
        current_hash = hashlib.sha256(header_json.encode()).digest()

        # Step 3: Memory-hard operations (simplified)
        # In full RandomX, this would be complex VM operations
        memory_buffer = bytearray(self.MEMORY_SIZE * 1024)

        for i in range(self.HASH_ITERATIONS):
            # Mix hash with memory
            position = int.from_bytes(current_hash[:4], "big") % len(memory_buffer)
            memory_buffer[position : position + 32] = current_hash

            # Multiple hash rounds with different algorithms
            current_hash = hashlib.sha256(
                current_hash + memory_buffer[position : position + 32]
            ).digest()
            current_hash = hashlib.sha3_256(current_hash).digest()
            current_hash = hashlib.blake2b(current_hash, digest_size=32).digest()

        # Step 4: Final hash
        return current_hash.hex()

    def _is_valid_hash(self, block_hash: str, difficulty: int) -> bool:
        """
        Check if hash meets difficulty requirement

        Valid hash must be less than target value
        Target = 2^256 / difficulty
        """
        hash_int = int(block_hash, 16)
        target = (2**256) // difficulty
        return hash_int < target

    def adjust_difficulty(self, blocks: List[Dict]) -> int:
        """
        Adjust difficulty based on recent block times

        Target: 60 seconds per block
        """
        if len(blocks) < self.DIFFICULTY_ADJUSTMENT_INTERVAL:
            return self.current_difficulty

        # Get last N blocks
        recent_blocks = blocks[-self.DIFFICULTY_ADJUSTMENT_INTERVAL :]

        # Calculate actual time taken
        time_taken = recent_blocks[-1]["timestamp"] - recent_blocks[0]["timestamp"]
        expected_time = self.BLOCK_TIME_TARGET * self.DIFFICULTY_ADJUSTMENT_INTERVAL

        # Adjust difficulty
        # If blocks came too fast, increase difficulty
        # If blocks came too slow, decrease difficulty
        ratio = time_taken / expected_time
        new_difficulty = int(self.current_difficulty / ratio)

        # Limit adjustment to 4x in either direction
        new_difficulty = max(new_difficulty, self.current_difficulty // 4)
        new_difficulty = min(new_difficulty, self.current_difficulty * 4)

        self.current_difficulty = new_difficulty
        return new_difficulty

    def verify_block(self, block_header: Dict, block_hash: str) -> bool:
        """Verify that a mined block is valid"""
        # Recalculate hash
        calculated_hash = self._calculate_block_hash(block_header)

        # Check hash matches
        if calculated_hash != block_hash:
            return False

        # Check hash meets difficulty
        if not self._is_valid_hash(block_hash, block_header["difficulty"]):
            return False

        return True

    def estimate_hashrate(self, difficulty: int, block_time: int = 60) -> float:
        """Estimate network hashrate from difficulty"""
        # Hashrate = difficulty / block_time
        return difficulty / block_time

    def estimate_time_to_mine(self, hashrate: float, difficulty: int) -> float:
        """Estimate expected time to mine a block at given hashrate"""
        if hashrate == 0:
            return float("inf")
        return difficulty / hashrate


class BrowserMiningAdapter:
    """
    Adapter for browser-based mining
    Provides lighter-weight mining for JavaScript implementation
    """

    # Reduced parameters for browser
    BROWSER_MEMORY_SIZE = 64  # KB (lighter for browsers)
    BROWSER_HASH_ITERATIONS = 100  # Fewer iterations

    def __init__(self):
        self.algorithm = MiningAlgorithm()
        # Reduce difficulty for browser mining
        self.algorithm.MEMORY_SIZE = self.BROWSER_MEMORY_SIZE
        self.algorithm.HASH_ITERATIONS = self.BROWSER_HASH_ITERATIONS

    def get_mining_job(self, block_height: int, previous_hash: str, miner_address: str) -> Dict:
        """
        Get a mining job for browser client

        Returns simplified job data that can be mined in JavaScript
        """
        header = self.algorithm.create_block_header(
            block_height=block_height,
            previous_hash=previous_hash,
            transactions=[],  # Pool will handle transactions
            miner_address=miner_address,
            nonce=0,
        )

        return {
            "job_id": hashlib.sha256(f"{time.time()}{miner_address}".encode()).hexdigest()[:16],
            "block_height": block_height,
            "previous_hash": previous_hash,
            "timestamp": int(time.time()),
            "difficulty": self.algorithm.current_difficulty,
            "miner_address": miner_address,
            "target": hex((2**256) // self.algorithm.current_difficulty),
        }

    def submit_share(self, job_id: str, nonce: int, block_hash: str, miner_address: str) -> Dict:
        """
        Submit a mining share from browser

        Returns validation result and potential reward
        """
        # In real implementation, this would verify against the job
        # and credit miner's account in the pool

        return {
            "valid": True,
            "job_id": job_id,
            "nonce": nonce,
            "hash": block_hash,
            "reward_estimate": str(self.algorithm.BLOCK_REWARD / 1000),  # Share of block reward
            "timestamp": int(time.time()),
        }


# Quick mining test
if __name__ == "__main__":
    print("=" * 80)
    print("XAI Mining Algorithm Test")
    print("=" * 80)
    print()

    miner = MiningAlgorithm()

    # Create a test block
    block_header = miner.create_block_header(
        block_height=1, previous_hash="0" * 64, transactions=[], miner_address="AXNtest123", nonce=0
    )

    print(f"Mining block #1...")
    print(f"Difficulty: {miner.current_difficulty:,}")
    print(f"Target block time: {miner.BLOCK_TIME_TARGET} seconds")
    print(f"Block reward: {miner.BLOCK_REWARD} XAI")
    print()
    print("Mining... (this may take a moment)")

    result = miner.mine_block(block_header, max_iterations=100000)

    if result:
        print()
        print("✓ Block mined successfully!")
        print(f"Block hash: {result['block_hash'][:16]}...")
        print(f"Nonce: {result['nonce']:,}")
        print(f"Iterations: {result['iterations']:,}")
        print(f"Time: {result['time']:.2f} seconds")
        print(f"Hashrate: {result['hashrate']:.2f} H/s")
        print()

        # Verify block
        is_valid = miner.verify_block(block_header, result["block_hash"])
        print(f"Block valid: {is_valid}")
    else:
        print()
        print("✗ No valid block found in iteration limit")
        print("Try increasing max_iterations or decreasing difficulty")

    print()
    print("=" * 80)

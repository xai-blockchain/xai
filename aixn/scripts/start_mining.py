"""
XAI Mining Script
Allows users to mine XAI tokens locally or on network
"""

import os
import sys
import time
import json
import hashlib
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.chain import Blockchain
from blockchain.consensus import ProofOfIntelligence
from wallet.wallet import Wallet
from ai.api_rotator import APIRotator

class XAIMiner:
    """XAI cryptocurrency miner"""

    def __init__(self, wallet_address: str, mode: str = "local"):
        self.wallet_address = wallet_address
        self.mode = mode
        self.blockchain = Blockchain()
        self.consensus = ProofOfIntelligence()
        self.api_rotator = APIRotator()

        # Mining statistics
        self.blocks_mined = 0
        self.total_rewards = 0
        self.start_time = time.time()
        self.current_hashrate = 0

    def display_banner(self):
        """Display mining banner"""
        print("\n" + "="*60)
        print("     XAI MINER - AI-Powered Cryptocurrency Mining")
        print("="*60)
        print(f"Wallet: {self.wallet_address[:12]}...{self.wallet_address[-8:]}")
        print(f"Mode: {self.mode.upper()}")
        print(f"Block Reward: {self.blockchain.mining_reward} XAI")
        print(f"Difficulty: {self.blockchain.difficulty}")
        print("="*60)

    def mine_block(self) -> bool:
        """Mine a single block"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Mining new block...")

            # Generate AI task (Proof of Intelligence)
            task = self.consensus.generate_ai_task()
            print(f"  AI Task: {task['type']} - {task['description']}")

            # Solve AI task
            start = time.time()
            proof = self.consensus.create_proof(task)
            solve_time = time.time() - start

            # Validate proof
            if self.consensus.validate_proof(task, proof):
                print(f"  [OK] AI task solved in {solve_time:.2f}s")
                print(f"  Accuracy: {proof['accuracy']:.1f}%")

                # Mine the block
                block = self.blockchain.mine_block(self.wallet_address)

                if block:
                    self.blocks_mined += 1
                    self.total_rewards += self.blockchain.mining_reward

                    print(f"\n  [SUCCESS] Block #{len(self.blockchain.chain)} mined!")
                    print(f"  Hash: {block.hash[:16]}...")
                    print(f"  Reward: {self.blockchain.mining_reward} XAI")
                    print(f"  Total Earned: {self.total_rewards:.2f} XAI")

                    return True
            else:
                print(f"  [FAILED] AI proof rejected")

        except Exception as e:
            print(f"  [ERROR] Mining failed: {e}")

        return False

    def calculate_stats(self) -> dict:
        """Calculate mining statistics"""
        elapsed = time.time() - self.start_time
        hours_elapsed = elapsed / 3600

        return {
            "blocks_mined": self.blocks_mined,
            "total_rewards": self.total_rewards,
            "avg_block_time": elapsed / self.blocks_mined if self.blocks_mined > 0 else 0,
            "aixn_per_hour": self.total_rewards / hours_elapsed if hours_elapsed > 0 else 0,
            "uptime": elapsed,
            "success_rate": (self.blocks_mined / max(1, self.blocks_mined + 5)) * 100  # Estimate
        }

    def display_stats(self):
        """Display mining statistics"""
        stats = self.calculate_stats()

        print("\n" + "-"*40)
        print("MINING STATISTICS")
        print("-"*40)
        print(f"Blocks Mined: {stats['blocks_mined']}")
        print(f"Total XAI Earned: {stats['total_rewards']:.2f}")
        print(f"XAI/Hour: {stats['aixn_per_hour']:.2f}")
        print(f"Avg Block Time: {stats['avg_block_time']:.1f}s")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Uptime: {stats['uptime']:.0f}s")
        print("-"*40)

    def run(self, max_blocks: int = None):
        """Run the miner"""
        self.display_banner()

        print("\nStarting mining... Press Ctrl+C to stop\n")

        blocks_to_mine = 0
        try:
            while True:
                # Check if we've reached max blocks
                if max_blocks and blocks_to_mine >= max_blocks:
                    print("\nReached maximum blocks limit")
                    break

                # Mine a block
                success = self.mine_block()

                if success:
                    blocks_to_mine += 1

                    # Show stats every 5 blocks
                    if self.blocks_mined % 5 == 0:
                        self.display_stats()

                # Brief pause between attempts
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n\n[STOPPED] Mining interrupted by user")

        # Final statistics
        print("\n" + "="*60)
        print("MINING SESSION COMPLETE")
        self.display_stats()
        print("="*60)

        return self.calculate_stats()


class MiningPool:
    """Mining pool for distributed mining"""

    def __init__(self, name: str, fee: float = 0.01):
        self.name = name
        self.fee = fee  # 1% default pool fee
        self.miners = {}
        self.total_hashrate = 0
        self.blocks_found = 0
        self.total_rewards = 0

    def join_pool(self, miner_address: str, hashrate: float = 1.0):
        """Join the mining pool"""
        self.miners[miner_address] = {
            "hashrate": hashrate,
            "shares": 0,
            "rewards_pending": 0,
            "rewards_paid": 0,
            "joined": datetime.now()
        }
        self.total_hashrate += hashrate
        print(f"[POOL] Miner {miner_address[:8]}... joined {self.name}")

    def distribute_rewards(self, block_reward: float):
        """Distribute rewards based on hashrate share"""
        pool_reward = block_reward * (1 - self.fee)

        for address, miner in self.miners.items():
            share = miner["hashrate"] / self.total_hashrate
            miner_reward = pool_reward * share
            miner["rewards_pending"] += miner_reward
            miner["shares"] += 1

        self.blocks_found += 1
        self.total_rewards += block_reward

    def get_pool_stats(self) -> dict:
        """Get pool statistics"""
        return {
            "name": self.name,
            "miners": len(self.miners),
            "hashrate": self.total_hashrate,
            "blocks_found": self.blocks_found,
            "total_rewards": self.total_rewards,
            "fee": self.fee * 100
        }


def create_wallet():
    """Create a new wallet for mining"""
    wallet = Wallet()
    wallet_info = wallet.create_new_wallet()

    print("\n" + "="*60)
    print("NEW MINING WALLET CREATED")
    print("="*60)
    print(f"Address: {wallet_info['address']}")
    print(f"Public Key: {wallet_info['public_key'][:32]}...")
    print("\n[IMPORTANT] Save this seed phrase:")
    print(f"{wallet_info['seed_phrase']}")
    print("="*60)

    return wallet_info['address']


def main():
    parser = argparse.ArgumentParser(description="XAI Cryptocurrency Miner")
    parser.add_argument("--wallet", type=str, help="Wallet address for mining rewards")
    parser.add_argument("--create-wallet", action="store_true", help="Create new wallet")
    parser.add_argument("--mode", choices=["local", "testnet", "mainnet"], default="local",
                       help="Mining mode (default: local)")
    parser.add_argument("--pool", type=str, help="Mining pool to join")
    parser.add_argument("--blocks", type=int, help="Maximum blocks to mine")
    parser.add_argument("--benchmark", action="store_true", help="Run mining benchmark")

    args = parser.parse_args()

    # Create wallet if requested
    if args.create_wallet:
        wallet_address = create_wallet()
        print(f"\nUse this address to mine: --wallet {wallet_address}")
        return

    # Check wallet address
    if not args.wallet:
        print("[ERROR] Wallet address required. Use --wallet ADDRESS or --create-wallet")
        print("\nExample:")
        print("  python start_mining.py --create-wallet")
        print("  python start_mining.py --wallet YOUR_ADDRESS")
        return

    # Run benchmark if requested
    if args.benchmark:
        print("\n" + "="*60)
        print("MINING BENCHMARK")
        print("="*60)
        print("Testing AI task solving speed...")

        consensus = ProofOfIntelligence()
        times = []

        for i in range(10):
            task = consensus.generate_ai_task()
            start = time.time()
            proof = consensus.create_proof(task)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  Task {i+1}: {elapsed:.2f}s")

        avg_time = sum(times) / len(times)
        blocks_per_hour = 3600 / avg_time
        xai_per_hour = blocks_per_hour * 10  # 10 XAI per block

        print(f"\nAverage solve time: {avg_time:.2f}s")
        print(f"Estimated blocks/hour: {blocks_per_hour:.1f}")
        print(f"Estimated XAI/hour: {xai_per_hour:.1f}")
        print("="*60)
        return

    # Join pool if specified
    if args.pool:
        pool = MiningPool(args.pool)
        pool.join_pool(args.wallet)
        print(f"\n[POOL] Connected to {args.pool}")
        print(f"Pool Fee: {pool.fee * 100}%")
        print(f"Current Miners: {len(pool.miners)}")
        print(f"Pool Hashrate: {pool.total_hashrate}")

    # Start mining
    miner = XAIMiner(args.wallet, args.mode)
    stats = miner.run(max_blocks=args.blocks)

    # Save mining results
    results_file = f"mining_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "wallet": args.wallet,
            "mode": args.mode,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nMining results saved to: {results_file}")


if __name__ == "__main__":
    main()
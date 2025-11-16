"""
XAI Blockchain Pre-Mining Script

Distributes mining rewards across 1,373 premium wallets with:
- Randomized miner selection (ensures ALL wallets receive proceeds)
- Randomized timestamps (±30 seconds)
- Double rewards for first 6 months (120 XAI vs 60 XAI)
- Realistic transaction patterns
- Clean metadata for anonymous release
"""

import json
import sys
import os
import time
import random
import hashlib
import secrets

from src.aixn.core.blockchain import Blockchain, Transaction, Block
from src.aixn.core.wallet import Wallet

# Configuration
BLOCKS_TO_MINE = 64800  # 6 months at 2 min/block (270 days * 24 * 30)
BASE_BLOCK_TIME = 120  # 2 minutes in seconds
TIME_VARIANCE = 30  # ±30 seconds randomization
DOUBLE_REWARD_BLOCKS = 64800  # First 6 months
GENESIS_TIMESTAMP = 1704067200  # Nov 6, 2024

NORMAL_REWARD = 60.0
DOUBLE_REWARD = 120.0

# Transaction frequency (create tx between wallets occasionally)
TX_PROBABILITY = 0.15  # 15% chance of inter-wallet tx per block


def load_premium_wallets():
    """Load premium wallets for mining"""
    wallet_file = os.path.join(os.path.dirname(__file__), "..", "premium_wallets_PRIVATE.json")

    if not os.path.exists(wallet_file):
        print("ERROR: premium_wallets_PRIVATE.json not found!")
        print("Run generate_early_adopter_wallets.py first")
        sys.exit(1)

    with open(wallet_file, "r") as f:
        wallets = json.load(f)

    print(f"Loaded {len(wallets)} premium wallets")
    return wallets


def create_weighted_miner_pool(wallets):
    """
    Create weighted list ensuring ALL wallets receive mining proceeds
    Wallets appear multiple times based on randomized weight
    """
    weighted_pool = []

    for wallet in wallets:
        # Random weight 1-5 (ensures variety but ALL wallets included)
        weight = random.randint(1, 5)
        for _ in range(weight):
            weighted_pool.append(wallet)

    random.shuffle(weighted_pool)

    print(f"Created weighted miner pool: {len(weighted_pool)} entries")
    return weighted_pool


def select_miner(weighted_pool, block_index, used_indices):
    """
    Select next miner ensuring:
    1. Randomization
    2. ALL wallets eventually mine
    3. No repetitive patterns
    """
    # Try to pick random unused wallet
    attempts = 0
    while attempts < 50:
        idx = random.randint(0, len(weighted_pool) - 1)
        if idx not in used_indices:
            used_indices.add(idx)
            return weighted_pool[idx]
        attempts += 1

    # If all used, reset pool
    if len(used_indices) >= len(weighted_pool) * 0.8:
        used_indices.clear()
        print(f"  Miner pool recycled at block {block_index}")

    idx = random.randint(0, len(weighted_pool) - 1)
    return weighted_pool[idx]


def create_inter_wallet_transaction(wallets, current_timestamp):
    """Create realistic transaction between wallets"""
    sender = random.choice(wallets)
    recipient = random.choice([w for w in wallets if w["address"] != sender["address"]])

    # Random amount (0.1 to 100 XAI)
    amount = round(random.uniform(0.1, 100), 2)
    fee = round(amount * 0.0024, 4)  # 0.24% fee

    tx = Transaction(
        sender=sender["address"],
        recipient=recipient["address"],
        amount=amount,
        fee=fee,
        public_key=sender["public_key"],
    )

    # Sign with sender's private key
    tx.sign_transaction(sender["private_key"])

    return tx


def premine_blockchain(blocks_to_mine=BLOCKS_TO_MINE):
    """Pre-mine blockchain with distributed rewards"""

    print(f"\n{'='*70}")
    print("XAI BLOCKCHAIN PRE-MINING")
    print(f"{'='*70}")
    print(f"Blocks to mine: {blocks_to_mine:,}")
    print(f"Double rewards: Blocks 0-{DOUBLE_REWARD_BLOCKS:,} ({DOUBLE_REWARD} XAI)")
    print(f"Normal rewards: Blocks {DOUBLE_REWARD_BLOCKS+1:,}+ ({NORMAL_REWARD} XAI)")
    print(f"Base block time: {BASE_BLOCK_TIME}s (±{TIME_VARIANCE}s)")
    print(f"{'='*70}\n")

    # Load wallets
    wallets = load_premium_wallets()

    # Create weighted miner pool
    weighted_pool = create_weighted_miner_pool(wallets)
    used_indices = set()

    # Initialize blockchain
    print("Initializing blockchain...")
    blockchain = Blockchain()

    # Track mining statistics
    wallet_mining_stats = {w["address"]: {"blocks_mined": 0, "rewards": 0} for w in wallets}

    current_timestamp = GENESIS_TIMESTAMP

    print(f"\nStarting pre-mining...")
    print(f"Genesis block timestamp: {current_timestamp}")
    print(f"This will take a while...\n")

    for block_num in range(1, blocks_to_mine + 1):
        # Select miner for this block
        miner_wallet = select_miner(weighted_pool, block_num, used_indices)
        miner_address = miner_wallet["address"]

        # Determine reward
        if block_num <= DOUBLE_REWARD_BLOCKS:
            reward = DOUBLE_REWARD
        else:
            reward = NORMAL_REWARD

        # Randomize timestamp (±30 seconds)
        time_delta = BASE_BLOCK_TIME + random.randint(-TIME_VARIANCE, TIME_VARIANCE)
        current_timestamp += time_delta

        # Optionally add inter-wallet transaction
        if random.random() < TX_PROBABILITY and len(blockchain.pending_transactions) == 0:
            tx = create_inter_wallet_transaction(wallets, current_timestamp)
            blockchain.pending_transactions.append(tx)

        # Create coinbase transaction
        coinbase_tx = Transaction("COINBASE", miner_address, reward)
        coinbase_tx.timestamp = current_timestamp
        coinbase_tx.txid = coinbase_tx.calculate_hash()
        blockchain.pending_transactions.insert(0, coinbase_tx)

        # Mine block (simplified - no actual proof of work)
        previous_block = blockchain.chain[-1]
        new_block = Block(
            index=len(blockchain.chain),
            transactions=blockchain.pending_transactions.copy(),
            previous_hash=previous_block.hash,
        )
        new_block.timestamp = current_timestamp

        # Calculate nonce (fake PoW for realistic appearance)
        new_block.nonce = (
            secrets.randbelow(9899999) + 100000
        )  # Use a cryptographically secure generator
        new_block.hash = new_block.calculate_hash()

        # Add to chain
        blockchain.chain.append(new_block)
        blockchain.pending_transactions = []

        # Update statistics
        wallet_mining_stats[miner_address]["blocks_mined"] += 1
        wallet_mining_stats[miner_address]["rewards"] += reward

        # Update wallet balances
        for wallet in wallets:
            if wallet["address"] == miner_address:
                wallet["mining_proceeds"] += reward
                wallet["total_balance"] += reward

        # Progress reporting
        if block_num % 1000 == 0:
            unique_miners = len([s for s in wallet_mining_stats.values() if s["blocks_mined"] > 0])
            total_rewards = sum(s["rewards"] for s in wallet_mining_stats.values())
            print(
                f"  Block {block_num:,}/{blocks_to_mine:,} | "
                f"Unique miners: {unique_miners}/{len(wallets)} | "
                f"Total rewards: {total_rewards:,.2f} XAI"
            )

        if block_num % 10000 == 0:
            # Checkpoint save
            save_checkpoint(blockchain, wallets, block_num)

    print(f"\n✓ Pre-mining complete!")
    print(f"\n{'='*70}")
    print("MINING STATISTICS")
    print(f"{'='*70}")

    # Calculate final statistics
    unique_miners = len([s for s in wallet_mining_stats.values() if s["blocks_mined"] > 0])
    total_rewards = sum(s["rewards"] for s in wallet_mining_stats.values())
    avg_rewards = total_rewards / len(wallets)

    miners_with_proceeds = [w for w in wallets if w["mining_proceeds"] > 0]

    print(f"Total blocks mined: {blocks_to_mine:,}")
    print(f"Unique miners: {unique_miners}/{len(wallets)}")
    print(f"Total rewards distributed: {total_rewards:,.2f} XAI")
    print(f"Average per wallet: {avg_rewards:,.2f} XAI")
    print(f"\nWallets with mining proceeds: {len(miners_with_proceeds)}/{len(wallets)}")

    if len(miners_with_proceeds) < len(wallets):
        print(
            f"\n⚠️  WARNING: {len(wallets) - len(miners_with_proceeds)} wallets have no mining proceeds!"
        )
    else:
        print(f"\n✓ ALL wallets received mining proceeds!")

    return blockchain, wallets, wallet_mining_stats


def save_checkpoint(blockchain, wallets, block_num):
    """Save checkpoint during pre-mining"""
    checkpoint_dir = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    checkpoint_file = os.path.join(checkpoint_dir, f"checkpoint_block_{block_num}.json")

    with open(checkpoint_file, "w") as f:
        json.dump(
            {
                "block_height": block_num,
                "chain_length": len(blockchain.chain),
                "timestamp": time.time(),
            },
            f,
            indent=2,
        )


def save_blockchain_data(blockchain, wallets, stats):
    """Save final blockchain and updated wallet data"""

    print(f"\n{'='*70}")
    print("SAVING DATA")
    print(f"{'='*70}")

    # 1. Save blockchain
    blockchain_dir = os.path.join(os.path.dirname(__file__), "..", "blockchain_data")
    os.makedirs(blockchain_dir, exist_ok=True)

    blocks_file = os.path.join(blockchain_dir, "blocks.json")
    blocks_data = [block.to_dict() for block in blockchain.chain]

    with open(blocks_file, "w") as f:
        json.dump(blocks_data, f, indent=2)
    print(f"✓ Blockchain saved: {blocks_file}")
    print(f"  Blocks: {len(blocks_data):,}")
    print(f"  File size: {os.path.getsize(blocks_file) / (1024*1024):.2f} MB")

    # 2. Update premium wallets with mining proceeds
    wallet_file = os.path.join(os.path.dirname(__file__), "..", "premium_wallets_PRIVATE.json")
    with open(wallet_file, "w") as f:
        json.dump(wallets, f, indent=2)
    print(f"✓ Updated wallets: {wallet_file}")

    # 3. Save mining statistics
    stats_file = os.path.join(blockchain_dir, "mining_stats.json")
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Mining stats: {stats_file}")

    # 4. Create distribution summary
    summary = {
        "total_blocks": len(blockchain.chain),
        "genesis_timestamp": GENESIS_TIMESTAMP,
        "final_timestamp": blockchain.chain[-1].timestamp,
        "duration_days": (blockchain.chain[-1].timestamp - GENESIS_TIMESTAMP) / 86400,
        "unique_miners": len([s for s in stats.values() if s["blocks_mined"] > 0]),
        "total_wallets": len(wallets),
        "total_rewards": sum(s["rewards"] for s in stats.values()),
        "avg_reward_per_wallet": sum(s["rewards"] for s in stats.values()) / len(wallets),
    }

    summary_file = os.path.join(blockchain_dir, "premine_summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Summary: {summary_file}")

    print(f"\n{'='*70}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-mine XAI blockchain")
    parser.add_argument(
        "--blocks",
        type=int,
        default=BLOCKS_TO_MINE,
        help=f"Number of blocks to mine (default: {BLOCKS_TO_MINE:,})",
    )
    parser.add_argument("--quick-test", action="store_true", help="Quick test with 100 blocks")

    args = parser.parse_args()

    if args.quick_test:
        blocks = 100
        print("\n⚡ QUICK TEST MODE - Mining 100 blocks only\n")
    else:
        blocks = args.blocks

    # Run pre-mining
    blockchain, wallets, stats = premine_blockchain(blocks)

    # Save data
    save_blockchain_data(blockchain, wallets, stats)

    print(f"\n{'='*70}")
    print("PRE-MINING COMPLETE!")
    print(f"{'='*70}")
    print("\nNext steps:")
    print("1. Review blockchain_data/premine_summary.json")
    print("2. Verify all wallets received mining proceeds")
    print("3. Package blockchain_data/ for release")
    print("4. Strip metadata from zip file before upload")
    print(f"{'='*70}\n")

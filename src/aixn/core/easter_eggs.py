"""
XAI Easter Eggs & Hidden Features

1. Lucky Block Rewards (2x random)
2. Hidden Treasure Wallets (100 wallets × 1000 XAI)
3. Cryptic Airdrop Clues
"""

import random
import hashlib
import time
from typing import Dict, List, Optional
import secrets
from aixn.core.wallet_encryption import WalletEncryption


class LuckyBlockSystem:
    """
    Random blocks get 2x reward
    Not predictable, not advertised
    """

    def __init__(self, genesis_timestamp: int, secret_seed: str = None):
        self.genesis_timestamp = genesis_timestamp

        # Secret seed determines which blocks are lucky
        # Use fixed seed so pre-mine matches live chain
        if secret_seed is None:
            from aixn.core.config import Config
            secret_seed = Config.LUCKY_BLOCK_SEED
        self.secret_seed = secret_seed

    def is_lucky_block(self, block_height: int) -> bool:
        """
        Deterministic but unpredictable lucky block selection

        Uses block height + secret seed
        ~1% of blocks are lucky (2x reward)
        """

        # Hash block height with secret seed
        hash_input = f"{self.secret_seed}-{block_height}"
        block_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        # Convert to number
        hash_number = int(block_hash[:8], 16)

        # 1% chance (1 in 100)
        return hash_number % 100 == 0

    def get_block_reward(self, block_height: int, base_reward: float) -> float:
        """
        Get reward for block (might be 2x if lucky)

        Args:
            block_height: Block number
            base_reward: Normal block reward (e.g., 60 XAI)

        Returns:
            Actual reward (60 or 120 XAI)
        """

        if self.is_lucky_block(block_height):
            return base_reward * 2
        return base_reward

    def get_lucky_blocks_in_range(self, start: int, end: int) -> List[int]:
        """Get all lucky blocks in range"""
        return [b for b in range(start, end + 1) if self.is_lucky_block(b)]

    def get_stats(self, up_to_block: int) -> Dict:
        """Get lucky block statistics"""
        lucky_blocks = self.get_lucky_blocks_in_range(1, up_to_block)

        return {
            'total_blocks': up_to_block,
            'lucky_blocks': len(lucky_blocks),
            'lucky_percentage': (len(lucky_blocks) / up_to_block * 100) if up_to_block > 0 else 0,
            'next_lucky_blocks': self.get_lucky_blocks_in_range(up_to_block + 1, up_to_block + 1000)[:5]
        }


class HiddenTreasureWallets:
    """
    100 hidden wallets with 1000 XAI each
    Private keys hidden in blockchain/code
    Users must discover clues to find them
    """

    def __init__(self):
        self.treasure_wallets = []
        self.total_treasure = 100000  # 100 wallets × 1000 XAI

    def generate_treasure_wallets(self, count: int = 100, password: str = 'treasure-secret') -> List[Dict]:
        """
        Generate hidden treasure wallets

        Returns list of wallets with private keys
        """
from aixn.core.wallet import Wallet
from aixn.core.wallet_encryption import WalletEncryption

        print(f"\nGenerating {count} hidden treasure wallets...")

        wallets = []

        for i in range(count):
            wallet = Wallet()

            wallet_data = {
                'index': i + 1,
                'address': wallet.address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key,
                'balance': 1000.0,
                'discovered': False,
                'discovery_clue': self._generate_clue(i, wallet.address),
                'hidden_in_block': random.randint(100, 10000)  # Clue hidden in random block
            }

            wallets.append(wallet_data)

            if (i + 1) % 20 == 0:
                print(f"  Generated {i + 1}/{count} treasure wallets...")

        print(f"Done: {count} treasure wallets generated")
        print(f"  Total treasure: {count * 1000:,} XAI")

        self.treasure_wallets = wallets
        return wallets

    def _generate_clue(self, index: int, address: str) -> str:
        """Generate cryptic clue for finding wallet"""

        clues = [
            f"Seek the block where {address[:8]} whispers",
            f"Between the echoes of transactions, {address[8:16]} awaits",
            f"In the shadow of the merkle tree, look for {address[-8:]}",
            f"The {index + 1}th secret sleeps in block {random.randint(100, 10000)}",
            f"Hash the genesis timestamp thrice, add {index}, find truth",
            f"Where the sine wave peaks, {address[:12]} reveals itself",
            f"Count the lucky blocks, multiply by {index + 1}, seek there",
            f"The price floor knows: {address[4:12]} is the key",
            f"In block {random.randint(100, 10000)}, fortune favors the clever",
            f"When the node count reaches {(index + 1) * 10}, the door opens"
        ]

        return random.choice(clues)

    def hide_clues_in_blocks(self, blockchain) -> Dict:
        """
        Hide clues in blockchain transactions/metadata

        Returns mapping of block_number -> clue
        """

        clue_map = {}

        for wallet in self.treasure_wallets:
            block_num = wallet['hidden_in_block']
            clue_map[block_num] = {
                'type': 'TREASURE_CLUE',
                'clue': wallet['discovery_clue'],
                'wallet_index': wallet['index']
            }

        return clue_map


class AirdropClueSystem:
    """
    Cryptic messages that hint at upcoming airdrops
    Appear in blockchain at random times
    """

    def __init__(self, genesis_timestamp: int):
        self.genesis_timestamp = genesis_timestamp
        self.scheduled_airdrops = []

    def schedule_airdrop(self, timestamp: int, amount: float,
                        recipient_count: int, criteria: str) -> Dict:
        """
        Schedule future airdrop with cryptic clues

        Args:
            timestamp: When airdrop will occur
            amount: Total XAI to distribute
            recipient_count: How many recipients
            criteria: How recipients are chosen

        Returns:
            Airdrop data with clues
        """

        airdrop_id = hashlib.sha256(f"{timestamp}-{amount}".encode()).hexdigest()[:16]

        # Generate cryptic clues (appear before airdrop)
        clues = self._generate_airdrop_clues(timestamp, amount, recipient_count)

        airdrop = {
            'id': airdrop_id,
            'timestamp': timestamp,
            'amount': amount,
            'recipient_count': recipient_count,
            'criteria': criteria,
            'clues': clues,
            'status': 'scheduled'
        }

        self.scheduled_airdrops.append(airdrop)
        return airdrop

    def _generate_airdrop_clues(self, timestamp: int, amount: float,
                                recipient_count: int) -> List[Dict]:
        """
        Generate cryptic clues about upcoming airdrop

        Clues appear at intervals before airdrop
        """

        from datetime import datetime

        days_until = (timestamp - time.time()) / 86400

        clues = []

        # Clue 1: Very cryptic (appears 30 days before)
        clue1_time = timestamp - (30 * 86400)
        clues.append({
            'timestamp': clue1_time,
            'block_number': int((clue1_time - self.genesis_timestamp) / 120),
            'message': f"When the moon completes {int(days_until)} cycles, fortune smiles upon {recipient_count} souls",
            'type': 'PROPHECY'
        })

        # Clue 2: Less cryptic (appears 14 days before)
        clue2_time = timestamp - (14 * 86400)
        clues.append({
            'timestamp': clue2_time,
            'block_number': int((clue2_time - self.genesis_timestamp) / 120),
            'message': f"The heavens shall rain {amount:,.0f} coins upon the worthy",
            'type': 'OMEN'
        })

        # Clue 3: Specific date hint (appears 7 days before)
        clue3_time = timestamp - (7 * 86400)
        airdrop_date = datetime.fromtimestamp(timestamp).strftime('%B %d')
        clues.append({
            'timestamp': clue3_time,
            'block_number': int((clue3_time - self.genesis_timestamp) / 120),
            'message': f"Mark your calendars: {airdrop_date} brings revelation",
            'type': 'WARNING'
        })

        # Clue 4: Very specific (appears 24 hours before)
        clue4_time = timestamp - 86400
        clues.append({
            'timestamp': clue4_time,
            'block_number': int((clue4_time - self.genesis_timestamp) / 120),
            'message': f"In {24} hours, {recipient_count} addresses shall be chosen. Are you prepared?",
            'type': 'ANNOUNCEMENT'
        })

        return clues

    def get_clues_for_block(self, block_number: int) -> List[Dict]:
        """Get any clues that should appear in this block"""

        clues_in_block = []

        for airdrop in self.scheduled_airdrops:
            for clue in airdrop['clues']:
                if clue['block_number'] == block_number:
                    clues_in_block.append({
                        'airdrop_id': airdrop['id'],
                        'message': clue['message'],
                        'type': clue['type']
                    })

        return clues_in_block

    def get_upcoming_airdrops(self) -> List[Dict]:
        """Get list of upcoming airdrops (without revealing clues)"""

        current_time = time.time()

        upcoming = [
            {
                'id': a['id'],
                'days_until': (a['timestamp'] - current_time) / 86400,
                'amount': a['amount'],
                'recipient_count': a['recipient_count'],
                'status': a['status']
            }
            for a in self.scheduled_airdrops
            if a['timestamp'] > current_time and a['status'] == 'scheduled'
        ]

        return sorted(upcoming, key=lambda x: x['days_until'])


class EasterEggManager:
    """
    Manages all easter eggs in XAI blockchain
    """

    def __init__(self, genesis_timestamp: int, secret_seed: str = None):
        self.genesis_timestamp = genesis_timestamp
        self.lucky_blocks = LuckyBlockSystem(genesis_timestamp, secret_seed)
        self.treasure_wallets = HiddenTreasureWallets()
        self.airdrops = AirdropClueSystem(genesis_timestamp)

    def initialize_easter_eggs(self) -> Dict:
        """
        Initialize all easter eggs for genesis

        Returns summary of what was created
        """

        print("\n" + "=" * 70)
        print("INITIALIZING EASTER EGGS")
        print("=" * 70)

        # Generate treasure wallets
        treasures = self.treasure_wallets.generate_treasure_wallets(100)

        # Schedule some example airdrops
        print("\nScheduling mystery airdrops...")

        # Airdrop 1: 3 months after genesis
        self.airdrops.schedule_airdrop(
            timestamp=self.genesis_timestamp + (90 * 86400),
            amount=50000,
            recipient_count=100,
            criteria="Random selection from active nodes"
        )

        # Airdrop 2: 6 months after genesis
        self.airdrops.schedule_airdrop(
            timestamp=self.genesis_timestamp + (180 * 86400),
            amount=100000,
            recipient_count=500,
            criteria="Top 500 node operators by uptime"
        )

        # Airdrop 3: 1 year after genesis
        self.airdrops.schedule_airdrop(
            timestamp=self.genesis_timestamp + (365 * 86400),
            amount=200000,
            recipient_count=1000,
            criteria="Diamond hands (held for 365 days)"
        )

        print("Done: 3 mystery airdrops scheduled")

        # Lucky block stats
        lucky_stats = self.lucky_blocks.get_stats(10000)

        print("\n" + "=" * 70)
        print("EASTER EGG SUMMARY")
        print("=" * 70)
        print(f"\nLucky Blocks (2x Reward):")
        print(f"  First 10,000 blocks will have ~{lucky_stats['lucky_blocks']} lucky blocks")
        print(f"  Next 5 lucky blocks: {lucky_stats['next_lucky_blocks'][:5]}")

        print(f"\nHidden Treasure Wallets:")
        print(f"  Count: 100 wallets")
        print(f"  Balance each: 1,000 XAI")
        print(f"  Total treasure: 100,000 XAI")
        print(f"  Clues hidden in blocks: 100-10,000")

        print(f"\nMystery Airdrops:")
        print(f"  Scheduled: 3 airdrops")
        print(f"  Total value: 350,000 XAI")
        print(f"  Cryptic clues will appear before each drop")

        return {
            'lucky_blocks': lucky_stats,
            'treasure_wallets': len(treasures),
            'treasure_total': 100000,
            'scheduled_airdrops': len(self.airdrops.scheduled_airdrops),
            'airdrop_total': 350000
        }

    def get_block_easter_eggs(self, block_number: int) -> Dict:
        """
        Get any easter eggs that should appear in this block

        Returns:
            dict with lucky status, clues, etc.
        """

        return {
            'block_number': block_number,
            'is_lucky': self.lucky_blocks.is_lucky_block(block_number),
            'treasure_clues': self.treasure_wallets.treasure_wallets,
            'airdrop_clues': self.airdrops.get_clues_for_block(block_number)
        }


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI EASTER EGG SYSTEM")
    print("=" * 70)

    GENESIS_TIME = 1704067200

    # Initialize easter eggs
    easter_eggs = EasterEggManager(GENESIS_TIME)
    summary = easter_eggs.initialize_easter_eggs()

    # Test lucky blocks
    print("\n\nTesting Lucky Block System...")
    print("-" * 70)

    print("\nFirst 20 lucky blocks:")
    lucky_blocks = easter_eggs.lucky_blocks.get_lucky_blocks_in_range(1, 1000)
    print(f"  {lucky_blocks[:20]}")

    # Test block rewards
    print("\nBlock Reward Examples:")
    for block in [1, 42, 100, 237, 500]:
        reward = easter_eggs.lucky_blocks.get_block_reward(block, 60)
        status = "LUCKY! 🎰" if reward == 120 else "normal"
        print(f"  Block {block}: {reward} XAI ({status})")

    # Show upcoming airdrops
    print("\n\nUpcoming Mystery Airdrops:")
    print("-" * 70)
    upcoming = easter_eggs.airdrops.get_upcoming_airdrops()
    for airdrop in upcoming:
        print(f"\nAirdrop {airdrop['id'][:8]}...")
        print(f"  Days until: {airdrop['days_until']:.0f}")
        print(f"  Amount: {airdrop['amount']:,.0f} XAI")
        print(f"  Recipients: {airdrop['recipient_count']}")

    # Show example treasure clue
    print("\n\nExample Treasure Wallet Clues:")
    print("-" * 70)
    for wallet in easter_eggs.treasure_wallets.treasure_wallets[:5]:
        print(f"\nTreasure #{wallet['index']}:")
        print(f"  Clue: {wallet['discovery_clue']}")
        print(f"  Hidden in block: {wallet['hidden_in_block']}")
        print(f"  Prize: {wallet['balance']} XAI")

    print("\n" + "=" * 70)

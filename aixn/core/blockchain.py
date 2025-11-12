"""
AXN Blockchain Core - Production Implementation
Real cryptocurrency blockchain with transactions, mining, and consensus
"""

import hashlib
import json
import time
import os
from typing import List, Dict, Optional
from datetime import datetime
import ecdsa
import base58
from .gamification import (
    AirdropManager, StreakTracker, TreasureHuntManager,
    FeeRefundCalculator, TimeCapsuleManager
)

class Transaction:
    """Real cryptocurrency transaction with ECDSA signatures"""

    def __init__(self, sender: str, recipient: str, amount: float, fee: float = 0.0, public_key: str = None, tx_type: str = "normal"):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.signature = None
        self.txid = None
        self.public_key = public_key  # Store sender's public key for signature verification
        self.tx_type = tx_type  # Transaction type: normal, airdrop, treasure, refund, timecapsule

    def calculate_hash(self) -> str:
        """Calculate transaction hash (TXID)"""
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def sign_transaction(self, private_key: str):
        """Sign transaction with sender's private key"""
        if self.sender == "COINBASE":
            # Coinbase transactions don't need signatures
            self.txid = self.calculate_hash()
            return

        try:
            sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
            message = self.calculate_hash().encode()
            signature = sk.sign(message)
            self.signature = signature.hex()
            self.txid = self.calculate_hash()
        except Exception as e:
            raise ValueError(f"Failed to sign transaction: {e}")

    def verify_signature(self) -> bool:
        """Verify transaction signature"""
        if self.sender == "COINBASE":
            return True

        if not self.signature or not self.public_key:
            return False

        try:
            # Use the provided public key for verification
            vk = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(self.public_key),
                curve=ecdsa.SECP256k1
            )

            # Verify the address matches this public key
            pub_hash = hashlib.sha256(self.public_key.encode()).hexdigest()
            expected_address = f"AXN{pub_hash[:40]}"
            if expected_address != self.sender:
                print(f"Address mismatch: expected {expected_address}, got {self.sender}")
                return False

            message = self.calculate_hash().encode()
            signature = bytes.fromhex(self.signature)
            return vk.verify(signature, message)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'txid': self.txid,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'public_key': self.public_key,
            'tx_type': self.tx_type
        }


class Block:
    """Blockchain block with real proof-of-work"""

    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, difficulty: int = 4):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.hash = None
        self.merkle_root = self.calculate_merkle_root()

    def calculate_merkle_root(self) -> str:
        """Calculate merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b"").hexdigest()

        tx_hashes = [tx.txid for tx in self.transactions]

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self) -> str:
        """Mine block with proof-of-work"""
        target = '0' * self.difficulty

        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target):
                print(f"Block mined! Hash: {self.hash}")
                return self.hash
            self.nonce += 1

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce,
            'hash': self.hash,
            'difficulty': self.difficulty
        }


class Blockchain:
    """AXN Blockchain - Real cryptocurrency implementation"""

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.blocks_dir = os.path.join(self.data_dir, 'blocks')
        os.makedirs(self.blocks_dir, exist_ok=True)
        self.utxo_file = os.path.join(self.data_dir, 'utxo_set.json')
        self.pending_tx_file = os.path.join(self.data_dir, 'pending_transactions.json')

        self.chain: List[Block] = [] # This will be a cache of loaded blocks, not the primary storage
        self.pending_transactions: List[Transaction] = []
        self.difficulty = 4
        self.initial_block_reward = 60.0
        self.halving_interval = 194400
        self.transaction_fee_percent = 0.24
        self.utxo_set = {}

        # Initialize gamification features
        self.airdrop_manager = AirdropManager()
        self.streak_tracker = StreakTracker()
        self.treasure_manager = TreasureHuntManager()
        self.fee_refund_calculator = FeeRefundCalculator()
        self.timecapsule_manager = TimeCapsuleManager()

        if not self.load_from_disk():
            self.create_genesis_block()

    def _save_block_to_disk(self, block: Block):
        """Save a single block to its file."""
        block_file = os.path.join(self.blocks_dir, f'block_{block.index}.json')
        with open(block_file, 'w') as f:
            json.dump(block.to_dict(), f, indent=2)

    def save_to_disk(self):
        """Save the blockchain state (UTXO set and pending transactions) to disk."""
        # Save UTXO set
        with open(self.utxo_file, 'w') as f:
            json.dump(self.utxo_set, f, indent=2)

        # Save pending transactions
        pending_tx_data = [tx.to_dict() for tx in self.pending_transactions]
        with open(self.pending_tx_file, 'w') as f:
            json.dump(pending_tx_data, f, indent=2)

    def _load_block_from_disk(self, block_index: int) -> Optional[Block]:
        """Load a single block from its file."""
        block_file = os.path.join(self.blocks_dir, f'block_{block_index}.json')
        if not os.path.exists(block_file):
            return None
        try:
            with open(block_file, 'r') as f:
                block_data = json.load(f)
            transactions = []
            for tx_data in block_data['transactions']:
                tx = Transaction(
                    tx_data['sender'],
                    tx_data['recipient'],
                    tx_data['amount'],
                    tx_data['fee'],
                    tx_data['public_key'],
                    tx_data['tx_type']
                )
                tx.timestamp = tx_data['timestamp']
                tx.signature = tx_data['signature']
                tx.txid = tx_data['txid']
                transactions.append(tx)

            block = Block(
                block_data['index'],
                transactions,
                block_data['previous_hash'],
                block_data['difficulty']
            )
            block.timestamp = block_data['timestamp']
            block.nonce = block_data['nonce']
            block.hash = block_data['hash']
            block.merkle_root = block_data['merkle_root']
            return block
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading block {block_index} from disk: {e}")
            return None

    def load_from_disk(self) -> bool:
        """Load the blockchain state from disk (blocks, UTXO set, pending transactions)."""
        # Load UTXO set
        if os.path.exists(self.utxo_file):
            try:
                with open(self.utxo_file, 'r') as f:
                    self.utxo_set = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading UTXO set: {e}. Starting fresh.")
                self.utxo_set = {}

        # Load pending transactions
        if os.path.exists(self.pending_tx_file):
            try:
                with open(self.pending_tx_file, 'r') as f:
                    pending_tx_data = json.load(f)
                    self.pending_transactions = []
                    for tx_data in pending_tx_data:
                        tx = Transaction(
                            tx_data['sender'],
                            tx_data['recipient'],
                            tx_data['amount'],
                            tx_data['fee'],
                            tx_data['public_key'],
                            tx_data['tx_type']
                        )
                        tx.timestamp = tx_data['timestamp']
                        tx.signature = tx_data['signature']
                        tx.txid = tx_data['txid']
                        self.pending_transactions.append(tx)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading pending transactions: {e}. Starting fresh.")
                self.pending_transactions = []

        # Load blocks
        block_files = sorted([f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')],
                             key=lambda x: int(x.split('_')[1].split('.')[0]))

        if not block_files:
            return False

        self.chain = []
        for block_file in block_files:
            block_index = int(block_file.split('_')[1].split('.')[0])
            block = self._load_block_from_disk(block_index)
            if block:
                self.chain.append(block)
            else:
                print(f"Failed to load block {block_index}. Data might be corrupted.")
                return False # Indicate failure if any block fails to load

        print(f"Loaded {len(self.chain)} blocks from disk.")
        return True

    def create_genesis_block(self):
        """Create or load the genesis block"""
        import os

        # Try to load genesis block from file (for unified network)
        genesis_file = os.path.join(os.path.dirname(__file__), 'genesis.json')

        if os.path.exists(genesis_file):
            print(f"Loading genesis block from {genesis_file}")
            with open(genesis_file, 'r') as f:
                genesis_data = json.load(f)

            # Recreate ALL genesis transactions
            genesis_transactions = []
            for tx_data in genesis_data['transactions']:
                genesis_tx = Transaction(
                    tx_data['sender'],
                    tx_data['recipient'],
                    tx_data['amount'],
                    tx_data['fee']
                )
                genesis_tx.timestamp = tx_data['timestamp']
                genesis_tx.txid = tx_data['txid']
                genesis_tx.signature = tx_data['signature']
                genesis_transactions.append(genesis_tx)

            print(f"Loaded {len(genesis_transactions)} genesis transactions (Total: {sum(tx.amount for tx in genesis_transactions)} AXN)")

            # Create genesis block with pre-defined values
            genesis_block = Block(0, genesis_transactions, "0", self.difficulty)
            genesis_block.timestamp = genesis_data['timestamp']
            genesis_block.nonce = genesis_data['nonce']
            genesis_block.merkle_root = genesis_data['merkle_root']
            genesis_block.hash = genesis_data['hash']

            # Mine it to get proper PoW hash
            print("Mining unified genesis block...")
            genesis_block.hash = genesis_block.mine_block()

            print(f"Genesis block loaded: {genesis_block.hash}")
        else:
            print("Creating new genesis block...")
            genesis_tx = Transaction("COINBASE", "GENESIS", 1000000000.0)  # 1 billion AXN pre-mine
            genesis_tx.txid = genesis_tx.calculate_hash()

            genesis_block = Block(0, [genesis_tx], "0", self.difficulty)
            genesis_block.hash = genesis_block.mine_block()

        self.chain.append(genesis_block)
        self.update_utxo_set(genesis_block)
        self._save_block_to_disk(genesis_block) # Save genesis block to its file
        self.save_to_disk() # Save UTXO and pending TXs

    def get_latest_block(self) -> Block:
        """Get the last block in the chain by loading it from disk."""
        block_files = sorted([f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')],
                             key=lambda x: int(x.split('_')[1].split('.')[0]),
                             reverse=True)
        if not block_files:
            raise Exception("No blocks found in storage.")
        latest_block_index = int(block_files[0].split('_')[1].split('.')[0])
        latest_block = self._load_block_from_disk(latest_block_index)
        if not latest_block:
            raise Exception(f"Failed to load latest block {latest_block_index}.")
        return latest_block

    def get_block_reward(self, block_height: int) -> float:
        """Calculate block reward with halving every 1 year (262,800 blocks at 2min/block)

        Emission schedule:
        - Year 1 (blocks 0-262,799): 60 AXN/block → ~15.8M AXN
        - Year 2 (blocks 262,800-525,599): 30 AXN/block → ~7.9M AXN
        - Year 3 (blocks 525,600-788,399): 15 AXN/block → ~3.9M AXN
        - Year 4 (blocks 788,400-1,051,199): 7.5 AXN/block → ~2.0M AXN
        - Continues halving until mining pool exhausted (72.6M AXN total)
        """
        halvings = block_height // self.halving_interval
        reward = self.initial_block_reward / (2 ** halvings)

        # Ensure reward doesn't go below minimum (0.00000001 AXN)
        if reward < 0.00000001:
            return 0.0

        return reward

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool after validation"""
        # Validate transaction
        if not self.validate_transaction(transaction):
            return False

        self.pending_transactions.append(transaction)
        return True

    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate a transaction"""
        # Coinbase transactions are always valid
        if transaction.sender == "COINBASE":
            return True

        # Verify signature
        if not transaction.verify_signature():
            print("Invalid signature")
            return False

        # Check sender has sufficient balance
        balance = self.get_balance(transaction.sender)
        total_needed = transaction.amount + transaction.fee

        if balance < total_needed:
            print(f"Insufficient balance. Has: {balance}, Needs: {total_needed}")
            return False

        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        """Mine a new block with pending transactions"""
        # Calculate block reward based on current chain height (with halving)
        block_height = len(self.chain)
        base_reward = self.get_block_reward(block_height)

        # Update miner streak and apply bonus
        self.streak_tracker.update_miner_streak(miner_address, time.time())
        final_reward, streak_bonus = self.streak_tracker.apply_streak_bonus(miner_address, base_reward)

        # Create coinbase transaction (block reward + transaction fees + streak bonus)
        total_fees = sum(tx.fee for tx in self.pending_transactions)
        coinbase_reward = final_reward + total_fees

        coinbase_tx = Transaction("COINBASE", miner_address, coinbase_reward)
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create new block
        block_transactions = [coinbase_tx] + self.pending_transactions
        new_block = Block(
            len(self.chain),
            block_transactions,
            self.get_latest_block().hash,
            self.difficulty
        )

        # Mine the block
        new_block.hash = new_block.mine_block()

        # Add to chain (cache)
        self.chain.append(new_block)
        self._save_block_to_disk(new_block)

        # Update UTXO set
        self.update_utxo_set(new_block)

        # Process gamification features for this block
        self._process_gamification_features(new_block, miner_address)

        # Clear pending transactions
        self.pending_transactions = []

        # Log streak bonus if applied
        if streak_bonus > 0:
            print(f"STREAK BONUS: +{streak_bonus:.4f} AXN ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)")

        self.save_to_disk()
        return new_block

    def _process_gamification_features(self, block: Block, miner_address: str):
        """Process all gamification features after mining a block"""
        block_height = block.index

        # 1. Check for airdrop (every 100th block)
        if self.airdrop_manager.should_trigger_airdrop(block_height):
            airdrop_amounts = self.airdrop_manager.execute_airdrop(
                block_height, block.hash, self
            )
            if airdrop_amounts:
                # Create airdrop transactions and add to next block pending
                for recipient, amount in airdrop_amounts.items():
                    airdrop_tx = Transaction("COINBASE", recipient, amount, tx_type="airdrop")
                    airdrop_tx.txid = airdrop_tx.calculate_hash()
                    self.pending_transactions.append(airdrop_tx)

        # 2. Process fee refunds based on congestion
        pending_count = len(self.pending_transactions)
        refunds = self.fee_refund_calculator.process_refunds(block, pending_count)
        if refunds:
            # Create refund transactions
            for recipient, amount in refunds.items():
                refund_tx = Transaction("COINBASE", recipient, amount, tx_type="refund")
                refund_tx.txid = refund_tx.calculate_hash()
                self.pending_transactions.append(refund_tx)

        # 3. Check for unlockable time capsules
        unlockable_capsules = self.timecapsule_manager.get_unlockable_capsules()
        for capsule in unlockable_capsules:
            # Create time capsule release transaction
            capsule_tx = Transaction(
                capsule['sender'],
                capsule['recipient'],
                capsule['amount'],
                tx_type="timecapsule"
            )
            capsule_tx.txid = capsule_tx.calculate_hash()
            self.timecapsule_manager.release_capsule(capsule['id'], capsule_tx.txid)
            self.pending_transactions.append(capsule_tx)

    def update_utxo_set(self, block: Block):
        """Update unspent transaction outputs"""
        for tx in block.transactions:
            # Add new outputs
            if tx.recipient not in self.utxo_set:
                self.utxo_set[tx.recipient] = []

            self.utxo_set[tx.recipient].append({
                'txid': tx.txid,
                'amount': tx.amount,
                'spent': False
            })

            # Mark sender's outputs as spent
            if tx.sender != "COINBASE" and tx.sender in self.utxo_set:
                spent_amount = tx.amount + tx.fee
                remaining = spent_amount

                for utxo in self.utxo_set[tx.sender]:
                    if not utxo['spent'] and remaining > 0:
                        if utxo['amount'] <= remaining:
                            utxo['spent'] = True
                            remaining -= utxo['amount']
                        else:
                            # Partial spend - split UTXO
                            utxo['amount'] -= remaining
                            remaining = 0

    def get_balance(self, address: str) -> float:
        """Get balance of an address"""
        if address not in self.utxo_set:
            return 0.0

        balance = sum(
            utxo['amount']
            for utxo in self.utxo_set[address]
            if not utxo['spent']
        )
        return balance

    def validate_chain(self) -> bool:
        """Validate entire blockchain by loading blocks from disk."""
        block_files = sorted([f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')],
                             key=lambda x: int(x.split('_')[1].split('.')[0]))

        if not block_files:
            return False # No blocks to validate

        # Load genesis block separately
        previous_block = self._load_block_from_disk(0)
        if not previous_block:
            print("Failed to load genesis block for validation.")
            return False

        for i in range(1, len(block_files)):
            current_block = self._load_block_from_disk(i)
            if not current_block:
                print(f"Failed to load block {i} for validation.")
                return False

            # Verify hash
            if current_block.hash != current_block.calculate_hash():
                print(f"Block {i} has invalid hash")
                return False

            # Verify previous hash
            if current_block.previous_hash != previous_block.hash:
                print(f"Block {i} has invalid previous hash")
                return False

            # Verify proof of work
            if not current_block.hash.startswith('0' * current_block.difficulty):
                print(f"Block {i} doesn't meet difficulty requirement")
                return False

            # Verify all transactions (simplified for now, full validation would require UTXO tracking)
            # For now, just check transaction signatures if applicable
            for tx in current_block.transactions:
                if tx.sender != "COINBASE" and not tx.verify_signature():
                    print(f"Block {i} has invalid transaction signature")
                    return False

            previous_block = current_block
        return True

    def get_transaction_history(self, address: str) -> List[dict]:
        """Get all transactions involving an address by iterating through blocks on disk."""
        history = []
        block_files = sorted([f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')],
                             key=lambda x: int(x.split('_')[1].split('.')[0]))

        for block_file in block_files:
            block_index = int(block_file.split('_')[1].split('.')[0])
            block = self._load_block_from_disk(block_index)
            if block:
                for tx in block.transactions:
                    if tx.sender == address or tx.recipient == address:
                        history.append({
                            'block': block.index,
                            'txid': tx.txid,
                            'sender': tx.sender,
                            'recipient': tx.recipient,
                            'amount': tx.amount,
                            'fee': tx.fee,
                            'timestamp': tx.timestamp,
                            'type': 'sent' if tx.sender == address else 'received'
                        })
        return history

    def get_stats(self) -> dict:
        """Get blockchain statistics."""
        block_files = [f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')]
        num_blocks = len(block_files)

        total_transactions = 0
        # This is inefficient, but for stats, we might need to iterate through blocks
        # A more optimized solution would cache this or store it separately
        for i in range(num_blocks):
            block = self._load_block_from_disk(i)
            if block:
                total_transactions += len(block.transactions)

        total_supply = sum(self.get_balance(addr) for addr in self.utxo_set)

        return {
            'blocks': num_blocks,
            'total_transactions': total_transactions,
            'pending_transactions': len(self.pending_transactions),
            'difficulty': self.difficulty,
            'total_supply': total_supply,
            'unique_addresses': len(self.utxo_set),
            'latest_block_hash': self.get_latest_block().hash
        }

    def to_dict(self) -> dict:
        """Export entire blockchain by loading blocks from disk."""
        block_files = sorted([f for f in os.listdir(self.blocks_dir) if f.startswith('block_') and f.endswith('.json')],
                             key=lambda x: int(x.split('_')[1].split('.')[0]))
        
        chain_data = []
        for block_file in block_files:
            block_index = int(block_file.split('_')[1].split('.')[0])
            block = self._load_block_from_disk(block_index)
            if block:
                chain_data.append(block.to_dict())

        pending_tx_data = [tx.to_dict() for tx in self.pending_transactions]

        return {
            'chain': chain_data,
            'pending_transactions': pending_tx_data,
            'difficulty': self.difficulty,
            'stats': self.get_stats()
        }

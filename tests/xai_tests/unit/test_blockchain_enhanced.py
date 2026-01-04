"""
Enhanced comprehensive tests for blockchain.py to achieve 98%+ coverage

Tests edge cases, error paths, UTXO management, and persistence operations
"""

import pytest
import os
import json
import time
import tempfile
from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet

PREV_HASH = "0" * 64


class TestBlockchainPersistence:
    """Test blockchain persistence and loading"""

    def test_load_from_disk_success(self, tmp_path):
        """Test successful loading from disk"""
        bc1 = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Create some blocks
        bc1.mine_pending_transactions(wallet.address)
        bc1.mine_pending_transactions(wallet.address)

        initial_height = len(bc1.chain)

        # Create new blockchain instance - should load from disk
        bc2 = Blockchain(data_dir=str(tmp_path))

        assert len(bc2.chain) == initial_height

    def test_load_from_disk_no_data(self, tmp_path):
        """Test loading when no disk data exists creates genesis"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert len(bc.chain) == 1  # Genesis block
        assert bc.chain[0].index == 0

    def test_save_chain_to_disk(self, tmp_path):
        """Test saving chain to disk via block persistence"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Blocks are saved automatically when mined via _save_block_to_disk
        # Verify files exist
        assert os.path.exists(os.path.join(str(tmp_path), "blocks"))

    def test_save_state_to_disk(self, tmp_path):
        """Test saving state (UTXO and pending transactions) to disk"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Save state - pass the utxo_manager object, not the dict
        bc.storage.save_state_to_disk(bc.utxo_manager, bc.pending_transactions)

        # Verify state file exists (UTXO saved to utxo_set.json)
        assert os.path.exists(os.path.join(str(tmp_path), "utxo_set.json"))


class TestGenesisBlockLoading:
    """Test genesis block creation and loading"""

    def test_create_genesis_from_file(self, tmp_path):
        """Test loading genesis block from genesis.json"""
        bc = Blockchain(data_dir=str(tmp_path))

        genesis = bc.chain[0]
        assert genesis.index == 0
        assert genesis.previous_hash == "0" * 64
        assert len(genesis.transactions) > 0

    def test_genesis_block_coinbase(self, tmp_path):
        """Test genesis block contains coinbase transaction"""
        bc = Blockchain(data_dir=str(tmp_path))

        genesis = bc.chain[0]
        has_coinbase = any(tx.sender == "COINBASE" for tx in genesis.transactions)

        assert has_coinbase


class TestTransactionInitialization:
    """Test Transaction initialization edge cases"""

    def test_transaction_default_outputs(self):
        """Test transaction creates default outputs"""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0
        )

        assert len(tx.outputs) == 1
        assert tx.outputs[0]["address"] == tx.recipient
        assert tx.outputs[0]["amount"] == 10.0

    def test_transaction_custom_outputs(self):
        """Test transaction with custom outputs"""
        outputs = [
            {"address": "XAI" + "a" * 40, "amount": 5.0},
            {"address": "XAI" + "b" * 40, "amount": 3.0}
        ]

        tx = Transaction(
            sender="XAI" + "c" * 40,
            recipient="XAI" + "a" * 40,
            amount=8.0,
            outputs=outputs
        )

        assert len(tx.outputs) == 2
        assert tx.outputs == outputs

    def test_transaction_zero_amount_no_outputs(self):
        """Test transaction with zero amount doesn't create default output"""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=0.0
        )

        assert len(tx.outputs) == 0

    def test_transaction_none_recipient(self):
        """Test transaction with None recipient"""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient=None,
            amount=10.0
        )

        # Should not create default output when recipient is None
        assert len(tx.outputs) == 0

    def test_transaction_custom_inputs(self):
        """Test transaction with custom inputs"""
        inputs = [
            {"txid": "a" * 64, "vout": 0},
            {"txid": "b" * 64, "vout": 1}
        ]

        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            inputs=inputs
        )

        assert len(tx.inputs) == 2
        assert tx.inputs == inputs


class TestTransactionSigning:
    """Test transaction signing edge cases"""

    def test_sign_coinbase_transaction(self):
        """Test coinbase transaction signing (no signature needed)"""
        tx = Transaction(
            sender="COINBASE",
            recipient="XAI" + "a" * 40,
            amount=12.0
        )

        tx.sign_transaction("fake_private_key")

        assert tx.txid is not None
        assert tx.signature is None

    def test_sign_transaction_invalid_key(self):
        """Test signing with invalid private key raises error"""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            recipient="XAI" + "a" * 40,
            amount=10.0
        )

        with pytest.raises(ValueError, match="Failed to sign transaction"):
            tx.sign_transaction("invalid_key")


class TestTransactionVerification:
    """Test transaction signature verification edge cases"""

    def test_verify_coinbase_signature(self):
        """Test coinbase transaction verification always succeeds"""
        tx = Transaction(
            sender="COINBASE",
            recipient="XAI" + "a" * 40,
            amount=12.0
        )

        assert tx.verify_signature() is True

    def test_verify_missing_signature(self):
        """Test verification fails when signature is missing"""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            recipient="XAI" + "a" * 40,
            amount=10.0,
            public_key=wallet.public_key
        )

        assert tx.verify_signature() is False

    def test_verify_missing_public_key(self):
        """Test verification fails when public key is missing"""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            recipient="XAI" + "a" * 40,
            amount=10.0
        )
        tx.signature = "fake_signature"

        assert tx.verify_signature() is False

    def test_verify_address_mismatch(self):
        """Test verification fails when address doesn't match public key"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient="XAI" + "a" * 40,
            amount=10.0,
            public_key=wallet2.public_key  # Wrong public key
        )

        tx.sign_transaction(wallet1.private_key)

        assert tx.verify_signature() is False

    def test_verify_invalid_signature_format(self):
        """Test verification fails with invalid signature format"""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            recipient="XAI" + "a" * 40,
            amount=10.0,
            public_key=wallet.public_key
        )
        tx.signature = "invalid"
        tx.txid = tx.calculate_hash()

        assert tx.verify_signature() is False


class TestBlockMerkleRoot:
    """Test block merkle root calculation"""

    def test_merkle_root_empty_transactions(self):
        """Test merkle root with no transactions"""
        block = Block(1, [], PREV_HASH)

        merkle = block.calculate_merkle_root()

        assert merkle is not None
        assert len(merkle) == 64  # SHA256 hex length

    def test_merkle_root_odd_transactions(self):
        """Test merkle root with odd number of transactions"""
        wallet = Wallet()
        txs = [
            Transaction("COINBASE", wallet.address, 12.0),
            Transaction("XAI" + "a" * 40, "XAI" + "b" * 40, 5.0),
            Transaction("XAI" + "c" * 40, "XAI" + "d" * 40, 3.0)
        ]

        for tx in txs:
            tx.txid = tx.calculate_hash()

        block = Block(1, txs, PREV_HASH)

        merkle = block.calculate_merkle_root()

        assert merkle is not None
        assert len(merkle) == 64

    def test_merkle_root_even_transactions(self):
        """Test merkle root with even number of transactions"""
        wallet = Wallet()
        txs = [
            Transaction("COINBASE", wallet.address, 12.0),
            Transaction("XAI" + "a" * 40, "XAI" + "b" * 40, 5.0),
        ]

        for tx in txs:
            tx.txid = tx.calculate_hash()

        block = Block(1, txs, PREV_HASH)

        merkle = block.calculate_merkle_root()

        assert merkle is not None


class TestBlockMining:
    """Test block mining edge cases"""

    def test_mine_block_difficulty_1(self):
        """Test mining with difficulty 1"""
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH, difficulty=1)
        hash_result = block.mine_block()

        assert hash_result.startswith("0")

    def test_mine_block_difficulty_2(self):
        """Test mining with difficulty 2"""
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH, difficulty=2)
        hash_result = block.mine_block()

        assert hash_result.startswith("00")

    def test_block_miner_extraction(self):
        """Test miner address is extracted from coinbase"""
        wallet = Wallet()
        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        block = Block(1, [coinbase], PREV_HASH)

        assert block.miner == wallet.address

    def test_block_no_miner(self):
        """Test block without coinbase has no miner"""
        tx = Transaction("XAI" + "a" * 40, "XAI" + "b" * 40, 10.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH)

        assert block.miner is None


class TestBlockchainUTXOManagement:
    """Test UTXO management edge cases"""

    def test_get_balance_no_utxos(self, tmp_path):
        """Test getting balance for address with no UTXOs"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        balance = bc.get_balance(wallet.address)

        assert balance == 0.0

    def test_get_balance_with_utxos(self, tmp_path):
        """Test getting balance for address with UTXOs"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine a block to create UTXO
        bc.mine_pending_transactions(wallet.address)

        balance = bc.get_balance(wallet.address)

        assert balance > 0


class TestBlockchainSupplyTracking:
    """Test supply tracking edge cases"""

    def test_get_circulating_supply(self, tmp_path):
        """Test getting circulating supply"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine some blocks
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        supply = bc.get_circulating_supply()

        assert supply > 0
        assert supply <= bc.max_supply

    def test_total_supply_calculation(self, tmp_path):
        """Test total supply calculation from UTXO set"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Calculate total from UTXO set
        utxo_set = bc.utxo_manager.get_utxo_set()
        total = sum(utxo["amount"] for utxos in utxo_set.values() for utxo in utxos)

        assert total > 0


class TestBlockchainValidation:
    """Test blockchain validation edge cases"""

    def test_validate_empty_chain(self, tmp_path):
        """Test validating empty chain passed explicitly"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Pass an explicitly empty chain - this should be invalid
        # Note: validate_chain() falls back to disk when in-memory chain is empty
        result = bc.validate_chain(chain=[])

        # Empty chain validation should return False (or tuple with False)
        # The method returns bool or tuple, handle both
        is_valid = result[0] if isinstance(result, tuple) else result
        assert is_valid is False

    def test_validate_chain_invalid_previous_hash(self, tmp_path):
        """Test detecting invalid previous hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        # Create a copy of the chain with tampered previous_hash
        import copy
        tampered_chain = copy.deepcopy(bc.chain)
        tampered_chain[2].previous_hash = "0" * 64

        # Validate the tampered chain explicitly
        result = bc.validate_chain(chain=tampered_chain)

        # The method returns bool or tuple, handle both
        is_valid = result[0] if isinstance(result, tuple) else result
        assert is_valid is False

    def test_validate_chain_invalid_hash(self, tmp_path):
        """Test detecting invalid block hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Tamper with block hash
        bc.chain[1].hash = "0" * 64

        result = bc.validate_chain()

        assert result is False


class TestBlockchainRewardCalculation:
    """Test block reward calculation edge cases"""

    def test_get_block_reward_genesis(self, tmp_path):
        """Test reward for genesis block"""
        bc = Blockchain(data_dir=str(tmp_path))

        reward = bc.get_block_reward(0)

        assert reward == bc.initial_block_reward

    def test_get_block_reward_before_first_halving(self, tmp_path):
        """Test reward before first halving"""
        bc = Blockchain(data_dir=str(tmp_path))

        reward = bc.get_block_reward(100000)

        assert reward == bc.initial_block_reward

    def test_get_block_reward_at_halving_boundary(self, tmp_path):
        """Test reward exactly at halving boundary"""
        bc = Blockchain(data_dir=str(tmp_path))

        reward = bc.get_block_reward(bc.halving_interval)

        assert reward == bc.initial_block_reward / 2

    def test_get_block_reward_after_many_halvings(self, tmp_path):
        """Test reward after many halvings approaches zero"""
        bc = Blockchain(data_dir=str(tmp_path))

        # After 30 halvings, reward should be negligible or zero
        block_number = bc.halving_interval * 30
        reward = bc.get_block_reward(block_number)

        assert reward < 0.00001 or reward == 0.0


class TestTransactionToDict:
    """Test transaction to_dict method"""

    def test_transaction_to_dict_complete(self):
        """Test transaction to_dict includes all fields"""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            recipient="XAI" + "a" * 40,
            amount=10.0,
            fee=0.24,
            public_key=wallet.public_key,
            tx_type="normal",
            nonce=0
        )
        tx.sign_transaction(wallet.private_key)

        tx_dict = tx.to_dict()

        assert "txid" in tx_dict
        assert "sender" in tx_dict
        assert "recipient" in tx_dict
        assert "amount" in tx_dict
        assert "fee" in tx_dict
        assert "timestamp" in tx_dict
        assert "signature" in tx_dict
        assert "public_key" in tx_dict
        assert "tx_type" in tx_dict
        assert "nonce" in tx_dict
        assert "inputs" in tx_dict
        assert "outputs" in tx_dict


class TestBlockToDict:
    """Test block to_dict method"""

    def test_block_to_dict_complete(self):
        """Test block to_dict includes all fields"""
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH, difficulty=4)
        block.mine_block()

        block_dict = block.to_dict()

        assert "index" in block_dict
        assert "timestamp" in block_dict
        assert "transactions" in block_dict
        assert "previous_hash" in block_dict
        assert "merkle_root" in block_dict
        assert "nonce" in block_dict
        assert "hash" in block_dict
        assert "difficulty" in block_dict


class TestBlockchainGamification:
    """Test gamification features integration"""

    def test_airdrop_manager_initialized(self, tmp_path):
        """Test airdrop manager is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.airdrop_manager is not None

    def test_streak_tracker_initialized(self, tmp_path):
        """Test streak tracker is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.streak_tracker is not None

    def test_treasure_manager_initialized(self, tmp_path):
        """Test treasure manager is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.treasure_manager is not None

    def test_fee_refund_calculator_initialized(self, tmp_path):
        """Test fee refund calculator is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.fee_refund_calculator is not None

    def test_timecapsule_manager_initialized(self, tmp_path):
        """Test time capsule manager is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.timecapsule_manager is not None


class TestBlockchainManagers:
    """Test manager initialization"""

    def test_nonce_tracker_initialized(self, tmp_path):
        """Test nonce tracker is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.nonce_tracker is not None

    def test_trade_manager_initialized(self, tmp_path):
        """Test trade manager is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.trade_manager is not None

    def test_transaction_validator_initialized(self, tmp_path):
        """Test transaction validator is initialized"""
        bc = Blockchain(data_dir=str(tmp_path))

        assert bc.transaction_validator is not None


class TestTransactionHashCalculation:
    """Test transaction hash calculation"""

    def test_calculate_hash_deterministic(self):
        """Test hash calculation is deterministic"""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=0.24
        )
        tx.timestamp = 1000000  # Fixed timestamp

        hash1 = tx.calculate_hash()
        hash2 = tx.calculate_hash()

        assert hash1 == hash2

    def test_calculate_hash_different_inputs(self):
        """Test different transactions produce different hashes"""
        tx1 = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0
        )

        tx2 = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=11.0  # Different amount
        )

        assert tx1.calculate_hash() != tx2.calculate_hash()


class TestBlockHashCalculation:
    """Test block hash calculation"""

    def test_calculate_hash_deterministic(self):
        """Test block hash calculation is deterministic"""
        tx = Transaction("COINBASE", "XAI" + "a" * 40, 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH)
        block.timestamp = 1000000  # Fixed timestamp
        block.nonce = 0

        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()

        assert hash1 == hash2

    def test_calculate_hash_changes_with_nonce(self):
        """Test block hash changes with nonce"""
        tx = Transaction("COINBASE", "XAI" + "a" * 40, 12.0)
        tx.txid = tx.calculate_hash()

        block = Block(1, [tx], PREV_HASH)
        block.timestamp = 1000000

        block.nonce = 0
        hash1 = block.calculate_hash()

        block.nonce = 1
        hash2 = block.calculate_hash()

        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

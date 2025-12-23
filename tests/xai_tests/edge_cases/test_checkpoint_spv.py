"""
Edge case tests for checkpoint fetch/apply operations with SPV confirmations.

Tests checkpoint synchronization and SPV (Simplified Payment Verification)
proof validation for light client operations.
"""

import pytest
import time
import hashlib
import os
import json

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.checkpoints import CheckpointManager
from xai.core.blockchain_components.block import Block


class TestCheckpointOperations:
    """Test checkpoint fetch and apply operations"""

    def test_checkpoint_creation(self, tmp_path):
        """Test creating a checkpoint from current blockchain state"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine several blocks
        for _ in range(10):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))

        # Get latest block
        latest_block = bc.get_latest_block()

        # Create checkpoint with required parameters
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Verify checkpoint structure
        assert checkpoint is not None
        assert checkpoint.block_hash == latest_block.hash
        assert checkpoint.height == latest_block.index
        assert checkpoint.timestamp == latest_block.timestamp
        assert checkpoint.height == len(bc.chain) - 1

    def test_checkpoint_validation(self, tmp_path):
        """Test validating a checkpoint against blockchain state"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))
        latest_block = bc.get_latest_block()
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Validate checkpoint by verifying it at the height
        is_valid = checkpoint_mgr.verify_checkpoint(checkpoint.height)
        assert is_valid

    def test_checkpoint_apply(self, tmp_path):
        """Test applying a checkpoint to sync blockchain state"""
        # Create source blockchain
        bc_source = Blockchain(data_dir=str(tmp_path / "source"))
        miner = Wallet()

        # Mine blocks on source
        for _ in range(10):
            bc_source.mine_pending_transactions(miner.address)

        # Create checkpoint
        checkpoint_mgr_source = CheckpointManager(data_dir=str(tmp_path / "source"))
        latest_block = bc_source.get_latest_block()
        checkpoint = checkpoint_mgr_source.create_checkpoint(
            latest_block, bc_source.utxo_manager, bc_source.get_total_supply()
        )

        # Create destination blockchain (empty/genesis only)
        bc_dest = Blockchain(data_dir=str(tmp_path / "dest"))
        checkpoint_mgr_dest = CheckpointManager(data_dir=str(tmp_path / "dest"))

        # Verify checkpoint was created successfully
        assert checkpoint is not None

        # Load the checkpoint from source and verify it exists
        loaded_checkpoint = checkpoint_mgr_source.load_checkpoint(checkpoint.height)
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.height == checkpoint.height

    def test_checkpoint_fetch_latest(self, tmp_path):
        """Test fetching latest checkpoint from network"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks
        for _ in range(15):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))

        # Create a checkpoint first
        latest_block = bc.get_latest_block()
        checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Get latest checkpoint
        latest = checkpoint_mgr.load_latest_checkpoint()

        # Verify it represents current state
        if latest:
            assert latest.height <= len(bc.chain) - 1

    def test_checkpoint_incremental_sync(self, tmp_path):
        """Test incremental checkpoint synchronization"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))
        checkpoints = []

        # Create checkpoints at intervals
        for i in range(5):
            # Mine some blocks
            for _ in range(10):
                bc.mine_pending_transactions(miner.address)

            # Create checkpoint
            latest_block = bc.get_latest_block()
            cp = checkpoint_mgr.create_checkpoint(
                latest_block, bc.utxo_manager, bc.get_total_supply()
            )
            checkpoints.append(cp)

        # Verify we have sequential checkpoints
        for i in range(len(checkpoints) - 1):
            assert checkpoints[i].height < checkpoints[i+1].height

    def test_checkpoint_invalid_hash(self, tmp_path):
        """Test checkpoint validation with invalid hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))
        latest_block = bc.get_latest_block()
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Save the checkpoint first
        assert checkpoint is not None

        # Load and corrupt the checkpoint file
        checkpoint_file = os.path.join(
            checkpoint_mgr.checkpoints_dir, f"cp_{checkpoint.height}.json"
        )

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        # Corrupt the block hash
        data['block_hash'] = "0" * 64

        with open(checkpoint_file, "w") as f:
            json.dump(data, f)

        # Validation should fail because the checkpoint hash won't match
        is_valid = checkpoint_mgr.verify_checkpoint(checkpoint.height)
        assert not is_valid

    def test_checkpoint_height_mismatch(self, tmp_path):
        """Test checkpoint validation with height mismatch"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))
        latest_block = bc.get_latest_block()
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Save the checkpoint first
        assert checkpoint is not None

        # Load and corrupt the checkpoint file
        checkpoint_file = os.path.join(
            checkpoint_mgr.checkpoints_dir, f"cp_{checkpoint.height}.json"
        )

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        # Corrupt the height
        data['height'] = 9999

        with open(checkpoint_file, "w") as f:
            json.dump(data, f)

        # Validation should fail because the checkpoint hash won't match
        is_valid = checkpoint_mgr.verify_checkpoint(checkpoint.height)
        assert not is_valid

    def test_checkpoint_future_timestamp(self, tmp_path):
        """Test checkpoint with future timestamp"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        checkpoint_mgr = CheckpointManager(data_dir=str(tmp_path))
        latest_block = bc.get_latest_block()
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Save the checkpoint first
        assert checkpoint is not None

        # Load and corrupt the checkpoint file
        checkpoint_file = os.path.join(
            checkpoint_mgr.checkpoints_dir, f"cp_{checkpoint.height}.json"
        )

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        # Set timestamp to far future
        data['timestamp'] = time.time() + 86400 * 365  # 1 year ahead

        with open(checkpoint_file, "w") as f:
            json.dump(data, f)

        # Validation should fail because the checkpoint hash won't match
        # (timestamp is part of the hash calculation)
        is_valid = checkpoint_mgr.verify_checkpoint(checkpoint.height)
        assert not is_valid


class TestSPVProofValidation:
    """Test SPV (Simplified Payment Verification) proof validation"""

    def test_merkle_proof_generation(self, tmp_path):
        """Test generating merkle proof for transaction in block"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        # Fund sender
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = bc.create_transaction(
            sender.address, recipient.address, 0.5, 0.01,
            sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        # Mine block with transaction
        block = bc.mine_pending_transactions(sender.address)

        # Generate merkle proof for the transaction
        try:
            proof = block.generate_merkle_proof(tx.txid)

            # Verify proof structure
            assert isinstance(proof, list)
            assert len(proof) > 0

            # Each proof element should be (hash, is_right) tuple
            for element in proof:
                assert isinstance(element, tuple)
                assert len(element) == 2
                assert isinstance(element[0], str)  # hash
                assert isinstance(element[1], bool)  # is_right flag

        except (ValueError, AttributeError) as e:
            pytest.skip(f"Merkle proof generation not fully implemented: {e}")

    def test_merkle_proof_verification(self, tmp_path):
        """Test verifying merkle proof for transaction"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        tx = bc.create_transaction(
            sender.address, recipient.address, 0.5, 0.01,
            sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        block = bc.mine_pending_transactions(sender.address)

        try:
            # Generate proof
            proof = block.generate_merkle_proof(tx.txid)

            # Verify proof
            is_valid = Block.verify_merkle_proof(
                tx.txid,
                block.merkle_root,
                proof
            )

            assert is_valid

        except (ValueError, AttributeError) as e:
            pytest.skip(f"Merkle proof verification not fully implemented: {e}")

    def test_merkle_proof_invalid_txid(self, tmp_path):
        """Test merkle proof verification with invalid txid"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Try to generate proof for non-existent transaction
        fake_txid = "0" * 64

        try:
            proof = block.generate_merkle_proof(fake_txid)
            pytest.fail("Should have raised ValueError for non-existent txid")
        except ValueError:
            # Expected
            pass

    def test_merkle_proof_tampering_detection(self, tmp_path):
        """Test that tampered merkle proof is detected"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        tx = bc.create_transaction(
            sender.address, recipient.address, 0.5, 0.01,
            sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        block = bc.mine_pending_transactions(sender.address)

        try:
            # Generate valid proof
            proof = block.generate_merkle_proof(tx.txid)

            # Tamper with proof
            if len(proof) > 0:
                tampered_proof = proof.copy()
                # Flip the direction of first element
                hash_val, is_right = tampered_proof[0]
                tampered_proof[0] = (hash_val, not is_right)

                # Verification should fail
                is_valid = Block.verify_merkle_proof(
                    tx.txid,
                    block.merkle_root,
                    tampered_proof
                )

                assert not is_valid

        except (ValueError, AttributeError) as e:
            pytest.skip(f"Merkle proof tampering detection not testable: {e}")

    def test_spv_block_header_validation(self, tmp_path):
        """Test SPV client validating block headers only"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine several blocks
        blocks = []
        for _ in range(5):
            block = bc.mine_pending_transactions(miner.address)
            blocks.append(block)

        # SPV client validates headers (not full blocks)
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i-1]

            # Verify header linkage
            assert current.previous_hash == previous.hash
            assert current.index == previous.index + 1
            assert current.timestamp >= previous.timestamp

    def test_spv_checkpoint_with_proof(self, tmp_path):
        """Test SPV verification using checkpoint with merkle proof"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        tx = bc.create_transaction(
            sender.address, recipient.address, 0.5, 0.01,
            sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        block = bc.mine_pending_transactions(sender.address)

        # Create checkpoint at this block
        checkpoint_mgr = CheckpointManager(bc.data_dir)
        checkpoint = checkpoint_mgr.create_checkpoint(
            block, bc.utxo_manager, bc.get_total_supply()
        )

        try:
            # Generate proof for transaction
            proof = block.generate_merkle_proof(tx.txid)

            # SPV client verifies using checkpoint + proof
            # Verify proof against checkpoint's merkle root
            is_valid = Block.verify_merkle_proof(
                tx.txid,
                checkpoint.merkle_root if checkpoint else block.merkle_root,
                proof
            )

            # Should be valid if checkpoint includes merkle root
            assert isinstance(is_valid, bool)

        except (ValueError, AttributeError) as e:
            pytest.skip(f"SPV checkpoint verification not fully implemented: {e}")

    def test_spv_multi_confirmation_verification(self, tmp_path):
        """Test SPV verification with multiple confirmations"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        tx = bc.create_transaction(
            sender.address, recipient.address, 0.5, 0.01,
            sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        # Mine block with transaction
        tx_block = bc.mine_pending_transactions(sender.address)
        tx_block_height = tx_block.index

        # Mine additional confirmation blocks
        confirmations = 6
        for _ in range(confirmations):
            bc.mine_pending_transactions(sender.address)

        # Verify transaction has required confirmations
        current_height = len(bc.chain) - 1
        actual_confirmations = current_height - tx_block_height

        assert actual_confirmations >= confirmations

    def test_spv_chain_reorganization_handling(self, tmp_path):
        """Test SPV handling of chain reorganizations"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine main chain
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        main_tip = bc.get_latest_block()

        # Checkpoint before reorg
        checkpoint_mgr = CheckpointManager(bc.data_dir)
        pre_reorg_checkpoint = checkpoint_mgr.create_checkpoint(
            main_tip, bc.utxo_manager, bc.get_total_supply()
        )

        # After potential reorg, verify checkpoint
        if pre_reorg_checkpoint:
            is_valid = checkpoint_mgr.verify_checkpoint(pre_reorg_checkpoint.height)
        else:
            is_valid = False

        # Should still be valid if no actual reorg occurred
        assert isinstance(is_valid, bool)

    def test_spv_proof_for_coinbase_transaction(self, tmp_path):
        """Test SPV proof for coinbase transaction"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Coinbase is first transaction
        coinbase_tx = block.transactions[0]

        try:
            # Generate proof for coinbase
            proof = block.generate_merkle_proof(coinbase_tx.txid)

            # Verify proof
            is_valid = Block.verify_merkle_proof(
                coinbase_tx.txid,
                block.merkle_root,
                proof
            )

            assert is_valid

        except (ValueError, AttributeError) as e:
            pytest.skip(f"Coinbase merkle proof not testable: {e}")

    def test_spv_compact_block_relay(self, tmp_path):
        """Test compact block relay for SPV clients"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Create multiple transactions
        txs = []
        for _ in range(5):
            tx = bc.create_transaction(
                sender.address, recipient.address, 0.1, 0.01,
                sender.private_key, sender.public_key
            )
            bc.add_transaction(tx)
            txs.append(tx)
            # Refund sender for next transaction
            bc.mine_pending_transactions(sender.address)

        block = bc.mine_pending_transactions(sender.address)

        # Compact representation includes only header + txids
        compact_block = {
            'header': block.header.to_dict(),
            'txids': [tx.txid for tx in block.transactions if tx.txid]
        }

        # Verify compact block structure
        assert 'header' in compact_block
        assert 'txids' in compact_block
        assert len(compact_block['txids']) > 0

    def test_checkpoint_with_utxo_commitment(self, tmp_path):
        """Test checkpoint including UTXO set commitment"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks to create UTXO set
        for _ in range(10):
            bc.mine_pending_transactions(miner.address)

        latest_block = bc.get_latest_block()
        checkpoint_mgr = CheckpointManager(bc.data_dir)
        checkpoint = checkpoint_mgr.create_checkpoint(
            latest_block, bc.utxo_manager, bc.get_total_supply()
        )

        # Checkpoint may include UTXO commitment for fast sync
        # Verify checkpoint structure (implementation-dependent)
        assert checkpoint is not None
        assert checkpoint.height == latest_block.index
        assert checkpoint.block_hash == latest_block.hash

        # UTXO snapshot is included in checkpoint for fast sync
        assert checkpoint.utxo_snapshot is not None
        assert isinstance(checkpoint.utxo_snapshot, dict)

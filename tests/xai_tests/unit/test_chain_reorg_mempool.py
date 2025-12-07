"""
Unit tests for chain reorganization mempool revalidation

Tests that pending transactions are properly revalidated after a chain reorganization
to prevent double-spends and invalid transactions from remaining in the mempool.

This test suite verifies the critical security fix that ensures mempool transactions
are validated against the new chain state after a reorganization.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from xai.core.blockchain import Blockchain, Transaction, Block


def create_mock_block(index, previous_hash, transactions=None):
    """Create a mock block that will be recognized by _materialize as a Block instance."""
    mock_block = Mock(spec=Block)
    mock_block.transactions = transactions or []
    mock_block.hash = "0000" + "a" * 60
    mock_block.index = index
    mock_block.previous_hash = previous_hash
    mock_block.timestamp = 1000000
    mock_block.difficulty = 4
    mock_block.nonce = 100
    mock_block.header = Mock()
    mock_block.header.hash = mock_block.hash
    mock_block.header.index = index
    mock_block.header.previous_hash = previous_hash
    return mock_block


class TestChainReorgMempoolRevalidation:
    """Test mempool revalidation during chain reorganization"""

    def test_replace_chain_revalidates_mempool_transactions(self, tmp_path, caplog):
        """
        Test that replace_chain() revalidates all pending transactions.

        This is the core security fix: after a chain reorganization, transactions
        valid in the old chain may become invalid (double-spends, invalid nonces,
        insufficient balance). This test verifies they are properly removed.
        """
        bc = Blockchain(data_dir=str(tmp_path))

        # Create mock transactions
        mock_tx_valid = Mock(spec=Transaction)
        mock_tx_valid.txid = "tx_valid"
        mock_tx_valid.sender = "XAI" + "a" * 40
        mock_tx_valid.recipient = "XAI" + "b" * 40
        mock_tx_valid.amount = 100.0

        mock_tx_invalid = Mock(spec=Transaction)
        mock_tx_invalid.txid = "tx_invalid"
        mock_tx_invalid.sender = "XAI" + "c" * 40
        mock_tx_invalid.recipient = "XAI" + "d" * 40
        mock_tx_invalid.amount = 50.0

        # Add both to mempool
        bc.pending_transactions = [mock_tx_valid, mock_tx_invalid]

        # Mock the validator to simulate that tx_invalid becomes invalid after reorg
        def mock_validate(tx, **kwargs):
            return tx.txid == "tx_valid"

        # Create mock block that will be recognized as Block instance
        mock_block = create_mock_block(1, bc.chain[0].hash)

        # Create the new chain using genesis + mock block
        new_chain = [bc.chain[0], mock_block]

        # Mock all the methods that replace_chain depends on
        with patch.object(bc.transaction_validator, 'validate_transaction', side_effect=mock_validate):
            with patch.object(bc, '_validate_chain_structure', return_value=True):
                with patch.object(bc.storage, '_save_block_to_disk'):
                    with patch.object(bc.storage, 'save_state_to_disk'):
                        with patch.object(bc, '_rebuild_contract_state'):
                            with patch.object(bc, '_rebuild_governance_state_from_chain'):
                                with patch.object(bc, 'sync_smart_contract_vm'):
                                    with patch.object(bc, '_rebuild_nonce_tracker'):
                                        with patch.object(bc.utxo_manager, 'process_transaction_inputs', return_value=True):
                                            with patch.object(bc.utxo_manager, 'process_transaction_outputs'):
                                                with caplog.at_level(logging.INFO):
                                                    result = bc.replace_chain(new_chain)

        # Verify replace_chain succeeded
        assert result is True, "replace_chain should succeed with valid longer chain"

        # CRITICAL ASSERTION: Only valid transaction remains
        assert len(bc.pending_transactions) == 1, \
            f"Expected 1 valid transaction, but found {len(bc.pending_transactions)}"
        assert bc.pending_transactions[0].txid == "tx_valid", \
            "Wrong transaction remained in mempool"

        # Verify logging occurred
        log_messages = [record.message for record in caplog.records]
        eviction_logged = any("Evicting transaction" in msg or "evicted" in msg
                             for msg in log_messages)
        assert eviction_logged, "Expected eviction log message"

    def test_all_transactions_remain_valid_after_reorg(self, tmp_path, caplog):
        """Test when all mempool transactions remain valid after reorganization"""
        bc = Blockchain(data_dir=str(tmp_path))

        mock_tx1 = Mock(spec=Transaction)
        mock_tx1.txid = "tx1"
        mock_tx1.sender = "XAI" + "a" * 40

        mock_tx2 = Mock(spec=Transaction)
        mock_tx2.txid = "tx2"
        mock_tx2.sender = "XAI" + "b" * 40

        bc.pending_transactions = [mock_tx1, mock_tx2]

        mock_block = create_mock_block(1, bc.chain[0].hash)
        new_chain = [bc.chain[0], mock_block]

        with patch.object(bc.transaction_validator, 'validate_transaction', return_value=True):
            with patch.object(bc, '_validate_chain_structure', return_value=True):
                with patch.object(bc.storage, '_save_block_to_disk'):
                    with patch.object(bc.storage, 'save_state_to_disk'):
                        with patch.object(bc, '_rebuild_contract_state'):
                            with patch.object(bc, '_rebuild_governance_state_from_chain'):
                                with patch.object(bc, 'sync_smart_contract_vm'):
                                    with patch.object(bc, '_rebuild_nonce_tracker'):
                                        with patch.object(bc.utxo_manager, 'process_transaction_inputs', return_value=True):
                                            with patch.object(bc.utxo_manager, 'process_transaction_outputs'):
                                                with caplog.at_level(logging.DEBUG):
                                                    result = bc.replace_chain(new_chain)

        assert result is True, "replace_chain should succeed with valid longer chain"
        assert len(bc.pending_transactions) == 2
        log_messages = [record.message for record in caplog.records]
        assert any("all" in msg.lower() and "valid" in msg.lower() for msg in log_messages)

    def test_all_transactions_invalid_after_reorg(self, tmp_path, caplog):
        """Test when all mempool transactions become invalid after reorganization"""
        bc = Blockchain(data_dir=str(tmp_path))

        mock_tx1 = Mock(spec=Transaction)
        mock_tx1.txid = "tx1"
        mock_tx1.sender = "XAI" + "a" * 40
        mock_tx1.recipient = "XAI" + "b" * 40
        mock_tx1.amount = 100.0

        mock_tx2 = Mock(spec=Transaction)
        mock_tx2.txid = "tx2"
        mock_tx2.sender = "XAI" + "c" * 40
        mock_tx2.recipient = "XAI" + "d" * 40
        mock_tx2.amount = 50.0

        bc.pending_transactions = [mock_tx1, mock_tx2]

        mock_block = create_mock_block(1, bc.chain[0].hash)
        new_chain = [bc.chain[0], mock_block]

        with patch.object(bc.transaction_validator, 'validate_transaction', return_value=False):
            with patch.object(bc, '_validate_chain_structure', return_value=True):
                with patch.object(bc.storage, '_save_block_to_disk'):
                    with patch.object(bc.storage, 'save_state_to_disk'):
                        with patch.object(bc, '_rebuild_contract_state'):
                            with patch.object(bc, '_rebuild_governance_state_from_chain'):
                                with patch.object(bc, 'sync_smart_contract_vm'):
                                    with patch.object(bc, '_rebuild_nonce_tracker'):
                                        with patch.object(bc.utxo_manager, 'process_transaction_inputs', return_value=True):
                                            with patch.object(bc.utxo_manager, 'process_transaction_outputs'):
                                                with caplog.at_level(logging.INFO):
                                                    result = bc.replace_chain(new_chain)

        assert result is True, "replace_chain should succeed with valid longer chain"
        assert len(bc.pending_transactions) == 0
        log_messages = [record.message for record in caplog.records]
        assert any("2 invalid transactions evicted" in msg for msg in log_messages)

    def test_validation_exception_handling(self, tmp_path, caplog):
        """Test that exceptions during validation cause transaction eviction"""
        bc = Blockchain(data_dir=str(tmp_path))

        mock_tx = Mock(spec=Transaction)
        mock_tx.txid = "tx_exception"
        mock_tx.sender = "XAI" + "a" * 40
        mock_tx.recipient = "XAI" + "b" * 40
        mock_tx.amount = 100.0

        bc.pending_transactions = [mock_tx]

        mock_block = create_mock_block(1, bc.chain[0].hash)
        new_chain = [bc.chain[0], mock_block]

        with patch.object(bc.transaction_validator, 'validate_transaction',
                         side_effect=Exception("Validation error")):
            with patch.object(bc, '_validate_chain_structure', return_value=True):
                with patch.object(bc.storage, '_save_block_to_disk'):
                    with patch.object(bc.storage, 'save_state_to_disk'):
                        with patch.object(bc, '_rebuild_contract_state'):
                            with patch.object(bc, '_rebuild_governance_state_from_chain'):
                                with patch.object(bc, 'sync_smart_contract_vm'):
                                    with patch.object(bc, '_rebuild_nonce_tracker'):
                                        with patch.object(bc.utxo_manager, 'process_transaction_inputs', return_value=True):
                                            with patch.object(bc.utxo_manager, 'process_transaction_outputs'):
                                                with caplog.at_level(logging.WARNING):
                                                    result = bc.replace_chain(new_chain)

        assert result is True, "replace_chain should succeed with valid longer chain"
        assert len(bc.pending_transactions) == 0
        log_messages = [record.message for record in caplog.records]
        assert any("validation raised exception" in msg and "Validation error" in msg
                  for msg in log_messages)

    def test_empty_mempool_revalidation(self, tmp_path, caplog):
        """Test that empty mempool is handled gracefully"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc.pending_transactions = []

        mock_block = create_mock_block(1, bc.chain[0].hash)
        new_chain = [bc.chain[0], mock_block]

        with patch.object(bc, '_validate_chain_structure', return_value=True):
            with patch.object(bc.storage, '_save_block_to_disk'):
                with patch.object(bc.storage, 'save_state_to_disk'):
                    with patch.object(bc, '_rebuild_contract_state'):
                        with patch.object(bc, '_rebuild_governance_state_from_chain'):
                            with patch.object(bc, 'sync_smart_contract_vm'):
                                with patch.object(bc, '_rebuild_nonce_tracker'):
                                    with patch.object(bc.utxo_manager, 'process_transaction_inputs', return_value=True):
                                        with patch.object(bc.utxo_manager, 'process_transaction_outputs'):
                                            with caplog.at_level(logging.DEBUG):
                                                result = bc.replace_chain(new_chain)

        assert result is True, "replace_chain should succeed with valid longer chain"
        assert len(bc.pending_transactions) == 0

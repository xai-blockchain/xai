"""
Unit tests for chain reorganization mempool revalidation

Tests that pending transactions are properly revalidated after a chain reorganization
to prevent double-spends and invalid transactions from remaining in the mempool.
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch

from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet


class TestChainReorgMempoolRevalidation:
    """Test mempool revalidation during chain reorganization"""

    def test_mempool_revalidation_called_during_replace_chain(self, tmp_path, caplog):
        """
        Test that mempool transactions are revalidated after chain replacement.

        This test verifies:
        1. replace_chain() calls validate_transaction for each pending transaction
        2. Invalid transactions are evicted from mempool
        3. Appropriate logging occurs
        """
        # Create blockchain
        bc = Blockchain(data_dir=str(tmp_path))

        # Create mock transactions for mempool
        mock_tx1 = Mock(spec=Transaction)
        mock_tx1.txid = "tx1_valid"
        mock_tx1.sender = "XAI" + "a" * 40
        mock_tx1.recipient = "XAI" + "b" * 40
        mock_tx1.amount = 100.0

        mock_tx2 = Mock(spec=Transaction)
        mock_tx2.txid = "tx2_invalid"
        mock_tx2.sender = "XAI" + "c" * 40
        mock_tx2.recipient = "XAI" + "d" * 40
        mock_tx2.amount = 50.0

        # Add to mempool
        bc.pending_transactions = [mock_tx1, mock_tx2]
        original_count = len(bc.pending_transactions)
        assert original_count == 2

        # Mock transaction validator to return True for tx1, False for tx2
        with patch.object(bc.transaction_validator, 'validate_transaction') as mock_validate:
            mock_validate.side_effect = lambda tx, **kwargs: tx.txid == "tx1_valid"

            # Create alternative chain - must be longer to trigger replacement
            # Mine an additional block to make alternative chain longer
            alternative_chain = bc.chain.copy()
            new_block = bc.mine_block("XAI" + "x" * 40)
            if new_block:
                alternative_chain.append(new_block)

            # Perform chain reorganization
            with caplog.at_level(logging.INFO):
                result = bc.replace_chain(alternative_chain)

            assert result is True

            # Verify validator was called for each transaction
            assert mock_validate.call_count == 2

            # Verify only valid transaction remains
            assert len(bc.pending_transactions) == 1
            assert bc.pending_transactions[0].txid == "tx1_valid"

            # Verify logging occurred
            log_messages = [record.message for record in caplog.records]
            assert any("Mempool revalidation complete" in msg for msg in log_messages), \
                "Expected mempool revalidation log message"
            assert any("Evicting transaction" in msg or "evicted" in msg for msg in log_messages), \
                "Expected transaction eviction log message"

    def test_mempool_all_valid_after_reorg(self, tmp_path, caplog):
        """Test mempool when all transactions remain valid after reorganization"""
        # Create blockchain
        bc = Blockchain(data_dir=str(tmp_path))

        # Create mock transactions
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

        # Mock validator to return True for all transactions
        with patch.object(bc.transaction_validator, 'validate_transaction') as mock_validate:
            mock_validate.return_value = True

            # Create alternative chain - copy current and add block
            alternative_chain = bc.chain.copy()
            new_block = bc.mine_block("XAI" + "x" * 40)
            if new_block:
                alternative_chain.append(new_block)

            with caplog.at_level(logging.DEBUG):
                result = bc.replace_chain(alternative_chain)

            assert result is True

            # Verify all transactions remain
            assert len(bc.pending_transactions) == 2
            assert bc.pending_transactions[0].txid == "tx1"
            assert bc.pending_transactions[1].txid == "tx2"

            # Verify logging shows all transactions valid
            log_messages = [record.message for record in caplog.records]
            assert any("all" in msg and "valid" in msg for msg in log_messages), \
                "Expected log message indicating all transactions remain valid"

    def test_mempool_all_invalid_after_reorg(self, tmp_path, caplog):
        """Test mempool when all transactions become invalid after reorganization"""
        # Create blockchain
        bc = Blockchain(data_dir=str(tmp_path))

        # Create mock transactions
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

        # Mock validator to return False for all transactions
        with patch.object(bc.transaction_validator, 'validate_transaction') as mock_validate:
            mock_validate.return_value = False

            # Create alternative chain - copy current and add block
            alternative_chain = bc.chain.copy()
            new_block = bc.mine_block("XAI" + "x" * 40)
            if new_block:
                alternative_chain.append(new_block)

            with caplog.at_level(logging.INFO):
                result = bc.replace_chain(alternative_chain)

            assert result is True

            # Verify all transactions evicted
            assert len(bc.pending_transactions) == 0

            # Verify logging shows evictions
            log_messages = [record.message for record in caplog.records]
            assert any("2 invalid transactions evicted" in msg for msg in log_messages), \
                "Expected log message showing 2 evictions"

    def test_mempool_validation_exception_handling(self, tmp_path, caplog):
        """Test that validation exceptions are handled and transactions are evicted"""
        # Create blockchain
        bc = Blockchain(data_dir=str(tmp_path))

        # Create mock transaction
        mock_tx = Mock(spec=Transaction)
        mock_tx.txid = "tx_exception"
        mock_tx.sender = "XAI" + "a" * 40
        mock_tx.recipient = "XAI" + "b" * 40
        mock_tx.amount = 100.0

        bc.pending_transactions = [mock_tx]

        # Mock validator to raise exception
        with patch.object(bc.transaction_validator, 'validate_transaction') as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            # Create alternative chain - copy current and add block
            alternative_chain = bc.chain.copy()
            new_block = bc.mine_block("XAI" + "x" * 40)
            if new_block:
                alternative_chain.append(new_block)

            with caplog.at_level(logging.WARNING):
                result = bc.replace_chain(alternative_chain)

            assert result is True

            # Verify transaction evicted due to exception
            assert len(bc.pending_transactions) == 0

            # Verify exception was logged
            log_messages = [record.message for record in caplog.records]
            assert any("validation raised exception" in msg and "Validation error" in msg
                      for msg in log_messages), \
                "Expected log message about validation exception"

    def test_empty_mempool_revalidation(self, tmp_path, caplog):
        """Test that empty mempool doesn't cause issues during reorg"""
        # Create blockchain
        bc = Blockchain(data_dir=str(tmp_path))

        # Ensure mempool is empty
        bc.pending_transactions = []

        # Create alternative chain - copy current and add block
        alternative_chain = bc.chain.copy()
        new_block = bc.mine_block("XAI" + "x" * 40)
        if new_block:
            alternative_chain.append(new_block)

        with caplog.at_level(logging.DEBUG):
            result = bc.replace_chain(alternative_chain)

        assert result is True
        assert len(bc.pending_transactions) == 0

        # Should log that all 0 transactions remain valid
        log_messages = [record.message for record in caplog.records]
        assert any("0 transactions remain valid" in msg or "all 0" in msg for msg in log_messages), \
            "Expected log message about empty mempool validation"

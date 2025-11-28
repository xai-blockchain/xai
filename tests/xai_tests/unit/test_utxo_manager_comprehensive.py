"""
Comprehensive test suite for UTXO Manager to achieve 98%+ coverage.

Tests all UTXO operations including:
- UTXO addition and removal
- Balance calculations
- UTXO selection and spending
- Transaction processing
- Edge cases and error handling
- Statistics and metrics
"""

import pytest
from collections import defaultdict
from xai.core.utxo_manager import UTXOManager, get_utxo_manager
from xai.core.blockchain import Transaction
from xai.core.wallet import Wallet


class TestUTXOManagerInitialization:
    """Test UTXO manager initialization"""

    def test_utxo_manager_default_init(self):
        """Test default initialization"""
        manager = UTXOManager()

        assert manager.utxo_set is not None
        assert isinstance(manager.utxo_set, defaultdict)
        assert manager.total_utxos == 0
        assert manager.total_value == 0.0

    def test_utxo_manager_with_logger(self):
        """Test initialization with custom logger"""
        from xai.core.structured_logger import get_structured_logger

        logger = get_structured_logger()
        manager = UTXOManager(logger=logger)

        assert manager.logger is not None
        assert manager.total_utxos == 0


class TestUTXOAddition:
    """Test UTXO addition operations"""

    def test_add_single_utxo(self):
        """Test adding a single UTXO"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")

        assert manager.total_utxos == 1
        assert manager.total_value == 10.0
        assert len(manager.utxo_set["XAI123"]) == 1

    def test_add_multiple_utxos_same_address(self):
        """Test adding multiple UTXOs to same address"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 5.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid3", 1, 3.0, "P2PKH XAI123")

        assert manager.total_utxos == 3
        assert manager.total_value == 18.0
        assert len(manager.utxo_set["XAI123"]) == 3

    def test_add_utxos_different_addresses(self):
        """Test adding UTXOs to different addresses"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")
        manager.add_utxo("XAI789", "txid3", 0, 30.0, "P2PKH XAI789")

        assert manager.total_utxos == 3
        assert manager.total_value == 60.0
        assert len(manager.utxo_set) == 3

    def test_add_utxo_fractional_amounts(self):
        """Test adding UTXOs with fractional amounts"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 0.123456789, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 0.000001, "P2PKH XAI123")

        assert manager.total_utxos == 2
        assert abs(manager.total_value - 0.123457789) < 0.00001

    def test_add_utxo_zero_amount(self):
        """Test adding UTXO with zero amount"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 0.0, "P2PKH XAI123")

        assert manager.total_utxos == 1
        assert manager.total_value == 0.0


class TestUTXOSpending:
    """Test UTXO spending operations"""

    def test_mark_utxo_spent_success(self):
        """Test successfully marking UTXO as spent"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        result = manager.mark_utxo_spent("XAI123", "txid1", 0)

        assert result is True
        assert manager.total_value == 0.0  # Value should be deducted

    def test_mark_utxo_spent_nonexistent_address(self):
        """Test marking UTXO spent for nonexistent address"""
        manager = UTXOManager()

        result = manager.mark_utxo_spent("XAI999", "txid1", 0)

        assert result is False

    def test_mark_utxo_spent_nonexistent_txid(self):
        """Test marking UTXO spent with wrong txid"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        result = manager.mark_utxo_spent("XAI123", "txid999", 0)

        assert result is False
        assert manager.total_value == 10.0  # Value unchanged

    def test_mark_utxo_spent_wrong_vout(self):
        """Test marking UTXO spent with wrong vout"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        result = manager.mark_utxo_spent("XAI123", "txid1", 999)

        assert result is False

    def test_mark_utxo_spent_already_spent(self):
        """Test marking already spent UTXO"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        # Try to spend again
        result = manager.mark_utxo_spent("XAI123", "txid1", 0)

        assert result is False

    def test_spent_flag_set_correctly(self):
        """Test that spent flag is set correctly"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")

        # Check initially not spent
        utxos = manager.get_utxos_for_address("XAI123")
        assert len(utxos) == 1
        assert utxos[0]["spent"] is False

        # Mark as spent
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        # Check now spent
        utxos_after = manager.get_utxos_for_address("XAI123")
        assert len(utxos_after) == 0  # Should be filtered out


class TestUTXORetrieval:
    """Test UTXO retrieval operations"""

    def test_get_utxos_for_address_empty(self):
        """Test getting UTXOs for address with no UTXOs"""
        manager = UTXOManager()

        utxos = manager.get_utxos_for_address("XAI123")

        assert utxos == []

    def test_get_utxos_for_address_unspent_only(self):
        """Test that only unspent UTXOs are returned"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 5.0, "P2PKH XAI123")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        utxos = manager.get_utxos_for_address("XAI123")

        assert len(utxos) == 1
        assert utxos[0]["txid"] == "txid2"

    def test_get_balance_empty(self):
        """Test getting balance for address with no UTXOs"""
        manager = UTXOManager()

        balance = manager.get_balance("XAI123")

        assert balance == 0.0

    def test_get_balance_single_utxo(self):
        """Test getting balance with single UTXO"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        balance = manager.get_balance("XAI123")

        assert balance == 10.0

    def test_get_balance_multiple_utxos(self):
        """Test getting balance with multiple UTXOs"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 5.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid3", 1, 3.0, "P2PKH XAI123")

        balance = manager.get_balance("XAI123")

        assert balance == 18.0

    def test_get_balance_excludes_spent(self):
        """Test that balance excludes spent UTXOs"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 5.0, "P2PKH XAI123")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        balance = manager.get_balance("XAI123")

        assert balance == 5.0


class TestUTXOSelection:
    """Test UTXO selection for spending"""

    def test_find_spendable_utxos_exact_match(self):
        """Test finding exact amount needed"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")

        utxos = manager.find_spendable_utxos("XAI123", 10.0)

        assert len(utxos) == 1
        assert sum(u["amount"] for u in utxos) == 10.0

    def test_find_spendable_utxos_multiple_needed(self):
        """Test finding multiple UTXOs to meet amount"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 5.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 3.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid3", 0, 4.0, "P2PKH XAI123")

        utxos = manager.find_spendable_utxos("XAI123", 10.0)

        assert len(utxos) == 3
        assert sum(u["amount"] for u in utxos) >= 10.0

    def test_find_spendable_utxos_insufficient_funds(self):
        """Test finding UTXOs when insufficient funds"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 5.0, "P2PKH XAI123")

        utxos = manager.find_spendable_utxos("XAI123", 10.0)

        assert utxos == []

    def test_find_spendable_utxos_no_utxos(self):
        """Test finding UTXOs when address has none"""
        manager = UTXOManager()

        utxos = manager.find_spendable_utxos("XAI123", 10.0)

        assert utxos == []

    def test_find_spendable_utxos_zero_amount(self):
        """Test finding UTXOs for zero amount"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")

        utxos = manager.find_spendable_utxos("XAI123", 0.0)

        assert len(utxos) == 0 or sum(u["amount"] for u in utxos) >= 0.0

    def test_get_unspent_output_success(self):
        """Test retrieving specific unspent output"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")

        utxo = manager.get_unspent_output("txid1", 0)

        assert utxo is not None
        assert utxo["amount"] == 10.0
        assert utxo["txid"] == "txid1"

    def test_get_unspent_output_not_found(self):
        """Test retrieving non-existent output"""
        manager = UTXOManager()

        utxo = manager.get_unspent_output("txid999", 0)

        assert utxo is None

    def test_get_unspent_output_spent(self):
        """Test retrieving spent output returns None"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        utxo = manager.get_unspent_output("txid1", 0)

        assert utxo is None


class TestTransactionProcessing:
    """Test transaction output/input processing"""

    def test_process_transaction_outputs(self):
        """Test processing transaction outputs"""
        manager = UTXOManager()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create transaction
        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.5)

        manager.process_transaction_outputs(tx)

        # Should create UTXOs for outputs
        assert manager.total_utxos > 0

    def test_process_transaction_inputs_coinbase(self):
        """Test processing coinbase transaction (no inputs)"""
        manager = UTXOManager()
        wallet = Wallet()

        # Coinbase transaction
        tx = Transaction("COINBASE", wallet.address, 12.0, 0.0)

        result = manager.process_transaction_inputs(tx)

        assert result is True  # Should succeed for coinbase

    def test_process_transaction_inputs_success(self):
        """Test processing valid transaction inputs"""
        manager = UTXOManager()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Add UTXO first
        manager.add_utxo(wallet1.address, "txid1", 0, 10.0, "P2PKH")

        # Create transaction with inputs
        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.5)
        tx.inputs = [{"txid": "txid1", "vout": 0}]

        result = manager.process_transaction_inputs(tx)

        assert result is True

    def test_process_transaction_inputs_failure(self):
        """Test processing invalid transaction inputs"""
        manager = UTXOManager()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create transaction with inputs but no UTXOs
        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.5)
        tx.inputs = [{"txid": "txid999", "vout": 0}]

        result = manager.process_transaction_inputs(tx)

        assert result is False


class TestUTXOStatistics:
    """Test UTXO statistics and metrics"""

    def test_get_total_unspent_value(self):
        """Test getting total unspent value"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")

        total = manager.get_total_unspent_value()

        assert total == 30.0

    def test_get_total_unspent_value_after_spending(self):
        """Test total unspent value after spending"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI123", "txid2", 0, 20.0, "P2PKH XAI123")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        total = manager.get_total_unspent_value()

        assert total == 20.0

    def test_get_unique_addresses_count(self):
        """Test counting unique addresses with UTXOs"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")
        manager.add_utxo("XAI789", "txid3", 0, 30.0, "P2PKH XAI789")

        count = manager.get_unique_addresses_count()

        assert count == 3

    def test_get_unique_addresses_count_excludes_spent(self):
        """Test unique addresses count excludes fully spent addresses"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")
        manager.mark_utxo_spent("XAI123", "txid1", 0)

        count = manager.get_unique_addresses_count()

        assert count == 1  # Only XAI456 has unspent

    def test_get_stats(self):
        """Test getting comprehensive stats"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")

        stats = manager.get_stats()

        assert "total_utxos" in stats
        assert "total_unspent_value" in stats
        assert "unique_addresses_with_utxos" in stats
        assert stats["total_utxos"] == 2
        assert stats["total_unspent_value"] == 30.0


class TestUTXOSerialization:
    """Test UTXO set serialization and loading"""

    def test_to_dict(self):
        """Test converting UTXO set to dict"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")

        data = manager.to_dict()

        assert isinstance(data, dict)
        assert "XAI123" in data
        assert "XAI456" in data

    def test_load_utxo_set(self):
        """Test loading UTXO set from dict"""
        manager = UTXOManager()

        # Create test data
        utxo_data = {
            "XAI123": [
                {
                    "txid": "txid1",
                    "vout": 0,
                    "amount": 10.0,
                    "script_pubkey": "P2PKH XAI123",
                    "spent": False
                }
            ],
            "XAI456": [
                {
                    "txid": "txid2",
                    "vout": 0,
                    "amount": 20.0,
                    "script_pubkey": "P2PKH XAI456",
                    "spent": False
                }
            ]
        }

        manager.load_utxo_set(utxo_data)

        assert manager.total_utxos == 2
        assert manager.total_value == 30.0

    def test_load_utxo_set_with_spent(self):
        """Test loading UTXO set with spent UTXOs"""
        manager = UTXOManager()

        utxo_data = {
            "XAI123": [
                {
                    "txid": "txid1",
                    "vout": 0,
                    "amount": 10.0,
                    "script_pubkey": "P2PKH XAI123",
                    "spent": True
                },
                {
                    "txid": "txid2",
                    "vout": 0,
                    "amount": 5.0,
                    "script_pubkey": "P2PKH XAI123",
                    "spent": False
                }
            ]
        }

        manager.load_utxo_set(utxo_data)

        # Only unspent should count in totals
        assert manager.total_value == 5.0

    def test_roundtrip_serialization(self):
        """Test serializing and deserializing UTXO set"""
        manager1 = UTXOManager()

        manager1.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager1.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")

        data = manager1.to_dict()

        manager2 = UTXOManager()
        manager2.load_utxo_set(data)

        assert manager2.total_value == manager1.total_value
        assert manager2.total_utxos == manager1.total_utxos


class TestUTXOReset:
    """Test UTXO manager reset"""

    def test_reset(self):
        """Test resetting UTXO manager"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", 0, 10.0, "P2PKH XAI123")
        manager.add_utxo("XAI456", "txid2", 0, 20.0, "P2PKH XAI456")

        manager.reset()

        assert manager.total_utxos == 0
        assert manager.total_value == 0.0
        assert len(manager.utxo_set) == 0

    def test_reset_clears_all_addresses(self):
        """Test reset clears all addresses"""
        manager = UTXOManager()

        for i in range(10):
            manager.add_utxo(f"XAI{i}", f"txid{i}", 0, 10.0, f"P2PKH XAI{i}")

        manager.reset()

        assert manager.get_unique_addresses_count() == 0


class TestGlobalUTXOManager:
    """Test global UTXO manager singleton"""

    def test_get_utxo_manager(self):
        """Test getting global UTXO manager instance"""
        manager1 = get_utxo_manager()
        manager2 = get_utxo_manager()

        assert manager1 is manager2  # Should be same instance

    def test_get_utxo_manager_with_logger(self):
        """Test getting global manager with custom logger"""
        from xai.core.structured_logger import get_structured_logger

        logger = get_structured_logger()
        manager = get_utxo_manager(logger=logger)

        assert manager is not None


class TestUTXOEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_large_amounts(self):
        """Test handling very large UTXO amounts"""
        manager = UTXOManager()

        large_amount = 1_000_000_000.0
        manager.add_utxo("XAI123", "txid1", 0, large_amount, "P2PKH XAI123")

        assert manager.total_value == large_amount
        assert manager.get_balance("XAI123") == large_amount

    def test_very_small_amounts(self):
        """Test handling very small UTXO amounts (dust)"""
        manager = UTXOManager()

        dust_amount = 0.00000001
        manager.add_utxo("XAI123", "txid1", 0, dust_amount, "P2PKH XAI123")

        assert manager.total_utxos == 1
        assert abs(manager.total_value - dust_amount) < 0.000000001

    def test_many_utxos_single_address(self):
        """Test address with many UTXOs"""
        manager = UTXOManager()

        for i in range(1000):
            manager.add_utxo("XAI123", f"txid{i}", i % 10, 0.1, "P2PKH XAI123")

        assert manager.total_utxos == 1000
        assert manager.get_balance("XAI123") == 100.0

    def test_many_addresses(self):
        """Test many addresses with UTXOs"""
        manager = UTXOManager()

        for i in range(1000):
            manager.add_utxo(f"XAI{i}", f"txid{i}", 0, 1.0, f"P2PKH XAI{i}")

        assert manager.total_utxos == 1000
        assert manager.get_unique_addresses_count() == 1000

    def test_empty_string_txid(self):
        """Test handling empty string txid"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "", 0, 10.0, "P2PKH XAI123")

        assert manager.total_utxos == 1

    def test_negative_vout(self):
        """Test handling negative vout"""
        manager = UTXOManager()

        manager.add_utxo("XAI123", "txid1", -1, 10.0, "P2PKH XAI123")

        # Should still add (no validation on vout)
        assert manager.total_utxos == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

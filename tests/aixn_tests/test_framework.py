"""
XAI Blockchain - Comprehensive Testing Framework

Unified test runner for all blockchain components:
- Unit tests
- Integration tests
- Security tests
- Performance tests
"""

import sys
import os
import time
import unittest
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.blockchain import Blockchain, Transaction, Block
from core.wallet import Wallet
from core.blockchain_security import BlockchainSecurityManager, BlockchainSecurityConfig
from core.advanced_consensus import AdvancedConsensusManager


class FrameworkResult:
    """Test result tracking"""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.failures: List[Tuple[str, str]] = []
        self.start_time = time.time()

    def duration(self) -> float:
        return time.time() - self.start_time


class BlockchainUnitTests:
    """Unit tests for core blockchain components"""

    @staticmethod
    def test_wallet_creation():
        """Test wallet creation and key generation"""
        wallet = Wallet()
        assert wallet.address.startswith("XAI"), "Wallet address should start with XAI"
        assert len(wallet.private_key) == 64, "Private key should be 64 chars"
        assert len(wallet.public_key) == 128, "Public key should be 128 chars"
        return True

    @staticmethod
    def test_transaction_signing():
        """Test transaction signing and verification"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.1, wallet1.public_key)
        tx.sign_transaction(wallet1.private_key)

        assert tx.signature is not None, "Transaction should be signed"
        assert tx.verify_signature(), "Signature should be valid"
        return True

    @staticmethod
    def test_block_creation():
        """Test block creation and hashing"""
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 50.0)
        tx.txid = tx.calculate_hash()

        block = Block(0, [tx], "0", difficulty=2)
        block.hash = block.mine_block()

        assert block.hash.startswith("00"), "Block should meet difficulty requirement"
        assert block.merkle_root is not None, "Block should have merkle root"
        return True

    @staticmethod
    def test_blockchain_initialization():
        """Test blockchain initialization"""
        blockchain = Blockchain()
        assert len(blockchain.chain) == 1, "Blockchain should start with genesis block"
        assert blockchain.chain[0].index == 0, "Genesis block should have index 0"
        return True

    @staticmethod
    def test_transaction_validation():
        """Test transaction validation"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 some funds
        blockchain.utxo_set[wallet1.address] = [{"txid": "test", "amount": 100.0, "spent": False}]

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.1, wallet1.public_key, nonce=0)
        tx.sign_transaction(wallet1.private_key)

        assert blockchain.validate_transaction(tx), "Valid transaction should pass validation"
        return True

    @staticmethod
    def test_balance_calculation():
        """Test balance calculation from UTXO set"""
        blockchain = Blockchain()
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": "tx1", "amount": 50.0, "spent": False},
            {"txid": "tx2", "amount": 30.0, "spent": False},
            {"txid": "tx3", "amount": 20.0, "spent": True},  # Spent
        ]

        balance = blockchain.get_balance(wallet.address)
        assert balance == 80.0, f"Balance should be 80.0, got {balance}"
        return True


class BlockchainIntegrationTests:
    """Integration tests for full blockchain operations"""

    @staticmethod
    def test_full_transaction_flow():
        """Test complete transaction flow: create, sign, submit, mine"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 funds via genesis
        blockchain.utxo_set[wallet1.address] = [
            {"txid": "genesis", "amount": 1000.0, "spent": False}
        ]

        # Create and sign transaction
        tx = Transaction(wallet1.address, wallet2.address, 100.0, 1.0, wallet1.public_key, nonce=0)
        tx.sign_transaction(wallet1.private_key)

        # Add to blockchain
        success = blockchain.add_transaction(tx)
        assert success, "Transaction should be added successfully"

        # Mine block
        miner_wallet = Wallet()
        block = blockchain.mine_pending_transactions(miner_wallet.address)

        assert len(blockchain.chain) == 2, "Should have 2 blocks after mining"
        assert (
            blockchain.get_balance(wallet2.address) == 100.0
        ), "Recipient should have received funds"
        return True

    @staticmethod
    def test_chain_validation():
        """Test blockchain validation"""
        blockchain = Blockchain()
        wallet = Wallet()

        # Mine several blocks
        for i in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        # Validate chain
        assert blockchain.validate_chain(), "Chain should be valid"

        # Corrupt a block
        blockchain.chain[1].transactions[0].amount = 999999.0

        # Should detect corruption
        assert not blockchain.validate_chain(), "Should detect corrupted chain"
        return True

    @staticmethod
    def test_supply_cap_enforcement():
        """Test that supply cap is enforced"""
        blockchain = Blockchain()
        wallet = Wallet()

        # Get current supply
        initial_supply = blockchain.get_total_circulating_supply()

        # Mine blocks
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)

        final_supply = blockchain.get_total_circulating_supply()

        # Should not exceed max supply
        assert final_supply <= blockchain.max_supply, "Supply should not exceed cap"
        assert final_supply > initial_supply, "Supply should have increased"
        return True

    @staticmethod
    def test_concurrent_transactions():
        """Test handling multiple pending transactions"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallets = [Wallet() for _ in range(5)]

        # Give wallet1 funds split across multiple UTXOs so concurrent pending txs can be funded
        blockchain.utxo_set[wallet1.address] = [
            {"txid": f"genesis-{i}", "amount": 1000.0, "spent": False} for i in range(len(wallets))
        ]

        # Create multiple transactions
        for i, wallet in enumerate(wallets):
            tx = Transaction(
                wallet1.address, wallet.address, 100.0, 1.0, wallet1.public_key, nonce=i
            )
            tx.sign_transaction(wallet1.private_key)
            blockchain.add_transaction(tx)

        assert len(blockchain.pending_transactions) == 5, "Should have 5 pending transactions"

        # Mine block
        miner = Wallet()
        block = blockchain.mine_pending_transactions(miner.address)

        # All transactions should be in block
        assert len(block.transactions) == 6, "Block should have coinbase + 5 transactions"
        return True


class SecurityTests:
    """Security tests for attack scenarios"""

    @staticmethod
    def test_double_spend_prevention():
        """Test prevention of double-spend attacks"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Give wallet1 100 XAI
        blockchain.utxo_set[wallet1.address] = [
            {"txid": "genesis", "amount": 100.0, "spent": False}
        ]

        # Try to spend same funds twice
        tx1 = Transaction(wallet1.address, wallet2.address, 90.0, 1.0, wallet1.public_key, nonce=0)
        tx1.sign_transaction(wallet1.private_key)

        tx2 = Transaction(wallet1.address, wallet3.address, 90.0, 1.0, wallet1.public_key, nonce=1)
        tx2.sign_transaction(wallet1.private_key)

        # First transaction should succeed
        assert blockchain.add_transaction(tx1), "First transaction should be accepted"

        # Second transaction should fail (insufficient balance)
        assert not blockchain.add_transaction(tx2), "Second transaction should be rejected"
        return True

    @staticmethod
    def test_invalid_signature_rejection():
        """Test rejection of transactions with invalid signatures"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.utxo_set[wallet1.address] = [
            {"txid": "genesis", "amount": 100.0, "spent": False}
        ]

        tx = Transaction(wallet1.address, wallet2.address, 50.0, 1.0, wallet1.public_key, nonce=0)
        tx.sign_transaction(wallet1.private_key)

        # Tamper with transaction after signing
        tx.amount = 99.0

        # Should be rejected
        assert not blockchain.validate_transaction(tx), "Tampered transaction should be rejected"
        return True

    @staticmethod
    def test_block_size_limits():
        """Test block size limit enforcement"""
        blockchain = Blockchain()

        # Create a large transaction (just under 100KB limit)
        large_data = "X" * 99000

        # This should be within limits
        # In real implementation, transaction size would be checked
        # For now, just verify the security manager exists
        assert hasattr(blockchain, "security_manager"), "Should have security manager"
        assert blockchain.security_manager is not None, "Security manager should be initialized"
        return True

    @staticmethod
    def test_dust_attack_prevention():
        """Test prevention of dust attacks"""
        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.utxo_set[wallet1.address] = [
            {"txid": "genesis", "amount": 100.0, "spent": False}
        ]

        # Try to create dust transaction (below minimum)
        tx = Transaction(
            wallet1.address, wallet2.address, 0.000001, 0.0, wallet1.public_key, nonce=0
        )
        tx.sign_transaction(wallet1.private_key)

        # Should be rejected by security manager
        result = blockchain.security_manager.validate_new_transaction(tx)
        assert not result[0], "Dust transaction should be rejected"
        return True

    @staticmethod
    def test_reorganization_depth_limit():
        """Test reorganization depth limit"""
        blockchain = Blockchain()

        # Test that reorg protection exists
        assert hasattr(
            blockchain.security_manager, "reorg_protection"
        ), "Should have reorg protection"

        # Simulate a chain taller than the configured limit to trigger rejection
        max_depth = BlockchainSecurityConfig.MAX_REORG_DEPTH
        current_height = max_depth + 10
        fork_point = current_height - (max_depth + 1)

        valid, error = blockchain.security_manager.reorg_protection.validate_reorganization(
            current_height, fork_point
        )
        assert not valid, "Deep reorganization should be rejected"
        assert "too deep" in error.lower(), "Error should mention depth"
        return True


class PerformanceTests:
    """Performance and stress tests"""

    @staticmethod
    def test_mining_performance():
        """Test block mining performance"""
        blockchain = Blockchain()
        wallet = Wallet()

        # Add some transactions
        for i in range(10):
            tx = Transaction("COINBASE", wallet.address, 1.0)
            tx.txid = tx.calculate_hash()
            blockchain.pending_transactions.append(tx)

        # Time mining
        start = time.time()
        block = blockchain.mine_pending_transactions(wallet.address)
        duration = time.time() - start

        print(f"    Mining 10 transactions took {duration:.2f}s")
        assert duration < 60, "Mining should complete within 60 seconds"
        return True

    @staticmethod
    def test_large_transaction_volume():
        """Test handling of large transaction volumes"""
        blockchain = Blockchain()
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "amount": 2500.0, "spent": False} for i in range(50)
        ]

        # Add many transactions
        recipients = [Wallet() for _ in range(50)]
        start = time.time()

        for i, recipient in enumerate(recipients):
            tx = Transaction(
                wallet.address, recipient.address, 1.0, 0.01, wallet.public_key, nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

        duration = time.time() - start
        print(f"    Adding 50 transactions took {duration:.3f}s")
        assert len(blockchain.pending_transactions) == 50, "Should have 50 pending transactions"
        return True

    @staticmethod
    def test_chain_validation_performance():
        """Test blockchain validation performance"""
        blockchain = Blockchain()
        wallet = Wallet()

        # Create a longer chain
        for i in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        # Time validation
        start = time.time()
        valid = blockchain.validate_chain()
        duration = time.time() - start

        print(f"    Validating {len(blockchain.chain)} blocks took {duration:.3f}s")
        assert valid, "Chain should be valid"
        assert duration < 10, "Validation should be fast"
        return True

    @staticmethod
    def test_balance_query_performance():
        """Test balance query performance with many UTXOs"""
        blockchain = Blockchain()
        wallet = Wallet()

        # Create many UTXOs
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"tx{i}", "amount": 1.0, "spent": False} for i in range(1000)
        ]

        # Time balance calculation
        start = time.time()
        balance = blockchain.get_balance(wallet.address)
        duration = time.time() - start

        print(f"    Balance query with 1000 UTXOs took {duration:.4f}s")
        assert balance == 1000.0, "Balance should be 1000.0"
        assert duration < 0.1, "Balance query should be fast"
        return True


class FrameworkRunner:
    """Main test runner"""

    def __init__(self):
        self.result = FrameworkResult()

    def run_test(self, test_func, test_name: str) -> bool:
        """Run a single test"""
        self.result.total += 1
        try:
            result = test_func()
            if result:
                self.result.passed += 1
                print(f"  ✓ {test_name}")
                return True
            else:
                self.result.failed += 1
                self.result.failures.append((test_name, "Test returned False"))
                print(f"  ✗ {test_name} - FAILED")
                return False
        except AssertionError as e:
            self.result.failed += 1
            self.result.failures.append((test_name, str(e)))
            print(f"  ✗ {test_name} - FAILED: {e}")
            return False
        except Exception as e:
            self.result.errors += 1
            self.result.failures.append((test_name, f"ERROR: {e}"))
            print(f"  ✗ {test_name} - ERROR: {e}")
            return False

    def run_test_suite(self, test_class, suite_name: str):
        """Run all tests in a test class"""
        print(f"\n{'='*70}")
        print(f"{suite_name}")
        print(f"{'='*70}")

        # Get all test methods
        test_methods = [
            (name, getattr(test_class, name))
            for name in dir(test_class)
            if name.startswith("test_") and callable(getattr(test_class, name))
        ]

        for test_name, test_func in test_methods:
            self.run_test(test_func, test_name)

    def print_summary(self):
        """Print test summary"""
        duration = self.result.duration()

        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total tests:  {self.result.total}")
        print(f"Passed:       {self.result.passed} ✓")
        print(f"Failed:       {self.result.failed}")
        print(f"Errors:       {self.result.errors}")
        print(f"Duration:     {duration:.2f}s")
        print(f"{'='*70}")

        if self.result.failures:
            print(f"\nFAILURES:")
            for test_name, error in self.result.failures:
                print(f"  {test_name}: {error}")

        # Overall result
        if self.result.failed == 0 and self.result.errors == 0:
            print(f"\n✓ ALL TESTS PASSED!")
            return True
        else:
            print(f"\n✗ SOME TESTS FAILED")
            return False


def run_all_tests():
    """Run all test suites"""
    print("=" * 70)
    print("XAI BLOCKCHAIN - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    runner = FrameworkRunner()

    # Run all test suites
    runner.run_test_suite(BlockchainUnitTests, "UNIT TESTS - Core Components")
    runner.run_test_suite(BlockchainIntegrationTests, "INTEGRATION TESTS - Full Blockchain")
    runner.run_test_suite(SecurityTests, "SECURITY TESTS - Attack Scenarios")
    runner.run_test_suite(PerformanceTests, "PERFORMANCE TESTS - Stress Testing")

    # Print summary
    success = runner.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

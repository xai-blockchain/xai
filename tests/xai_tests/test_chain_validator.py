"""
XAI Blockchain - Chain Validator Tests

Unit tests for chain validation system
"""

import unittest
import sys
import os
import json
import hashlib
import time

from xai.core.chain_validator import (
    ChainValidator,
    ValidationReport,
    ValidationIssue,
    validate_blockchain_on_startup,
)


class TestValidationReport(unittest.TestCase):
    """Test ValidationReport functionality"""

    def test_create_report(self):
        """Test creating a validation report"""
        report = ValidationReport(
            success=True, total_blocks=100, total_transactions=500, validation_time=1.5
        )

        self.assertTrue(report.success)
        self.assertEqual(report.total_blocks, 100)
        self.assertEqual(report.total_transactions, 500)
        self.assertEqual(report.validation_time, 1.5)

    def test_add_issue(self):
        """Test adding issues to report"""
        report = ValidationReport(
            success=False, total_blocks=100, total_transactions=500, validation_time=1.5
        )

        report.add_issue("critical", 50, "block_hash", "Block hash is invalid")

        self.assertEqual(len(report.issues), 1)
        self.assertEqual(len(report.get_critical_issues()), 1)
        self.assertEqual(len(report.get_error_issues()), 0)

    def test_report_to_dict(self):
        """Test converting report to dictionary"""
        report = ValidationReport(
            success=True, total_blocks=100, total_transactions=500, validation_time=1.5
        )

        report.add_issue("warning", 10, "timestamp", "Future timestamp")

        report_dict = report.to_dict()

        self.assertIn("success", report_dict)
        self.assertIn("total_blocks", report_dict)
        self.assertIn("issues", report_dict)
        self.assertEqual(report_dict["issues"]["warnings"], 1)


class TestChainValidator(unittest.TestCase):
    """Test ChainValidator functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = ChainValidator(max_supply=121000000.0, verbose=False)

    def test_validator_creation(self):
        """Test creating a validator"""
        self.assertEqual(self.validator.max_supply, 121000000.0)
        self.assertFalse(self.validator.verbose)

    def test_calculate_merkle_root_empty(self):
        """Test merkle root calculation with no transactions"""
        merkle_root = self.validator._calculate_merkle_root([])
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(merkle_root, expected)

    def test_calculate_merkle_root_single(self):
        """Test merkle root calculation with single transaction"""
        transactions = [{"txid": "abc123"}]
        merkle_root = self.validator._calculate_merkle_root(transactions)
        self.assertEqual(merkle_root, "abc123")

    def test_calculate_merkle_root_multiple(self):
        """Test merkle root calculation with multiple transactions"""
        transactions = [{"txid": "tx1"}, {"txid": "tx2"}]
        merkle_root = self.validator._calculate_merkle_root(transactions)

        # Calculate expected
        combined = "tx1" + "tx2"
        expected = hashlib.sha256(combined.encode()).hexdigest()

        self.assertEqual(merkle_root, expected)

    def test_validate_empty_chain(self):
        """Test validating empty chain"""
        blockchain_data = {"chain": []}

        report = self.validator.validate_chain(blockchain_data)

        self.assertFalse(report.success)
        self.assertEqual(len(report.get_critical_issues()), 1)
        self.assertEqual(report.get_critical_issues()[0].issue_type, "empty_chain")

    def test_validate_genesis_block_index(self):
        """Test genesis block index validation"""
        genesis = {
            "index": 1,  # Invalid - should be 0
            "previous_hash": "0",
            "hash": "abc123",
            "transactions": [],
            "merkle_root": hashlib.sha256(b"").hexdigest(),
            "nonce": 0,
            "timestamp": time.time(),
            "difficulty": 4,
        }

        blockchain_data = {"chain": [genesis]}

        report = self.validator.validate_chain(blockchain_data)

        self.assertFalse(report.genesis_valid)
        # Should have issue about genesis index
        genesis_issues = [i for i in report.issues if i.issue_type == "genesis_index"]
        self.assertGreater(len(genesis_issues), 0)

    def test_validate_genesis_previous_hash(self):
        """Test genesis block previous_hash validation"""
        genesis = {
            "index": 0,
            "previous_hash": "invalid",  # Should be "0"
            "hash": "abc123",
            "transactions": [],
            "merkle_root": hashlib.sha256(b"").hexdigest(),
            "nonce": 0,
            "timestamp": time.time(),
            "difficulty": 4,
        }

        blockchain_data = {"chain": [genesis]}

        report = self.validator.validate_chain(blockchain_data)

        self.assertFalse(report.genesis_valid)
        # Should have issue about genesis previous_hash
        genesis_issues = [i for i in report.issues if i.issue_type == "genesis_previous_hash"]
        self.assertGreater(len(genesis_issues), 0)

    def test_validate_supply_cap(self):
        """Test supply cap validation"""
        # Test valid supply
        result = self.validator._validate_supply_cap(50000000.0)
        self.assertTrue(result)

        # Test exceeded supply
        result = self.validator._validate_supply_cap(150000000.0)
        self.assertFalse(result)

        # Check that issue was added
        supply_issues = [
            i for i in self.validator.report.issues if i.issue_type == "supply_cap_exceeded"
        ]
        self.assertGreater(len(supply_issues), 0)


class TestValidationFunctions(unittest.TestCase):
    """Test validation utility functions"""

    def test_validate_blockchain_on_startup(self):
        """Test the main validation entry point"""
        # Create minimal valid blockchain
        genesis_tx = {
            "txid": hashlib.sha256(b"genesis").hexdigest(),
            "sender": "COINBASE",
            "recipient": "GENESIS",
            "amount": 1000000.0,
            "fee": 0.0,
            "timestamp": time.time(),
            "signature": None,
            "public_key": None,
            "tx_type": "normal",
            "nonce": None,
        }

        merkle_root = hashlib.sha256(b"genesis").hexdigest()

        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": [genesis_tx],
            "previous_hash": "0",
            "merkle_root": merkle_root,
            "nonce": 0,
            "difficulty": 2,
        }

        # Calculate hash
        block_data = {
            "index": genesis_block["index"],
            "timestamp": genesis_block["timestamp"],
            "transactions": genesis_block["transactions"],
            "previous_hash": genesis_block["previous_hash"],
            "merkle_root": genesis_block["merkle_root"],
            "nonce": genesis_block["nonce"],
        }
        block_string = json.dumps(block_data, sort_keys=True)
        genesis_hash = hashlib.sha256(block_string.encode()).hexdigest()

        # Add leading zeros to meet difficulty
        genesis_block["nonce"] = 0
        while True:
            block_data["nonce"] = genesis_block["nonce"]
            block_string = json.dumps(block_data, sort_keys=True)
            test_hash = hashlib.sha256(block_string.encode()).hexdigest()
            if test_hash.startswith("0" * genesis_block["difficulty"]):
                genesis_hash = test_hash
                break
            genesis_block["nonce"] += 1

            # Prevent infinite loop in tests
            if genesis_block["nonce"] > 100000:
                self.fail("Could not mine genesis block in reasonable time")

        genesis_block["hash"] = genesis_hash

        blockchain_data = {"chain": [genesis_block], "pending_transactions": [], "difficulty": 2}

        # Validate
        is_valid, report = validate_blockchain_on_startup(
            blockchain_data, max_supply=121000000.0, verbose=False
        )

        # Should pass basic validation
        self.assertTrue(report.genesis_valid)
        self.assertTrue(report.chain_integrity)
        self.assertTrue(report.pow_valid)
        self.assertTrue(report.merkle_roots_valid)


class TestUTXOReconstruction(unittest.TestCase):
    """Test UTXO set reconstruction"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = ChainValidator(max_supply=121000000.0, verbose=False)

    def test_rebuild_utxo_set_empty(self):
        """Test rebuilding UTXO set from empty chain"""
        chain = []
        utxo_set, total_supply = self.validator._rebuild_utxo_set(chain)

        self.assertEqual(len(utxo_set), 0)
        self.assertEqual(total_supply, 0.0)

    def test_rebuild_utxo_set_genesis(self):
        """Test rebuilding UTXO set from genesis block"""
        genesis_tx = {
            "txid": "genesis_tx",
            "sender": "COINBASE",
            "recipient": "GENESIS",
            "amount": 1000000.0,
            "fee": 0.0,
        }

        genesis_block = {"index": 0, "transactions": [genesis_tx]}

        chain = [genesis_block]
        utxo_set, total_supply = self.validator._rebuild_utxo_set(chain)

        self.assertEqual(len(utxo_set), 1)
        self.assertIn("GENESIS", utxo_set)
        self.assertEqual(total_supply, 1000000.0)

    def test_rebuild_utxo_set_with_spend(self):
        """Test rebuilding UTXO set with a spend"""
        # Genesis
        genesis_tx = {
            "txid": "genesis_tx",
            "sender": "COINBASE",
            "recipient": "ADDR_A",
            "amount": 1000.0,
            "fee": 0.0,
        }

        genesis_block = {"index": 0, "transactions": [genesis_tx]}

        # Block 1 - ADDR_A sends to ADDR_B
        tx1 = {
            "txid": "tx1",
            "sender": "ADDR_A",
            "recipient": "ADDR_B",
            "amount": 500.0,
            "fee": 1.0,
        }

        coinbase_tx = {
            "txid": "coinbase1",
            "sender": "COINBASE",
            "recipient": "MINER",
            "amount": 12.0,
            "fee": 0.0,
        }

        block1 = {"index": 1, "transactions": [coinbase_tx, tx1]}

        chain = [genesis_block, block1]
        utxo_set, total_supply = self.validator._rebuild_utxo_set(chain)

        # ADDR_A should have remaining balance
        # ADDR_B should have received amount
        # MINER should have coinbase
        self.assertIn("ADDR_A", utxo_set)
        self.assertIn("ADDR_B", utxo_set)
        self.assertIn("MINER", utxo_set)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestValidationReport))
    suite.addTests(loader.loadTestsFromTestCase(TestChainValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestUTXOReconstruction))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

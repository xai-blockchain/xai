from __future__ import annotations

"""
Microbenchmark tests for performance-critical operations.

Tests signature verification, Merkle tree operations, UTXO lookups,
and block serialization performance. Reports timing statistics for
each operation category.
"""

import pytest
import time
import json
import statistics

from xai.core.wallet import Wallet
from xai.core.transaction import Transaction
from xai.core.transactions.utxo_manager import UTXOManager
from xai.core.blockchain import Blockchain
from xai.core.security.crypto_utils import sign_message_hex, verify_signature_hex, derive_public_key_hex

class TestSignatureVerificationBenchmarks:
    """Microbenchmarks for ECDSA signature operations."""

    def _generate_signed_message(self, wallet: Wallet) -> tuple[str, str, str]:
        """Generate a signed message for testing."""
        message = f"test_message_{time.time()}".encode()
        signature = sign_message_hex(wallet.private_key, message)
        return wallet.public_key, message, signature

    def test_single_signature_verification_timing(self, tmp_path):
        """Benchmark single signature verification."""
        wallet = Wallet()
        pub_key, message, signature = self._generate_signed_message(wallet)

        # Warmup
        for _ in range(10):
            verify_signature_hex(pub_key, message, signature)

        # Benchmark
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = verify_signature_hex(pub_key, message, signature)
            assert result
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nSingle signature verification: {avg_us:.2f} microseconds")
        assert avg_us < 10_000, f"Verification too slow: {avg_us} us"

    def test_batch_signature_verification_timing(self, tmp_path):
        """Benchmark batch signature verification throughput."""
        # Prepare 100 unique signatures
        wallets = [Wallet() for _ in range(100)]
        signatures = [self._generate_signed_message(w) for w in wallets]

        # Benchmark batch verification
        start = time.perf_counter()
        for pub_key, message, signature in signatures:
            result = verify_signature_hex(pub_key, message, signature)
            assert result
        elapsed = time.perf_counter() - start

        verifications_per_second = 100 / elapsed
        print(f"\nBatch verification: {verifications_per_second:.2f} verifications/second")
        assert verifications_per_second > 10, "Batch verification too slow"

    def test_signature_verification_with_varying_message_sizes(self, tmp_path):
        """Benchmark signature verification with different message sizes."""
        wallet = Wallet()
        message_sizes = [32, 256, 1024, 4096, 16384]
        results = {}

        for size in message_sizes:
            message = b"x" * size
            signature = sign_message_hex(wallet.private_key, message)

            # Benchmark
            iterations = 50
            start = time.perf_counter()
            for _ in range(iterations):
                verify_signature_hex(wallet.public_key, message, signature)
            elapsed = time.perf_counter() - start

            avg_us = (elapsed / iterations) * 1_000_000
            results[size] = avg_us

        print("\nSignature verification by message size:")
        for size, timing in results.items():
            print(f"  {size} bytes: {timing:.2f} us")

        # All sizes should verify in reasonable time
        assert all(t < 20_000 for t in results.values())

    def test_transaction_signature_verification_timing(self, tmp_path):
        """Benchmark transaction signature verification specifically."""
        wallet = Wallet()
        recipient = Wallet()

        # Create and sign transactions
        transactions = []
        for i in range(100):
            tx = Transaction(wallet.address, recipient.address, float(i + 1), 0.01)
            tx.timestamp = 1000000 + i
            tx.public_key = wallet.public_key
            tx.sign_transaction(wallet.private_key)
            transactions.append(tx)

        # Benchmark verification
        start = time.perf_counter()
        for tx in transactions:
            result = tx.verify_signature()
            assert result
        elapsed = time.perf_counter() - start

        verifications_per_second = 100 / elapsed
        avg_ms = (elapsed / 100) * 1000
        print(f"\nTransaction signature verification: {avg_ms:.2f} ms/tx ({verifications_per_second:.2f}/s)")
        assert verifications_per_second > 10

class TestUTXOLookupBenchmarks:
    """Microbenchmarks for UTXO manager operations."""

    def test_utxo_add_timing(self, tmp_path):
        """Benchmark UTXO addition performance."""
        manager = UTXOManager()

        # Benchmark adding UTXOs
        iterations = 10000
        start = time.perf_counter()
        for i in range(iterations):
            manager.add_utxo(f"XAI{i % 1000:040d}", f"txid{i:064x}", i % 10, 1.0, "P2PKH")
        elapsed = time.perf_counter() - start

        adds_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nUTXO add: {avg_us:.2f} us/add ({adds_per_second:.0f}/s)")
        assert adds_per_second > 1000

    def test_utxo_lookup_timing(self, tmp_path):
        """Benchmark UTXO lookup performance."""
        manager = UTXOManager()

        # Populate with UTXOs
        addresses = [f"XAI{i:040d}" for i in range(1000)]
        for i, addr in enumerate(addresses):
            for j in range(10):
                manager.add_utxo(addr, f"txid{i:06d}{j:02d}", j, 1.0, "P2PKH")

        # Benchmark lookups
        iterations = 10000
        start = time.perf_counter()
        for i in range(iterations):
            addr = addresses[i % 1000]
            manager.get_utxos_for_address(addr)
        elapsed = time.perf_counter() - start

        lookups_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nUTXO lookup: {avg_us:.2f} us/lookup ({lookups_per_second:.0f}/s)")
        assert lookups_per_second > 10000

    def test_utxo_balance_calculation_timing(self, tmp_path):
        """Benchmark balance calculation with many UTXOs."""
        manager = UTXOManager()

        # Create address with many UTXOs
        addr = "XAI" + "1" * 40
        for i in range(1000):
            manager.add_utxo(addr, f"txid{i:064x}", 0, 1.0, "P2PKH")

        # Benchmark balance calculation
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            balance = manager.get_balance(addr)
            assert balance == 1000.0
        elapsed = time.perf_counter() - start

        calcs_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nBalance calculation (1000 UTXOs): {avg_us:.2f} us/calc ({calcs_per_second:.0f}/s)")
        assert calcs_per_second > 100

    def test_utxo_mark_spent_timing(self, tmp_path):
        """Benchmark marking UTXOs as spent."""
        manager = UTXOManager()

        # Create UTXOs
        addr = "XAI" + "1" * 40
        for i in range(5000):
            manager.add_utxo(addr, f"txid{i:064x}", 0, 1.0, "P2PKH")

        # Benchmark marking spent
        iterations = 5000
        start = time.perf_counter()
        for i in range(iterations):
            manager.mark_utxo_spent(addr, f"txid{i:064x}", 0)
        elapsed = time.perf_counter() - start

        marks_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nUTXO mark spent: {avg_us:.2f} us/mark ({marks_per_second:.0f}/s)")
        assert marks_per_second > 1000

    def test_utxo_find_spendable_timing(self, tmp_path):
        """Benchmark finding spendable UTXOs."""
        manager = UTXOManager()

        # Create UTXOs of varying amounts
        addr = "XAI" + "1" * 40
        for i in range(1000):
            manager.add_utxo(addr, f"txid{i:064x}", 0, float(i % 10 + 1), "P2PKH")

        # Benchmark finding spendable
        iterations = 1000
        start = time.perf_counter()
        for i in range(iterations):
            amount = float((i % 50) + 1)
            manager.find_spendable_utxos(addr, amount)
        elapsed = time.perf_counter() - start

        finds_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nFind spendable UTXOs: {avg_us:.2f} us/find ({finds_per_second:.0f}/s)")
        assert finds_per_second > 100

    def test_utxo_merkle_root_timing(self, tmp_path):
        """Benchmark Merkle root calculation."""
        manager = UTXOManager()

        # Populate with UTXOs
        for i in range(1000):
            manager.add_utxo(f"XAI{i:040d}", f"txid{i:064x}", 0, 1.0, "P2PKH")

        # Benchmark Merkle root calculation
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            root = manager.calculate_merkle_root()
            assert len(root) == 64
        elapsed = time.perf_counter() - start

        calcs_per_second = iterations / elapsed
        avg_ms = (elapsed / iterations) * 1000
        print(f"\nMerkle root (1000 UTXOs): {avg_ms:.2f} ms/calc ({calcs_per_second:.2f}/s)")
        assert avg_ms < 1000

    def test_utxo_consistency_check_timing(self, tmp_path):
        """Benchmark UTXO consistency verification."""
        manager = UTXOManager()

        # Populate with UTXOs
        for i in range(10000):
            manager.add_utxo(f"XAI{i % 1000:040d}", f"txid{i:064x}", i % 10, 1.0, "P2PKH")

        # Benchmark consistency check
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = manager.verify_utxo_consistency()
            assert result["is_consistent"]
        elapsed = time.perf_counter() - start

        checks_per_second = iterations / elapsed
        avg_ms = (elapsed / iterations) * 1000
        print(f"\nConsistency check (10000 UTXOs): {avg_ms:.2f} ms/check ({checks_per_second:.2f}/s)")
        assert avg_ms < 5000

class TestBlockSerializationBenchmarks:
    """Microbenchmarks for block serialization/deserialization."""

    def test_transaction_to_dict_timing(self, tmp_path):
        """Benchmark transaction serialization."""
        wallet = Wallet()
        recipient = Wallet()

        # Create transactions
        transactions = []
        for i in range(100):
            tx = Transaction(wallet.address, recipient.address, float(i + 1), 0.01)
            tx.timestamp = 1000000 + i
            tx.public_key = wallet.public_key
            tx.sign_transaction(wallet.private_key)
            transactions.append(tx)

        # Benchmark serialization
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            for tx in transactions:
                tx.to_dict()
        elapsed = time.perf_counter() - start

        serializations = iterations * 100
        per_second = serializations / elapsed
        avg_us = (elapsed / serializations) * 1_000_000
        print(f"\nTransaction to_dict: {avg_us:.2f} us/tx ({per_second:.0f}/s)")
        assert per_second > 10000

    def test_transaction_json_serialization_timing(self, tmp_path):
        """Benchmark full JSON serialization of transactions."""
        wallet = Wallet()
        recipient = Wallet()

        # Create transactions
        transactions = []
        for i in range(100):
            tx = Transaction(wallet.address, recipient.address, float(i + 1), 0.01)
            tx.timestamp = 1000000 + i
            tx.public_key = wallet.public_key
            tx.sign_transaction(wallet.private_key)
            transactions.append(tx)

        # Benchmark JSON serialization
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            for tx in transactions:
                json.dumps(tx.to_dict())
        elapsed = time.perf_counter() - start

        serializations = iterations * 100
        per_second = serializations / elapsed
        avg_us = (elapsed / serializations) * 1_000_000
        print(f"\nTransaction JSON serialize: {avg_us:.2f} us/tx ({per_second:.0f}/s)")
        assert per_second > 5000

    def test_block_serialization_timing(self, tmp_path):
        """Benchmark full block serialization."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Create blocks with transactions
        blocks = []
        for _ in range(10):
            blockchain.mine_pending_transactions(miner.address)
            blocks.append(blockchain.get_latest_block())

        # Benchmark block serialization
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            for block in blocks:
                block.to_dict()
        elapsed = time.perf_counter() - start

        serializations = iterations * 10
        per_second = serializations / elapsed
        avg_ms = (elapsed / serializations) * 1000
        print(f"\nBlock to_dict: {avg_ms:.3f} ms/block ({per_second:.2f}/s)")
        assert per_second > 100

    def test_block_json_serialization_timing(self, tmp_path):
        """Benchmark block JSON serialization."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Create blocks
        for _ in range(10):
            blockchain.mine_pending_transactions(miner.address)

        blocks = blockchain.chain[1:11]

        # Benchmark JSON serialization
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            for block in blocks:
                json.dumps(block.to_dict())
        elapsed = time.perf_counter() - start

        serializations = iterations * 10
        per_second = serializations / elapsed
        avg_ms = (elapsed / serializations) * 1000
        print(f"\nBlock JSON serialize: {avg_ms:.3f} ms/block ({per_second:.2f}/s)")
        assert per_second > 50

class TestMerkleTreeBenchmarks:
    """Microbenchmarks for Merkle tree operations."""

    def test_block_merkle_root_calculation_timing(self, tmp_path):
        """Benchmark block Merkle root calculation."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        miner = Wallet()

        blockchain.mine_pending_transactions(sender.address)

        # Create block with many transactions
        for i in range(100):
            tx = blockchain.create_transaction(
                sender.address, Wallet().address, 0.01, 0.001,
                sender.private_key, sender.public_key
            )
            blockchain.add_transaction(tx)

        # Get the transactions for merkle calculation
        transactions = blockchain.pending_transactions.copy()

        # Import Merkle calculation function
        from xai.core.chain.block_header import BlockHeader

        # Benchmark merkle root calculation
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            # Calculate merkle root from transaction hashes
            tx_hashes = [tx.txid or tx.calculate_hash() for tx in transactions]
            if tx_hashes:
                import hashlib
                while len(tx_hashes) > 1:
                    if len(tx_hashes) % 2:
                        tx_hashes.append(tx_hashes[-1])
                    tx_hashes = [
                        hashlib.sha256((tx_hashes[i] + tx_hashes[i+1]).encode()).hexdigest()
                        for i in range(0, len(tx_hashes), 2)
                    ]
        elapsed = time.perf_counter() - start

        calcs_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nMerkle root (100 txs): {avg_us:.2f} us/calc ({calcs_per_second:.0f}/s)")
        assert calcs_per_second > 100

class TestCryptoOperationsBenchmarks:
    """Microbenchmarks for cryptographic operations."""

    def test_key_derivation_timing(self, tmp_path):
        """Benchmark public key derivation."""
        wallet = Wallet()

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            derive_public_key_hex(wallet.private_key)
        elapsed = time.perf_counter() - start

        derivations_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nPublic key derivation: {avg_us:.2f} us/derivation ({derivations_per_second:.0f}/s)")
        assert derivations_per_second > 100

    def test_signature_creation_timing(self, tmp_path):
        """Benchmark signature creation."""
        wallet = Wallet()
        message = b"test message for signing benchmark"

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            sign_message_hex(wallet.private_key, message)
        elapsed = time.perf_counter() - start

        signatures_per_second = iterations / elapsed
        avg_us = (elapsed / iterations) * 1_000_000
        print(f"\nSignature creation: {avg_us:.2f} us/sig ({signatures_per_second:.0f}/s)")
        assert signatures_per_second > 100

    def test_wallet_creation_timing(self, tmp_path):
        """Benchmark wallet/keypair generation."""
        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            Wallet()
        elapsed = time.perf_counter() - start

        wallets_per_second = iterations / elapsed
        avg_ms = (elapsed / iterations) * 1000
        print(f"\nWallet creation: {avg_ms:.2f} ms/wallet ({wallets_per_second:.2f}/s)")
        assert wallets_per_second > 10

class TestComprehensiveBenchmarkSummary:
    """Run comprehensive benchmark suite and report summary."""

    def test_benchmark_summary(self, tmp_path, capsys):
        """Generate comprehensive benchmark summary."""
        print("\n" + "="*60)
        print("XAI BLOCKCHAIN MICROBENCHMARK SUMMARY")
        print("="*60)

        results = {}

        # Signature verification
        wallet = Wallet()
        message = b"test message"
        signature = sign_message_hex(wallet.private_key, message)

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            verify_signature_hex(wallet.public_key, message, signature)
        elapsed = time.perf_counter() - start
        results["sig_verify"] = iterations / elapsed

        # UTXO lookup
        manager = UTXOManager()
        for i in range(1000):
            manager.add_utxo(f"XAI{i:040d}", f"txid{i:064x}", 0, 1.0, "P2PKH")

        start = time.perf_counter()
        for i in range(1000):
            manager.get_utxos_for_address(f"XAI{i:040d}")
        elapsed = time.perf_counter() - start
        results["utxo_lookup"] = 1000 / elapsed

        # Transaction serialization
        tx = Transaction(wallet.address, Wallet().address, 1.0, 0.01)
        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        start = time.perf_counter()
        for _ in range(1000):
            json.dumps(tx.to_dict())
        elapsed = time.perf_counter() - start
        results["tx_serialize"] = 1000 / elapsed

        # Merkle root
        start = time.perf_counter()
        for _ in range(100):
            manager.calculate_merkle_root()
        elapsed = time.perf_counter() - start
        results["merkle_root"] = 100 / elapsed

        print("\nOperation                    Rate")
        print("-" * 40)
        print(f"Signature verification:      {results['sig_verify']:.0f}/s")
        print(f"UTXO lookup:                 {results['utxo_lookup']:.0f}/s")
        print(f"Transaction serialization:   {results['tx_serialize']:.0f}/s")
        print(f"Merkle root calculation:     {results['merkle_root']:.2f}/s")
        print("="*60)

        # All operations should meet minimum thresholds
        assert results["sig_verify"] > 100
        assert results["utxo_lookup"] > 1000
        assert results["tx_serialize"] > 1000
        assert results["merkle_root"] > 1

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

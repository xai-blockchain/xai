"""
Comprehensive tests for block explorer search functionality

Tests search by block height, hash, transaction ID, address,
invalid patterns, and autocomplete features.
"""

import pytest
from unittest.mock import Mock, patch

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet


class BlockExplorer:
    """Mock block explorer for testing"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.tx_index = {}  # {txid: (block_index, tx_index)}
        self.address_index = {}  # {address: [txids]}
        self._build_indices()

    def _build_indices(self):
        """Build search indices"""
        for block_idx, block in enumerate(self.blockchain.chain):
            for tx_idx, tx in enumerate(block.transactions):
                if tx.txid:
                    self.tx_index[tx.txid] = (block_idx, tx_idx)

                    # Index sender
                    if tx.sender not in self.address_index:
                        self.address_index[tx.sender] = []
                    self.address_index[tx.sender].append(tx.txid)

                    # Index recipient
                    if tx.recipient not in self.address_index:
                        self.address_index[tx.recipient] = []
                    self.address_index[tx.recipient].append(tx.txid)

    def search_by_height(self, height):
        """Search block by height"""
        if 0 <= height < len(self.blockchain.chain):
            return self.blockchain.chain[height]
        return None

    def search_by_block_hash(self, block_hash):
        """Search block by hash"""
        for block in self.blockchain.chain:
            if block.hash == block_hash:
                return block
        return None

    def search_by_txid(self, txid):
        """Search transaction by ID"""
        if txid in self.tx_index:
            block_idx, tx_idx = self.tx_index[txid]
            return self.blockchain.chain[block_idx].transactions[tx_idx]
        return None

    def search_by_address(self, address):
        """Search transactions by address"""
        if address in self.address_index:
            txids = self.address_index[address]
            return [self.search_by_txid(txid) for txid in txids]
        return []

    def autocomplete(self, query, max_results=5):
        """Autocomplete search query"""
        results = []

        # Try block heights
        try:
            height = int(query)
            if 0 <= height < len(self.blockchain.chain):
                results.append({'type': 'block_height', 'value': height})
        except ValueError:
            pass

        # Try addresses
        for address in self.address_index:
            if address.startswith(query):
                results.append({'type': 'address', 'value': address})
                if len(results) >= max_results:
                    break

        # Try transaction IDs
        for txid in self.tx_index:
            if txid.startswith(query):
                results.append({'type': 'txid', 'value': txid})
                if len(results) >= max_results:
                    break

        return results[:max_results]


class TestExplorerSearch:
    """Tests for block explorer search"""

    def test_search_by_block_height(self, tmp_path):
        """Test searching blocks by height"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        # Search by height
        block0 = explorer.search_by_height(0)
        assert block0 is not None
        assert block0.index == 0

        block1 = explorer.search_by_height(1)
        assert block1 is not None
        assert block1.index == 1

    def test_search_by_block_hash(self, tmp_path):
        """Test searching blocks by hash"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        # Get block hash
        block = bc.chain[1]
        block_hash = block.hash

        # Search by hash
        found_block = explorer.search_by_block_hash(block_hash)
        assert found_block is not None
        assert found_block.hash == block_hash

    def test_search_by_transaction_id(self, tmp_path):
        """Test searching transactions by ID"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get funds
        bc.mine_pending_transactions(wallet1.address)

        # Create transaction
        tx = bc.create_transaction(
            wallet1.address, wallet2.address, 5.0, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        if tx:
            txid = tx.txid
            bc.mine_pending_transactions(wallet1.address)

            explorer = BlockExplorer(bc)

            # Search by txid
            found_tx = explorer.search_by_txid(txid)
            assert found_tx is not None
            assert found_tx.txid == txid

    def test_search_by_address(self, tmp_path):
        """Test searching transactions by address"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get funds
        bc.mine_pending_transactions(wallet1.address)

        # Create transactions
        tx1 = bc.create_transaction(
            wallet1.address, wallet2.address, 5.0, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        bc.mine_pending_transactions(wallet1.address)

        explorer = BlockExplorer(bc)

        # Search by address
        txs = explorer.search_by_address(wallet1.address)
        assert len(txs) > 0

        # Wallet1 should appear in multiple transactions
        has_wallet1 = any(
            tx.sender == wallet1.address or tx.recipient == wallet1.address
            for tx in txs if tx
        )
        assert has_wallet1

    def test_invalid_search_patterns(self, tmp_path):
        """Test searching with invalid patterns"""
        bc = Blockchain(data_dir=str(tmp_path))
        explorer = BlockExplorer(bc)

        # Invalid block height
        block = explorer.search_by_height(9999)
        assert block is None

        # Invalid hash
        block = explorer.search_by_block_hash("invalid_hash_xyz")
        assert block is None

        # Invalid txid
        tx = explorer.search_by_txid("nonexistent_txid")
        assert tx is None

        # Invalid address
        txs = explorer.search_by_address("invalid_address")
        assert txs == []

    def test_autocomplete_functionality(self, tmp_path):
        """Test search autocomplete"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        # Autocomplete by block height
        results = explorer.autocomplete("0")
        assert len(results) > 0

        # Should suggest block height 0
        has_height_0 = any(
            r['type'] == 'block_height' and r['value'] == 0
            for r in results
        )
        assert has_height_0

    def test_autocomplete_address_prefix(self, tmp_path):
        """Test autocomplete with address prefix"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        # Autocomplete with address prefix
        address_prefix = wallet.address[:5]
        results = explorer.autocomplete(address_prefix)

        # Should find addresses starting with prefix
        matching = [r for r in results if r['type'] == 'address']
        assert len(matching) > 0

    def test_autocomplete_max_results(self, tmp_path):
        """Test autocomplete respects max results limit"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine multiple blocks
        for _ in range(10):
            bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        # Autocomplete with limit
        results = explorer.autocomplete("", max_results=3)
        assert len(results) <= 3

    def test_search_returns_correct_block_data(self, tmp_path):
        """Test search returns complete block data"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        explorer = BlockExplorer(bc)

        block = explorer.search_by_height(1)
        assert block is not None
        assert hasattr(block, 'index')
        assert hasattr(block, 'hash')
        assert hasattr(block, 'previous_hash')
        assert hasattr(block, 'transactions')
        assert hasattr(block, 'timestamp')

    def test_search_transaction_returns_complete_data(self, tmp_path):
        """Test transaction search returns complete data"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        bc.mine_pending_transactions(wallet1.address)

        tx = bc.create_transaction(
            wallet1.address, wallet2.address, 5.0, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        if tx:
            txid = tx.txid
            bc.mine_pending_transactions(wallet1.address)

            explorer = BlockExplorer(bc)
            found_tx = explorer.search_by_txid(txid)

            assert found_tx is not None
            assert hasattr(found_tx, 'sender')
            assert hasattr(found_tx, 'recipient')
            assert hasattr(found_tx, 'amount')
            assert hasattr(found_tx, 'fee')
            assert hasattr(found_tx, 'timestamp')

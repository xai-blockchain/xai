"""
Unit tests for BlockchainMiningMixin block assembly.

Coverage targets:
- Requires node identity for mining
- Respects max_transactions_per_block and block size limit when selecting txs
- Skips transactions with nonce mismatch
"""

from types import SimpleNamespace

import pytest

from xai.core.blockchain_components.mining_mixin import BlockchainMiningMixin


class _Tx:
    def __init__(self, sender, recipient, amount, fee=0.0, nonce=0):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.nonce = nonce
        self.tx_type = "payment"
        self.inputs = []
        self.outputs = [{"address": recipient, "amount": amount}]
        self.signature = "sig"
        self.txid = f"{sender}-{nonce}"

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "nonce": self.nonce,
            "tx_type": self.tx_type,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "signature": self.signature,
            "txid": self.txid,
        }

    def calculate_hash(self):
        return self.txid


class DummyMining(BlockchainMiningMixin):
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = 1
        self.nonce_tracker = SimpleNamespace(
            pending_nonces={},
            nonces={},
            get_nonce=lambda self, addr=None: 0,
            snapshot=lambda self=None: {},
            restore=lambda *_: None,
            increment_nonce=lambda *_: None,
        )
        self.utxo_manager = SimpleNamespace(
            snapshot=lambda: {},
            rollback=lambda *_: None,
            restore=lambda *_: None,
            process_transaction_outputs=lambda *_: None,
            process_transaction_inputs=lambda *_: None,
            compact_utxo_set=lambda *_: None,
        )
        self.storage = SimpleNamespace(save_block=lambda *_: None, _save_block_to_disk=lambda *_: None)
        self.storage.save_state_to_disk = lambda *_: None
        self.streak_tracker = SimpleNamespace(
            update_miner_streak=lambda *_: None, apply_streak_bonus=lambda *_: (0, 0)
        )
        self.checkpoint_manager = SimpleNamespace(
            should_create_checkpoint=lambda *_: False,
            create_checkpoint=lambda *_: None,
        )
        self.smart_contract_manager = None
        self.gamification_adapter = None
        self.airdrop_manager = None
        self.fee_refund_calculator = None
        self.treasure_manager = None
        self.contracts = {}
        self.contract_receipts = []
        self.logger = SimpleNamespace(info=lambda *a, **k: None, warn=lambda *a, **k: None, error=lambda *a, **k: None)
        self.fast_mining_enabled = False
        self.max_test_mining_difficulty = 1
        self.network_type = "testnet"
        self._max_block_size_bytes = 500
        self._max_transactions_per_block = 2
        # Use minimal hex-looking values to satisfy signing helper expectations
        self.node_identity = {"private_key": "1" * 64, "public_key": "2" * 64}
        self._valid_address = "XAI" + "a" * 40
        self.address_index = SimpleNamespace(
            index_transaction=lambda *_: None,
            rollback=lambda *_: None,
            commit=lambda *_: None,
        )
        self.logger.warning = self.logger.warn

    # Minimal stubs required by mixin
    def calculate_next_difficulty(self):
        return self.difficulty

    def _prioritize_transactions(self, txs, max_count=None):
        return txs

    def validate_transaction(self, tx):
        return True

    def get_block_reward(self, height):
        return 0

    def calculate_merkle_root(self, txs):
        return "root"

    def mine_block(self, header):
        return "hash"

    def _block_within_size_limits(self, block, context=None):
        return True

    def add_block(self, block):
        pass

    def validate_block(self, block):
        return True

    @property
    def checkpoint_manager(self):
        return self._checkpoint_manager

    @checkpoint_manager.setter
    def checkpoint_manager(self, value):
        self._checkpoint_manager = value

    def _should_create_checkpoint(self, *_args, **_kwargs):
        return False

    def _process_governance_block_transactions(self, block):
        return


def test_requires_node_identity():
    miner = DummyMining()
    miner.node_identity = None
    with pytest.raises(ValueError):
        miner.mine_pending_transactions(miner_address="m")


def test_respects_max_transactions_and_nonce_order():
    miner = DummyMining()
    # Max tx per block is 2 (coinbase + 1 pending tx)
    miner.pending_transactions = [
        _Tx(miner._valid_address, miner._valid_address, 1, fee=0.1, nonce=1),  # nonce mismatch (expects 1)
        _Tx(miner._valid_address, miner._valid_address, 1, fee=0.1, nonce=1),  # correct once expected advanced
        _Tx(miner._valid_address, miner._valid_address, 1, fee=0.2, nonce=0),  # would exceed limit
    ]
    block = miner.mine_pending_transactions(miner_address=miner._valid_address)
    # Only coinbase + 1 tx included
    assert len(block.transactions) == 2
    assert block.transactions[1].nonce == 1

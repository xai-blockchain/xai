import copy
import hashlib
import json

import pytest

from xai.core.blockchain import Blockchain
from xai.core.security.crypto_utils import generate_secp256k1_keypair_hex, sign_message_hex
from xai.core.consensus.finality import FinalityValidationError


def _pubkey_to_address(public_key_hex: str) -> str:
    digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()
    return f"XAI{digest[:40]}"


@pytest.fixture
def validator_accounts():
    accounts = []
    for _ in range(2):
        priv, pub = generate_secp256k1_keypair_hex()
        accounts.append(
            {
                "private_key": priv,
                "public_key": pub,
                "address": _pubkey_to_address(pub),
                "voting_power": 50,
            }
        )
    return accounts


@pytest.fixture
def finality_blockchain(tmp_path, monkeypatch, validator_accounts):
    validator_payload = [
        {
            "address": entry["address"],
            "public_key": entry["public_key"],
            "voting_power": entry["voting_power"],
        }
        for entry in validator_accounts
    ]
    monkeypatch.setenv("XAI_VALIDATOR_SET", json.dumps(validator_payload))
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    bc = Blockchain(data_dir=str(tmp_path))
    return bc, validator_accounts


def _vote(blockchain: Blockchain, block, account) -> dict:
    payload = blockchain.finality_manager.build_vote_payload(block.header)
    signature = sign_message_hex(account["private_key"], payload)
    return blockchain.submit_finality_vote(
        validator_address=account["address"],
        signature=signature,
        block_hash=block.hash,
    )


def test_finality_certificate_quorum(finality_blockchain):
    blockchain, accounts = finality_blockchain
    block = blockchain.storage.load_block_from_disk(0)
    first_vote = _vote(blockchain, block, accounts[0])
    assert first_vote["finalized"] is False
    second_vote = _vote(blockchain, block, accounts[1])
    assert second_vote["finalized"] is True
    certificate = blockchain.get_finality_certificate(block_hash=block.hash)
    assert certificate is not None
    assert blockchain.is_block_finalized(block_hash=block.hash) is True


def test_finality_prevents_reorg(finality_blockchain, monkeypatch):
    blockchain, accounts = finality_blockchain
    blockchain.mine_pending_transactions(miner_address=accounts[0]["address"])
    block = blockchain.storage.load_block_from_disk(1)
    _vote(blockchain, block, accounts[0])
    _vote(blockchain, block, accounts[1])
    blocks = []
    for idx in range(len(blockchain.chain)):
        stored = blockchain.storage.load_block_from_disk(idx)
        blocks.append(copy.deepcopy(stored))
    blocks[1].header.nonce += 1
    blocks[1].header.hash = blocks[1].header.calculate_hash()
    monkeypatch.setattr(Blockchain, "_validate_chain_structure", lambda self, chain: True)
    replaced = blockchain.replace_chain(blocks)
    assert replaced is False


def test_double_sign_slashes_validator(finality_blockchain):
    blockchain, accounts = finality_blockchain
    validator = accounts[0]
    block = blockchain.storage.load_block_from_disk(0)
    payload = blockchain.finality_manager.build_vote_payload(block.header)
    signature = sign_message_hex(validator["private_key"], payload)
    blockchain.finality_manager.record_vote(
        validator_address=validator["address"],
        header=block.header,
        signature=signature,
    )
    conflicting_header = copy.deepcopy(block.header)
    conflicting_header.nonce += 1
    conflicting_header.hash = conflicting_header.calculate_hash()
    conflicting_payload = blockchain.finality_manager.build_vote_payload(conflicting_header)
    conflicting_signature = sign_message_hex(validator["private_key"], conflicting_payload)
    with pytest.raises(FinalityValidationError):
        blockchain.finality_manager.record_vote(
            validator_address=validator["address"],
            header=conflicting_header,
            signature=conflicting_signature,
        )
    status = blockchain.slashing_manager.get_validator_status(validator["address"])
    assert status["slashed_count"] >= 1


def test_finality_persists_across_restart(finality_blockchain, validator_accounts, monkeypatch, tmp_path):
    blockchain, accounts = finality_blockchain
    block = blockchain.storage.load_block_from_disk(0)

    # Finalize genesis block
    for account in accounts:
        _vote(blockchain, block, account)
    assert blockchain.is_block_finalized(block_hash=block.hash) is True

    # Persisted state files should exist
    finality_dir = tmp_path / "finality"
    assert (finality_dir / "finality_certificates.json").exists()
    assert (finality_dir / "finality_state.json").exists()

    # Rehydrate a new blockchain instance and ensure finality is retained
    validator_payload = [
        {
            "address": entry["address"],
            "public_key": entry["public_key"],
            "voting_power": entry["voting_power"],
        }
        for entry in validator_accounts
    ]
    monkeypatch.setenv("XAI_VALIDATOR_SET", json.dumps(validator_payload))
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    reloaded = Blockchain(data_dir=str(tmp_path))
    assert reloaded.is_block_finalized(block_hash=block.hash) is True
    highest = reloaded.finality_manager.get_highest_finalized_height()
    assert highest == block.header.index

"""
Tests for HTLC generation logic in atomic_swap_11_coins.
"""

from decimal import Decimal
from typing import Any, Dict

from xai.core.aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC, CoinType


def test_utxo_htlc_includes_hash_and_timelock():
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.1, counterparty_address="pubkey", timelock_hours=1)
    assert contract["contract_type"] == "HTLC_UTXO"
    assert "OP_SHA256" in contract["script_template"]
    assert str(contract["timelock"]) in contract["refund_method"]
    assert contract["secret_hash"] in contract["script_template"]
    assert "recommended_fee" in contract
    assert contract["recommended_fee"]["unit"] == "BTC"


def test_eth_htlc_contains_hash_and_recipient():
    htlc = AtomicSwapHTLC(CoinType.ETH)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.2, counterparty_address="0xRecipient", timelock_hours=1)
    solidity = contract["smart_contract"]
    assert "AtomicSwapETH" in solidity
    assert contract["secret_hash"] in solidity
    assert "0xRecipient" in solidity
    # amount is embedded as ether literal
    assert str(0.2) in solidity
    assert "recommended_gas" in contract
    assert contract["recommended_gas"]["gas_limit"] > 0


def test_hash_parity_is_sha256_across_protocols():
    """Expose a single canonical SHA-256 hash for both BTC and ETH legs."""
    htlc_eth = AtomicSwapHTLC(CoinType.ETH)
    contract = htlc_eth.create_swap_contract(axn_amount=1, other_coin_amount=0.2, counterparty_address="0xRecipient", timelock_hours=1)
    assert "secret_hash" in contract
    assert "secret_hash_keccak" not in contract


def test_verify_swap_claim_checks_secret_and_timelock(monkeypatch):
    htlc = AtomicSwapHTLC(CoinType.BTC)
    contract = htlc.create_swap_contract(axn_amount=1, other_coin_amount=0.1, counterparty_address="pub", timelock_hours=1)
    secret = contract["secret"]
    secret_hash = contract["secret_hash"]

    valid, msg = htlc.verify_swap_claim(secret, secret_hash, contract)
    assert valid is True
    assert "Valid claim" in msg

    # Wrong secret fails
    valid, msg = htlc.verify_swap_claim("00" * 32, secret_hash, contract)
    assert valid is False

    # Expired timelock fails
    monkeypatch.setattr("time.time", lambda: contract["timelock"] + 1)
    valid, msg = htlc.verify_swap_claim(secret, secret_hash, contract)
    assert valid is False
    assert "Timelock expired" in msg


def test_utxo_deployment_includes_redeem_script():
    """UTXO deployment config should yield concrete P2WSH details."""
    htlc = AtomicSwapHTLC(CoinType.BTC)
    deployment_cfg: Dict[str, Any] = {
        "utxo": {
            "sender_pubkey": "02" + "11" * 32,
            "recipient_pubkey": "03" + "22" * 32,
            "hrp": "tb",
            "network": "testnet",
        }
    }
    contract = htlc.create_swap_contract(
        axn_amount=1,
        other_coin_amount=0.1,
        counterparty_address="ignore-for-utxo",
        timelock_hours=1,
        deployment_config=deployment_cfg,
    )
    assert contract["deployment_ready"] is True
    assert contract["p2wsh_address"].startswith("tb1")
    assert "redeem_script_hex" in contract
    assert isinstance(contract["funding_amount_sats"], int)


def test_ethereum_deployment_invokes_deployer(monkeypatch):
    """Ethereum deployment config should call deploy_htlc with expected params."""
    htlc = AtomicSwapHTLC(CoinType.ETH)

    class DummyEth:
        chain_id = 5

    class DummyWeb3:
        eth = DummyEth()

    captured: Dict[str, Any] = {}

    class DummyContract:
        address = "0xdeadbeef"
        abi = [{"name": "claim"}]

    def fake_deploy(w3, **kwargs):
        captured["web3"] = w3
        captured.update(kwargs)
        return DummyContract()

    monkeypatch.setattr(
        "xai.core.aixn_blockchain.atomic_swap_11_coins.htlc_deployer.deploy_htlc",
        fake_deploy,
    )

    deployment_cfg = {
        "ethereum": {
            "web3": DummyWeb3(),
            "sender": "0xFeedCafe000000000000000000000000000000",
            "auto_deploy": True,
        }
    }
    contract = htlc.create_swap_contract(
        axn_amount=1,
        other_coin_amount=0.5,
        counterparty_address="0xRecipient0000000000000000000000000000000000",
        timelock_hours=1,
        deployment_config=deployment_cfg,
    )
    assert contract["deployment_ready"] is True
    assert contract["contract_address"] == "0xdeadbeef"
    assert contract["chain_id"] == 5
    assert captured["sender"] == deployment_cfg["ethereum"]["sender"]

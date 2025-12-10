import json
from pathlib import Path

from xai.tools.atomic_swap_cli import (
    generate_swap_artifacts,
    build_btc_refund_witness,
    UTXOParams,
)


def test_generate_swap_artifacts_with_utxo(tmp_path):
    artifacts = generate_swap_artifacts(
        pair="XAI/BTC",
        axn_amount=1000,
        other_amount=0.01,
        counterparty="recipient",
        utxo=UTXOParams(
            sender_pubkey="02" + "11" * 32,
            recipient_pubkey="03" + "22" * 32,
            hrp="tb",
            network="testnet",
        ),
    )
    assert artifacts["pair"] == "XAI/BTC"
    swap = artifacts["swap"]
    assert swap["contract_type"] == "HTLC_UTXO"
    assert swap["deployment_ready"] is True
    assert swap["p2wsh_address"].startswith("tb1")

    output_file = tmp_path / "swap_artifacts.json"
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(artifacts, handle)
    assert output_file.exists()


def test_build_btc_refund_witness_returns_stack():
    redeem_script = "51" * 10
    witness = build_btc_refund_witness("aa" * 32, redeem_script)
    assert witness["signature"] == "aa" * 32
    assert witness["redeem_script"] == redeem_script

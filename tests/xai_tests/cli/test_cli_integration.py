from __future__ import annotations

from click.testing import CliRunner
import json
from pathlib import Path
from typing import Any

from xai.cli.enhanced_cli import cli, XAIClient

def _stub_methods(monkeypatch):
    monkeypatch.setattr(
        XAIClient,
        "get_blockchain_info",
        lambda self: {
            "height": 42,
            "latest_block": "abc123",
            "difficulty": 1000,
            "pending_transactions": 3,
            "network_hashrate": "1 GH/s",
            "total_supply": 1_000_000,
        },
    )
    monkeypatch.setattr(
        XAIClient,
        "get_block",
        lambda self, block_id: {"block": {"index": 42, "hash": f"block-{block_id}", "transactions": []}},
    )
    monkeypatch.setattr(
        XAIClient,
        "get_mempool",
        lambda self: {"transactions": [{"txid": "tx1", "sender": "A", "recipient": "B", "amount": 1.0, "fee": 0.01}]},
    )

def test_blockchain_info_json(monkeypatch):
    _stub_methods(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["--json-output", "blockchain", "info"])
    assert result.exit_code == 0
    assert '"height": 42' in result.output
    assert '"pending_transactions": 3' in result.output

def test_block_fetch_and_mempool(monkeypatch):
    _stub_methods(monkeypatch)
    runner = CliRunner()

    block_res = runner.invoke(cli, ["--json-output", "blockchain", "block", "42"])
    assert block_res.exit_code == 0
    assert "block-42" in block_res.output

    mempool_res = runner.invoke(cli, ["--json-output", "blockchain", "mempool"])
    assert mempool_res.exit_code == 0
    assert "tx1" in mempool_res.output

def test_blockchain_state_command(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        XAIClient,
        "get_state_snapshot",
        lambda self: {"success": True, "state": {"height": 99, "tip": "abc", "pending_transactions": 5}},
    )
    result = runner.invoke(cli, ["--json-output", "blockchain", "state"])
    assert result.exit_code == 0
    assert '"height": 99' in result.output

def test_blockchain_validate_block_command(monkeypatch):
    runner = CliRunner()

    def _validate(self, **kwargs):
        assert kwargs["index"] == 7
        return {"valid": True, "block_index": 7, "block_hash": "deadbeef", "transactions_valid": True}

    monkeypatch.setattr(XAIClient, "validate_block", _validate)
    result = runner.invoke(cli, ["--json-output", "blockchain", "validate-block", "--index", "7"])
    assert result.exit_code == 0
    assert '"block_index": 7' in result.output

def test_blockchain_consensus_command(monkeypatch):
    runner = CliRunner()

    def _mock(self):
        return {"success": True, "consensus": {"difficulty": 4, "forks_detected": 0}}

    monkeypatch.setattr(XAIClient, "get_consensus_info", _mock)
    result = runner.invoke(cli, ["--json-output", "blockchain", "consensus"])
    assert result.exit_code == 0
    assert '"difficulty": 4' in result.output

def test_mempool_drop_requires_api_key(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(cli, ["mempool", "drop", "abc123"])
    assert result.exit_code != 0
    assert "API key required" in result.output

def test_mempool_drop_success(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        XAIClient,
        "delete_mempool_transaction",
        lambda self, txid, ban_sender=False: {"success": True, "txid": txid, "ban_applied": ban_sender},
    )
    result = runner.invoke(
        cli,
        ["--api-key", "secret", "--json-output", "mempool", "drop", "deadbeef", "--ban-sender"],
    )
    assert result.exit_code == 0
    assert '"ban_applied": true' in result.output

def test_blockchain_genesis_show(tmp_path):
    genesis_payload = {
        "index": 0,
        "timestamp": 1700000000.0,
        "transactions": [
            {"sender": "COINBASE", "recipient": "XAI123", "amount": 1.0, "fee": 0.0, "timestamp": 1700000000.0}
        ],
        "hash": "abc123",
    }
    genesis_file = tmp_path / "genesis.json"
    genesis_file.write_text(json.dumps(genesis_payload), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json-output", "blockchain", "genesis", "show", "--genesis-path", str(genesis_file)],
    )
    assert result.exit_code == 0
    assert '"transaction_count": 1' in result.output

def test_blockchain_genesis_verify(tmp_path):
    genesis_payload = {
        "index": 0,
        "timestamp": 1700000000.0,
        "transactions": [
            {"sender": "COINBASE", "recipient": "XAI123", "amount": 1.0, "fee": 0.0, "timestamp": 1700000000.0}
        ],
    }
    genesis_file = tmp_path / "genesis.json"
    genesis_file.write_text(json.dumps(genesis_payload), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json-output", "blockchain", "genesis", "verify", "--genesis-path", str(genesis_file)],
    )
    assert result.exit_code == 0
    assert '"hash_match": false' in result.output

def test_blockchain_reset_and_rollback_commands(monkeypatch, tmp_path):
    class DummyBlockchain:
        reset_calls: list[tuple[str, bool]] = []
        rollback_calls: list[tuple[str, int]] = []

        def __init__(self, data_dir: str):
            self.data_dir = data_dir

        def reset_chain_state(self, preserve_checkpoints: bool = False):
            DummyBlockchain.reset_calls.append((self.data_dir, preserve_checkpoints))
            return {"previous_height": 10, "new_height": 0}

        def restore_checkpoint(self, height: int):
            DummyBlockchain.rollback_calls.append((self.data_dir, height))
            return {
                "previous_height": 10,
                "new_height": height,
                "removed_blocks": 10 - height,
                "checkpoint_height": height,
            }

    def fake_factory(path: Path):
        return DummyBlockchain(str(path))

    monkeypatch.setattr("xai.cli.enhanced_cli._create_blockchain_instance", fake_factory)
    runner = CliRunner()

    reset_res = runner.invoke(
        cli,
        ["--json-output", "blockchain", "reset", "--data-dir", str(tmp_path), "--yes"],
    )
    assert reset_res.exit_code == 0
    assert '"new_height": 0' in reset_res.output
    assert DummyBlockchain.reset_calls == [(str(tmp_path), False)]

    rollback_res = runner.invoke(
        cli,
        [
            "--json-output",
            "blockchain",
            "rollback",
            "--data-dir",
            str(tmp_path),
            "--height",
            "1",
            "--yes",
        ],
    )
    assert rollback_res.exit_code == 0
    assert '"checkpoint_height": 1' in rollback_res.output
    assert DummyBlockchain.rollback_calls == [(str(tmp_path), 1)]

def test_cli_local_transport_balance_and_block(monkeypatch, tmp_path):
    class DummyBlock:
        def __init__(self, index: int):
            self.index = index

        def to_dict(self):
            return {"index": self.index, "hash": f"local-{self.index}", "transactions": []}

    class DummyChain:
        def __init__(self, data_dir: str):
            self.data_dir = data_dir

        def get_stats(self):
            return {
                "chain_height": 5,
                "latest_block_hash": "feedface",
                "difficulty": 12345,
                "pending_transactions_count": 2,
                "total_circulating_supply": 100.0,
            }

        def get_balance(self, address: str):
            return 42.0 if address == "local-addr" else 0.0

        def get_block(self, index: int):
            return DummyBlock(index)

    monkeypatch.setattr(
        "xai.cli.enhanced_cli._create_blockchain_instance",
        lambda path: DummyChain(str(path)),
    )
    runner = CliRunner()
    info_res = runner.invoke(
        cli,
        [
            "--transport",
            "local",
            "--local-data-dir",
            str(tmp_path),
            "--json-output",
            "blockchain",
            "info",
        ],
    )
    assert info_res.exit_code == 0
    assert '"transport": "local"' in info_res.output
    assert '"height": 5' in info_res.output

    balance_res = runner.invoke(
        cli,
        [
            "--transport",
            "local",
            "--local-data-dir",
            str(tmp_path),
            "--json-output",
            "wallet",
            "balance",
            "local-addr",
        ],
    )
    assert balance_res.exit_code == 0
    assert '"balance": 42.0' in balance_res.output

    block_res = runner.invoke(
        cli,
        [
            "--transport",
            "local",
            "--local-data-dir",
            str(tmp_path),
            "--json-output",
            "blockchain",
            "block",
            "3",
        ],
    )
    assert block_res.exit_code == 0
    assert '"hash": "local-3"' in block_res.output

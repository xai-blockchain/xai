"""
Unit tests for genesis loading safeguards in enhanced CLI.
"""

from pathlib import Path

import click
import pytest

from xai.cli.enhanced_cli import _load_genesis_file


def test_world_writable_genesis_path_rejected(tmp_path, monkeypatch):
    genesis = tmp_path / "genesis.json"
    genesis.write_text('{"index": 0}')
    genesis.chmod(0o666)
    monkeypatch.setenv("XAI_GENESIS_PATH", str(genesis))

    with pytest.raises(click.ClickException):
        _load_genesis_file(None)


def test_world_writable_parent_rejected(tmp_path, monkeypatch):
    parent = tmp_path / "ww"
    parent.mkdir()
    parent.chmod(0o777)
    genesis = parent / "genesis.json"
    genesis.write_text('{"index": 0}')
    monkeypatch.setenv("XAI_GENESIS_PATH", str(genesis))

    with pytest.raises(click.ClickException):
        _load_genesis_file(None)


def test_symlink_genesis_rejected(tmp_path, monkeypatch):
    target = tmp_path / "target.json"
    target.write_text('{"index": 0}')
    symlink = tmp_path / "link.json"
    symlink.symlink_to(target)
    monkeypatch.setenv("XAI_GENESIS_PATH", str(symlink))

    with pytest.raises(click.ClickException):
        _load_genesis_file(None)

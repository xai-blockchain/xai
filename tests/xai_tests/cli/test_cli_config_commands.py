import json
import shutil
from pathlib import Path

import yaml
from click.testing import CliRunner

from xai.cli.enhanced_cli import cli


def _prepare_config_dir(tmp_path: Path) -> Path:
    """Copy repo config directory to temp path for isolated editing."""
    source = Path("src/xai/config")
    target = tmp_path / "config"
    shutil.copytree(source, target)
    return target


def test_config_show_section(tmp_path):
    config_dir = _prepare_config_dir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json-output",
            "config",
            "--environment",
            "development",
            "--config-dir",
            str(config_dir),
            "show",
            "--section",
            "network",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["section"] == "network"
    assert payload["config"]["max_peers"] == 10


def test_config_get_key(tmp_path):
    config_dir = _prepare_config_dir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config",
            "--environment",
            "development",
            "--config-dir",
            str(config_dir),
            "get",
            "blockchain.difficulty",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["key"] == "blockchain.difficulty"
    assert payload["value"] == 2


def test_config_set_updates_file(tmp_path):
    config_dir = _prepare_config_dir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config",
            "--environment",
            "development",
            "--config-dir",
            str(config_dir),
            "set",
            "network.max_peers",
            "25",
            "--value-type",
            "int",
        ],
    )
    assert result.exit_code == 0, result.output
    config_path = config_dir / "development.yaml"
    data = yaml.safe_load(config_path.read_text())
    assert data["network"]["max_peers"] == 25

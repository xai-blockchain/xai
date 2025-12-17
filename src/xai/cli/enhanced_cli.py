#!/usr/bin/env python3
"""
XAI Blockchain - Revolutionary AI-Enhanced CLI
Production-grade command-line interface with rich terminal UX
"""

from __future__ import annotations

import sys
import json
import logging
import os
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
from copy import deepcopy
import importlib.resources as importlib_resources

try:
    import click
    try:
        from click.shell_completion import get_completion_script as _click_completion_script
    except ImportError:
        _click_completion_script = None
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich import box
    from rich.tree import Tree
    from rich.live import Live
    from rich.layout import Layout
except ImportError:
    print("ERROR: Required packages not installed. Install with:")
    print("  pip install click rich")
    sys.exit(1)

import requests
from xai.wallet.offline_signing import sign_offline, signing_preview
from xai.config_manager import (
    ConfigManager,
    Environment as ConfigEnvironment,
    DEFAULT_CONFIG_DIR as CONFIG_DEFAULT_DIR,
)
import yaml

# Configure module logger
logger = logging.getLogger(__name__)

# Rich console for beautiful output
console = Console()


def _cli_fail(exc: Exception, exit_code: int = 1) -> None:
    """Centralized CLI error handler for consistent messaging."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)

# Default configuration
DEFAULT_NODE_URL = "http://localhost:18545"
DEFAULT_TIMEOUT = 30.0
DEFAULT_DATA_DIR = Path(os.getenv("XAI_DATA_DIR", os.path.expanduser("~/.xai"))).expanduser()


class XAIClient:
    """Client for interacting with XAI blockchain node"""

    def __init__(
        self,
        node_url: str = DEFAULT_NODE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        api_key: Optional[str] = None,
    ):
        self.node_url = node_url.rstrip('/')
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to node"""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Node request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(method, url, timeout=self.timeout, headers=headers, **kwargs)
            response.raise_for_status()
            logger.debug("Node response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Node communication error: %s", e)
            raise click.ClickException(f"Node communication error: {e}")

    def get_balance(self, address: str) -> Dict[str, Any]:
        """Get wallet balance"""
        return self._request("GET", f"/balance/{address}")

    def get_transaction_history(self, address: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get transaction history"""
        return self._request("GET", f"/history/{address}", params={"limit": limit, "offset": offset})

    def get_block(self, block_id: str) -> Dict[str, Any]:
        """Get block by index or hash"""
        return self._request("GET", f"/block/{block_id}")

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._request("GET", "/info")

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._request("GET", "/network/info")

    def get_peers(self) -> Dict[str, Any]:
        """Get connected peers"""
        return self._request("GET", "/peers")

    def get_mining_status(self) -> Dict[str, Any]:
        """Get mining status"""
        return self._request("GET", "/mining/status")

    def start_mining(self, address: str, threads: int = 1, intensity: int = 1) -> Dict[str, Any]:
        """Start mining"""
        return self._request("POST", "/mining/start", json={
            "miner_address": address,
            "threads": threads,
            "intensity": intensity
        })

    def stop_mining(self) -> Dict[str, Any]:
        """Stop mining"""
        return self._request("POST", "/mining/stop")

    def submit_transaction(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Deprecated: use submit_signed_transaction to avoid transmitting private keys."""
        raise RuntimeError("submit_transaction is disabled. Use submit_signed_transaction with a pre-signed payload.")

    def submit_signed_transaction(self, signed_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a fully signed transaction (no private keys transmitted)."""
        return self._request("POST", "/send", json=signed_payload)

    def get_address_nonce(self, address: str) -> Dict[str, Any]:
        """Fetch confirmed and next nonce for an address."""
        return self._request("GET", f"/address/{address}/nonce")

    def get_mempool(self) -> Dict[str, Any]:
        """Get mempool transactions"""
        return self._request("GET", "/mempool")

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Retrieve deterministic state snapshot."""
        return self._request("GET", "/state/snapshot")

    def validate_block(
        self,
        *,
        index: Optional[int] = None,
        block_hash: Optional[str] = None,
        include_transactions: bool = False,
    ) -> Dict[str, Any]:
        """Validate a block by index or hash."""
        payload: Dict[str, Any] = {"include_transactions": include_transactions}
        if index is not None:
            payload["index"] = index
        if block_hash:
            payload["hash"] = block_hash
        return self._request("POST", "/blocks/validate", json=payload)

    def delete_mempool_transaction(self, txid: str, ban_sender: bool = False) -> Dict[str, Any]:
        """Remove a transaction from the mempool."""
        params = {"ban_sender": "true" if ban_sender else "false"}
        return self._request("DELETE", f"/mempool/{txid}", params=params)

    def get_consensus_info(self) -> Dict[str, Any]:
        """Fetch consensus manager status."""
        return self._request("GET", "/consensus/info")


# ============================================================================
# Configuration helpers
# ============================================================================

def _config_env_choices() -> List[str]:
    """Return list of valid environment option strings."""
    return [env.value for env in ConfigEnvironment]


def _parse_config_value(raw_value: str, value_type: str) -> Any:
    """Parse CLI string into the requested value type."""
    vt = value_type.lower()
    if vt == "json":
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON value: {exc}") from exc

    if vt == "bool":
        lowered = raw_value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        raise click.ClickException(f"Cannot parse boolean value from '{raw_value}'")

    if vt == "int":
        try:
            return int(raw_value)
        except ValueError as exc:
            raise click.ClickException(f"Cannot parse integer value from '{raw_value}'") from exc

    if vt == "float":
        try:
            return float(raw_value)
        except ValueError as exc:
            raise click.ClickException(f"Cannot parse float value from '{raw_value}'") from exc

    if vt in {"str", "string"}:
        return raw_value

    # auto detection
    lowered = raw_value.strip().lower()
    if lowered in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        return _parse_config_value(raw_value, "bool")
    try:
        return int(raw_value)
    except ValueError:
        try:
            return float(raw_value)
        except ValueError:
            pass
    # attempt JSON object/list if braces present
    stripped = raw_value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            pass
    return raw_value


def _read_yaml_config(path: Path) -> Dict[str, Any]:
    """Load YAML config into dict."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise click.ClickException(f"Config file {path} must contain a mapping.")
        return data


def _write_yaml_config(path: Path, data: Dict[str, Any]) -> None:
    """Persist config dict to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def _set_nested_value(target: Dict[str, Any], parts: List[str], value: Any) -> None:
    """Set nested dictionary value creating intermediate dicts as needed."""
    cursor = target
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _resolve_config_file_path(environment: str, config_dir: Path, explicit_file: Optional[Path]) -> Tuple[Path, str]:
    """Determine which config file should be edited."""
    if explicit_file:
        return explicit_file, environment
    env_file = config_dir / f"{environment}.yaml"
    if env_file.exists():
        return env_file, environment
    # fall back to default
    return config_dir / "default.yaml", "default"


def _emit_config_payload(ctx: click.Context, payload: Dict[str, Any], output_format: str = "auto") -> None:
    """Render config payload respecting CLI formatting preferences."""
    want_json = ctx.obj.get("json_output") or output_format == "json"
    if want_json:
        click.echo(json.dumps(payload, indent=2))
        return

    if output_format == "yaml":
        click.echo(yaml.safe_dump(payload, sort_keys=False))
        return

    # Default to table view using rich
    if isinstance(payload.get("config"), dict):
        table = Table(title=payload.get("section", "Configuration"), box=box.SIMPLE)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        for key, value in payload["config"].items():
            table.add_row(str(key), json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))
        console.print(table)
    else:
        console.print(Panel.fit(str(payload)))


def _determine_data_dir(path: Optional[Path], *, require_exists: bool = False) -> Path:
    """Resolve a blockchain data directory, optionally ensuring it exists."""
    resolved = (path or DEFAULT_DATA_DIR).expanduser()
    if require_exists and not resolved.exists():
        raise click.ClickException(
            f"Data directory '{resolved}' not found. Use --data-dir to target a valid node state."
        )
    if not require_exists:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_genesis_file(override_path: Optional[Path]) -> Tuple[Dict[str, Any], Path]:
    """Load genesis configuration from explicit path/env/package."""
    candidate_paths: List[Path] = []
    if override_path:
        candidate_paths.append(override_path.expanduser())
    env_path = os.getenv("XAI_GENESIS_PATH")
    if env_path:
        candidate_paths.append(Path(env_path).expanduser())
    try:
        pkg_genesis = importlib_resources.files("xai.core").joinpath("genesis.json")
        candidate_paths.append(Path(str(pkg_genesis)))
    except (FileNotFoundError, ModuleNotFoundError):
        pass

    for candidate in candidate_paths:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle), candidate

    raise click.ClickException(
        "Unable to locate genesis.json. Provide --genesis-path or set XAI_GENESIS_PATH."
    )


def _compute_genesis_hash(genesis_data: Dict[str, Any]) -> Tuple[str, str]:
    """Recompute declared vs actual genesis block hash."""
    from xai.core.transaction import Transaction
    from xai.core.block_header import BlockHeader
    from xai.core.blockchain_components.block import Block
    from xai.core.config import Config

    transactions: List[Transaction] = []
    for tx_data in genesis_data.get("transactions", []):
        outputs = tx_data.get("outputs") or [
            {"address": tx_data.get("recipient", ""), "amount": tx_data.get("amount", 0.0)}
        ]
        tx = Transaction(
            tx_data.get("sender", "COINBASE"),
            tx_data.get("recipient", ""),
            tx_data.get("amount", 0.0),
            fee=tx_data.get("fee", 0.0),
            tx_type=tx_data.get("tx_type", "coinbase"),
            outputs=outputs,
            metadata=tx_data.get("metadata") or {},
        )
        tx.timestamp = tx_data.get("timestamp", genesis_data.get("timestamp", time.time()))
        tx.signature = tx_data.get("signature")
        tx.txid = tx_data.get("txid") or tx.calculate_hash()
        transactions.append(tx)

    merkle_root = Block._calculate_merkle_root_static(transactions)
    header = BlockHeader(
        index=genesis_data.get("index", 0),
        previous_hash=genesis_data.get("previous_hash", "0" * 64),
        merkle_root=merkle_root,
        timestamp=genesis_data.get("timestamp", time.time()),
        difficulty=genesis_data.get("difficulty", Config.INITIAL_DIFFICULTY),
        nonce=genesis_data.get("nonce", 0),
        miner_pubkey=genesis_data.get("miner_pubkey", "genesis_miner_pubkey"),
        version=genesis_data.get("version", Config.BLOCK_HEADER_VERSION),
    )
    actual_hash = header.calculate_hash()
    return genesis_data.get("hash", ""), actual_hash


def _emit_admin_payload(ctx: click.Context, payload: Dict[str, Any], title: str) -> None:
    """Emit blockchain admin payload honoring global formatting flags."""
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(show_header=False, box=box.ROUNDED, title=title)
    for key, value in payload.items():
        table.add_row(f"[bold cyan]{key.replace('_', ' ').title()}[/]", str(value))
    console.print(Panel(table, border_style="cyan"))


def _create_blockchain_instance(data_dir: Path):
    """Instantiate a Blockchain for the given data dir."""
    from xai.core.blockchain import Blockchain

    return Blockchain(data_dir=str(data_dir))


class LocalNodeClient:
    """
    Direct-on-disk blockchain client used when the CLI runs with --transport local.

    Provides read-only access to blockchain data without requiring the HTTP API.
    Unsupported operations raise ClickException with guidance to use HTTP transport.
    """

    def __init__(self, data_dir: Path, mempool_limit: int = 200) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.api_key: Optional[str] = None  # parity with XAIClient attribute
        self._mempool_limit = max(1, mempool_limit)
        self._blockchain = None

    def _require_blockchain(self):
        if self._blockchain is None:
            if not self.data_dir.exists():
                raise click.ClickException(
                    f"Data directory '{self.data_dir}' not found. "
                    "Specify --data-dir pointing to a valid node state."
                )
            self._blockchain = _create_blockchain_instance(self.data_dir)
        return self._blockchain

    @staticmethod
    def _block_to_dict(block: Any) -> Dict[str, Any]:
        if hasattr(block, "to_dict") and callable(getattr(block, "to_dict")):
            return block.to_dict()
        if isinstance(block, dict):
            return block
        raise click.ClickException("Unable to serialize block in local transport.")

    @staticmethod
    def _unsupported(operation: str) -> None:
        raise click.ClickException(
            f"{operation} is unavailable with --transport local. "
            "Reconnect via HTTP (default) for live node capabilities."
        )

    def _estimate_hashrate(self, difficulty: Optional[float]) -> str:
        if not difficulty:
            return "unknown"
        try:
            from xai.core.config import Config
            target = getattr(Config, "BLOCK_TIME_TARGET", 120) or 120
        except Exception:
            target = 120
        hashrate = max(float(difficulty) / max(target, 1.0), 0.0)
        if hashrate >= 1e12:
            return f"{hashrate / 1e12:.2f} TH/s"
        if hashrate >= 1e9:
            return f"{hashrate / 1e9:.2f} GH/s"
        if hashrate >= 1e6:
            return f"{hashrate / 1e6:.2f} MH/s"
        if hashrate >= 1e3:
            return f"{hashrate / 1e3:.2f} kH/s"
        return f"{hashrate:.2f} H/s"

    def get_blockchain_info(self) -> Dict[str, Any]:
        chain = self._require_blockchain()
        stats = chain.get_stats()
        return {
            "transport": "local",
            "height": stats.get("chain_height", 0),
            "latest_block": stats.get("latest_block_hash", ""),
            "difficulty": stats.get("difficulty"),
            "pending_transactions": stats.get("pending_transactions_count", 0),
            "network_hashrate": self._estimate_hashrate(stats.get("difficulty")),
            "total_supply": stats.get("total_circulating_supply", 0.0),
            "data_dir": str(self.data_dir),
        }

    def get_block(self, block_id: str) -> Dict[str, Any]:
        chain = self._require_blockchain()
        block_obj = None
        try:
            index = int(block_id)
            block_obj = chain.get_block(index)
        except (TypeError, ValueError):
            normalized = block_id.strip()
            if normalized and normalized.startswith("0x"):
                normalized = normalized[2:]
            block_obj = chain.get_block_by_hash(normalized or block_id)
        if block_obj is None:
            raise click.ClickException(f"Block '{block_id}' not found in {self.data_dir}.")
        return {"block": self._block_to_dict(block_obj)}

    def get_balance(self, address: str) -> Dict[str, Any]:
        chain = self._require_blockchain()
        balance = chain.get_balance(address)
        return {
            "address": address,
            "balance": balance,
            "pending_incoming": 0.0,
            "pending_outgoing": 0.0,
        }

    def get_transaction_history(self, address: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        chain = self._require_blockchain()
        window, total = chain.get_transaction_history_window(address, limit, offset)
        return {
            "address": address,
            "transaction_count": total,
            "limit": limit,
            "offset": offset,
            "transactions": window,
        }

    def get_address_nonce(self, address: str) -> Dict[str, Any]:
        chain = self._require_blockchain()
        tracker = getattr(chain, "nonce_tracker", None)
        if tracker is None:
            raise click.ClickException("Nonce tracker unavailable in local transport.")
        confirmed = tracker.get_nonce(address)
        next_nonce = tracker.get_next_nonce(address)
        pending_nonce = next_nonce - 1 if next_nonce - 1 > confirmed else None
        return {
            "address": address,
            "confirmed_nonce": max(confirmed, -1),
            "next_nonce": next_nonce,
            "pending_nonce": pending_nonce,
        }

    def get_mempool(self) -> Dict[str, Any]:
        chain = self._require_blockchain()
        overview = chain.get_mempool_overview(self._mempool_limit)
        transactions = overview.get("transactions", []) if isinstance(overview, dict) else []
        return {"transactions": transactions, "overview": overview, "limit": self._mempool_limit}

    def get_state_snapshot(self) -> Dict[str, Any]:
        chain = self._require_blockchain()
        if not hasattr(chain, "compute_state_snapshot"):
            raise click.ClickException("State snapshots unavailable in this build.")
        snapshot = chain.compute_state_snapshot()
        return {"success": True, "state": snapshot}

    def validate_block(self, **kwargs: Any) -> Dict[str, Any]:
        self._unsupported("Block validation")

    def get_consensus_info(self) -> Dict[str, Any]:
        self._unsupported("Consensus metrics")

    def delete_mempool_transaction(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self._unsupported("Mempool eviction")

    def start_mining(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self._unsupported("Mining control")

    def stop_mining(self) -> Dict[str, Any]:
        self._unsupported("Mining control")

    def get_mining_status(self) -> Dict[str, Any]:
        self._unsupported("Mining status")

    def submit_signed_transaction(self, signed_payload: Dict[str, Any]) -> Dict[str, Any]:
        self._unsupported("Transaction submission")

    def get_network_info(self) -> Dict[str, Any]:
        self._unsupported("Network diagnostics")

    def get_peers(self) -> Dict[str, Any]:
        self._unsupported("Peer listing")


# ============================================================================
# CLI Groups
# ============================================================================

@click.group()
@click.option(
    '--node-url',
    default=DEFAULT_NODE_URL,
    help='XAI node URL',
    show_default=True,
)
@click.option(
    '--timeout',
    default=DEFAULT_TIMEOUT,
    type=float,
    help='Request timeout in seconds',
    show_default=True,
)
@click.option('--json-output', is_flag=True, help='Output raw JSON')
@click.option(
    '--api-key',
    envvar='XAI_API_KEY',
    help='API key for authenticated endpoints',
)
@click.option(
    '--transport',
    type=click.Choice(['http', 'local']),
    default='http',
    show_default=True,
    help='Communication transport. Use local to read blockchain data directly from disk.',
)
@click.option(
    '--local-data-dir',
    type=click.Path(file_okay=False, path_type=Path),
    help='Blockchain data directory used with --transport local (defaults to ~/.xai).',
)
@click.option(
    '--local-mempool-limit',
    type=click.IntRange(1, 1000),
    default=200,
    show_default=True,
    help='Maximum transactions returned from mempool when using local transport.',
)
@click.pass_context
def cli(
    ctx: click.Context,
    node_url: str,
    timeout: float,
    json_output: bool,
    api_key: Optional[str],
    transport: str,
    local_data_dir: Optional[Path],
    local_mempool_limit: int,
):
    """
    XAI Blockchain CLI - Revolutionary AI-Enhanced Blockchain

    A production-grade command-line interface for interacting with
    the XAI blockchain network, featuring AI compute jobs, mining,
    trading, and comprehensive blockchain operations.
    """
    ctx.ensure_object(dict)
    if transport == 'local':
        resolved_dir = _determine_data_dir(local_data_dir, require_exists=True)
        client_obj = LocalNodeClient(resolved_dir, mempool_limit=local_mempool_limit)
        logger.info("CLI using local transport", extra={"data_dir": str(resolved_dir)})
        effective_api_key = None
    else:
        client_obj = XAIClient(node_url, timeout, api_key=api_key)
        effective_api_key = api_key

    ctx.obj['client'] = client_obj
    ctx.obj['json_output'] = json_output
    ctx.obj['api_key'] = effective_api_key
    ctx.obj['transport'] = transport


def _generate_completion_script(prog_name: str, shell: str) -> str:
    """
    Generate shell completion script with Click if available, otherwise fallback.
    """
    shell = shell.lower()
    if _click_completion_script:
        return _click_completion_script(prog_name, shell)

    upper = prog_name.replace("-", "_").upper()
    if shell == "bash":
        return f"""_{prog_name}_completion() {{
    COMPREPLY=( $( env COMP_WORDS="${{COMP_WORDS[*]}}" COMP_CWORD=$COMP_CWORD _{upper}_COMPLETE=complete-bash {prog_name} ) )
    return 0
}}
complete -F _{prog_name}_completion {prog_name}
"""
    if shell == "zsh":
        return f"""#compdef {prog_name}
_{prog_name}_completion() {{
    eval $( env _{upper}_COMPLETE=complete-zsh {prog_name} )
}}
_{prog_name}_completion "$@"
"""
    raise click.ClickException("Unsupported shell for completion")


@cli.command("completion")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh"]),
    default="bash",
    show_default=True,
    help="Target shell for completion script.",
)
@click.pass_context
def completion(ctx: click.Context, shell: str):
    """Emit shell completion script for the XAI CLI."""
    prog_name = ctx.info_name or "xai"
    script = _generate_completion_script(prog_name, shell)
    click.echo(script)


# ============================================================================
# Config management group
# ============================================================================


@cli.group("config")
@click.option(
    "--environment",
    type=click.Choice(_config_env_choices()),
    default="development",
    show_default=True,
    help="Configuration environment to manage.",
)
@click.option(
    "--config-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=CONFIG_DEFAULT_DIR,
    show_default=True,
    help="Directory containing environment config files.",
)
@click.option(
    "--config-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional explicit config file path to inspect/edit.",
)
@click.pass_context
def config_group(ctx: click.Context, environment: str, config_dir: Path, config_file: Optional[Path]):
    """Manage node configuration files with validation and safe editing."""
    ctx.ensure_object(dict)
    ctx.obj["config_ctx"] = {
        "environment": environment,
        "config_dir": config_dir,
        "config_file": config_file,
    }


def _config_context(ctx: click.Context) -> Dict[str, Any]:
    """Fetch configuration CLI context."""
    config_ctx = ctx.obj.get("config_ctx")
    if not config_ctx:
        raise click.ClickException("Configuration context unavailable.")
    return config_ctx


def _create_config_manager(ctx: click.Context) -> ConfigManager:
    """Instantiate ConfigManager respecting CLI context."""
    config_ctx = _config_context(ctx)
    return ConfigManager(
        environment=config_ctx["environment"],
        config_dir=str(config_ctx["config_dir"]),
    )


@config_group.command("show")
@click.option("--section", help="Return only a specific configuration section.")
@click.option("--key", help="Return a single config value via dot-notation (e.g., network.port).")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["auto", "json", "yaml"]),
    default="auto",
    show_default=True,
)
@click.pass_context
def config_show(ctx: click.Context, section: Optional[str], key: Optional[str], output_format: str):
    """Display current configuration for the selected environment."""
    manager = _create_config_manager(ctx)
    if key:
        value = manager.get(key)
        if value is None:
            raise click.ClickException(f"Unknown configuration key '{key}'.")
        payload = {"key": key, "value": value, "environment": manager.environment.value}
    elif section:
        section_data = manager.get_section(section)
        if section_data is None:
            raise click.ClickException(f"Configuration section '{section}' not found.")
        payload = {"section": section, "config": section_data, "environment": manager.environment.value}
    else:
        payload = {"environment": manager.environment.value, "config": manager.to_dict()}
    _emit_config_payload(ctx, payload, output_format)


@config_group.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str):
    """Fetch a single configuration value."""
    manager = _create_config_manager(ctx)
    value = manager.get(key)
    if value is None:
        raise click.ClickException(f"Configuration key '{key}' not found.")
    _emit_config_payload(ctx, {"key": key, "value": value, "environment": manager.environment.value}, "json")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--value-type",
    type=click.Choice(["auto", "int", "float", "bool", "string", "str", "json"]),
    default="auto",
    show_default=True,
    help="Interpretation for the provided value.",
)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, value_type: str):
    """Update a configuration value with validation."""
    config_ctx = _config_context(ctx)
    config_file, file_env = _resolve_config_file_path(
        config_ctx["environment"],
        config_ctx["config_dir"],
        config_ctx["config_file"],
    )
    parsed_value = _parse_config_value(value, value_type)
    parts = key.split(".")
    if not parts:
        raise click.ClickException("Invalid configuration key.")

    click.echo(f"Updating {key} in {config_file} ({file_env} environment)...")
    data = _read_yaml_config(config_file)
    updated = deepcopy(data)
    _set_nested_value(updated, parts, parsed_value)

    previous_text = config_file.read_text(encoding="utf-8") if config_file.exists() else None
    try:
        _write_yaml_config(config_file, updated)
        # validation via ConfigManager; raises on invalid configuration
        ConfigManager(environment=config_ctx["environment"], config_dir=str(config_ctx["config_dir"]))
    except Exception as exc:  # broad to rollback on any failure
        if previous_text is not None:
            config_file.write_text(previous_text, encoding="utf-8")
        else:
            config_file.unlink(missing_ok=True)
        raise click.ClickException(f"Failed to apply configuration: {exc}") from exc

    console.print(
        f"[bold green]Configuration updated:[/] {key} = {parsed_value} "
        f"(environment={config_ctx['environment']})"
    )


# ============================================================================
# Wallet Commands
# ============================================================================

@cli.group()
def wallet():
    """Wallet management commands"""
    pass


@wallet.command('create')
@click.option('--save-keystore', is_flag=True, help='Save to encrypted keystore')
@click.option('--keystore-output', type=click.Path(), help='Keystore output path')
@click.option('--kdf', type=click.Choice(['pbkdf2', 'argon2id']), default='pbkdf2',
              help='Key derivation function')
@click.pass_context
def wallet_create(ctx: click.Context, save_keystore: bool, keystore_output: Optional[str], kdf: str):
    """Create a new wallet"""
    from xai.core.wallet import Wallet
    from xai.wallet.cli import create_keystore

    with console.status("[bold green]Generating wallet..."):
        wallet = Wallet()

    if ctx.obj['json_output']:
        click.echo(json.dumps({
            "address": wallet.address,
            "public_key": wallet.public_key
        }, indent=2))
        return

    # Display wallet info in a beautiful panel
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Address", wallet.address)
    table.add_row("[bold cyan]Public Key", wallet.public_key[:40] + "...")

    console.print(Panel(table, title="[bold green]New Wallet Created",
                       border_style="green"))

    if save_keystore:
        try:
            keystore_path = create_keystore(
                address=wallet.address,
                private_key=wallet.private_key,
                public_key=wallet.public_key,
                output_path=keystore_output,
                kdf=kdf
            )
            console.print(f"\n[bold green]✓[/] Encrypted keystore saved to: [cyan]{keystore_path}[/]")
        except (click.ClickException, ValueError, OSError) as exc:
            _cli_fail(exc)
    else:
        console.print("\n[yellow]⚠[/] Private key not saved. Use --save-keystore to encrypt and save.")


@wallet.command('balance')
@click.argument('address')
@click.pass_context
def wallet_balance(ctx: click.Context, address: str):
    """Check wallet balance"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status(f"[bold cyan]Fetching balance for {address[:20]}..."):
            data = client.get_balance(address)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        balance = data.get('balance', 0)
        pending_in = data.get('pending_incoming', 0)
        pending_out = data.get('pending_outgoing', 0)

        # Create beautiful balance display
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Address", address[:40] + "...")
        table.add_row("[bold green]Balance", f"{balance:.8f} XAI")
        if pending_in > 0:
            table.add_row("[bold yellow]Pending In", f"{pending_in:.8f} XAI")
        if pending_out > 0:
            table.add_row("[bold yellow]Pending Out", f"{pending_out:.8f} XAI")

        console.print(Panel(table, title="[bold green]Wallet Balance",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('history')
@click.argument('address')
@click.option('--limit', default=10, help='Number of transactions to show')
@click.option('--offset', default=0, help='Pagination offset')
@click.pass_context
def wallet_history(ctx: click.Context, address: str, limit: int, offset: int):
    """View transaction history"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching transaction history..."):
            data = client.get_transaction_history(address, limit, offset)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        transactions = data.get('transactions', [])

        if not transactions:
            console.print("[yellow]No transactions found[/]")
            return

        # Create beautiful transaction table
        table = Table(title=f"Transaction History - {address[:20]}...",
                     box=box.ROUNDED, show_lines=True)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("From/To", style="yellow")
        table.add_column("TX ID", style="blue")

        for tx in transactions:
            timestamp = datetime.fromtimestamp(tx.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
            tx_type = "Sent" if tx.get('sender') == address else "Received"
            amount = f"{tx.get('amount', 0):.8f} XAI"
            other_addr = tx.get('recipient' if tx_type == "Sent" else 'sender', 'N/A')[:20]
            tx_id = tx.get('txid', 'N/A')[:16]

            table.add_row(timestamp, tx_type, amount, other_addr + "...", tx_id + "...")

        console.print(table)

        if len(transactions) == limit:
            console.print(f"\n[dim]Showing {limit} transactions. Use --limit and --offset for more.[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('send')
@click.option('--sender', required=True, help='Sender address')
@click.option('--recipient', required=True, help='Recipient address')
@click.option('--amount', required=True, type=float, help='Amount to send')
@click.option('--fee', default=0.001, type=float, help='Transaction fee')
@click.option('--keystore', type=click.Path(exists=True), help='Keystore file path')
@click.pass_context
def wallet_send(ctx: click.Context, sender: str, recipient: str, amount: float,
                fee: float, keystore: Optional[str]):
    """Send XAI to another address"""
    from xai.wallet.cli import get_private_key_secure

    # Confirm transaction
    console.print("\n[bold yellow]Transaction Summary:[/]")
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_row("From", sender[:40] + "...")
    table.add_row("To", recipient[:40] + "...")
    table.add_row("Amount", f"{amount:.8f} XAI")
    table.add_row("Fee", f"{fee:.8f} XAI")
    table.add_row("Total", f"{amount + fee:.8f} XAI")
    console.print(table)

    if not Confirm.ask("\n[bold]Confirm transaction?[/]", default=False):
        console.print("[yellow]Transaction cancelled[/]")
        return

    client: XAIClient = ctx.obj['client']

    try:
        nonce_resp = client.get_address_nonce(sender)
        nonce = nonce_resp.get("next_nonce")
        if nonce is None:
            raise click.ClickException("Nonce unavailable for sender")

        # Build canonical payload for preview
        base_tx = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "fee": fee,
            "nonce": int(nonce),
            "tx_type": "normal",
            "metadata": {},
            "timestamp": time.time(),
        }
        payload_str, tx_hash, canonical_payload = signing_preview(base_tx)

        console.print("\n[bold cyan]Signing payload:[/]")
        console.print(Syntax(payload_str, "json", theme="monokai", word_wrap=True))
        console.print(f"\n[bold]Signing hash:[/] [cyan]{tx_hash}[/]")

        ack = Prompt.ask(
            f"Type the first 8+ characters of the signing hash to confirm",
            default="",
            show_default=False,
        )
        if not ack or len(ack.strip()) < 8 or not tx_hash.lower().startswith(ack.strip().lower()):
            console.print("[bold red]Acknowledgement mismatch. Aborting before using private key.[/]")
            return

        # Security: Get private key securely *after* user has acknowledged the payload/hash
        try:
            private_key = get_private_key_secure(
                keystore_path=keystore,
                allow_env=False,
                prompt="Enter sender's private key"
            )
        except (click.ClickException, ValueError, OSError) as exc:
            _cli_fail(exc)

        signed_payload = sign_offline(base_tx, private_key, acknowledged_digest=ack.strip())
        submission_payload = {
            "sender": canonical_payload["sender"],
            "recipient": canonical_payload["recipient"],
            "amount": canonical_payload["amount"],
            "fee": canonical_payload["fee"],
            "nonce": canonical_payload["nonce"],
            "timestamp": canonical_payload["timestamp"],
            "public_key": signed_payload["public_key"],
            "signature": signed_payload["signature"],
            "metadata": canonical_payload["metadata"] or None,
            "txid": signed_payload["txid"],
        }

        with console.status("[bold cyan]Sending transaction..."):
            result = client.submit_signed_transaction(submission_payload)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("\n[bold green]✓ Transaction sent successfully![/]")
            console.print(f"TX ID: [cyan]{result.get('txid', 'pending')}[/]")
        else:
            console.print(f"\n[bold red]✗ Transaction failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('portfolio')
@click.argument('address')
@click.pass_context
def wallet_portfolio(ctx: click.Context, address: str):
    """Show complete wallet portfolio"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Loading portfolio..."):
            balance_data = client.get_balance(address)
            history_data = client.get_transaction_history(address, limit=100)

        if ctx.obj['json_output']:
            click.echo(json.dumps({
                'balance': balance_data,
                'history': history_data
            }, indent=2))
            return

        # Calculate portfolio stats
        balance = balance_data.get('balance', 0)
        transactions = history_data.get('transactions', [])

        total_sent = sum(tx.get('amount', 0) for tx in transactions if tx.get('sender') == address)
        total_received = sum(tx.get('amount', 0) for tx in transactions if tx.get('recipient') == address)
        tx_count = len(transactions)

        # Portfolio panel
        layout = Layout()
        layout.split_column(
            Layout(name="balance"),
            Layout(name="stats")
        )

        # Balance table
        balance_table = Table(show_header=False, box=box.ROUNDED)
        balance_table.add_row("[bold cyan]Current Balance", f"[bold green]{balance:.8f} XAI[/]")
        balance_table.add_row("[bold cyan]Total Received", f"{total_received:.8f} XAI")
        balance_table.add_row("[bold cyan]Total Sent", f"{total_sent:.8f} XAI")
        balance_table.add_row("[bold cyan]Transaction Count", str(tx_count))

        console.print(Panel(balance_table, title=f"[bold green]Portfolio - {address[:20]}...",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Blockchain Commands
# ============================================================================

@cli.group()
def blockchain():
    """Blockchain information commands"""
    pass


@blockchain.command('info')
@click.pass_context
def blockchain_info(ctx: click.Context):
    """Get blockchain information"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching blockchain info..."):
            data = client.get_blockchain_info()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        # Create beautiful info panel
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Chain Height", str(data.get('height', 0)))
        table.add_row("[bold cyan]Latest Block", data.get('latest_block', 'N/A')[:40])
        table.add_row("[bold cyan]Difficulty", str(data.get('difficulty', 0)))
        table.add_row("[bold cyan]Pending Transactions", str(data.get('pending_transactions', 0)))
        table.add_row("[bold cyan]Network Hashrate", data.get('network_hashrate', 'N/A'))
        table.add_row("[bold cyan]Total Supply", f"{data.get('total_supply', 0):.2f} XAI")

        console.print(Panel(table, title="[bold green]Blockchain Information",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('block')
@click.argument('block_id')
@click.pass_context
def blockchain_block(ctx: click.Context, block_id: str):
    """Get block by index or hash"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status(f"[bold cyan]Fetching block {block_id}..."):
            data = client.get_block(block_id)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        block = data.get('block', {})

        # Block header table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Index", str(block.get('index', 0)))
        table.add_row("[bold cyan]Hash", block.get('hash', 'N/A')[:64])
        table.add_row("[bold cyan]Previous Hash", block.get('previous_hash', 'N/A')[:64])
        table.add_row("[bold cyan]Timestamp", datetime.fromtimestamp(
            block.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("[bold cyan]Difficulty", str(block.get('difficulty', 0)))
        table.add_row("[bold cyan]Nonce", str(block.get('nonce', 0)))
        table.add_row("[bold cyan]Transactions", str(len(block.get('transactions', []))))
        table.add_row("[bold cyan]Miner", block.get('miner', 'N/A')[:40])

        console.print(Panel(table, title=f"[bold green]Block {block_id}",
                           border_style="green"))

        # Show transactions if any
        transactions = block.get('transactions', [])
        if transactions:
            console.print(f"\n[bold]Transactions ({len(transactions)}):[/]")
            for i, tx in enumerate(transactions[:10], 1):
                console.print(f"  {i}. {tx.get('sender', 'N/A')[:20]}... → "
                            f"{tx.get('recipient', 'N/A')[:20]}... "
                            f"[green]{tx.get('amount', 0):.8f} XAI[/]")
            if len(transactions) > 10:
                console.print(f"  [dim]... and {len(transactions) - 10} more[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('mempool')
@click.pass_context
def blockchain_mempool(ctx: click.Context):
    """View pending transactions in mempool"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching mempool..."):
            data = client.get_mempool()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        transactions = data.get('transactions', [])

        if not transactions:
            console.print("[yellow]Mempool is empty[/]")
            return

        # Mempool table
        table = Table(title=f"Mempool - {len(transactions)} Pending Transactions",
                     box=box.ROUNDED)
        table.add_column("TX ID", style="cyan")
        table.add_column("From", style="yellow")
        table.add_column("To", style="yellow")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Fee", style="magenta", justify="right")

        for tx in transactions[:20]:
            table.add_row(
                tx.get('txid', 'N/A')[:16] + "...",
                tx.get('sender', 'N/A')[:20] + "...",
                tx.get('recipient', 'N/A')[:20] + "...",
                f"{tx.get('amount', 0):.8f}",
                f"{tx.get('fee', 0):.8f}"
            )

        console.print(table)

        if len(transactions) > 20:
            console.print(f"\n[dim]Showing 20 of {len(transactions)} transactions[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('state')
@click.pass_context
def blockchain_state(ctx: click.Context):
    """Inspect deterministic chain state snapshot."""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching state snapshot..."):
            data = client.get_state_snapshot()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        state = data.get("state", {})
        table = Table(show_header=False, box=box.ROUNDED, title="State Snapshot")
        table.add_row("[bold cyan]Height", str(state.get("height", 0)))
        table.add_row("[bold cyan]Tip Hash", (state.get("tip") or "")[:64])
        table.add_row("[bold cyan]UTXO Digest", state.get("utxo_digest", "unavailable"))
        table.add_row("[bold cyan]Pending Transactions", str(state.get("pending_transactions", 0)))
        table.add_row("[bold cyan]Mempool Bytes", str(state.get("mempool_bytes", 0)))
        table.add_row("[bold cyan]Timestamp", datetime.fromtimestamp(state.get("timestamp", time.time())).isoformat())
        console.print(Panel(table, border_style="cyan"))
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('validate-block')
@click.option('--index', type=int, help='Block height to validate')
@click.option('--hash', 'block_hash', help='Block hash to validate')
@click.option('--include-transactions/--skip-transactions', default=True, show_default=True,
              help='Perform full transaction validation as well')
@click.pass_context
def blockchain_validate_block(
    ctx: click.Context,
    index: Optional[int],
    block_hash: Optional[str],
    include_transactions: bool,
):
    """Validate a block header and optionally its transactions."""
    if index is None and not block_hash:
        raise click.ClickException("Provide either --index or --hash for block validation.")

    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Validating block..."):
            result = client.validate_block(
                index=index,
                block_hash=block_hash,
                include_transactions=include_transactions,
            )

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        status = "[bold green]VALID[/]" if result.get("valid") else "[bold red]INVALID[/]"
        table = Table(show_header=False, box=box.ROUNDED, title="Block Validation")
        table.add_row("[bold cyan]Result", status)
        table.add_row("[bold cyan]Block Index", str(result.get("block_index")))
        table.add_row("[bold cyan]Block Hash", str(result.get("block_hash")))
        if result.get("error"):
            table.add_row("[bold red]Error", result.get("error"))
        if include_transactions:
            tx_status = "VALID" if result.get("transactions_valid") else "INVALID"
            table.add_row("[bold cyan]Transactions", tx_status)
            if result.get("transactions_error"):
                table.add_row("[bold red]TX Error", result.get("transactions_error"))
        console.print(Panel(table, border_style="cyan"))
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('consensus')
@click.pass_context
def blockchain_consensus(ctx: click.Context):
    """Show consensus manager status and metrics."""
    client: XAIClient = ctx.obj['client']
    try:
        with console.status("[bold cyan]Fetching consensus info..."):
            data = client.get_consensus_info()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        info = data.get("consensus", {})
        table = Table(show_header=False, box=box.ROUNDED, title="Consensus Info")
        for key, value in info.items():
            table.add_row(f"[bold cyan]{key}", json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))
        console.print(Panel(table, border_style="cyan"))
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.group("genesis")
def blockchain_genesis():
    """Inspect and verify genesis configuration."""
    pass


@blockchain_genesis.command("show")
@click.option(
    "--genesis-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Explicit path to genesis.json (defaults to packaged file or XAI_GENESIS_PATH).",
)
@click.pass_context
def blockchain_genesis_show(ctx: click.Context, genesis_path: Optional[Path]):
    """Display genesis allocation summary."""
    data, source_path = _load_genesis_file(genesis_path)
    total_allocation = sum(tx.get("amount", 0.0) for tx in data.get("transactions", []))
    tx_count = len(data.get("transactions", []))
    summary = {
        "genesis_path": str(source_path),
        "index": data.get("index", 0),
        "timestamp": data.get("timestamp"),
        "transaction_count": tx_count,
        "total_allocation": total_allocation,
        "declared_hash": data.get("hash"),
    }
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(summary, indent=2))
        return

    table = Table(title="Genesis Summary", box=box.ROUNDED)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    for key, value in summary.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    console.print(Panel(table, border_style="cyan"))


@blockchain_genesis.command("verify")
@click.option(
    "--genesis-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Explicit path to genesis.json.",
)
@click.pass_context
def blockchain_genesis_verify(ctx: click.Context, genesis_path: Optional[Path]):
    """Verify declared genesis hash matches computed hash."""
    from xai.core.config import Config

    data, source_path = _load_genesis_file(genesis_path)
    declared_hash, actual_hash = _compute_genesis_hash(data)
    expected_hash = getattr(Config, "SAFE_GENESIS_HASHES", {}).get(getattr(Config, "NETWORK_TYPE", ""), "")
    payload = {
        "genesis_path": str(source_path),
        "declared_hash": declared_hash or "N/A",
        "calculated_hash": actual_hash,
        "hash_match": bool(declared_hash) and declared_hash == actual_hash,
        "expected_network_hash": expected_hash,
        "matches_expected": bool(expected_hash) and actual_hash == expected_hash,
    }
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2))
    else:
        table = Table(title="Genesis Verification", box=box.ROUNDED)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        for key, value in payload.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        console.print(Panel(table, border_style="cyan"))


@blockchain.command("checkpoints")
@click.option(
    "--data-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_DATA_DIR,
    show_default=True,
    help="Node data directory containing checkpoint snapshots.",
)
@click.option("--limit", type=int, default=10, show_default=True, help="Maximum checkpoints to display.")
@click.pass_context
def blockchain_checkpoints(ctx: click.Context, data_dir: Path, limit: int):
    """List checkpoints available on disk."""
    from xai.core.checkpoints import CheckpointManager

    resolved = _determine_data_dir(data_dir, require_exists=True)
    manager = CheckpointManager(data_dir=str(resolved))
    heights = sorted(manager.list_checkpoints(), reverse=True)
    rows: List[Dict[str, Any]] = []
    for height in heights[: max(limit, 0)]:
        checkpoint = manager.load_checkpoint(height)
        rows.append(
            {
                "height": height,
                "hash": checkpoint.block_hash if checkpoint else "unknown",
                "timestamp": checkpoint.timestamp if checkpoint else None,
                "difficulty": checkpoint.difficulty if checkpoint else None,
            }
        )

    payload = {"data_dir": str(resolved), "checkpoints": rows, "total": len(heights)}
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2))
    else:
        if not rows:
            console.print(f"[yellow]No checkpoints found in {resolved}[/]")
            return
        table = Table(title=f"Checkpoints ({payload['total']} total)", box=box.ROUNDED)
        table.add_column("Height", style="cyan", justify="right")
        table.add_column("Hash", style="green")
        table.add_column("Timestamp", style="magenta")
        table.add_column("Difficulty", style="yellow")
        for entry in rows:
            timestamp = entry["timestamp"]
            human_time = datetime.fromtimestamp(timestamp).isoformat() if timestamp else "unknown"
            table.add_row(
                str(entry["height"]),
                (entry["hash"] or "")[:32] + ("..." if entry["hash"] and len(entry["hash"]) > 32 else ""),
                human_time,
                str(entry["difficulty"] or "unknown"),
            )
        console.print(Panel(table, border_style="cyan"))


@blockchain.command("reset")
@click.option(
    "--data-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_DATA_DIR,
    show_default=True,
    help="Directory containing blockchain data to reset.",
)
@click.option(
    "--preserve-checkpoints/--purge-checkpoints",
    default=False,
    show_default=True,
    help="Keep checkpoint snapshots instead of deleting them.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def blockchain_reset(ctx: click.Context, data_dir: Path, preserve_checkpoints: bool, yes: bool):
    """Reset local blockchain storage back to genesis."""
    resolved = _determine_data_dir(data_dir, require_exists=False)
    if not yes:
        if not Confirm.ask(
            f"[bold yellow]Reset blockchain data in {resolved}? This removes block files and UTXOs.[/]"
        ):
            console.print("[yellow]Reset aborted[/]")
            return
    try:
        blockchain = _create_blockchain_instance(resolved)
        summary = blockchain.reset_chain_state(preserve_checkpoints=preserve_checkpoints)
    except Exception as exc:
        raise click.ClickException(f"Chain reset failed: {exc}") from exc

    summary.update(
        {
            "data_dir": str(resolved),
            "checkpoints_action": "preserved" if preserve_checkpoints else "purged",
        }
    )
    _emit_admin_payload(ctx, summary, "Chain Reset")


@blockchain.command("rollback")
@click.option(
    "--data-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_DATA_DIR,
    show_default=True,
    help="Directory containing blockchain data.",
)
@click.option("--height", type=int, required=True, help="Checkpoint height to restore.")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def blockchain_rollback(ctx: click.Context, data_dir: Path, height: int, yes: bool):
    """Rollback local state to a specific checkpoint height."""
    if height < 0:
        raise click.ClickException("Height must be non-negative.")
    resolved = _determine_data_dir(data_dir, require_exists=True)
    if not yes:
        if not Confirm.ask(
            f"[bold yellow]Restore checkpoint at height {height} in {resolved}? This rewinds the chain.[/]"
        ):
            console.print("[yellow]Rollback aborted[/]")
            return
    try:
        blockchain = _create_blockchain_instance(resolved)
        summary = blockchain.restore_checkpoint(height)
    except Exception as exc:
        raise click.ClickException(f"Checkpoint restore failed: {exc}") from exc

    summary["data_dir"] = str(resolved)
    _emit_admin_payload(ctx, summary, "Checkpoint Rollback")


@cli.group()
def mempool():
    """Mempool management operations."""
    pass


@mempool.command("drop")
@click.argument("txid")
@click.option("--ban-sender", is_flag=True, help="Temporarily ban sender after eviction")
@click.pass_context
def mempool_drop(ctx: click.Context, txid: str, ban_sender: bool):
    """Evict a transaction from the mempool (requires API key with admin scope)."""
    client: XAIClient = ctx.obj['client']
    if not client.api_key:
        raise click.ClickException("API key required for mempool management. Provide --api-key or XAI_API_KEY.")

    try:
        with console.status(f"[bold cyan]Dropping {txid[:12]}..."):
            result = client.delete_mempool_transaction(txid, ban_sender=ban_sender)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            message = f"Transaction {txid} evicted"
            if result.get("ban_applied"):
                message += " and sender banned temporarily"
            console.print(f"[bold green]✓ {message}[/]")
        else:
            console.print(f"[bold red]✗ Failed to evict transaction:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Mining Commands
# ============================================================================

@cli.group()
def mining():
    """Mining operations"""
    pass


@mining.command('start')
@click.option('--address', required=True, help='Miner address (receives rewards)')
@click.option('--threads', default=1, type=int, help='Number of mining threads')
@click.option('--intensity', default=1, type=int, help='Mining intensity (1-10)')
@click.pass_context
def mining_start(ctx: click.Context, address: str, threads: int, intensity: int):
    """Start mining"""
    client: XAIClient = ctx.obj['client']

    console.print(f"[bold cyan]Starting mining...[/]")
    console.print(f"  Address: {address}")
    console.print(f"  Threads: {threads}")
    console.print(f"  Intensity: {intensity}\n")

    try:
        result = client.start_mining(address, threads, intensity)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("[bold green]✓ Mining started successfully![/]")
        else:
            console.print(f"[bold red]✗ Failed to start mining:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('stop')
@click.pass_context
def mining_stop(ctx: click.Context):
    """Stop mining"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Stopping mining..."):
            result = client.stop_mining()

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("[bold green]✓ Mining stopped[/]")
        else:
            console.print(f"[bold red]✗ Failed to stop mining:[/] {result.get('error', 'Unknown')}")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('status')
@click.pass_context
def mining_status(ctx: click.Context):
    """Check mining status"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching mining status..."):
            data = client.get_mining_status()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        is_mining = data.get('mining', False)

        if not is_mining:
            console.print("[yellow]Mining is not active[/]")
            return

        # Mining status table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Status", "[bold green]Active[/]")
        table.add_row("[bold cyan]Miner Address", data.get('miner_address', 'N/A')[:40])
        table.add_row("[bold cyan]Threads", str(data.get('threads', 0)))
        table.add_row("[bold cyan]Hashrate", data.get('hashrate', 'N/A'))
        table.add_row("[bold cyan]Blocks Mined", str(data.get('blocks_mined', 0)))
        table.add_row("[bold cyan]Total Rewards", f"{data.get('total_rewards', 0):.8f} XAI")

        console.print(Panel(table, title="[bold green]Mining Status",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('stats')
@click.option('--address', required=True, help='Miner address')
@click.pass_context
def mining_stats(ctx: click.Context, address: str):
    """Detailed mining statistics"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Calculating mining statistics..."):
            balance_data = client.get_balance(address)
            history_data = client.get_transaction_history(address, limit=100)

        if ctx.obj['json_output']:
            click.echo(json.dumps({
                'balance': balance_data,
                'history': history_data
            }, indent=2))
            return

        # Calculate mining stats from transaction history
        transactions = history_data.get('transactions', [])
        mining_rewards = [tx for tx in transactions if tx.get('type') == 'mining_reward']

        total_rewards = sum(tx.get('amount', 0) for tx in mining_rewards)
        blocks_mined = len(mining_rewards)

        # Stats table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Miner Address", address[:40] + "...")
        table.add_row("[bold cyan]Blocks Mined", str(blocks_mined))
        table.add_row("[bold cyan]Total Rewards", f"{total_rewards:.8f} XAI")
        table.add_row("[bold cyan]Current Balance", f"{balance_data.get('balance', 0):.8f} XAI")
        if blocks_mined > 0:
            table.add_row("[bold cyan]Avg Reward/Block", f"{total_rewards/blocks_mined:.8f} XAI")

        console.print(Panel(table, title="[bold green]Mining Statistics",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Network Commands
# ============================================================================

@cli.group()
def network():
    """Network information commands"""
    pass


@network.command('info')
@click.pass_context
def network_info(ctx: click.Context):
    """Get network information"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching network info..."):
            data = client.get_network_info()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        # Network info table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Network", data.get('network', 'mainnet'))
        table.add_row("[bold cyan]Version", data.get('version', 'N/A'))
        table.add_row("[bold cyan]Node ID", data.get('node_id', 'N/A')[:40])
        table.add_row("[bold cyan]Connected Peers", str(data.get('peer_count', 0)))
        table.add_row("[bold cyan]Network Hashrate", data.get('network_hashrate', 'N/A'))
        table.add_row("[bold cyan]Sync Status",
                     "[green]Synced[/]" if data.get('synced') else "[yellow]Syncing...[/]")

        console.print(Panel(table, title="[bold green]Network Information",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@network.command('peers')
@click.pass_context
def network_peers(ctx: click.Context):
    """List connected peers"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching peers..."):
            data = client.get_peers()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        peers = data.get('peers', [])

        if not peers:
            console.print("[yellow]No peers connected[/]")
            return

        # Peers table
        table = Table(title=f"Connected Peers - {len(peers)} nodes",
                     box=box.ROUNDED)
        table.add_column("Node ID", style="cyan")
        table.add_column("Address", style="yellow")
        table.add_column("Version", style="green")
        table.add_column("Connected", style="magenta")

        for peer in peers:
            node_id = peer.get('node_id', 'N/A')[:16] + "..."
            address = peer.get('address', 'N/A')
            version = peer.get('version', 'N/A')
            connected_time = peer.get('connected_time', 0)

            # Format connection duration
            duration = int(time.time() - connected_time) if connected_time else 0
            if duration < 60:
                duration_str = f"{duration}s"
            elif duration < 3600:
                duration_str = f"{duration//60}m"
            else:
                duration_str = f"{duration//3600}h"

            table.add_row(node_id, address, version, duration_str)

        console.print(table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# AI Commands (Revolutionary AI-Blockchain Features)
# Import production-grade AI commands module
# ============================================================================

from xai.cli.ai_commands import ai

# Register AI commands group
cli.add_command(ai)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main CLI entry point"""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/]")
        sys.exit(130)
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


if __name__ == '__main__':
    main()

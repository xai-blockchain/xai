#!/usr/bin/env python3
"""
XAI Smart Contract CLI Commands - Contract Management Interface

Provides CLI equivalents for smart contract API endpoints:
- Deploy contracts
- Call contract functions
- View contract information and state
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any

try:
    import click
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich.table import Table
except ImportError:
    print("ERROR: Required packages not installed. Install with:")
    print("  pip install click rich")
    sys.exit(1)

import requests

from xai.wallet.offline_signing import sign_offline, signing_preview

logger = logging.getLogger(__name__)
console = Console()


def _handle_cli_error(exc: Exception, exit_code: int = 1) -> None:
    """Centralized CLI error handler for consistent messaging/exit codes."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


class ContractClient:
    """Client for smart contract API operations."""

    def __init__(self, node_url: str, timeout: float = 30.0, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to contract endpoint."""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Contract request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=headers, **kwargs
            )
            response.raise_for_status()
            logger.debug("Contract response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Contract API error: %s", e)
            raise click.ClickException(f"Contract API error: {e}")

    def deploy_contract(
        self,
        sender: str,
        bytecode: str,
        value: float,
        fee: float,
        gas_limit: int,
        public_key: str,
        signature: str,
        nonce: int | None = None,
        abi: Any | None = None,
    ) -> dict[str, Any]:
        """Deploy a smart contract."""
        payload = {
            "sender": sender,
            "bytecode": bytecode,
            "value": value,
            "fee": fee,
            "gas_limit": gas_limit,
            "public_key": public_key,
            "signature": signature,
            "metadata": {},
        }
        if nonce is not None:
            payload["nonce"] = nonce
        if abi:
            payload["metadata"]["abi"] = abi
        return self._request("POST", "/contracts/deploy", json=payload)

    def call_contract(
        self,
        sender: str,
        contract_address: str,
        value: float,
        fee: float,
        gas_limit: int,
        public_key: str,
        signature: str,
        payload: dict[str, Any] | None = None,
        data: str | None = None,
        nonce: int | None = None,
    ) -> dict[str, Any]:
        """Call a smart contract function."""
        request_payload: dict[str, Any] = {
            "sender": sender,
            "contract_address": contract_address,
            "value": value,
            "fee": fee,
            "gas_limit": gas_limit,
            "public_key": public_key,
            "signature": signature,
        }
        if payload is not None:
            request_payload["payload"] = payload
        elif data:
            request_payload["data"] = data
        if nonce is not None:
            request_payload["nonce"] = nonce
        return self._request("POST", "/contracts/call", json=request_payload)

    def get_contract_state(self, address: str) -> dict[str, Any]:
        """Get contract state."""
        return self._request("GET", f"/contracts/{address}/state")

    def get_contract_abi(self, address: str) -> dict[str, Any]:
        """Get contract ABI."""
        return self._request("GET", f"/contracts/{address}/abi")

    def get_contract_events(
        self, address: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Get contract events."""
        return self._request(
            "GET",
            f"/contracts/{address}/events",
            params={"limit": limit, "offset": offset},
        )

    def get_contract_interfaces(self, address: str) -> dict[str, Any]:
        """Detect contract interfaces."""
        return self._request("GET", f"/contracts/{address}/interfaces")

    def get_feature_status(self) -> dict[str, Any]:
        """Get smart contract feature status."""
        return self._request("GET", "/contracts/governance/status")

    def get_nonce(self, address: str) -> dict[str, Any]:
        """Get address nonce."""
        return self._request("GET", f"/address/{address}/nonce")


@click.group()
def contract():
    """Smart contract deployment and interaction commands."""
    pass


@contract.command("deploy")
@click.option("--sender", required=True, help="Deployer wallet address")
@click.option("--bytecode", required=True, help="Hex-encoded contract bytecode")
@click.option("--value", default=0.0, type=float, help="Initial contract balance")
@click.option("--fee", default=0.01, type=float, help="Transaction fee")
@click.option("--gas-limit", default=1000000, type=int, help="Gas limit for deployment")
@click.option("--keystore", type=click.Path(exists=True), help="Keystore file for signing")
@click.option("--abi-file", type=click.Path(exists=True), help="Path to contract ABI JSON file")
@click.pass_context
def deploy_contract(
    ctx: click.Context,
    sender: str,
    bytecode: str,
    value: float,
    fee: float,
    gas_limit: int,
    keystore: str | None,
    abi_file: str | None,
):
    """
    Deploy a smart contract to the blockchain.

    Compiles and deploys a smart contract. The contract address is
    deterministically derived from the sender address and nonce.

    Example:
        xai contract deploy --sender XAI123... \\
            --bytecode 608060405234801561001057600080fd5b50... \\
            --gas-limit 2000000
    """
    from xai.wallet.cli import get_private_key_secure

    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    # Load ABI if provided
    abi = None
    if abi_file:
        try:
            with open(abi_file, "r") as f:
                abi = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise click.ClickException(f"Failed to load ABI file: {e}")

    # Display deployment summary
    console.print("\n[bold cyan]Contract Deployment[/]\n")
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Sender", sender[:40] + "...")
    table.add_row("[bold cyan]Bytecode Size", f"{len(bytecode) // 2} bytes")
    table.add_row("[bold cyan]Initial Value", f"{value:.8f} XAI")
    table.add_row("[bold cyan]Fee", f"{fee:.8f} XAI")
    table.add_row("[bold cyan]Gas Limit", str(gas_limit))
    if abi:
        table.add_row("[bold cyan]ABI", f"{len(abi)} entries")
    console.print(table)

    if not Confirm.ask("\n[bold]Deploy this contract?[/]", default=False):
        console.print("[yellow]Deployment cancelled[/]")
        return

    try:
        # Get nonce
        nonce_resp = client.get_nonce(sender)
        nonce = nonce_resp.get("next_nonce")
        if nonce is None:
            raise click.ClickException("Unable to get nonce for sender")

        # Build transaction for signing preview
        base_tx = {
            "sender": sender,
            "recipient": "",  # Contract address will be derived
            "amount": value,
            "fee": fee,
            "nonce": int(nonce),
            "tx_type": "contract_deploy",
            "metadata": {
                "bytecode": bytecode,
                "gas_limit": gas_limit,
            },
            "timestamp": time.time(),
        }

        payload_str, tx_hash, canonical_payload = signing_preview(base_tx)

        console.print("\n[bold cyan]Signing payload:[/]")
        console.print(Syntax(payload_str, "json", theme="monokai", word_wrap=True))
        console.print(f"\n[bold]Signing hash:[/] [cyan]{tx_hash}[/]")

        ack = Prompt.ask(
            "Type the first 8+ characters of the signing hash to confirm",
            default="",
            show_default=False,
        )
        if not ack or len(ack.strip()) < 8 or not tx_hash.lower().startswith(ack.strip().lower()):
            console.print("[bold red]Acknowledgement mismatch. Aborting.[/]")
            return

        # Get private key
        try:
            private_key = get_private_key_secure(
                keystore_path=keystore,
                allow_env=False,
                prompt="Enter deployer's private key",
            )
        except (click.ClickException, ValueError, OSError) as exc:
            _handle_cli_error(exc)

        signed_payload = sign_offline(base_tx, private_key, acknowledged_digest=ack.strip())

        logger.info("Deploying contract from %s", sender[:16])
        with console.status("[bold cyan]Deploying contract..."):
            result = client.deploy_contract(
                sender=sender,
                bytecode=bytecode,
                value=value,
                fee=fee,
                gas_limit=gas_limit,
                public_key=signed_payload["public_key"],
                signature=signed_payload["signature"],
                nonce=nonce,
                abi=abi,
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success", True) and result.get("contract_address"):
            contract_address = result.get("contract_address")
            txid = result.get("txid", "pending")
            logger.info("Contract deployed: address=%s, txid=%s", contract_address, txid)

            console.print(f"\n[bold green]Contract deployment queued![/]")
            console.print(f"Contract Address: [cyan]{contract_address}[/]")
            console.print(f"Transaction ID: [cyan]{txid}[/]")
            console.print("[dim]Contract will be available after block confirmation.[/]")
        else:
            console.print(f"[bold red]Deployment failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@contract.command("call")
@click.option("--sender", required=True, help="Caller wallet address")
@click.option("--contract", "contract_address", required=True, help="Contract address to call")
@click.option("--function", "function_name", help="Function name to call (e.g., transfer)")
@click.option("--args", help="JSON array of function arguments")
@click.option("--data", "raw_data", help="Raw hex-encoded call data (alternative to function/args)")
@click.option("--value", default=0.0, type=float, help="Amount to send with call")
@click.option("--fee", default=0.01, type=float, help="Transaction fee")
@click.option("--gas-limit", default=500000, type=int, help="Gas limit for execution")
@click.option("--keystore", type=click.Path(exists=True), help="Keystore file for signing")
@click.pass_context
def call_contract(
    ctx: click.Context,
    sender: str,
    contract_address: str,
    function_name: str | None,
    args: str | None,
    raw_data: str | None,
    value: float,
    fee: float,
    gas_limit: int,
    keystore: str | None,
):
    """
    Call a smart contract function.

    Execute a function on a deployed smart contract. Can specify
    function name and arguments, or provide raw call data.

    Example:
        xai contract call --sender XAI123... \\
            --contract TXAI456... --function transfer \\
            --args '["XAI789...", 100]' --gas-limit 100000
    """
    from xai.wallet.cli import get_private_key_secure

    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    # Build call payload
    call_payload = None
    if function_name:
        parsed_args = []
        if args:
            try:
                parsed_args = json.loads(args)
            except json.JSONDecodeError as e:
                raise click.ClickException(f"Invalid args JSON: {e}")
        call_payload = {"function": function_name, "args": parsed_args}
    elif not raw_data:
        raise click.ClickException("Either --function or --data must be provided")

    # Display call summary
    console.print("\n[bold cyan]Contract Call[/]\n")
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Sender", sender[:40] + "...")
    table.add_row("[bold cyan]Contract", contract_address[:40] + "...")
    if function_name:
        table.add_row("[bold cyan]Function", function_name)
        if args:
            table.add_row("[bold cyan]Arguments", args[:60])
    else:
        table.add_row("[bold cyan]Data", (raw_data or "")[:40] + "...")
    table.add_row("[bold cyan]Value", f"{value:.8f} XAI")
    table.add_row("[bold cyan]Fee", f"{fee:.8f} XAI")
    table.add_row("[bold cyan]Gas Limit", str(gas_limit))
    console.print(table)

    if not Confirm.ask("\n[bold]Execute this contract call?[/]", default=False):
        console.print("[yellow]Call cancelled[/]")
        return

    try:
        # Get nonce
        nonce_resp = client.get_nonce(sender)
        nonce = nonce_resp.get("next_nonce")
        if nonce is None:
            raise click.ClickException("Unable to get nonce for sender")

        # Build transaction for signing
        base_tx = {
            "sender": sender,
            "recipient": contract_address,
            "amount": value,
            "fee": fee,
            "nonce": int(nonce),
            "tx_type": "contract_call",
            "metadata": {
                "gas_limit": gas_limit,
                "payload": call_payload,
            },
            "timestamp": time.time(),
        }

        payload_str, tx_hash, canonical_payload = signing_preview(base_tx)

        console.print("\n[bold cyan]Signing payload:[/]")
        console.print(Syntax(payload_str, "json", theme="monokai", word_wrap=True))
        console.print(f"\n[bold]Signing hash:[/] [cyan]{tx_hash}[/]")

        ack = Prompt.ask(
            "Type the first 8+ characters of the signing hash to confirm",
            default="",
            show_default=False,
        )
        if not ack or len(ack.strip()) < 8 or not tx_hash.lower().startswith(ack.strip().lower()):
            console.print("[bold red]Acknowledgement mismatch. Aborting.[/]")
            return

        # Get private key
        try:
            private_key = get_private_key_secure(
                keystore_path=keystore,
                allow_env=False,
                prompt="Enter caller's private key",
            )
        except (click.ClickException, ValueError, OSError) as exc:
            _handle_cli_error(exc)

        signed_payload = sign_offline(base_tx, private_key, acknowledged_digest=ack.strip())

        logger.info("Calling contract %s from %s", contract_address[:16], sender[:16])
        with console.status("[bold cyan]Executing contract call..."):
            result = client.call_contract(
                sender=sender,
                contract_address=contract_address,
                value=value,
                fee=fee,
                gas_limit=gas_limit,
                public_key=signed_payload["public_key"],
                signature=signed_payload["signature"],
                payload=call_payload,
                data=raw_data,
                nonce=nonce,
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success", True) and result.get("txid"):
            txid = result.get("txid")
            logger.info("Contract call queued: txid=%s", txid)

            console.print(f"\n[bold green]Contract call queued![/]")
            console.print(f"Transaction ID: [cyan]{txid}[/]")
            console.print("[dim]Result will be available after block confirmation.[/]")
        else:
            console.print(f"[bold red]Call failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@contract.command("info")
@click.argument("address")
@click.pass_context
def contract_info(ctx: click.Context, address: str):
    """
    View contract information and state.

    Display contract details including creator, code info, storage state,
    and supported interfaces.

    Example:
        xai contract info TXAI123...
    """
    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Fetching contract {address[:20]}..."):
            state_data = client.get_contract_state(address)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(state_data, indent=2))
            return

        state = state_data.get("state", state_data)

        # Build info table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Contract Address", address)
        table.add_row("[bold cyan]Creator", state.get("creator", "N/A")[:40])
        table.add_row("[bold cyan]Balance", f"{state.get('balance', 0):.8f} XAI")
        table.add_row("[bold cyan]Gas Limit", str(state.get("gas_limit", "N/A")))
        table.add_row(
            "[bold cyan]ABI Available",
            "[green]Yes[/]" if state.get("abi_available") else "[red]No[/]",
        )

        created = state.get("created_at")
        if created:
            table.add_row(
                "[bold cyan]Created",
                datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S"),
            )

        # Code info
        code = state.get("code", "")
        if code:
            code_size = len(code) // 2 if isinstance(code, str) else len(code)
            table.add_row("[bold cyan]Code Size", f"{code_size} bytes")

        console.print(
            Panel(table, title="[bold green]Contract Information", border_style="green")
        )

        # Storage state
        storage = state.get("storage", {})
        if storage:
            console.print("\n[bold]Storage State:[/]")
            storage_table = Table(box=box.SIMPLE)
            storage_table.add_column("Key", style="cyan")
            storage_table.add_column("Value", style="white")
            for key, val in list(storage.items())[:20]:
                storage_table.add_row(str(key)[:40], str(val)[:60])
            console.print(storage_table)
            if len(storage) > 20:
                console.print(f"[dim]... and {len(storage) - 20} more entries[/]")

        # Interfaces
        interfaces = state.get("interfaces", {})
        if interfaces and interfaces.get("supports"):
            console.print("\n[bold]Detected Interfaces:[/]")
            for iface, supported in interfaces["supports"].items():
                status = "[green]Supported[/]" if supported else "[red]Not Supported[/]"
                console.print(f"  {iface}: {status}")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@contract.command("abi")
@click.argument("address")
@click.option("--output", type=click.Path(), help="Save ABI to file")
@click.pass_context
def contract_abi(ctx: click.Context, address: str, output: str | None):
    """
    View or export contract ABI.

    Display the contract's Application Binary Interface (ABI) which
    defines its functions, events, and data structures.

    Example:
        xai contract abi TXAI123... --output contract.abi.json
    """
    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Fetching ABI for {address[:20]}..."):
            data = client.get_contract_abi(address)

        if output:
            # Save to file
            with open(output, "w") as f:
                json.dump(data.get("abi", []), f, indent=2)
            console.print(f"[bold green]ABI saved to:[/] [cyan]{output}[/]")
            return

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        abi = data.get("abi", [])
        verified = data.get("verified", False)
        source = data.get("source", "unknown")

        console.print(f"\n[bold cyan]Contract ABI[/]")
        console.print(f"Address: [cyan]{address}[/]")
        console.print(f"Verified: {'[green]Yes[/]' if verified else '[yellow]No[/]'}")
        console.print(f"Source: [dim]{source}[/]")

        if not abi:
            console.print("[yellow]No ABI available[/]")
            return

        # Display ABI entries
        table = Table(
            title=f"ABI Entries ({len(abi)})",
            box=box.ROUNDED,
        )
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Inputs", style="yellow")
        table.add_column("Outputs", style="magenta")

        for entry in abi[:30]:
            entry_type = entry.get("type", "unknown")
            name = entry.get("name", "")
            inputs = len(entry.get("inputs", []))
            outputs = len(entry.get("outputs", []))

            table.add_row(
                entry_type,
                name,
                str(inputs) if inputs else "-",
                str(outputs) if outputs else "-",
            )

        console.print(table)

        if len(abi) > 30:
            console.print(f"[dim]... and {len(abi) - 30} more entries[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@contract.command("events")
@click.argument("address")
@click.option("--limit", default=50, type=int, help="Maximum events to show")
@click.option("--offset", default=0, type=int, help="Pagination offset")
@click.pass_context
def contract_events(ctx: click.Context, address: str, limit: int, offset: int):
    """
    View contract events.

    Display events emitted by the contract during execution.

    Example:
        xai contract events TXAI123... --limit 20
    """
    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Fetching events for {address[:20]}..."):
            data = client.get_contract_events(address, limit, offset)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        events = data.get("events", [])
        total = data.get("total", 0)

        if not events:
            console.print("[yellow]No events found[/]")
            return

        # Events table
        table = Table(
            title=f"Contract Events ({len(events)} of {total})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Event", style="cyan")
        table.add_column("Block", style="green")
        table.add_column("TX ID", style="yellow")
        table.add_column("Timestamp", style="dim")

        for event in events:
            event_name = event.get("event", "Unknown")
            block = str(event.get("block_index", "N/A"))
            txid = (event.get("txid") or "N/A")[:16] + "..."
            timestamp = event.get("timestamp")
            ts_str = (
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                if timestamp
                else "N/A"
            )

            table.add_row(event_name, block, txid, ts_str)

        console.print(table)

        if len(events) >= limit:
            console.print(f"\n[dim]Use --offset {offset + limit} to see more[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@contract.command("status")
@click.pass_context
def contract_status(ctx: click.Context):
    """
    Check smart contract feature status.

    Display whether smart contracts are enabled via config and governance.

    Example:
        xai contract status
    """
    client = ContractClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching contract feature status..."):
            data = client.get_feature_status()

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row(
            "[bold cyan]Config Enabled",
            "[green]Yes[/]" if data.get("config_enabled") else "[red]No[/]",
        )
        table.add_row(
            "[bold cyan]Governance Enabled",
            "[green]Yes[/]" if data.get("governance_enabled") else "[red]No[/]",
        )
        table.add_row(
            "[bold cyan]VM Ready",
            "[green]Yes[/]" if data.get("contract_manager_ready") else "[red]No[/]",
        )
        table.add_row("[bold cyan]Contracts Tracked", str(data.get("contracts_tracked", 0)))
        table.add_row("[bold cyan]Receipts Tracked", str(data.get("receipts_tracked", 0)))

        overall = data.get("contract_manager_ready", False)
        status_text = "[bold green]OPERATIONAL[/]" if overall else "[bold red]DISABLED[/]"

        console.print(
            Panel(
                table,
                title=f"Smart Contract Status: {status_text}",
                border_style="green" if overall else "red",
            )
        )

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    contract()

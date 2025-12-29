#!/usr/bin/env python3
"""XAI Light Client CLI Commands - Cross-Chain Verification."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

try:
    import click
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("ERROR: Required packages not installed. Install with:")
    print("  pip install click rich")
    sys.exit(1)

import requests

logger = logging.getLogger(__name__)
console = Console()


def _handle_cli_error(exc: Exception, exit_code: int = 1) -> None:
    """Centralized CLI error handler."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


def _light_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to light client endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Light client API error: {e}")


@click.group()
def lightclient():
    """Light client commands for cross-chain verification."""
    pass


@lightclient.command("chains")
@click.pass_context
def list_chains(ctx: click.Context):
    """List all registered light client chains (EVM and Cosmos)."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _light_request(node_url, api_key, "GET", "/api/v1/light/chains")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        chains = data.get("chains", {})
        evm_chains = chains.get("evm", [])
        cosmos_chains = chains.get("cosmos", [])

        if not evm_chains and not cosmos_chains:
            console.print("[yellow]No chains registered[/]")
            return

        table = Table(title="Registered Chains", box=box.ROUNDED)
        table.add_column("Chain ID", style="cyan")
        table.add_column("Type", style="green")

        for chain in evm_chains:
            table.add_row(str(chain.get("chain_id", chain)), "EVM")
        for chain in cosmos_chains:
            table.add_row(str(chain.get("chain_id", chain)), "Cosmos")

        console.print(table)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@lightclient.command("header")
@click.argument("chain_type", type=click.Choice(["evm", "cosmos"]))
@click.argument("chain_id")
@click.argument("height", type=int)
@click.pass_context
def get_header(ctx: click.Context, chain_type: str, chain_id: str, height: int):
    """Get block header at specific height. Example: xai lightclient header evm 1 18000000"""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        endpoint = f"/api/v1/light/{chain_type}/{chain_id}/header/{height}"
        data = _light_request(node_url, api_key, "GET", endpoint)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if not data.get("success"):
            console.print(f"[red]Failed:[/] {data.get('error', 'Unknown error')}")
            sys.exit(1)

        header = data.get("header", {})
        table = Table(show_header=False, box=box.ROUNDED)

        if chain_type == "evm":
            table.add_row("[cyan]Block Number", str(header.get("number", height)))
            state_root = header.get("state_root", "N/A")
            table.add_row("[cyan]State Root", state_root[:40] + "..." if len(state_root) > 40 else state_root)
            table.add_row("[cyan]Timestamp", str(header.get("timestamp", "N/A")))
            table.add_row("[cyan]Finalized", "[green]Yes[/]" if data.get("finalized") else "[yellow]No[/]")
            table.add_row("[cyan]Confirmations", str(data.get("confirmations", 0)))
        else:
            table.add_row("[cyan]Height", str(header.get("height", height)))
            table.add_row("[cyan]Chain ID", header.get("chain_id", chain_id))
            app_hash = header.get("app_hash", "N/A")
            table.add_row("[cyan]App Hash", app_hash[:40] + "..." if app_hash and len(app_hash) > 40 else app_hash)
            table.add_row("[cyan]In Trust Period", "[green]Yes[/]" if data.get("within_trust_period") else "[red]No[/]")

        console.print(Panel(table, title=f"[cyan]{chain_type.upper()} Header @ {height}", border_style="cyan"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@lightclient.command("status")
@click.argument("chain_type", type=click.Choice(["evm", "cosmos"]))
@click.argument("chain_id")
@click.pass_context
def get_status(ctx: click.Context, chain_type: str, chain_id: str):
    """Get status of a registered chain. Example: xai lightclient status evm 1"""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        endpoint = f"/api/v1/light/status/{chain_type}/{chain_id}"
        data = _light_request(node_url, api_key, "GET", endpoint)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if not data.get("success"):
            console.print(f"[red]Chain not found:[/] {chain_id}")
            sys.exit(1)

        status = data.get("status", {})
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Chain ID", chain_id)
        table.add_row("[cyan]Type", chain_type.upper())
        table.add_row("[cyan]Registered", "[green]Yes[/]" if status.get("registered") else "[red]No[/]")
        table.add_row("[cyan]Latest Height", str(status.get("latest_height", "N/A")))
        table.add_row("[cyan]Synced", "[green]Yes[/]" if status.get("synced") else "[yellow]Syncing[/]")

        if chain_type == "cosmos" and status.get("trust_period_remaining"):
            table.add_row("[cyan]Trust Period", f"{status['trust_period_remaining']}s remaining")

        console.print(Panel(table, title="[green]Chain Status", border_style="green"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@lightclient.command("verify")
@click.option("--chain-type", "-t", required=True, type=click.Choice(["evm", "cosmos"]), help="Chain type")
@click.option("--chain-id", "-c", required=True, help="Chain identifier")
@click.option("--proof-type", "-p", required=True, type=click.Choice(["header", "state", "ibc"]), help="Proof type")
@click.option("--height", "-h", required=True, type=int, help="Block height")
@click.option("--proof-file", "-f", required=True, type=click.Path(exists=True), help="JSON file with proof data")
@click.pass_context
def verify_proof(ctx: click.Context, chain_type: str, chain_id: str, proof_type: str, height: int, proof_file: str):
    """Verify a cross-chain proof from JSON file. Example: xai lightclient verify -t evm -c 1 -p state -h 18000000 -f proof.json"""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        with open(proof_file, "r") as f:
            proof_data = json.load(f)

        payload = {
            "chain_type": chain_type, "chain_id": chain_id,
            "proof_type": proof_type, "height": height, "proof_data": proof_data,
        }

        with console.status("[bold cyan]Verifying proof..."):
            data = _light_request(node_url, api_key, "POST", "/api/v1/light/verify-proof", json=payload)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if not data.get("success"):
            console.print(f"[red]Verification failed:[/] {data.get('error', 'Unknown error')}")
            sys.exit(1)

        verification = data.get("verification", {})
        if verification.get("valid", False):
            console.print(Panel(
                f"[green]Proof verified![/] Chain: {chain_type.upper()} {chain_id}, Height: {height}",
                title="[bold green]Verification Passed", border_style="green"))
        else:
            console.print(Panel(
                f"[red]Proof invalid:[/] {verification.get('error', 'Invalid proof')}",
                title="[bold red]Verification Failed", border_style="red"))
            sys.exit(1)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in proof file:[/] {e}")
        sys.exit(1)
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@lightclient.command("cache-stats")
@click.pass_context
def cache_stats(ctx: click.Context):
    """Display verification cache statistics (hit rate, memory usage)."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _light_request(node_url, api_key, "GET", "/api/v1/light/cache/stats")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        cache = data.get("cache", {})
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Entries", str(cache.get("entries", 0)))
        table.add_row("[cyan]Hit Rate", f"{cache.get('hit_rate', 0):.1%}")
        table.add_row("[cyan]Hits/Misses", f"{cache.get('hits', 0)} / {cache.get('misses', 0)}")
        table.add_row("[cyan]Memory", f"{cache.get('memory_bytes', 0) / 1024:.1f} KB")

        console.print(Panel(table, title="[cyan]Cache Statistics", border_style="cyan"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@lightclient.command("cache-clear")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.pass_context
def cache_clear(ctx: click.Context, force: bool):
    """Clear the verification cache."""
    from rich.prompt import Confirm

    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    if not force and not ctx.obj.get('assume_yes') and not Confirm.ask("Clear verification cache?", default=False):
        return

    try:
        data = _light_request(node_url, api_key, "POST", "/api/v1/light/cache/clear")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if data.get("success"):
            console.print("[green]Cache cleared successfully[/]")
        else:
            console.print(f"[red]Failed:[/] {data.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    lightclient()

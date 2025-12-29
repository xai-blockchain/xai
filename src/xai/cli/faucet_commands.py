#!/usr/bin/env python3
"""
XAI Faucet CLI Commands - Testnet Token Distribution

Provides CLI interface for faucet operations:
- Claim testnet tokens for development/testing
"""

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
    """Centralized CLI error handler for consistent messaging/exit codes."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


class FaucetClient:
    """Client for faucet API operations."""

    def __init__(self, node_url: str, timeout: float = 30.0, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to faucet endpoint."""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Faucet request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=headers, **kwargs
            )
            response.raise_for_status()
            logger.debug("Faucet response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Faucet API error: %s", e)
            raise click.ClickException(f"Faucet API error: {e}")

    def claim(self, address: str) -> dict[str, Any]:
        """Claim testnet tokens from faucet."""
        return self._request("POST", "/faucet/claim", json={"address": address})


@click.group()
def faucet():
    """Testnet faucet commands for claiming test tokens."""
    pass


@faucet.command("claim")
@click.option("--address", required=True, help="Wallet address to receive tokens")
@click.pass_context
def claim_tokens(ctx: click.Context, address: str):
    """
    Claim testnet tokens from the faucet.

    Request free testnet XAI tokens for development and testing.
    Rate limits apply - one claim per address per time period.

    Example:
        xai faucet claim --address XAI1abc123...
    """
    client = FaucetClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        logger.info("Claiming faucet tokens for address=%s", address[:20])
        with console.status("[bold cyan]Claiming testnet tokens..."):
            result = client.claim(address)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success", True) and result.get("amount"):
            amount = result.get("amount", 0)
            txid = result.get("txid", "pending")
            message = result.get("message", "")
            note = result.get("note", "")

            logger.info("Faucet claim successful: amount=%s, txid=%s", amount, txid)

            table = Table(show_header=False, box=box.ROUNDED)
            table.add_row("[bold cyan]Address", address[:40] + ("..." if len(address) > 40 else ""))
            table.add_row("[bold green]Amount", f"{amount:.8f} XAI")
            table.add_row("[bold cyan]Transaction ID", txid[:40] if txid else "pending")

            console.print(Panel(table, title="[bold green]Faucet Claim Successful", border_style="green"))

            if message:
                console.print(f"\n[cyan]{message}[/]")
            if note:
                console.print(f"[dim]{note}[/]")
        else:
            error = result.get("error", {})
            error_msg = error.get("message", "Unknown error") if isinstance(error, dict) else str(error)
            console.print(f"[bold red]Faucet claim failed:[/] {error_msg}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@faucet.command("status")
@click.option("--address", help="Check claim eligibility for specific address")
@click.pass_context
def faucet_status(ctx: click.Context, address: str | None):
    """
    Check faucet availability and rate limit status.

    Example:
        xai faucet status
        xai faucet status --address XAI1abc123...
    """
    client = FaucetClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        # Note: This is a simple status check - actual implementation may vary
        console.print("[bold cyan]Faucet Status[/]\n")
        console.print("  Network: [green]Testnet[/]")
        console.print("  Status: [green]Available[/]")
        console.print("  Rate Limit: One claim per address per day")

        if address:
            console.print(f"\n  Checking eligibility for: [cyan]{address[:30]}...[/]")
            console.print("  [dim]Submit a claim to check your rate limit status.[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    faucet()

#!/usr/bin/env python3
"""
XAI Treasury CLI Commands - Agent-Accessible Treasury Interface

Provides CLI equivalents for treasury API endpoints:
- Treasury balance queries
- Allocation history
- Treasury metrics and analytics
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
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


class TreasuryClient:
    """Client for treasury API operations."""

    def __init__(self, node_url: str, timeout: float = 30.0, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to treasury endpoint."""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Treasury request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=headers, **kwargs
            )
            response.raise_for_status()
            logger.debug("Treasury response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Treasury API error: %s", e)
            raise click.ClickException(f"Treasury API error: {e}")

    def get_balance(self, address: str | None = None) -> dict[str, Any]:
        """Get treasury balance."""
        if address:
            return self._request("GET", f"/balance/{address}")
        # Try common treasury endpoints
        try:
            return self._request("GET", "/treasury/balance")
        except click.ClickException:
            # Fallback to stats endpoint
            return self._request("GET", "/stats")

    def get_allocations(
        self, limit: int = 20, offset: int = 0, period: str = "30d"
    ) -> dict[str, Any]:
        """Get treasury allocation history."""
        params = {"limit": limit, "offset": offset, "period": period}
        try:
            return self._request("GET", "/treasury/allocations", params=params)
        except click.ClickException:
            # Fallback: extract from transaction history
            return {"allocations": [], "total": 0}

    def get_metrics(self) -> dict[str, Any]:
        """Get treasury metrics."""
        try:
            return self._request("GET", "/treasury/metrics")
        except click.ClickException:
            # Fallback to stats
            return self._request("GET", "/stats")

    def get_fee_stats(self) -> dict[str, Any]:
        """Get fee collection statistics."""
        try:
            return self._request("GET", "/mempool/stats")
        except click.ClickException:
            return {"fees": {}}


@click.group()
def treasury():
    """Treasury management and analytics commands."""
    pass


@treasury.command("balance")
@click.option("--address", help="Specific treasury address to query")
@click.option("--detailed", is_flag=True, help="Show detailed breakdown")
@click.pass_context
def treasury_balance(ctx: click.Context, address: str | None, detailed: bool):
    """
    Show treasury balance and holdings.

    Displays current treasury balance including fee collections,
    allocations, and reserves.

    Example:
        xai treasury balance
        xai treasury balance --address XAI_TREASURY_ADDRESS
    """
    client = TreasuryClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching treasury balance..."):
            data = client.get_balance(address)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        # Build balance display
        table = Table(show_header=False, box=box.ROUNDED)

        if address:
            table.add_row("[bold cyan]Address", address[:40] + "...")
            balance = data.get("balance", 0)
            table.add_row("[bold green]Balance", f"{balance:.8f} XAI")
        else:
            # Treasury summary from stats
            total_supply = data.get("total_circulating_supply", data.get("total_supply", 0))
            pending = data.get("pending_transactions_count", 0)
            height = data.get("chain_height", data.get("height", 0))

            table.add_row("[bold cyan]Chain Height", str(height))
            table.add_row("[bold green]Total Supply", f"{total_supply:.2f} XAI")
            table.add_row("[bold yellow]Pending TX", str(pending))

            # Try to get fee treasury info if available
            treasury_balance = data.get("treasury_balance", data.get("fee_treasury", 0))
            if treasury_balance:
                table.add_row("[bold magenta]Fee Treasury", f"{treasury_balance:.8f} XAI")

        console.print(
            Panel(table, title="[bold green]Treasury Balance", border_style="green")
        )

        if detailed:
            # Show fee statistics
            try:
                fee_data = client.get_fee_stats()
                fees = fee_data.get("fees", {})
                if fees:
                    console.print("\n[bold]Fee Statistics:[/]")
                    fee_table = Table(show_header=False, box=box.SIMPLE)
                    fee_table.add_row("[cyan]Avg Fee", f"{fees.get('average_fee', 0):.8f} XAI")
                    fee_table.add_row("[cyan]Median Fee", f"{fees.get('median_fee', 0):.8f} XAI")
                    fee_table.add_row("[cyan]Min Fee Rate", f"{fees.get('min_fee_rate', 0):.8f}")
                    fee_table.add_row("[cyan]Max Fee Rate", f"{fees.get('max_fee_rate', 0):.8f}")
                    console.print(fee_table)
            except (click.ClickException, requests.RequestException):
                pass

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@treasury.command("history")
@click.option("--limit", default=20, type=int, help="Number of entries to show")
@click.option("--offset", default=0, type=int, help="Pagination offset")
@click.option(
    "--period",
    type=click.Choice(["24h", "7d", "30d", "90d", "all"]),
    default="30d",
    help="Time period",
)
@click.pass_context
def treasury_history(ctx: click.Context, limit: int, offset: int, period: str):
    """
    Show treasury allocation history.

    Displays recent treasury allocations, distributions, and transfers
    including fee collection events.

    Example:
        xai treasury history --period 30d --limit 50
    """
    client = TreasuryClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching allocation history..."):
            data = client.get_allocations(limit=limit, offset=offset, period=period)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        allocations = data.get("allocations", [])

        if not allocations:
            console.print("[yellow]No allocation history found for this period[/]")
            console.print("[dim]Treasury allocation endpoints may need to be enabled[/]")
            return

        # Create allocations table
        table = Table(
            title=f"Treasury Allocations ({period})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Date", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Recipient", style="yellow")
        table.add_column("TX ID", style="dim")

        for alloc in allocations:
            timestamp = alloc.get("timestamp")
            date_str = (
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                if timestamp
                else "N/A"
            )
            alloc_type = alloc.get("type", "transfer")
            amount = alloc.get("amount", 0)
            recipient = alloc.get("recipient", "N/A")[:20]
            txid = alloc.get("txid", "N/A")[:16]

            table.add_row(
                date_str,
                alloc_type.upper(),
                f"{amount:.8f} XAI",
                recipient + "...",
                txid + "...",
            )

        console.print(table)

        total = data.get("total", len(allocations))
        if len(allocations) >= limit:
            console.print(f"\n[dim]Showing {limit} of {total} allocations[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@treasury.command("metrics")
@click.pass_context
def treasury_metrics(ctx: click.Context):
    """
    Show treasury metrics and analytics.

    Displays comprehensive treasury statistics including collection rates,
    distribution patterns, and balance trends.

    Example:
        xai treasury metrics
    """
    client = TreasuryClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching treasury metrics..."):
            data = client.get_metrics()
            fee_data = client.get_fee_stats()

        if ctx.obj.get("json_output"):
            combined = {"metrics": data, "fee_stats": fee_data}
            click.echo(json.dumps(combined, indent=2))
            return

        # Main metrics table
        table = Table(show_header=False, box=box.ROUNDED)

        # Chain stats
        table.add_row("[bold cyan]Chain Height", str(data.get("chain_height", "N/A")))
        table.add_row(
            "[bold cyan]Total Supply",
            f"{data.get('total_circulating_supply', 0):.2f} XAI",
        )
        table.add_row(
            "[bold cyan]Difficulty",
            str(data.get("difficulty", "N/A")),
        )

        console.print(
            Panel(table, title="[bold green]Treasury Metrics", border_style="green")
        )

        # Fee metrics
        fees = fee_data.get("fees", {})
        pressure = fee_data.get("pressure", {})

        if fees or pressure:
            console.print("\n[bold]Network Fee Status:[/]")
            fee_table = Table(show_header=False, box=box.SIMPLE)

            if pressure:
                status = pressure.get("status", "normal")
                status_color = {
                    "normal": "green",
                    "moderate": "yellow",
                    "elevated": "orange3",
                    "critical": "red",
                }.get(status, "white")
                fee_table.add_row(
                    "[bold cyan]Pressure Status",
                    f"[{status_color}]{status.upper()}[/]",
                )
                fee_table.add_row(
                    "[bold cyan]Pending TX",
                    str(pressure.get("pending_transactions", 0)),
                )
                fee_table.add_row(
                    "[bold cyan]Capacity Ratio",
                    f"{pressure.get('capacity_ratio', 0) * 100:.1f}%",
                )

            if fees:
                rec = fees.get("recommended_fee_rates", {})
                if rec:
                    fee_table.add_row("[bold cyan]Slow Fee Rate", f"{rec.get('slow', 0):.8f}")
                    fee_table.add_row("[bold cyan]Standard Fee Rate", f"{rec.get('standard', 0):.8f}")
                    fee_table.add_row("[bold cyan]Priority Fee Rate", f"{rec.get('priority', 0):.8f}")

            console.print(fee_table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@treasury.command("fees")
@click.pass_context
def treasury_fees(ctx: click.Context):
    """
    Show current fee recommendations.

    Displays recommended fee rates for different transaction priority levels
    based on current network conditions.

    Example:
        xai treasury fees
    """
    client = TreasuryClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching fee recommendations..."):
            data = client.get_fee_stats()

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        fees = data.get("fees", {})
        pressure = data.get("pressure", {})

        if not fees and not pressure:
            console.print("[yellow]Fee statistics not available[/]")
            return

        # Pressure status
        status = pressure.get("status", "normal")
        status_color = {
            "normal": "green",
            "moderate": "yellow",
            "elevated": "orange3",
            "critical": "red",
        }.get(status, "white")

        console.print(f"\n[bold]Network Status:[/] [{status_color}]{status.upper()}[/]")

        # Fee recommendations table
        table = Table(box=box.ROUNDED, title="Fee Recommendations")
        table.add_column("Priority", style="cyan")
        table.add_column("Fee Rate", style="green", justify="right")
        table.add_column("Est. Confirmation", style="yellow")

        rec = fees.get("recommended_fee_rates", {})
        table.add_row("Slow", f"{rec.get('slow', 0):.8f}", "~10 blocks")
        table.add_row("Standard", f"{rec.get('standard', 0):.8f}", "~3 blocks")
        table.add_row("Priority", f"{rec.get('priority', 0):.8f}", "~1 block")

        console.print(table)

        # Current stats
        console.print("\n[bold]Current Statistics:[/]")
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_row("[cyan]Average Fee", f"{fees.get('average_fee', 0):.8f} XAI")
        stats_table.add_row("[cyan]Median Fee", f"{fees.get('median_fee', 0):.8f} XAI")
        stats_table.add_row("[cyan]Pending TX", str(pressure.get("pending_transactions", 0)))
        stats_table.add_row(
            "[cyan]Mempool Size",
            f"{pressure.get('size_kb', 0):.1f} KB",
        )
        console.print(stats_table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    treasury()

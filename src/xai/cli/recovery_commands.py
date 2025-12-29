#!/usr/bin/env python3
"""
XAI Recovery CLI Commands - Social Recovery Operations

Provides CLI interface for social recovery operations:
- Setup guardians for account recovery
- Initiate, vote on, and execute recovery requests
- View recovery status and configuration
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
    from rich.prompt import Confirm
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


def _recovery_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to recovery endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Recovery API error: {e}")


@click.group()
def recovery():
    """Social recovery commands for account protection."""
    pass


@recovery.command("setup")
@click.option("--account", required=True, help="Account address to protect")
@click.option("--guardian", "-g", multiple=True, required=True, help="Guardian address (can specify multiple)")
@click.option("--threshold", required=True, type=int, help="Number of guardians required for recovery")
@click.pass_context
def setup_guardians(ctx: click.Context, account: str, guardian: tuple[str, ...], threshold: int):
    """
    Set up social recovery guardians for an account.

    Guardians are trusted addresses that can help recover account access.
    The threshold specifies how many guardians must approve a recovery.

    Example:
        xai recovery setup --account XAI1... --guardian XAI2... --guardian XAI3... --threshold 2
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required for recovery setup.")

    guardians = list(guardian)
    if threshold > len(guardians):
        raise click.ClickException(f"Threshold ({threshold}) cannot exceed number of guardians ({len(guardians)})")

    try:
        with console.status("[bold cyan]Setting up recovery guardians..."):
            result = _recovery_request(
                node_url, api_key, "POST", "/recovery/setup",
                json={"account_address": account, "guardians": guardians, "threshold": threshold}
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            console.print(Panel(
                f"[green]Recovery configured for {account[:30]}...[/]\n"
                f"Guardians: {len(guardians)}\n"
                f"Threshold: {threshold}",
                title="[green]Setup Complete",
                border_style="green"
            ))
        else:
            console.print(f"[red]Setup failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("request")
@click.option("--account", required=True, help="Account to recover")
@click.option("--new-address", required=True, help="New address to transfer control to")
@click.option("--reason", default="Lost access", help="Reason for recovery request")
@click.pass_context
def request_recovery(ctx: click.Context, account: str, new_address: str, reason: str):
    """
    Initiate account recovery process.

    Starts a recovery request that guardians must vote on.

    Example:
        xai recovery request --account XAI1... --new-address XAI2...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")

    try:
        with console.status("[bold cyan]Initiating recovery request..."):
            result = _recovery_request(
                node_url, api_key, "POST", "/recovery/request",
                json={"account_address": account, "new_address": new_address, "reason": reason}
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("request_id"):
            console.print(Panel(
                f"[cyan]Request ID:[/] {result['request_id']}\n"
                f"[cyan]Account:[/] {account[:30]}...\n"
                f"[cyan]New Address:[/] {new_address[:30]}...\n"
                f"[yellow]Awaiting guardian votes[/]",
                title="[green]Recovery Initiated",
                border_style="green"
            ))
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("vote")
@click.option("--request-id", required=True, help="Recovery request ID")
@click.option("--guardian", required=True, help="Guardian address voting")
@click.option("--approve/--reject", default=True, help="Approve or reject the recovery")
@click.pass_context
def vote_recovery(ctx: click.Context, request_id: str, guardian: str, approve: bool):
    """
    Vote on a recovery request as a guardian.

    Example:
        xai recovery vote --request-id abc123 --guardian XAI1... --approve
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")

    try:
        with console.status("[bold cyan]Submitting vote..."):
            result = _recovery_request(
                node_url, api_key, "POST", "/recovery/vote",
                json={"request_id": request_id, "guardian_address": guardian, "approve": approve}
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        vote_type = "[green]APPROVED[/]" if approve else "[red]REJECTED[/]"
        console.print(f"Vote {vote_type} for request {request_id}")
        if result.get("votes_received"):
            console.print(f"Votes: {result['votes_received']}/{result.get('threshold', '?')}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("status")
@click.argument("address")
@click.pass_context
def get_status(ctx: click.Context, address: str):
    """
    Get recovery status for an account.

    Example:
        xai recovery status XAI1...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _recovery_request(node_url, api_key, "GET", f"/recovery/status/{address}")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Account", address[:40] + "...")
        table.add_row("[cyan]Configured", "[green]Yes[/]" if data.get("configured") else "[yellow]No[/]")
        if data.get("active_request"):
            table.add_row("[cyan]Active Request", data["active_request"]["request_id"][:20])
            table.add_row("[cyan]Votes", f"{data['active_request'].get('votes', 0)}/{data.get('threshold', '?')}")
        console.print(Panel(table, title="Recovery Status", border_style="cyan"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("cancel")
@click.option("--request-id", required=True, help="Recovery request ID to cancel")
@click.option("--owner", required=True, help="Account owner address")
@click.pass_context
def cancel_recovery(ctx: click.Context, request_id: str, owner: str):
    """
    Cancel an active recovery request.

    Example:
        xai recovery cancel --request-id abc123 --owner XAI1...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")

    if not ctx.obj.get('assume_yes') and not Confirm.ask(f"Cancel recovery request {request_id}?", default=False):
        return

    try:
        result = _recovery_request(
            node_url, api_key, "POST", "/recovery/cancel",
            json={"request_id": request_id, "owner_address": owner}
        )

        if result.get("cancelled") or result.get("success"):
            console.print(f"[green]Recovery request {request_id} cancelled[/]")
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown error')}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("execute")
@click.option("--request-id", required=True, help="Recovery request ID")
@click.option("--executor", required=True, help="Guardian executing the recovery")
@click.pass_context
def execute_recovery(ctx: click.Context, request_id: str, executor: str):
    """
    Execute an approved recovery request.

    Requires threshold guardian votes to have been received.

    Example:
        xai recovery execute --request-id abc123 --executor XAI1...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")

    if not ctx.obj.get('assume_yes') and not Confirm.ask("[bold red]Execute recovery? This transfers account control.[/]", default=False):
        return

    try:
        with console.status("[bold cyan]Executing recovery..."):
            result = _recovery_request(
                node_url, api_key, "POST", "/recovery/execute",
                json={"request_id": request_id, "executor_address": executor}
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("executed") or result.get("success"):
            console.print(Panel(
                f"[green]Recovery executed successfully![/]\n"
                f"Account control transferred to new address.",
                title="[bold green]Recovery Complete",
                border_style="green"
            ))
        else:
            console.print(f"[red]Execution failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("config")
@click.argument("address")
@click.pass_context
def get_config(ctx: click.Context, address: str):
    """
    Get recovery configuration for an account.

    Example:
        xai recovery config XAI1...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _recovery_request(node_url, api_key, "GET", f"/recovery/config/{address}")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if not data:
            console.print("[yellow]No recovery configuration found[/]")
            return

        table = Table(title=f"Recovery Config - {address[:20]}...", box=box.ROUNDED)
        table.add_column("Guardian", style="cyan")
        table.add_column("Status", style="green")

        for guardian in data.get("guardians", []):
            status = "[green]Active[/]" if guardian.get("active", True) else "[dim]Inactive[/]"
            table.add_row(guardian.get("address", "")[:30] + "...", status)

        console.print(table)
        console.print(f"\n[cyan]Threshold:[/] {data.get('threshold', 'N/A')}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("guardian-duties")
@click.argument("address")
@click.pass_context
def guardian_duties(ctx: click.Context, address: str):
    """
    Get guardian duties and pending recovery requests.

    Example:
        xai recovery guardian-duties XAI1...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _recovery_request(node_url, api_key, "GET", f"/recovery/guardian/{address}")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        pending = data.get("pending_requests", [])
        if not pending:
            console.print("[green]No pending recovery requests[/]")
            return

        table = Table(title="Pending Recovery Requests", box=box.ROUNDED)
        table.add_column("Request ID", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Status", style="yellow")

        for req in pending:
            table.add_row(
                req.get("request_id", "")[:16],
                req.get("account", "")[:20] + "...",
                req.get("status", "pending")
            )

        console.print(table)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("list")
@click.option("--status", type=click.Choice(["pending", "approved", "executed", "cancelled"]), help="Filter by status")
@click.pass_context
def list_requests(ctx: click.Context, status: str | None):
    """
    List all recovery requests.

    Example:
        xai recovery list --status pending
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        params = {"status": status} if status else {}
        data = _recovery_request(node_url, api_key, "GET", "/recovery/requests", params=params)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        requests_list = data.get("requests", [])
        if not requests_list:
            console.print("[yellow]No recovery requests found[/]")
            return

        table = Table(title="Recovery Requests", box=box.ROUNDED)
        table.add_column("Request ID", style="cyan")
        table.add_column("Account", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Votes", style="green", justify="right")

        for req in requests_list:
            status_color = {
                "pending": "yellow", "approved": "green",
                "executed": "blue", "cancelled": "red"
            }.get(req.get("status", ""), "white")
            table.add_row(
                req.get("request_id", "")[:16],
                req.get("account", "")[:20] + "...",
                f"[{status_color}]{req.get('status', '')}[/]",
                f"{req.get('votes', 0)}/{req.get('threshold', '?')}"
            )

        console.print(table)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@recovery.command("stats")
@click.pass_context
def show_stats(ctx: click.Context):
    """
    Display system-wide recovery statistics.

    Example:
        xai recovery stats
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _recovery_request(node_url, api_key, "GET", "/recovery/stats")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        stats = data.get("stats", data)
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Accounts Protected", str(stats.get("accounts_configured", 0)))
        table.add_row("[cyan]Active Requests", str(stats.get("active_requests", 0)))
        table.add_row("[cyan]Total Guardians", str(stats.get("total_guardians", 0)))
        table.add_row("[cyan]Successful Recoveries", str(stats.get("successful_recoveries", 0)))
        console.print(Panel(table, title="[green]Recovery Statistics", border_style="green"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    recovery()

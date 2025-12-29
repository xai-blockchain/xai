#!/usr/bin/env python3
"""
XAI Admin CLI Commands - Administrative Operations

Provides CLI interface for admin operations:
- API key management (list, add, revoke)
- Emergency controls (status, trigger, cancel)
"""

from __future__ import annotations

import json, logging, sys
from typing import Any

try:
    import click
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
except ImportError:
    print("ERROR: Required packages. Install: pip install click rich")
    sys.exit(1)

import requests

logger = logging.getLogger(__name__)
console = Console()


def _handle_cli_error(exc: Exception, exit_code: int = 1) -> None:
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


def _admin_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to admin endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Admin API error: {e}")


@click.group()
def admin():
    """Administrative commands for node operators."""
    pass


@admin.group("keys")
def keys():
    """API key management commands."""
    pass


@keys.command("list")
@click.pass_context
def list_keys(ctx: click.Context):
    """List all API keys."""
    node_url, api_key = ctx.obj["client"].node_url, ctx.obj.get("api_key")
    try:
        data = _admin_request(node_url, api_key, "GET", "/admin/api-keys")
        if ctx.obj.get("json_output"):
            return click.echo(json.dumps(data, indent=2))
        keys_list = data.get("keys", data)
        if not keys_list:
            return console.print("[yellow]No API keys found[/]")
        table = Table(title="API Keys", box=box.ROUNDED)
        table.add_column("Key ID", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Scope", style="yellow")
        for key_id, kd in (keys_list.items() if isinstance(keys_list, dict) else []):
            table.add_row(str(key_id)[:16], kd.get("label", "")[:20], kd.get("scope", "user"))
        console.print(table)
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@keys.command("add")
@click.option("--label", required=True, help="Descriptive label")
@click.option("--scope", type=click.Choice(["user", "operator", "auditor", "admin"]), default="user")
@click.pass_context
def add_key(ctx: click.Context, label: str, scope: str):
    """Create a new API key."""
    node_url, api_key = ctx.obj["client"].node_url, ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required. Provide --api-key or XAI_API_KEY.")
    try:
        result = _admin_request(node_url, api_key, "POST", "/admin/api-keys", json={"label": label, "scope": scope})
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return
        if result.get("api_key"):
            console.print(f"[bold green]API Key Created![/]\nKey: [cyan]{result['api_key']}[/]")
            console.print("[bold red]Save this key now - it won't be shown again.[/]")
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown')}")
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@keys.command("revoke")
@click.argument("key_id")
@click.pass_context
def revoke_key(ctx: click.Context, key_id: str):
    """Revoke an API key."""
    node_url, api_key = ctx.obj["client"].node_url, ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")
    if not ctx.obj.get('assume_yes') and not Confirm.ask(f"Revoke key {key_id}?", default=False):
        return
    try:
        result = _admin_request(node_url, api_key, "DELETE", f"/admin/api-keys/{key_id}")
        if result.get("revoked") or result.get("success"):
            console.print(f"[green]Key {key_id} revoked[/]")
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown')}")
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@admin.group("emergency")
def emergency():
    """Emergency control commands."""
    pass


@emergency.command("status")
@click.pass_context
def emerg_status(ctx: click.Context):
    """Get emergency pause status."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        data = _admin_request(node_url, api_key, "GET", "/admin/emergency/status")
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return
        is_paused = data.get("paused", False)
        cb = data.get("circuit_breaker", {})
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Status", "[red]PAUSED[/]" if is_paused else "[green]NORMAL[/]")
        table.add_row("[cyan]Circuit Breaker", cb.get("state", "unknown"))
        console.print(Panel(table, title="Emergency Status", border_style="red" if is_paused else "green"))
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@emergency.command("trigger")
@click.option("--reason", required=True, help="Pause reason")
@click.pass_context
def emerg_trigger(ctx: click.Context, reason: str):
    """Trigger emergency pause."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")
    if not ctx.obj.get('assume_yes') and not Confirm.ask("[red]Pause operations?[/]", default=False):
        return
    try:
        result = _admin_request(node_url, api_key, "POST", "/admin/emergency/pause", json={"reason": reason})
        if result.get("paused"):
            console.print("[bold red]EMERGENCY PAUSE ACTIVATED[/]")
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown')}")
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@emergency.command("cancel")
@click.option("--reason", default="Manual unpause", help="Resume reason")
@click.pass_context
def emerg_cancel(ctx: click.Context, reason: str):
    """Cancel emergency pause."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required.")
    if not ctx.obj.get('assume_yes') and not Confirm.ask("Resume operations?", default=True):
        return
    try:
        result = _admin_request(node_url, api_key, "POST", "/admin/emergency/unpause", json={"reason": reason})
        if not result.get("paused", True):
            console.print("[green]Operations resumed[/]")
        else:
            console.print(f"[red]Failed:[/] {result.get('error', 'Unknown')}")
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    admin()

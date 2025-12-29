#!/usr/bin/env python3
"""
XAI Mining Bonus CLI Commands - Mining Rewards and Achievements

Provides CLI interface for mining bonus operations:
- Check current bonus status
- View achievements
- Display leaderboard
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
    """Centralized CLI error handler."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


def _mining_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to mining bonus endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Mining API error: {e}")


@click.group("mining-bonus")
def mining_bonus():
    """Mining bonus and achievement commands."""
    pass


@mining_bonus.command("bonus")
@click.argument("address")
@click.pass_context
def check_bonus(ctx: click.Context, address: str):
    """Check current mining bonus for an address."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        data = _mining_request(node_url, api_key, "GET", f"/mining/user-bonuses/{address}")
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Address", address[:40] + "...")
        table.add_row("[green]Total Bonus", f"{data.get('total_bonus', 0):.8f} XAI")
        table.add_row("[yellow]Pending", f"{data.get('pending', 0):.8f} XAI")
        table.add_row("[cyan]Claimed", f"{data.get('claimed', 0):.8f} XAI")
        console.print(Panel(table, title="[green]Mining Bonus", border_style="green"))
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@mining_bonus.command("achievements")
@click.argument("address")
@click.option("--blocks-mined", default=0, type=int, help="Blocks mined count")
@click.option("--streak-days", default=0, type=int, help="Streak days")
@click.pass_context
def list_achievements(ctx: click.Context, address: str, blocks_mined: int, streak_days: int):
    """List mining achievements for an address."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    params = {"blocks_mined": blocks_mined, "streak_days": streak_days}
    try:
        data = _mining_request(node_url, api_key, "GET", f"/mining/achievements/{address}", params=params)
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return
        achievements = data.get("achievements", data) if isinstance(data, dict) else data
        if not achievements:
            console.print("[yellow]No achievements[/]")
            return
        table = Table(title=f"Achievements - {address[:20]}...", box=box.ROUNDED)
        table.add_column("Achievement", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Reward", style="magenta", justify="right")
        for ach in (achievements if isinstance(achievements, list) else achievements.values()):
            if isinstance(ach, dict):
                name = ach.get("name", "Unknown")
                status = "[green]Unlocked[/]" if ach.get("unlocked") else "[dim]Locked[/]"
                reward = f"{ach.get('reward', 0):.4f} XAI" if ach.get("reward") else "-"
                table.add_row(name, status, reward)
        console.print(table)
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@mining_bonus.command("leaderboard")
@click.option("--limit", default=10, type=int, help="Entries to show")
@click.option("--metric", type=click.Choice(["composite", "blocks", "bonuses"]), default="composite")
@click.pass_context
def show_leaderboard(ctx: click.Context, limit: int, metric: str):
    """Display mining bonus leaderboard."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        if metric == "composite":
            data = _mining_request(node_url, api_key, "GET", "/mining/leaderboard/unified", params={"metric": metric, "limit": limit})
        else:
            data = _mining_request(node_url, api_key, "GET", "/mining/leaderboard", params={"limit": limit})
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return
        leaderboard = data.get("leaderboard", [])
        if not leaderboard:
            console.print("[yellow]Leaderboard empty[/]")
            return
        table = Table(title=f"Mining Leaderboard (Top {limit})", box=box.ROUNDED)
        table.add_column("Rank", style="yellow", justify="right")
        table.add_column("Miner", style="cyan")
        table.add_column("Blocks", style="green", justify="right")
        table.add_column("Bonuses", style="magenta", justify="right")
        for i, entry in enumerate(leaderboard, 1):
            if isinstance(entry, dict):
                addr = entry.get("address", "")[:20] + "..."
                blocks = str(entry.get("blocks_mined", entry.get("blocks", 0)))
                bonuses = f"{entry.get('total_bonuses', entry.get('bonuses', 0)):.4f}"
                rank = "[gold1]1[/]" if i == 1 else "[silver]2[/]" if i == 2 else "[orange3]3[/]" if i == 3 else str(i)
                table.add_row(rank, addr, blocks, bonuses)
        console.print(table)
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@mining_bonus.command("stats")
@click.pass_context
def show_stats(ctx: click.Context):
    """Display system-wide mining bonus statistics."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        data = _mining_request(node_url, api_key, "GET", "/mining/stats")
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return
        stats = data.get("stats", data)
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Total Bonuses Issued", f"{stats.get('total_bonuses_issued', 0):.8f} XAI")
        table.add_row("[cyan]Active Miners", str(stats.get("active_miners", 0)))
        table.add_row("[cyan]Achievements Unlocked", str(stats.get("achievements_unlocked", 0)))
        console.print(Panel(table, title="[green]Mining Bonus Stats", border_style="green"))
    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    mining_bonus()

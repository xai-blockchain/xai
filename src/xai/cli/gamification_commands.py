#!/usr/bin/env python3
"""
XAI Gamification CLI Commands

Provides CLI interface for gamification features:
- Airdrops, mining streaks, treasures, time capsules, refunds
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
    print("ERROR: Required packages not installed. Install with: pip install click rich")
    sys.exit(1)

import requests

logger = logging.getLogger(__name__)
console = Console()


def _api_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to gamification endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"API error: {e}")


@click.group()
def gamification():
    """Gamification commands (airdrops, streaks, treasures, time capsules)."""
    pass


# === AIRDROP COMMANDS ===

@gamification.group()
def airdrop():
    """Airdrop commands."""
    pass


@airdrop.command("winners")
@click.option("--limit", default=10, type=int, help="Number of winners to show")
@click.pass_context
def airdrop_winners(ctx: click.Context, limit: int):
    """Show recent airdrop winners."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/airdrop/winners?limit={limit}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    airdrops = data.get("airdrops", [])
    if not airdrops:
        console.print("[yellow]No recent airdrops[/]")
        return

    table = Table(title="Recent Airdrop Winners", box=box.ROUNDED)
    table.add_column("Address", style="cyan")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Time", style="dim")

    for ad in airdrops:
        table.add_row(ad.get("address", "")[:20] + "...", f"{ad.get('amount', 0):.4f}", str(ad.get("timestamp", "")))
    console.print(table)


@airdrop.command("history")
@click.argument("address")
@click.pass_context
def airdrop_history(ctx: click.Context, address: str):
    """Show airdrop history for an address."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/airdrop/user/{address}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    console.print(f"[cyan]Address:[/] {address}")
    console.print(f"[green]Total Airdrops:[/] {data.get('total_airdrops', 0)}")
    console.print(f"[green]Total Received:[/] {data.get('total_received', 0):.8f} XAI")


# === STREAK COMMANDS ===

@gamification.group()
def streak():
    """Mining streak commands."""
    pass


@streak.command("leaderboard")
@click.option("--limit", default=10, type=int, help="Number of entries")
@click.option("--sort", default="current_streak", type=click.Choice(["current_streak", "longest_streak"]))
@click.pass_context
def streak_leaderboard(ctx: click.Context, limit: int, sort: str):
    """Show mining streak leaderboard."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/mining/streaks?limit={limit}&sort_by={sort}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    leaderboard = data.get("leaderboard", [])
    if not leaderboard:
        console.print("[yellow]No streak data[/]")
        return

    table = Table(title="Mining Streak Leaderboard", box=box.ROUNDED)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Miner", style="cyan")
    table.add_column("Current", style="green", justify="right")
    table.add_column("Longest", style="yellow", justify="right")

    for i, entry in enumerate(leaderboard, 1):
        table.add_row(str(i), entry.get("address", "")[:16] + "...",
                      str(entry.get("current_streak", 0)), str(entry.get("longest_streak", 0)))
    console.print(table)


@streak.command("stats")
@click.argument("address")
@click.pass_context
def streak_stats(ctx: click.Context, address: str):
    """Show mining streak stats for an address."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/mining/streak/{address}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    stats = data.get("stats", {})
    console.print(Panel(
        f"[cyan]Current Streak:[/] {stats.get('current_streak', 0)} blocks\n"
        f"[yellow]Longest Streak:[/] {stats.get('longest_streak', 0)} blocks\n"
        f"[green]Total Blocks:[/] {stats.get('total_blocks', 0)}",
        title=f"Streak Stats - {address[:20]}...",
        border_style="cyan"
    ))


# === TREASURE COMMANDS ===

@gamification.group()
def treasure():
    """Treasure hunt commands."""
    pass


@treasure.command("list")
@click.pass_context
def treasure_list(ctx: click.Context):
    """List active treasure hunts."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", "/treasure/active")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    treasures = data.get("treasures", [])
    if not treasures:
        console.print("[yellow]No active treasures[/]")
        return

    table = Table(title=f"Active Treasures ({data.get('count', 0)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Type", style="yellow")
    table.add_column("Hint", style="dim")

    for t in treasures:
        table.add_row(t.get("id", "")[:12], f"{t.get('amount', 0):.4f}",
                      t.get("puzzle_type", ""), t.get("hint", "")[:30])
    console.print(table)


@treasure.command("details")
@click.argument("treasure_id")
@click.pass_context
def treasure_details(ctx: click.Context, treasure_id: str):
    """Show treasure hunt details."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/treasure/details/{treasure_id}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    t = data.get("treasure", {})
    console.print(Panel(
        f"[cyan]ID:[/] {t.get('id', 'N/A')}\n"
        f"[green]Amount:[/] {t.get('amount', 0):.8f} XAI\n"
        f"[yellow]Type:[/] {t.get('puzzle_type', 'N/A')}\n"
        f"[cyan]Hint:[/] {t.get('hint', 'None')}\n"
        f"[dim]Claimed:[/] {'Yes' if t.get('claimed') else 'No'}",
        title="Treasure Details", border_style="green"
    ))


@treasure.command("claim")
@click.option("--id", "treasure_id", required=True, help="Treasure ID")
@click.option("--claimer", required=True, help="Your address")
@click.option("--solution", required=True, help="Puzzle solution")
@click.pass_context
def treasure_claim(ctx: click.Context, treasure_id: str, claimer: str, solution: str):
    """Claim a treasure by solving its puzzle."""
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    if not api_key:
        raise click.ClickException("API key required")

    data = _api_request(node_url, api_key, "POST", "/treasure/claim",
                        json={"treasure_id": treasure_id, "claimer": claimer, "solution": solution})

    if data.get("success"):
        console.print(f"[green]Treasure claimed! Amount: {data.get('amount', 0):.8f} XAI[/]")
    else:
        console.print(f"[red]Failed:[/] {data.get('error', 'Unknown error')}")


# === TIMECAPSULE COMMANDS ===

@gamification.group()
def timecapsule():
    """Time capsule commands."""
    pass


@timecapsule.command("pending")
@click.pass_context
def timecapsule_pending(ctx: click.Context):
    """List pending time capsules."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", "/timecapsule/pending")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    capsules = data.get("capsules", [])
    console.print(f"[cyan]Pending Time Capsules:[/] {data.get('count', 0)}")
    if capsules:
        for c in capsules[:10]:
            console.print(f"  - {c.get('id', '')[:12]}: {c.get('amount', 0):.4f} XAI (unlocks: {c.get('unlock_time', 'N/A')})")


@timecapsule.command("user")
@click.argument("address")
@click.pass_context
def timecapsule_user(ctx: click.Context, address: str):
    """Show time capsules for an address."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/timecapsule/{address}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    console.print(f"[cyan]Sent:[/] {len(data.get('sent', []))} capsules")
    console.print(f"[green]Received:[/] {len(data.get('received', []))} capsules")


# === REFUND COMMANDS ===

@gamification.group()
def refund():
    """Fee refund commands."""
    pass


@refund.command("stats")
@click.pass_context
def refund_stats(ctx: click.Context):
    """Show system-wide refund statistics."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", "/refunds/stats")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    stats = data.get("stats", {})
    console.print(Panel(
        f"[cyan]Total Refunds:[/] {stats.get('total_refunds', 0)}\n"
        f"[green]Total Amount:[/] {stats.get('total_amount', 0):.8f} XAI\n"
        f"[yellow]Avg Refund:[/] {stats.get('average_refund', 0):.8f} XAI",
        title="Refund Statistics", border_style="green"
    ))


@refund.command("history")
@click.argument("address")
@click.pass_context
def refund_history(ctx: click.Context, address: str):
    """Show refund history for an address."""
    node_url = ctx.obj["client"].node_url
    data = _api_request(node_url, None, "GET", f"/refunds/{address}")

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2))
        return

    console.print(f"[cyan]Address:[/] {address}")
    console.print(f"[green]Total Refunds:[/] {data.get('total_refunds', 0)}")
    console.print(f"[green]Total Refunded:[/] {data.get('total_refunded', 0):.8f} XAI")


if __name__ == "__main__":
    gamification()

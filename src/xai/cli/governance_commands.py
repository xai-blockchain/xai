#!/usr/bin/env python3
"""
XAI Governance CLI Commands - Agent-Accessible Governance Interface

Provides CLI equivalents for all governance API endpoints:
- Proposal submission and listing
- Voting on proposals
- Voting power queries
- Proposal status and details
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


class GovernanceClient:
    """Client for governance API operations."""

    def __init__(self, node_url: str, timeout: float = 30.0, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to governance endpoint."""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Governance request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=headers, **kwargs
            )
            response.raise_for_status()
            logger.debug("Governance response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Governance API error: %s", e)
            raise click.ClickException(f"Governance API error: {e}")

    def list_proposals(
        self, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """List governance proposals."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._request("GET", "/governance/proposals", params=params)

    def get_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Get proposal details."""
        return self._request("GET", f"/governance/proposals/{proposal_id}")

    def submit_proposal(self, proposal_data: dict[str, Any]) -> dict[str, Any]:
        """Submit a new proposal."""
        return self._request("POST", "/governance/proposals/submit", json=proposal_data)

    def vote(
        self, proposal_id: str, voter: str, vote: str, signature: str | None = None
    ) -> dict[str, Any]:
        """Vote on a proposal."""
        payload = {
            "proposal_id": proposal_id,
            "voter_address": voter,
            "vote": vote,
        }
        if signature:
            payload["signature"] = signature
        return self._request("POST", "/governance/vote", json=payload)

    def get_voting_power(self, address: str) -> dict[str, Any]:
        """Get voting power for an address."""
        return self._request("GET", f"/governance/voting-power/{address}")


@click.group()
def governance():
    """Governance voting and proposal commands."""
    pass


@governance.command("list")
@click.option(
    "--status",
    type=click.Choice(["active", "pending", "approved", "rejected", "executed", "all"]),
    default="all",
    help="Filter proposals by status",
)
@click.option("--limit", default=20, type=int, help="Maximum proposals to show")
@click.option("--offset", default=0, type=int, help="Pagination offset")
@click.pass_context
def list_proposals(ctx: click.Context, status: str, limit: int, offset: int):
    """
    List governance proposals.

    Shows all proposals or filter by status. Displays proposal ID, title,
    status, vote counts, and creation time.

    Example:
        xai governance list --status active --limit 10
    """
    client = GovernanceClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching proposals..."):
            filter_status = status if status != "all" else None
            data = client.list_proposals(status=filter_status, limit=limit, offset=offset)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        proposals = data.get("proposals", [])
        if not proposals:
            console.print("[yellow]No proposals found[/]")
            return

        # Create proposals table
        table = Table(
            title=f"Governance Proposals ({len(proposals)})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white", max_width=40)
        table.add_column("Status", style="green")
        table.add_column("Yes", style="green", justify="right")
        table.add_column("No", style="red", justify="right")
        table.add_column("Created", style="dim")

        status_colors = {
            "active": "yellow",
            "pending": "blue",
            "approved": "green",
            "rejected": "red",
            "executed": "cyan",
        }

        for prop in proposals:
            prop_id = prop.get("id", prop.get("proposal_id", "N/A"))[:16]
            title = prop.get("title", "Untitled")[:40]
            prop_status = prop.get("status", "unknown")
            color = status_colors.get(prop_status, "white")
            yes_votes = prop.get("votes_for", prop.get("yes_votes", 0))
            no_votes = prop.get("votes_against", prop.get("no_votes", 0))
            created = prop.get("created_at", prop.get("timestamp"))
            created_str = (
                datetime.fromisoformat(created).strftime("%Y-%m-%d")
                if isinstance(created, str)
                else datetime.fromtimestamp(created).strftime("%Y-%m-%d")
                if created
                else "N/A"
            )

            table.add_row(
                prop_id,
                title,
                f"[{color}]{prop_status.upper()}[/]",
                str(yes_votes),
                str(no_votes),
                created_str,
            )

        console.print(table)

        if len(proposals) >= limit:
            console.print(
                f"\n[dim]Showing {limit} proposals. Use --offset to see more.[/]"
            )

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@governance.command("show")
@click.argument("proposal_id")
@click.pass_context
def show_proposal(ctx: click.Context, proposal_id: str):
    """
    Show detailed proposal information.

    Displays full proposal details including description, vote breakdown,
    timeline, and execution status.

    Example:
        xai governance show prop_abc123def456
    """
    client = GovernanceClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Fetching proposal {proposal_id}..."):
            data = client.get_proposal(proposal_id)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        proposal = data.get("proposal", data)

        # Build info table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Proposal ID", proposal.get("id", proposal_id))
        table.add_row("[bold cyan]Title", proposal.get("title", "Untitled"))
        table.add_row("[bold cyan]Status", proposal.get("status", "unknown").upper())
        table.add_row("[bold cyan]Creator", proposal.get("creator", "N/A")[:40])
        table.add_row("[bold cyan]Type", proposal.get("proposal_type", "N/A"))

        # Vote counts
        yes_votes = proposal.get("votes_for", proposal.get("yes_votes", 0))
        no_votes = proposal.get("votes_against", proposal.get("no_votes", 0))
        abstain = proposal.get("votes_abstain", 0)
        total = yes_votes + no_votes + abstain

        table.add_row("[bold green]Yes Votes", str(yes_votes))
        table.add_row("[bold red]No Votes", str(no_votes))
        if abstain > 0:
            table.add_row("[bold yellow]Abstain", str(abstain))
        table.add_row("[bold cyan]Total Votes", str(total))

        if total > 0:
            yes_pct = (yes_votes / total) * 100
            table.add_row("[bold cyan]Approval Rate", f"{yes_pct:.1f}%")

        # Timeline
        created = proposal.get("created_at")
        if created:
            table.add_row(
                "[bold cyan]Created",
                datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
                if isinstance(created, str)
                else datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M"),
            )

        ends = proposal.get("voting_ends_at")
        if ends:
            table.add_row(
                "[bold cyan]Voting Ends",
                datetime.fromisoformat(ends).strftime("%Y-%m-%d %H:%M")
                if isinstance(ends, str)
                else datetime.fromtimestamp(ends).strftime("%Y-%m-%d %H:%M"),
            )

        console.print(
            Panel(table, title="[bold green]Proposal Details", border_style="green")
        )

        # Description
        description = proposal.get("description", "")
        if description:
            console.print("\n[bold]Description:[/]")
            console.print(Panel(description[:500], border_style="dim"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@governance.command("propose")
@click.option("--title", required=True, help="Proposal title")
@click.option("--description", required=True, help="Proposal description")
@click.option(
    "--type",
    "proposal_type",
    type=click.Choice(["parameter_change", "ai_improvement", "treasury", "emergency"]),
    default="parameter_change",
    help="Type of proposal",
)
@click.option("--proposer", required=True, help="Proposer wallet address")
@click.option("--data", "payload_json", help="JSON payload for proposal data")
@click.pass_context
def create_proposal(
    ctx: click.Context,
    title: str,
    description: str,
    proposal_type: str,
    proposer: str,
    payload_json: str | None,
):
    """
    Submit a new governance proposal.

    Create a proposal for community voting. Proposals can modify parameters,
    improve AI systems, manage treasury, or handle emergencies.

    Example:
        xai governance propose --title "Increase Block Size" \\
            --description "Increase max block size to 2MB" \\
            --type parameter_change --proposer XAI123...
    """
    client = GovernanceClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    # Parse optional JSON payload
    payload = None
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid JSON payload: {e}")

    # Display proposal summary
    console.print("\n[bold cyan]New Governance Proposal[/]\n")
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Title", title)
    table.add_row("[bold cyan]Type", proposal_type.upper())
    table.add_row("[bold cyan]Proposer", proposer[:40] + "...")
    table.add_row("[bold cyan]Description", description[:100] + ("..." if len(description) > 100 else ""))
    if payload:
        table.add_row("[bold cyan]Payload", json.dumps(payload, indent=2)[:100])
    console.print(table)

    if not Confirm.ask("\n[bold]Submit this proposal?[/]", default=True):
        console.print("[yellow]Proposal submission cancelled[/]")
        return

    proposal_data = {
        "title": title,
        "description": description,
        "proposal_type": proposal_type,
        "proposer": proposer,
    }
    if payload:
        proposal_data["payload"] = payload

    try:
        logger.info("Submitting proposal: title=%s, type=%s", title, proposal_type)
        with console.status("[bold cyan]Submitting proposal..."):
            result = client.submit_proposal(proposal_data)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success", True):
            prop_id = result.get("proposal_id", "pending")
            logger.info("Proposal submitted: id=%s", prop_id)
            console.print(f"\n[bold green]Proposal submitted successfully![/]")
            console.print(f"Proposal ID: [cyan]{prop_id}[/]")
            console.print(f"Status: [yellow]{result.get('status', 'pending').upper()}[/]")
        else:
            console.print(f"[bold red]Submission failed:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@governance.command("vote")
@click.argument("proposal_id")
@click.option(
    "--choice",
    type=click.Choice(["yes", "no", "abstain"]),
    required=True,
    help="Vote choice",
)
@click.option("--voter", required=True, help="Voter wallet address")
@click.option("--keystore", type=click.Path(exists=True), help="Keystore file for signing")
@click.pass_context
def vote_proposal(
    ctx: click.Context,
    proposal_id: str,
    choice: str,
    voter: str,
    keystore: str | None,
):
    """
    Vote on a governance proposal.

    Cast your vote on an active proposal. Your voting power is calculated
    based on your XAI balance and staking history.

    Example:
        xai governance vote prop_abc123 --choice yes --voter XAI123...
    """
    client = GovernanceClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    # Get voting power first
    try:
        power_data = client.get_voting_power(voter)
        voting_power = power_data.get("voting_power", {}).get("total", 0)
    except (click.ClickException, requests.RequestException):
        voting_power = "unknown"

    # Display vote summary
    console.print("\n[bold cyan]Governance Vote[/]\n")
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Proposal ID", proposal_id)
    table.add_row("[bold cyan]Voter", voter[:40] + "...")
    table.add_row("[bold cyan]Choice", choice.upper())
    table.add_row("[bold cyan]Voting Power", str(voting_power))
    console.print(table)

    if not Confirm.ask(f"\n[bold]Cast {choice.upper()} vote?[/]", default=True):
        console.print("[yellow]Vote cancelled[/]")
        return

    try:
        logger.info("Casting vote: proposal=%s, choice=%s, voter=%s", proposal_id, choice, voter[:16])
        with console.status("[bold cyan]Submitting vote..."):
            result = client.vote(proposal_id, voter, choice)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success", True):
            logger.info("Vote cast successfully: proposal=%s", proposal_id)
            console.print(f"\n[bold green]Vote cast successfully![/]")
            console.print(f"Proposal: [cyan]{proposal_id}[/]")
            console.print(f"Choice: [yellow]{choice.upper()}[/]")
            console.print(f"Voting Power: [green]{result.get('voting_power', 'N/A')}[/]")
        else:
            console.print(f"[bold red]Vote failed:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@governance.command("power")
@click.argument("address")
@click.pass_context
def voting_power(ctx: click.Context, address: str):
    """
    Query voting power for an address.

    Shows voting power breakdown including coin-based power and
    any bonus power from staking or donations.

    Example:
        xai governance power XAI123...
    """
    client = GovernanceClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Calculating voting power for {address[:20]}..."):
            data = client.get_voting_power(address)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        voting_info = data.get("voting_power", data)

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Address", address[:40] + "...")
        table.add_row("[bold cyan]XAI Balance", f"{data.get('xai_balance', 0):.8f} XAI")
        table.add_row("[bold green]Coin Power", f"{voting_info.get('coin_power', 0):.2f}")
        table.add_row("[bold yellow]Donation Power", f"{voting_info.get('donation_power', 0):.2f}")
        table.add_row("[bold magenta]Total Power", f"{voting_info.get('total', 0):.2f}")

        console.print(
            Panel(table, title="[bold green]Voting Power", border_style="green")
        )

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    governance()

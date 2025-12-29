#!/usr/bin/env python3
"""
XAI Webhook CLI Commands - Webhook Management Interface

Provides CLI equivalents for webhook management API endpoints:
- Subscribe to blockchain events
- Unsubscribe from webhooks
- List registered webhooks
- View available event types
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
    """Centralized CLI error handler for consistent messaging/exit codes."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


class WebhookClient:
    """Client for webhook API operations."""

    def __init__(self, node_url: str, timeout: float = 30.0, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to webhook endpoint."""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Webhook request: %s %s", method, url)
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=headers, **kwargs
            )
            response.raise_for_status()
            logger.debug("Webhook response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Webhook API error: %s", e)
            raise click.ClickException(f"Webhook API error: {e}")

    def subscribe(
        self,
        url: str,
        events: list[str],
        owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new webhook subscription."""
        payload = {
            "url": url,
            "events": events,
            "owner": owner,
        }
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", "/api/v1/webhooks/register", json=payload)

    def unsubscribe(self, webhook_id: str, owner: str) -> dict[str, Any]:
        """Unregister a webhook subscription."""
        return self._request(
            "DELETE",
            f"/api/v1/webhooks/{webhook_id}",
            json={"owner": owner},
        )

    def list_webhooks(self, owner: str | None = None) -> dict[str, Any]:
        """List registered webhooks."""
        params = {}
        if owner:
            params["owner"] = owner
        return self._request("GET", "/api/v1/webhooks", params=params)

    def list_events(self) -> dict[str, Any]:
        """List available webhook event types."""
        return self._request("GET", "/api/v1/webhooks/events")

    def get_webhook(self, webhook_id: str, owner: str | None = None) -> dict[str, Any]:
        """Get webhook details."""
        params = {}
        if owner:
            params["owner"] = owner
        return self._request("GET", f"/api/v1/webhooks/{webhook_id}", params=params)

    def test_webhook(self, webhook_id: str, owner: str, event: str = "new_block") -> dict[str, Any]:
        """Send a test event to a webhook."""
        return self._request(
            "POST",
            f"/api/v1/webhooks/{webhook_id}/test",
            json={"owner": owner, "event": event},
        )


@click.group()
def webhook():
    """Webhook management commands for event subscriptions."""
    pass


@webhook.command("subscribe")
@click.option("--url", required=True, help="Webhook endpoint URL (must be HTTPS in production)")
@click.option(
    "--events",
    required=True,
    help="Comma-separated list of event types (e.g., new_block,new_transaction)",
)
@click.option("--owner", required=True, help="Owner wallet address")
@click.option("--metadata", help="Optional JSON metadata for the webhook")
@click.pass_context
def subscribe(
    ctx: click.Context,
    url: str,
    events: str,
    owner: str,
    metadata: str | None,
):
    """
    Subscribe to blockchain events via webhook.

    Register a webhook endpoint to receive notifications when blockchain
    events occur. The webhook secret will be displayed once upon creation.

    Available events:
        - new_block: New block mined
        - new_transaction: Transaction added to mempool
        - governance_vote: Vote cast on proposal
        - proposal_created: New governance proposal
        - proposal_executed: Proposal execution completed
        - balance_change: Address balance changed
        - contract_deployed: Smart contract deployed
        - contract_called: Smart contract invoked
        - mining_reward: Mining reward received
        - ai_task_completed: AI compute task finished

    Example:
        xai webhook subscribe --url https://example.com/hook \\
            --events new_block,new_transaction --owner XAI123...
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    # Parse events
    event_list = [e.strip() for e in events.split(",") if e.strip()]
    if not event_list:
        raise click.ClickException("At least one event type is required")

    # Parse metadata if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid JSON metadata: {e}")

    # Display subscription summary
    console.print("\n[bold cyan]Webhook Subscription[/]\n")
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]URL", url)
    table.add_row("[bold cyan]Events", ", ".join(event_list))
    table.add_row("[bold cyan]Owner", owner[:40] + ("..." if len(owner) > 40 else ""))
    if metadata_dict:
        table.add_row("[bold cyan]Metadata", json.dumps(metadata_dict)[:60])
    console.print(table)

    if not ctx.obj.get('assume_yes') and not Confirm.ask("\n[bold]Create this webhook subscription?[/]", default=True):
        console.print("[yellow]Subscription cancelled[/]")
        return

    try:
        logger.info("Creating webhook subscription: url=%s, events=%s", url, event_list)
        with console.status("[bold cyan]Creating webhook subscription..."):
            result = client.subscribe(url, event_list, owner, metadata_dict)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            webhook_id = result.get("webhook_id", "unknown")
            secret = result.get("secret", "")
            logger.info("Webhook created: id=%s", webhook_id)

            console.print(f"\n[bold green]Webhook subscription created![/]")
            console.print(f"Webhook ID: [cyan]{webhook_id}[/]")
            console.print(f"Events: [yellow]{', '.join(result.get('events', event_list))}[/]")

            if secret:
                console.print(f"\n[bold yellow]IMPORTANT: Save your webhook secret![/]")
                console.print(f"Secret: [cyan]{secret}[/]")
                console.print("[dim]This secret is used to verify webhook signatures.[/]")
                console.print("[dim]It will not be shown again.[/]")
        else:
            error = result.get("error", {})
            console.print(f"[bold red]Subscription failed:[/] {error.get('message', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@webhook.command("unsubscribe")
@click.argument("webhook_id")
@click.option("--owner", required=True, help="Owner wallet address (must match registration)")
@click.pass_context
def unsubscribe(ctx: click.Context, webhook_id: str, owner: str):
    """
    Unsubscribe from a webhook.

    Remove a webhook registration. The owner address must match
    the address used when creating the webhook.

    Example:
        xai webhook unsubscribe wh_abc123def456 --owner XAI123...
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    console.print(f"\n[bold cyan]Unsubscribe Webhook[/]")
    console.print(f"Webhook ID: [cyan]{webhook_id}[/]")
    console.print(f"Owner: [cyan]{owner[:40]}...[/]")

    if not ctx.obj.get('assume_yes') and not Confirm.ask("\n[bold]Remove this webhook?[/]", default=False):
        console.print("[yellow]Unsubscribe cancelled[/]")
        return

    try:
        logger.info("Removing webhook: id=%s", webhook_id)
        with console.status("[bold cyan]Removing webhook..."):
            result = client.unsubscribe(webhook_id, owner)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            logger.info("Webhook removed: id=%s", webhook_id)
            console.print(f"\n[bold green]Webhook removed successfully![/]")
        else:
            error = result.get("error", {})
            console.print(f"[bold red]Unsubscribe failed:[/] {error.get('message', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@webhook.command("list")
@click.option("--owner", help="Filter by owner address")
@click.pass_context
def list_webhooks(ctx: click.Context, owner: str | None):
    """
    List registered webhooks.

    Shows all webhooks or filter by owner address. Displays webhook ID,
    URL, event subscriptions, and status.

    Example:
        xai webhook list --owner XAI123...
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching webhooks..."):
            data = client.list_webhooks(owner)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        webhooks = data.get("webhooks", [])
        if not webhooks:
            console.print("[yellow]No webhooks found[/]")
            return

        # Create webhooks table
        table = Table(
            title=f"Registered Webhooks ({len(webhooks)})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("URL", style="white", max_width=40)
        table.add_column("Events", style="yellow", max_width=30)
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")

        for wh in webhooks:
            wh_id = wh.get("id", "N/A")[:16]
            url = wh.get("url", "N/A")[:40]
            events = ", ".join(wh.get("events", []))[:30]
            active = wh.get("active", True)
            status = "[green]Active[/]" if active else "[red]Disabled[/]"
            created = wh.get("created_at")
            created_str = (
                datetime.fromtimestamp(created).strftime("%Y-%m-%d")
                if created
                else "N/A"
            )

            table.add_row(wh_id, url, events, status, created_str)

        console.print(table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@webhook.command("events")
@click.pass_context
def list_events(ctx: click.Context):
    """
    List available webhook event types.

    Shows all supported event types and their descriptions.

    Example:
        xai webhook events
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status("[bold cyan]Fetching event types..."):
            data = client.list_events()

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        events = data.get("events", [])
        if not events:
            console.print("[yellow]No event types available[/]")
            return

        # Create events table
        table = Table(
            title="Available Webhook Events",
            box=box.ROUNDED,
        )
        table.add_column("Event Type", style="cyan")
        table.add_column("Description", style="white")

        for event in events:
            table.add_row(event.get("name", "N/A"), event.get("description", ""))

        console.print(table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@webhook.command("show")
@click.argument("webhook_id")
@click.option("--owner", help="Owner address for authentication")
@click.pass_context
def show_webhook(ctx: click.Context, webhook_id: str, owner: str | None):
    """
    Show webhook details.

    Display detailed information about a specific webhook registration.

    Example:
        xai webhook show wh_abc123def456 --owner XAI123...
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Fetching webhook {webhook_id}..."):
            data = client.get_webhook(webhook_id, owner)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        webhook = data.get("webhook", data)

        # Build info table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Webhook ID", webhook.get("id", webhook_id))
        table.add_row("[bold cyan]URL", webhook.get("url", "N/A"))
        table.add_row("[bold cyan]Owner", webhook.get("owner", "N/A")[:40])
        table.add_row("[bold cyan]Events", ", ".join(webhook.get("events", [])))
        table.add_row(
            "[bold cyan]Status",
            "[green]Active[/]" if webhook.get("active", True) else "[red]Disabled[/]",
        )
        table.add_row("[bold cyan]Failure Count", str(webhook.get("failure_count", 0)))

        created = webhook.get("created_at")
        if created:
            table.add_row(
                "[bold cyan]Created",
                datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S"),
            )

        last_delivery = webhook.get("last_delivery")
        if last_delivery:
            table.add_row(
                "[bold cyan]Last Delivery",
                datetime.fromtimestamp(last_delivery).strftime("%Y-%m-%d %H:%M:%S"),
            )

        last_error = webhook.get("last_error")
        if last_error:
            table.add_row("[bold red]Last Error", last_error[:60])

        console.print(
            Panel(table, title="[bold green]Webhook Details", border_style="green")
        )

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@webhook.command("test")
@click.argument("webhook_id")
@click.option("--owner", required=True, help="Owner address")
@click.option(
    "--event",
    default="new_block",
    help="Event type to simulate (default: new_block)",
)
@click.pass_context
def test_webhook(ctx: click.Context, webhook_id: str, owner: str, event: str):
    """
    Send a test event to a webhook.

    Sends a test delivery to verify webhook connectivity and configuration.

    Example:
        xai webhook test wh_abc123def456 --owner XAI123... --event new_block
    """
    client = WebhookClient(
        ctx.obj["client"].node_url,
        api_key=ctx.obj.get("api_key"),
    )

    try:
        with console.status(f"[bold cyan]Sending test event to {webhook_id}..."):
            result = client.test_webhook(webhook_id, owner, event)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            console.print(f"\n[bold green]Test delivery successful![/]")
            console.print(f"Webhook ID: [cyan]{webhook_id}[/]")
            console.print(f"Event: [yellow]{event}[/]")
        else:
            console.print(f"[bold red]Test delivery failed:[/] {result.get('message', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    webhook()

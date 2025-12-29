#!/usr/bin/env python3
"""
XAI Push Notification CLI Commands

Provides CLI interface for push notification operations:
- Device registration and unregistration
- Notification settings management
- Test notifications
- Device listing and stats
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


def _notif_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to notification endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Notification API error: {e}")


@click.group("notifications")
def notifications():
    """Push notification management commands."""
    pass


@notifications.command("register")
@click.option("--address", required=True, help="Wallet address for notifications")
@click.option("--token", required=True, help="Device push token (FCM/APNs)")
@click.option("--platform", required=True, type=click.Choice(["ios", "android", "web"]), help="Device platform")
@click.option("--device-id", default=None, help="Optional unique device identifier")
@click.option("--types", default=None, help="Notification types (comma-separated: transaction,confirmation,security)")
@click.pass_context
def register_device(ctx: click.Context, address: str, token: str, platform: str, device_id: str | None, types: str | None):
    """
    Register a device for push notifications.

    Example:
        xai notifications register --address XAI1abc... --token fcm_xyz... --platform android
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        payload = {
            "user_address": address,
            "device_token": token,
            "platform": platform,
        }
        if device_id:
            payload["device_id"] = device_id
        if types:
            payload["notification_types"] = [t.strip() for t in types.split(",")]

        with console.status("[bold cyan]Registering device..."):
            data = _notif_request(node_url, api_key, "POST", "/notifications/register", json=payload)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        device = data.get("device", {})
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Address", address[:40] + ("..." if len(address) > 40 else ""))
        table.add_row("[cyan]Platform", platform)
        table.add_row("[cyan]Token", token[:20] + "...")
        table.add_row("[green]Status", data.get("status", "registered"))
        console.print(Panel(table, title="[green]Device Registered", border_style="green"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@notifications.command("unregister")
@click.option("--token", required=True, help="Device push token to unregister")
@click.pass_context
def unregister_device(ctx: click.Context, token: str):
    """
    Unregister a device from push notifications.

    Example:
        xai notifications unregister --token fcm_xyz...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        with console.status("[bold cyan]Unregistering device..."):
            data = _notif_request(node_url, api_key, "DELETE", "/notifications/unregister", json={"device_token": token})

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        console.print(f"[green]Device unregistered:[/] {token[:20]}...")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@notifications.command("settings")
@click.argument("token")
@click.option("--enabled/--disabled", default=None, help="Enable or disable notifications")
@click.option("--types", default=None, help="Set notification types (comma-separated)")
@click.pass_context
def manage_settings(ctx: click.Context, token: str, enabled: bool | None, types: str | None):
    """
    Get or update notification settings for a device.

    Examples:
        xai notifications settings fcm_xyz...
        xai notifications settings fcm_xyz... --enabled --types transaction,security
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        # If no update options, just GET settings
        if enabled is None and types is None:
            data = _notif_request(node_url, api_key, "GET", f"/notifications/settings/{token}")
            if ctx.obj.get("json_output"):
                click.echo(json.dumps(data, indent=2))
                return

            table = Table(show_header=False, box=box.ROUNDED)
            table.add_row("[cyan]Token", data.get("device_token", token)[:20] + "...")
            table.add_row("[cyan]Platform", data.get("platform", "unknown"))
            table.add_row("[cyan]Address", data.get("user_address", "")[:30] + "...")
            table.add_row("[green]Enabled" if data.get("enabled") else "[red]Disabled", str(data.get("enabled", False)))
            table.add_row("[cyan]Types", ", ".join(data.get("notification_types", [])))
            table.add_row("[dim]Last Active", data.get("last_active", "unknown"))
            console.print(Panel(table, title="[cyan]Notification Settings", border_style="cyan"))
        else:
            # PUT to update settings
            payload = {}
            if enabled is not None:
                payload["enabled"] = enabled
            if types is not None:
                payload["notification_types"] = [t.strip() for t in types.split(",")]

            with console.status("[bold cyan]Updating settings..."):
                data = _notif_request(node_url, api_key, "PUT", f"/notifications/settings/{token}", json=payload)

            if ctx.obj.get("json_output"):
                click.echo(json.dumps(data, indent=2))
                return

            settings = data.get("settings", {})
            console.print(f"[green]Settings updated:[/]")
            console.print(f"  Enabled: {settings.get('enabled', False)}")
            console.print(f"  Types: {', '.join(settings.get('notification_types', []))}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@notifications.command("test")
@click.option("--token", required=True, help="Device token to send test notification")
@click.pass_context
def send_test(ctx: click.Context, token: str):
    """
    Send a test notification to verify device registration.

    Example:
        xai notifications test --token fcm_xyz...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        with console.status("[bold cyan]Sending test notification..."):
            data = _notif_request(node_url, api_key, "POST", "/notifications/test", json={"device_token": token})

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        if data.get("status") == "sent":
            console.print(f"[green]Test notification sent to:[/] {token[:20]}...")
        else:
            console.print(f"[yellow]Status:[/] {data.get('status', 'unknown')}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@notifications.command("devices")
@click.argument("address")
@click.pass_context
def list_devices(ctx: click.Context, address: str):
    """
    List all devices registered to an address.

    Example:
        xai notifications devices XAI1abc...
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        data = _notif_request(node_url, api_key, "GET", f"/notifications/devices/{address}")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        devices = data.get("devices", [])
        if not devices:
            console.print(f"[yellow]No devices registered for {address[:20]}...[/]")
            return

        table = Table(title=f"Devices for {address[:20]}...", box=box.ROUNDED)
        table.add_column("Token", style="cyan")
        table.add_column("Platform", style="green")
        table.add_column("Enabled", style="yellow")
        table.add_column("Types", style="dim")
        table.add_column("Last Active", style="dim")

        for dev in devices:
            status = "[green]Yes[/]" if dev.get("enabled") else "[red]No[/]"
            types_str = ", ".join(dev.get("notification_types", []))[:20]
            table.add_row(
                dev.get("device_token", "?"),
                dev.get("platform", "?"),
                status,
                types_str or "-",
                dev.get("last_active", "?")[:10],
            )

        console.print(table)
        console.print(f"\n[dim]Total devices: {data.get('device_count', len(devices))}[/]")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@notifications.command("stats")
@click.pass_context
def show_stats(ctx: click.Context):
    """
    Display push notification system statistics.

    Example:
        xai notifications stats
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")
    try:
        data = _notif_request(node_url, api_key, "GET", "/notifications/stats")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        stats = data.get("stats", {})
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Total Devices", str(stats.get("total_devices", 0)))
        table.add_row("[cyan]Enabled Devices", str(stats.get("enabled_devices", 0)))
        table.add_row("[cyan]iOS Devices", str(stats.get("ios_count", stats.get("by_platform", {}).get("ios", 0))))
        table.add_row("[cyan]Android Devices", str(stats.get("android_count", stats.get("by_platform", {}).get("android", 0))))
        table.add_row("[cyan]Web Devices", str(stats.get("web_count", stats.get("by_platform", {}).get("web", 0))))
        console.print(Panel(table, title="[green]Notification Stats", border_style="green"))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    notifications()

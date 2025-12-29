#!/usr/bin/env python3
"""
XAI Payment CLI Commands - Payment Request Operations

Provides CLI interface for payment operations:
- Create payment requests with QR codes
- Check payment request status
- Verify payments against requests
- Generate payment QR codes
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


def _payment_request(node_url: str, api_key: str | None, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
    """Make HTTP request to payment endpoint."""
    url = f"{node_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.request(method, url, timeout=30.0, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Payment API error: {e}")


@click.group()
def payment():
    """Payment request and QR code commands."""
    pass


@payment.command("create")
@click.option("--address", required=True, help="Receiving wallet address")
@click.option("--amount", required=True, type=float, help="Amount to request")
@click.option("--memo", default="", help="Payment memo/description")
@click.option("--expires", default=3600, type=int, help="Expiry time in seconds (default: 3600)")
@click.option("--save-qr", type=click.Path(), help="Save QR code to file (PNG)")
@click.pass_context
def create_request(ctx: click.Context, address: str, amount: float, memo: str, expires: int, save_qr: str | None):
    """
    Create a tracked payment request with QR code.

    Example:
        xai payment create --address XAI1... --amount 100.0 --memo "Invoice #123"
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        with console.status("[bold cyan]Creating payment request..."):
            result = _payment_request(
                node_url, api_key, "POST", "/payment/request",
                json={
                    "address": address,
                    "amount": amount,
                    "memo": memo,
                    "expires_in": expires
                }
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        request_id = result.get("request_id", "N/A")
        expires_at = result.get("expires_at", "N/A")

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Request ID", request_id)
        table.add_row("[cyan]Address", address[:40] + ("..." if len(address) > 40 else ""))
        table.add_row("[green]Amount", f"{amount:.8f} XAI")
        if memo:
            table.add_row("[cyan]Memo", memo[:40])
        table.add_row("[yellow]Expires", str(expires_at))
        table.add_row("[cyan]Status", "[yellow]pending[/]")

        console.print(Panel(table, title="[green]Payment Request Created", border_style="green"))

        # Save QR code if requested
        if save_qr and result.get("qr_image_base64"):
            import base64
            qr_data = base64.b64decode(result["qr_image_base64"])
            with open(save_qr, "wb") as f:
                f.write(qr_data)
            console.print(f"\n[green]QR code saved to:[/] {save_qr}")

        # Display payment URI if available
        if result.get("payment_uri"):
            console.print(f"\n[cyan]Payment URI:[/] {result['payment_uri']}")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@payment.command("status")
@click.argument("request_id")
@click.pass_context
def check_status(ctx: click.Context, request_id: str):
    """
    Check payment request status.

    Example:
        xai payment status abc123-def456
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    try:
        data = _payment_request(node_url, api_key, "GET", f"/payment/request/{request_id}")

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(data, indent=2))
            return

        status = data.get("status", "unknown")
        status_colors = {
            "pending": "yellow",
            "paid": "green",
            "expired": "red",
            "cancelled": "dim"
        }
        status_color = status_colors.get(status, "white")

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Request ID", data.get("request_id", "N/A"))
        table.add_row("[cyan]Address", data.get("address", "N/A")[:40] + "...")
        table.add_row("[cyan]Amount", f"{data.get('amount', 0):.8f} XAI")
        if data.get("memo"):
            table.add_row("[cyan]Memo", data["memo"][:40])
        table.add_row("[cyan]Status", f"[{status_color}]{status.upper()}[/]")

        if data.get("paid_txid"):
            table.add_row("[green]Paid TXID", data["paid_txid"][:40] + "...")
            if data.get("paid_at"):
                table.add_row("[green]Paid At", str(data["paid_at"]))

        border_color = "green" if status == "paid" else "yellow" if status == "pending" else "red"
        console.print(Panel(table, title=f"Payment Request Status", border_style=border_color))

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@payment.command("verify")
@click.option("--txid", required=True, help="Transaction ID to verify")
@click.option("--request-id", help="Payment request ID (optional)")
@click.option("--recipient", help="Expected recipient address (if no request-id)")
@click.option("--amount", type=float, help="Expected amount (if no request-id)")
@click.pass_context
def verify_payment(ctx: click.Context, txid: str, request_id: str | None, recipient: str | None, amount: float | None):
    """
    Verify a payment against a request or expected values.

    Example:
        xai payment verify --txid abc123 --request-id req456
        xai payment verify --txid abc123 --recipient XAI1... --amount 100.0
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    if not request_id and not recipient:
        raise click.ClickException("Either --request-id or --recipient must be provided")

    payload: dict[str, Any] = {"txid": txid}
    if request_id:
        payload["request_id"] = request_id
    if recipient:
        payload["recipient"] = recipient
    if amount is not None:
        payload["expected_amount"] = amount

    try:
        with console.status("[bold cyan]Verifying payment..."):
            result = _payment_request(
                node_url, api_key, "POST", "/payment/verify",
                json=payload
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        verified = result.get("verified", False)
        if verified:
            console.print(Panel(
                f"[green]Payment verified successfully![/]\n\n"
                f"[cyan]Transaction:[/] {txid[:40]}...\n"
                f"[cyan]Amount:[/] {result.get('amount', 'N/A')} XAI\n"
                f"[cyan]Confirmations:[/] {result.get('confirmations', 0)}",
                title="[bold green]Payment Verified",
                border_style="green"
            ))
        else:
            error = result.get("error", "Verification failed")
            console.print(Panel(
                f"[red]Payment verification failed[/]\n\n"
                f"[yellow]Reason:[/] {error}",
                title="[bold red]Verification Failed",
                border_style="red"
            ))
            sys.exit(1)

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@payment.command("qr")
@click.option("--address", required=True, help="Receiving wallet address")
@click.option("--amount", type=float, help="Amount to request (optional)")
@click.option("--memo", default="", help="Payment memo/description")
@click.option("--save", type=click.Path(), help="Save QR code to file (PNG)")
@click.pass_context
def generate_qr(ctx: click.Context, address: str, amount: float | None, memo: str, save: str | None):
    """
    Generate a payment QR code.

    Example:
        xai payment qr --address XAI1... --amount 50.0 --save payment.png
    """
    node_url = ctx.obj["client"].node_url
    api_key = ctx.obj.get("api_key")

    payload: dict[str, Any] = {"address": address, "memo": memo}
    if amount is not None:
        payload["amount"] = amount

    try:
        with console.status("[bold cyan]Generating QR code..."):
            result = _payment_request(
                node_url, api_key, "POST", "/payment/qr",
                json=payload
            )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
            return

        console.print("[green]QR code generated![/]")

        if result.get("payment_uri"):
            console.print(f"\n[cyan]Payment URI:[/] {result['payment_uri']}")

        # Save QR code if requested
        if save and result.get("qr_image_base64"):
            import base64
            qr_data = base64.b64decode(result["qr_image_base64"])
            with open(save, "wb") as f:
                f.write(qr_data)
            console.print(f"\n[green]QR code saved to:[/] {save}")
        elif not save:
            console.print("\n[dim]Use --save to save QR code to a file[/]")

    except (click.ClickException, requests.RequestException) as exc:
        _handle_cli_error(exc)


@payment.command("scan")
@click.argument("qr_data")
@click.pass_context
def scan_qr(ctx: click.Context, qr_data: str):
    """
    Parse a payment QR code data string.

    Example:
        xai payment scan "xai:XAI1...?amount=100&memo=Invoice"
    """
    try:
        # Parse XAI URI format: xai:<address>?amount=X&memo=Y
        if not qr_data.startswith("xai:"):
            console.print("[yellow]Warning:[/] Non-standard QR format")
            console.print(f"Raw data: {qr_data}")
            return

        # Parse URI
        parts = qr_data[4:].split("?", 1)
        address = parts[0]
        params: dict[str, str] = {}

        if len(parts) > 1:
            for param in parts[1].split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value

        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[cyan]Address", address)
        if "amount" in params:
            table.add_row("[green]Amount", f"{params['amount']} XAI")
        if "memo" in params:
            table.add_row("[cyan]Memo", params["memo"])
        if "label" in params:
            table.add_row("[cyan]Label", params["label"])

        console.print(Panel(table, title="Payment QR Details", border_style="cyan"))

    except Exception as exc:
        _handle_cli_error(exc)


if __name__ == "__main__":
    payment()

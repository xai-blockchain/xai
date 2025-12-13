#!/usr/bin/env python3
"""
XAI Blockchain - Revolutionary AI-Enhanced CLI
Production-grade command-line interface with rich terminal UX
"""

from __future__ import annotations

import sys
import json
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich import box
    from rich.tree import Tree
    from rich.live import Live
    from rich.layout import Layout
except ImportError:
    print("ERROR: Required packages not installed. Install with:")
    print("  pip install click rich")
    sys.exit(1)

import requests
from xai.wallet.offline_signing import sign_offline, signing_preview

# Configure module logger
logger = logging.getLogger(__name__)

# Rich console for beautiful output
console = Console()


def _cli_fail(exc: Exception, exit_code: int = 1) -> None:
    """Centralized CLI error handler for consistent messaging."""
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)

# Default configuration
DEFAULT_NODE_URL = "http://localhost:18545"
DEFAULT_TIMEOUT = 30.0


class XAIClient:
    """Client for interacting with XAI blockchain node"""

    def __init__(self, node_url: str = DEFAULT_NODE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.node_url = node_url.rstrip('/')
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to node"""
        url = f"{self.node_url}/{endpoint.lstrip('/')}"
        logger.debug("Node request: %s %s", method, url)
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            logger.debug("Node response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Node communication error: %s", e)
            raise click.ClickException(f"Node communication error: {e}")

    def get_balance(self, address: str) -> Dict[str, Any]:
        """Get wallet balance"""
        return self._request("GET", f"/balance/{address}")

    def get_transaction_history(self, address: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get transaction history"""
        return self._request("GET", f"/history/{address}", params={"limit": limit, "offset": offset})

    def get_block(self, block_id: str) -> Dict[str, Any]:
        """Get block by index or hash"""
        return self._request("GET", f"/block/{block_id}")

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._request("GET", "/info")

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._request("GET", "/network/info")

    def get_peers(self) -> Dict[str, Any]:
        """Get connected peers"""
        return self._request("GET", "/peers")

    def get_mining_status(self) -> Dict[str, Any]:
        """Get mining status"""
        return self._request("GET", "/mining/status")

    def start_mining(self, address: str, threads: int = 1, intensity: int = 1) -> Dict[str, Any]:
        """Start mining"""
        return self._request("POST", "/mining/start", json={
            "miner_address": address,
            "threads": threads,
            "intensity": intensity
        })

    def stop_mining(self) -> Dict[str, Any]:
        """Stop mining"""
        return self._request("POST", "/mining/stop")

    def submit_transaction(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Deprecated: use submit_signed_transaction to avoid transmitting private keys."""
        raise RuntimeError("submit_transaction is disabled. Use submit_signed_transaction with a pre-signed payload.")

    def submit_signed_transaction(self, signed_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a fully signed transaction (no private keys transmitted)."""
        return self._request("POST", "/send", json=signed_payload)

    def get_address_nonce(self, address: str) -> Dict[str, Any]:
        """Fetch confirmed and next nonce for an address."""
        return self._request("GET", f"/address/{address}/nonce")

    def get_mempool(self) -> Dict[str, Any]:
        """Get mempool transactions"""
        return self._request("GET", "/mempool")


# ============================================================================
# CLI Groups
# ============================================================================

@click.group()
@click.option('--node-url', default=DEFAULT_NODE_URL,
              help='XAI node URL', show_default=True)
@click.option('--timeout', default=DEFAULT_TIMEOUT, type=float,
              help='Request timeout in seconds', show_default=True)
@click.option('--json-output', is_flag=True, help='Output raw JSON')
@click.pass_context
def cli(ctx: click.Context, node_url: str, timeout: float, json_output: bool):
    """
    XAI Blockchain CLI - Revolutionary AI-Enhanced Blockchain

    A production-grade command-line interface for interacting with
    the XAI blockchain network, featuring AI compute jobs, mining,
    trading, and comprehensive blockchain operations.
    """
    ctx.ensure_object(dict)
    ctx.obj['client'] = XAIClient(node_url, timeout)
    ctx.obj['json_output'] = json_output


# ============================================================================
# Wallet Commands
# ============================================================================

@cli.group()
def wallet():
    """Wallet management commands"""
    pass


@wallet.command('create')
@click.option('--save-keystore', is_flag=True, help='Save to encrypted keystore')
@click.option('--keystore-output', type=click.Path(), help='Keystore output path')
@click.option('--kdf', type=click.Choice(['pbkdf2', 'argon2id']), default='pbkdf2',
              help='Key derivation function')
@click.pass_context
def wallet_create(ctx: click.Context, save_keystore: bool, keystore_output: Optional[str], kdf: str):
    """Create a new wallet"""
    from xai.core.wallet import Wallet
    from xai.wallet.cli import create_keystore

    with console.status("[bold green]Generating wallet..."):
        wallet = Wallet()

    if ctx.obj['json_output']:
        click.echo(json.dumps({
            "address": wallet.address,
            "public_key": wallet.public_key
        }, indent=2))
        return

    # Display wallet info in a beautiful panel
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Address", wallet.address)
    table.add_row("[bold cyan]Public Key", wallet.public_key[:40] + "...")

    console.print(Panel(table, title="[bold green]New Wallet Created",
                       border_style="green"))

    if save_keystore:
        try:
            keystore_path = create_keystore(
                address=wallet.address,
                private_key=wallet.private_key,
                public_key=wallet.public_key,
                output_path=keystore_output,
                kdf=kdf
            )
            console.print(f"\n[bold green]✓[/] Encrypted keystore saved to: [cyan]{keystore_path}[/]")
        except (click.ClickException, ValueError, OSError) as exc:
            _cli_fail(exc)
    else:
        console.print("\n[yellow]⚠[/] Private key not saved. Use --save-keystore to encrypt and save.")


@wallet.command('balance')
@click.argument('address')
@click.pass_context
def wallet_balance(ctx: click.Context, address: str):
    """Check wallet balance"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status(f"[bold cyan]Fetching balance for {address[:20]}..."):
            data = client.get_balance(address)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        balance = data.get('balance', 0)
        pending_in = data.get('pending_incoming', 0)
        pending_out = data.get('pending_outgoing', 0)

        # Create beautiful balance display
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Address", address[:40] + "...")
        table.add_row("[bold green]Balance", f"{balance:.8f} XAI")
        if pending_in > 0:
            table.add_row("[bold yellow]Pending In", f"{pending_in:.8f} XAI")
        if pending_out > 0:
            table.add_row("[bold yellow]Pending Out", f"{pending_out:.8f} XAI")

        console.print(Panel(table, title="[bold green]Wallet Balance",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('history')
@click.argument('address')
@click.option('--limit', default=10, help='Number of transactions to show')
@click.option('--offset', default=0, help='Pagination offset')
@click.pass_context
def wallet_history(ctx: click.Context, address: str, limit: int, offset: int):
    """View transaction history"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching transaction history..."):
            data = client.get_transaction_history(address, limit, offset)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        transactions = data.get('transactions', [])

        if not transactions:
            console.print("[yellow]No transactions found[/]")
            return

        # Create beautiful transaction table
        table = Table(title=f"Transaction History - {address[:20]}...",
                     box=box.ROUNDED, show_lines=True)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("From/To", style="yellow")
        table.add_column("TX ID", style="blue")

        for tx in transactions:
            timestamp = datetime.fromtimestamp(tx.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
            tx_type = "Sent" if tx.get('sender') == address else "Received"
            amount = f"{tx.get('amount', 0):.8f} XAI"
            other_addr = tx.get('recipient' if tx_type == "Sent" else 'sender', 'N/A')[:20]
            tx_id = tx.get('txid', 'N/A')[:16]

            table.add_row(timestamp, tx_type, amount, other_addr + "...", tx_id + "...")

        console.print(table)

        if len(transactions) == limit:
            console.print(f"\n[dim]Showing {limit} transactions. Use --limit and --offset for more.[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('send')
@click.option('--sender', required=True, help='Sender address')
@click.option('--recipient', required=True, help='Recipient address')
@click.option('--amount', required=True, type=float, help='Amount to send')
@click.option('--fee', default=0.001, type=float, help='Transaction fee')
@click.option('--keystore', type=click.Path(exists=True), help='Keystore file path')
@click.pass_context
def wallet_send(ctx: click.Context, sender: str, recipient: str, amount: float,
                fee: float, keystore: Optional[str]):
    """Send XAI to another address"""
    from xai.wallet.cli import get_private_key_secure

    # Confirm transaction
    console.print("\n[bold yellow]Transaction Summary:[/]")
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_row("From", sender[:40] + "...")
    table.add_row("To", recipient[:40] + "...")
    table.add_row("Amount", f"{amount:.8f} XAI")
    table.add_row("Fee", f"{fee:.8f} XAI")
    table.add_row("Total", f"{amount + fee:.8f} XAI")
    console.print(table)

    if not Confirm.ask("\n[bold]Confirm transaction?[/]", default=False):
        console.print("[yellow]Transaction cancelled[/]")
        return

    client: XAIClient = ctx.obj['client']

    try:
        nonce_resp = client.get_address_nonce(sender)
        nonce = nonce_resp.get("next_nonce")
        if nonce is None:
            raise click.ClickException("Nonce unavailable for sender")

        # Build canonical payload for preview
        base_tx = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "fee": fee,
            "nonce": int(nonce),
            "tx_type": "normal",
            "metadata": {},
            "timestamp": time.time(),
        }
        payload_str, tx_hash, canonical_payload = signing_preview(base_tx)

        console.print("\n[bold cyan]Signing payload:[/]")
        console.print(Syntax(payload_str, "json", theme="monokai", word_wrap=True))
        console.print(f"\n[bold]Signing hash:[/] [cyan]{tx_hash}[/]")

        ack = Prompt.ask(
            f"Type the first 8+ characters of the signing hash to confirm",
            default="",
            show_default=False,
        )
        if not ack or len(ack.strip()) < 8 or not tx_hash.lower().startswith(ack.strip().lower()):
            console.print("[bold red]Acknowledgement mismatch. Aborting before using private key.[/]")
            return

        # Security: Get private key securely *after* user has acknowledged the payload/hash
        try:
            private_key = get_private_key_secure(
                keystore_path=keystore,
                allow_env=False,
                prompt="Enter sender's private key"
            )
        except (click.ClickException, ValueError, OSError) as exc:
            _cli_fail(exc)

        signed_payload = sign_offline(base_tx, private_key, acknowledged_digest=ack.strip())
        submission_payload = {
            "sender": canonical_payload["sender"],
            "recipient": canonical_payload["recipient"],
            "amount": canonical_payload["amount"],
            "fee": canonical_payload["fee"],
            "nonce": canonical_payload["nonce"],
            "timestamp": canonical_payload["timestamp"],
            "public_key": signed_payload["public_key"],
            "signature": signed_payload["signature"],
            "metadata": canonical_payload["metadata"] or None,
            "txid": signed_payload["txid"],
        }

        with console.status("[bold cyan]Sending transaction..."):
            result = client.submit_signed_transaction(submission_payload)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("\n[bold green]✓ Transaction sent successfully![/]")
            console.print(f"TX ID: [cyan]{result.get('txid', 'pending')}[/]")
        else:
            console.print(f"\n[bold red]✗ Transaction failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@wallet.command('portfolio')
@click.argument('address')
@click.pass_context
def wallet_portfolio(ctx: click.Context, address: str):
    """Show complete wallet portfolio"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Loading portfolio..."):
            balance_data = client.get_balance(address)
            history_data = client.get_transaction_history(address, limit=100)

        if ctx.obj['json_output']:
            click.echo(json.dumps({
                'balance': balance_data,
                'history': history_data
            }, indent=2))
            return

        # Calculate portfolio stats
        balance = balance_data.get('balance', 0)
        transactions = history_data.get('transactions', [])

        total_sent = sum(tx.get('amount', 0) for tx in transactions if tx.get('sender') == address)
        total_received = sum(tx.get('amount', 0) for tx in transactions if tx.get('recipient') == address)
        tx_count = len(transactions)

        # Portfolio panel
        layout = Layout()
        layout.split_column(
            Layout(name="balance"),
            Layout(name="stats")
        )

        # Balance table
        balance_table = Table(show_header=False, box=box.ROUNDED)
        balance_table.add_row("[bold cyan]Current Balance", f"[bold green]{balance:.8f} XAI[/]")
        balance_table.add_row("[bold cyan]Total Received", f"{total_received:.8f} XAI")
        balance_table.add_row("[bold cyan]Total Sent", f"{total_sent:.8f} XAI")
        balance_table.add_row("[bold cyan]Transaction Count", str(tx_count))

        console.print(Panel(balance_table, title=f"[bold green]Portfolio - {address[:20]}...",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Blockchain Commands
# ============================================================================

@cli.group()
def blockchain():
    """Blockchain information commands"""
    pass


@blockchain.command('info')
@click.pass_context
def blockchain_info(ctx: click.Context):
    """Get blockchain information"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching blockchain info..."):
            data = client.get_blockchain_info()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        # Create beautiful info panel
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Chain Height", str(data.get('height', 0)))
        table.add_row("[bold cyan]Latest Block", data.get('latest_block', 'N/A')[:40])
        table.add_row("[bold cyan]Difficulty", str(data.get('difficulty', 0)))
        table.add_row("[bold cyan]Pending Transactions", str(data.get('pending_transactions', 0)))
        table.add_row("[bold cyan]Network Hashrate", data.get('network_hashrate', 'N/A'))
        table.add_row("[bold cyan]Total Supply", f"{data.get('total_supply', 0):.2f} XAI")

        console.print(Panel(table, title="[bold green]Blockchain Information",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('block')
@click.argument('block_id')
@click.pass_context
def blockchain_block(ctx: click.Context, block_id: str):
    """Get block by index or hash"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status(f"[bold cyan]Fetching block {block_id}..."):
            data = client.get_block(block_id)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        block = data.get('block', {})

        # Block header table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Index", str(block.get('index', 0)))
        table.add_row("[bold cyan]Hash", block.get('hash', 'N/A')[:64])
        table.add_row("[bold cyan]Previous Hash", block.get('previous_hash', 'N/A')[:64])
        table.add_row("[bold cyan]Timestamp", datetime.fromtimestamp(
            block.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("[bold cyan]Difficulty", str(block.get('difficulty', 0)))
        table.add_row("[bold cyan]Nonce", str(block.get('nonce', 0)))
        table.add_row("[bold cyan]Transactions", str(len(block.get('transactions', []))))
        table.add_row("[bold cyan]Miner", block.get('miner', 'N/A')[:40])

        console.print(Panel(table, title=f"[bold green]Block {block_id}",
                           border_style="green"))

        # Show transactions if any
        transactions = block.get('transactions', [])
        if transactions:
            console.print(f"\n[bold]Transactions ({len(transactions)}):[/]")
            for i, tx in enumerate(transactions[:10], 1):
                console.print(f"  {i}. {tx.get('sender', 'N/A')[:20]}... → "
                            f"{tx.get('recipient', 'N/A')[:20]}... "
                            f"[green]{tx.get('amount', 0):.8f} XAI[/]")
            if len(transactions) > 10:
                console.print(f"  [dim]... and {len(transactions) - 10} more[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@blockchain.command('mempool')
@click.pass_context
def blockchain_mempool(ctx: click.Context):
    """View pending transactions in mempool"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching mempool..."):
            data = client.get_mempool()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        transactions = data.get('transactions', [])

        if not transactions:
            console.print("[yellow]Mempool is empty[/]")
            return

        # Mempool table
        table = Table(title=f"Mempool - {len(transactions)} Pending Transactions",
                     box=box.ROUNDED)
        table.add_column("TX ID", style="cyan")
        table.add_column("From", style="yellow")
        table.add_column("To", style="yellow")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Fee", style="magenta", justify="right")

        for tx in transactions[:20]:
            table.add_row(
                tx.get('txid', 'N/A')[:16] + "...",
                tx.get('sender', 'N/A')[:20] + "...",
                tx.get('recipient', 'N/A')[:20] + "...",
                f"{tx.get('amount', 0):.8f}",
                f"{tx.get('fee', 0):.8f}"
            )

        console.print(table)

        if len(transactions) > 20:
            console.print(f"\n[dim]Showing 20 of {len(transactions)} transactions[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Mining Commands
# ============================================================================

@cli.group()
def mining():
    """Mining operations"""
    pass


@mining.command('start')
@click.option('--address', required=True, help='Miner address (receives rewards)')
@click.option('--threads', default=1, type=int, help='Number of mining threads')
@click.option('--intensity', default=1, type=int, help='Mining intensity (1-10)')
@click.pass_context
def mining_start(ctx: click.Context, address: str, threads: int, intensity: int):
    """Start mining"""
    client: XAIClient = ctx.obj['client']

    console.print(f"[bold cyan]Starting mining...[/]")
    console.print(f"  Address: {address}")
    console.print(f"  Threads: {threads}")
    console.print(f"  Intensity: {intensity}\n")

    try:
        result = client.start_mining(address, threads, intensity)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("[bold green]✓ Mining started successfully![/]")
        else:
            console.print(f"[bold red]✗ Failed to start mining:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('stop')
@click.pass_context
def mining_stop(ctx: click.Context):
    """Stop mining"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Stopping mining..."):
            result = client.stop_mining()

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            console.print("[bold green]✓ Mining stopped[/]")
        else:
            console.print(f"[bold red]✗ Failed to stop mining:[/] {result.get('error', 'Unknown')}")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('status')
@click.pass_context
def mining_status(ctx: click.Context):
    """Check mining status"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching mining status..."):
            data = client.get_mining_status()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        is_mining = data.get('mining', False)

        if not is_mining:
            console.print("[yellow]Mining is not active[/]")
            return

        # Mining status table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Status", "[bold green]Active[/]")
        table.add_row("[bold cyan]Miner Address", data.get('miner_address', 'N/A')[:40])
        table.add_row("[bold cyan]Threads", str(data.get('threads', 0)))
        table.add_row("[bold cyan]Hashrate", data.get('hashrate', 'N/A'))
        table.add_row("[bold cyan]Blocks Mined", str(data.get('blocks_mined', 0)))
        table.add_row("[bold cyan]Total Rewards", f"{data.get('total_rewards', 0):.8f} XAI")

        console.print(Panel(table, title="[bold green]Mining Status",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@mining.command('stats')
@click.option('--address', required=True, help='Miner address')
@click.pass_context
def mining_stats(ctx: click.Context, address: str):
    """Detailed mining statistics"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Calculating mining statistics..."):
            balance_data = client.get_balance(address)
            history_data = client.get_transaction_history(address, limit=100)

        if ctx.obj['json_output']:
            click.echo(json.dumps({
                'balance': balance_data,
                'history': history_data
            }, indent=2))
            return

        # Calculate mining stats from transaction history
        transactions = history_data.get('transactions', [])
        mining_rewards = [tx for tx in transactions if tx.get('type') == 'mining_reward']

        total_rewards = sum(tx.get('amount', 0) for tx in mining_rewards)
        blocks_mined = len(mining_rewards)

        # Stats table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Miner Address", address[:40] + "...")
        table.add_row("[bold cyan]Blocks Mined", str(blocks_mined))
        table.add_row("[bold cyan]Total Rewards", f"{total_rewards:.8f} XAI")
        table.add_row("[bold cyan]Current Balance", f"{balance_data.get('balance', 0):.8f} XAI")
        if blocks_mined > 0:
            table.add_row("[bold cyan]Avg Reward/Block", f"{total_rewards/blocks_mined:.8f} XAI")

        console.print(Panel(table, title="[bold green]Mining Statistics",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# Network Commands
# ============================================================================

@cli.group()
def network():
    """Network information commands"""
    pass


@network.command('info')
@click.pass_context
def network_info(ctx: click.Context):
    """Get network information"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching network info..."):
            data = client.get_network_info()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        # Network info table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Network", data.get('network', 'mainnet'))
        table.add_row("[bold cyan]Version", data.get('version', 'N/A'))
        table.add_row("[bold cyan]Node ID", data.get('node_id', 'N/A')[:40])
        table.add_row("[bold cyan]Connected Peers", str(data.get('peer_count', 0)))
        table.add_row("[bold cyan]Network Hashrate", data.get('network_hashrate', 'N/A'))
        table.add_row("[bold cyan]Sync Status",
                     "[green]Synced[/]" if data.get('synced') else "[yellow]Syncing...[/]")

        console.print(Panel(table, title="[bold green]Network Information",
                           border_style="green"))

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


@network.command('peers')
@click.pass_context
def network_peers(ctx: click.Context):
    """List connected peers"""
    client: XAIClient = ctx.obj['client']

    try:
        with console.status("[bold cyan]Fetching peers..."):
            data = client.get_peers()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        peers = data.get('peers', [])

        if not peers:
            console.print("[yellow]No peers connected[/]")
            return

        # Peers table
        table = Table(title=f"Connected Peers - {len(peers)} nodes",
                     box=box.ROUNDED)
        table.add_column("Node ID", style="cyan")
        table.add_column("Address", style="yellow")
        table.add_column("Version", style="green")
        table.add_column("Connected", style="magenta")

        for peer in peers:
            node_id = peer.get('node_id', 'N/A')[:16] + "..."
            address = peer.get('address', 'N/A')
            version = peer.get('version', 'N/A')
            connected_time = peer.get('connected_time', 0)

            # Format connection duration
            duration = int(time.time() - connected_time) if connected_time else 0
            if duration < 60:
                duration_str = f"{duration}s"
            elif duration < 3600:
                duration_str = f"{duration//60}m"
            else:
                duration_str = f"{duration//3600}h"

            table.add_row(node_id, address, version, duration_str)

        console.print(table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


# ============================================================================
# AI Commands (Revolutionary AI-Blockchain Features)
# Import production-grade AI commands module
# ============================================================================

from xai.cli.ai_commands import ai

# Register AI commands group
cli.add_command(ai)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main CLI entry point"""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/]")
        sys.exit(130)
    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _cli_fail(exc)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
XAI AI Compute Commands - Production Implementation
Blockchain-integrated AI task submission and provider management
"""

from __future__ import annotations

import sys
import json
import logging
import time
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Confirm, Prompt, IntPrompt, FloatPrompt
    from rich.syntax import Syntax
    from rich import box
    from rich.tree import Tree
    from rich.live import Live
except ImportError:
    print("ERROR: Required packages not installed. Install with:")
    print("  pip install click rich")
    sys.exit(1)

import requests

# Configure module logger
logger = logging.getLogger(__name__)

console = Console()

# Centralized CLI error handler for consistent messaging/exit codes
def _handle_cli_error(exc: Exception, exit_code: int = 1) -> None:
    logger.error("CLI error: %s", exc, exc_info=True)
    console.print(f"[bold red]Error:[/] {exc}")
    sys.exit(exit_code)


class TaskType(str, Enum):
    """AI task types supported by the network"""
    CODE_GENERATION = "code"
    SECURITY_AUDIT = "security"
    RESEARCH_ANALYSIS = "research"
    DATA_ANALYSIS = "analysis"
    OPTIMIZATION = "optimization"
    TRAINING = "training"
    INFERENCE = "inference"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIComputeClient:
    """Client for AI compute network operations"""

    def __init__(self, node_url: str, timeout: float = 30.0):
        self.node_url = node_url.rstrip('/')
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to AI compute endpoint"""
        url = f"{self.node_url}/ai/{endpoint.lstrip('/')}"
        logger.debug("AI compute request: %s %s", method, url)
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            logger.debug("AI compute response: status=%d", response.status_code)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("AI compute network error: %s", e)
            raise click.ClickException(f"AI compute network error: {e}")

    def submit_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit AI compute task"""
        return self._request("POST", "/tasks", json=task_data)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Query task status"""
        return self._request("GET", f"/tasks/{task_id}")

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel pending task"""
        return self._request("DELETE", f"/tasks/{task_id}")

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """List tasks with optional status filter"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._request("GET", "/tasks", params=params)

    def get_providers(self, sort_by: str = "reputation") -> Dict[str, Any]:
        """Get list of AI compute providers"""
        return self._request("GET", "/providers", params={"sort": sort_by})

    def get_provider_details(self, provider_id: str) -> Dict[str, Any]:
        """Get detailed provider information"""
        return self._request("GET", f"/providers/{provider_id}")

    def register_provider(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register as AI compute provider"""
        return self._request("POST", "/providers", json=provider_data)

    def get_earnings(self, provider_id: str, period: str = "30d") -> Dict[str, Any]:
        """Get provider earnings"""
        return self._request("GET", f"/providers/{provider_id}/earnings",
                           params={"period": period})

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get AI marketplace statistics"""
        return self._request("GET", "/stats")


def generate_task_id(task_type: str, description: str) -> str:
    """Generate unique task ID"""
    timestamp = int(time.time())
    hash_input = f"{task_type}{description}{timestamp}".encode()
    hash_suffix = hashlib.sha256(hash_input).hexdigest()[:8]
    return f"AI-{timestamp}-{hash_suffix}"


def estimate_task_cost(task_type: TaskType, priority: TaskPriority,
                       estimated_tokens: int = 0) -> float:
    """Estimate task cost based on parameters"""
    base_costs = {
        TaskType.CODE_GENERATION: 0.05,
        TaskType.SECURITY_AUDIT: 0.15,
        TaskType.RESEARCH_ANALYSIS: 0.10,
        TaskType.DATA_ANALYSIS: 0.08,
        TaskType.OPTIMIZATION: 0.12,
        TaskType.TRAINING: 0.50,
        TaskType.INFERENCE: 0.03,
    }

    priority_multipliers = {
        TaskPriority.LOW: 0.8,
        TaskPriority.MEDIUM: 1.0,
        TaskPriority.HIGH: 1.5,
        TaskPriority.CRITICAL: 2.5,
    }

    base_cost = base_costs.get(task_type, 0.10)
    priority_mult = priority_multipliers.get(priority, 1.0)

    # Token-based pricing
    token_cost = (estimated_tokens / 1000) * 0.002 if estimated_tokens > 0 else 0

    return (base_cost * priority_mult) + token_cost


@click.group()
def ai():
    """AI compute and provider commands"""
    pass


@ai.command('submit')
@click.option('--task-type', required=True,
              type=click.Choice([t.value for t in TaskType]),
              help='Type of AI task')
@click.option('--description', required=True, help='Task description')
@click.option('--priority', default='medium',
              type=click.Choice([p.value for p in TaskPriority]),
              help='Task priority')
@click.option('--max-cost', type=float, help='Maximum cost in XAI')
@click.option('--input-file', type=click.Path(exists=True),
              help='Input file for task (code, data, etc.)')
@click.option('--model', help='Preferred AI model (gpt-4, claude-3, etc.)')
@click.option('--timeout', type=int, default=300, help='Task timeout in seconds')
@click.option('--wallet', required=True, help='Wallet address for payment')
@click.pass_context
def submit_task(ctx: click.Context, task_type: str, description: str,
                priority: str, max_cost: Optional[float], input_file: Optional[str],
                model: Optional[str], timeout: int, wallet: str):
    """
    Submit AI compute job to the network

    Tasks are distributed to qualified providers based on:
    - Task type and complexity
    - Priority level
    - Cost constraints
    - Provider reputation and availability

    Example:
        xai ai submit --task-type security --description "Audit smart contract" --wallet ADDR
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    # Read input file if provided
    input_data = None
    if input_file:
        with open(input_file, 'r') as f:
            input_data = f.read()

    # Estimate cost
    estimated_cost = estimate_task_cost(
        TaskType(task_type),
        TaskPriority(priority)
    )

    if max_cost and estimated_cost > max_cost:
        console.print(f"[yellow]Warning:[/] Estimated cost ({estimated_cost:.4f} XAI) "
                     f"exceeds max cost ({max_cost:.4f} XAI)")
        if not Confirm.ask("Continue anyway?", default=False):
            return

    # Display task summary
    console.print("\n[bold cyan]AI Compute Task Submission[/]\n")

    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Task Type", task_type.upper())
    table.add_row("[bold cyan]Priority", priority.upper())
    table.add_row("[bold cyan]Description", description[:100])
    table.add_row("[bold cyan]Estimated Cost", f"{estimated_cost:.6f} XAI")
    if max_cost:
        table.add_row("[bold cyan]Max Cost", f"{max_cost:.6f} XAI")
    if model:
        table.add_row("[bold cyan]Preferred Model", model)
    table.add_row("[bold cyan]Timeout", f"{timeout}s")
    table.add_row("[bold cyan]Wallet", wallet[:40] + "...")
    if input_data:
        table.add_row("[bold cyan]Input Size", f"{len(input_data)} bytes")

    console.print(table)

    if not Confirm.ask("\n[bold]Submit this task to AI network?[/]", default=True):
        console.print("[yellow]Task submission cancelled[/]")
        return

    # Prepare task data
    task_data = {
        "task_type": task_type,
        "description": description,
        "priority": priority,
        "max_cost": max_cost or estimated_cost * 1.2,
        "timeout": timeout,
        "wallet": wallet,
        "input_data": input_data,
        "preferred_model": model,
        "submitted_at": time.time()
    }

    try:
        logger.info("Submitting AI task: type=%s, priority=%s, wallet=%s", task_type, priority, wallet[:16])
        with console.status("[bold cyan]Submitting to AI compute network..."):
            result = client.submit_task(task_data)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            task_id = result.get('task_id')
            logger.info("AI task submitted successfully: task_id=%s", task_id)
            console.print(f"\n[bold green]✓ Task submitted successfully![/]")
            console.print(f"Task ID: [cyan]{task_id}[/]")
            console.print(f"Status: [yellow]{result.get('status', 'PENDING').upper()}[/]")
            console.print(f"\nTrack progress: [bold]xai ai query {task_id}[/]")
        else:
            logger.error("AI task submission failed: %s", result.get('error', 'Unknown'))
            console.print(f"[bold red]✗ Submission failed:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('query')
@click.argument('task_id')
@click.option('--watch', is_flag=True, help='Watch status in real-time')
@click.pass_context
def query_task(ctx: click.Context, task_id: str, watch: bool):
    """
    Query AI task status and results

    Shows current status, assigned provider, progress, and results.
    Use --watch to monitor task progress in real-time.

    Example:
        xai ai query AI-1733123456-abc123 --watch
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    def fetch_and_display():
        try:
            data = client.get_task_status(task_id)

            if ctx.obj['json_output']:
                click.echo(json.dumps(data, indent=2))
                return True

            task = data.get('task', {})
            status = task.get('status', 'unknown')
            logger.debug("Task %s status: %s", task_id, status)

            # Status table
            table = Table(show_header=False, box=box.ROUNDED)
            table.add_row("[bold cyan]Task ID", task_id)

            status_color = {
                'pending': 'yellow',
                'assigned': 'blue',
                'in_progress': 'cyan',
                'completed': 'green',
                'failed': 'red',
                'cancelled': 'dim'
            }.get(status, 'white')

            table.add_row("[bold cyan]Status", f"[{status_color}]{status.upper()}[/]")

            if task.get('provider_id'):
                table.add_row("[bold cyan]Provider", task['provider_id'])
            if task.get('model_used'):
                table.add_row("[bold cyan]Model", task['model_used'])
            if task.get('progress'):
                progress = task['progress']
                table.add_row("[bold cyan]Progress", f"{progress}%")
            if task.get('estimated_completion'):
                eta = datetime.fromtimestamp(task['estimated_completion'])
                table.add_row("[bold cyan]ETA", eta.strftime('%Y-%m-%d %H:%M:%S'))
            if task.get('actual_cost'):
                table.add_row("[bold cyan]Cost", f"{task['actual_cost']:.6f} XAI")
            if task.get('result'):
                result_preview = task['result'][:200]
                table.add_row("[bold cyan]Result", result_preview + "..." if len(task['result']) > 200 else result_preview)
            if task.get('error'):
                table.add_row("[bold red]Error", task['error'])

            console.print(Panel(table, title=f"[bold green]AI Task Status",
                               border_style="green"))

            return status in ['completed', 'failed', 'cancelled']

        except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
            console.print(f"[bold red]Error:[/] {exc}")
            return True

    if watch:
        console.print("[dim]Watching task status (Ctrl+C to stop)...[/]\n")
        try:
            while True:
                done = fetch_and_display()
                if done:
                    break
                time.sleep(5)
                console.clear()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped watching[/]")
    else:
        fetch_and_display()


@ai.command('cancel')
@click.argument('task_id')
@click.pass_context
def cancel_task(ctx: click.Context, task_id: str):
    """
    Cancel pending AI task

    Only tasks in PENDING or ASSIGNED status can be cancelled.
    In-progress tasks cannot be cancelled.

    Example:
        xai ai cancel AI-1733123456-abc123
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    if not Confirm.ask(f"[bold]Cancel task {task_id}?[/]", default=False):
        console.print("[yellow]Cancelled[/]")
        return

    try:
        logger.info("Cancelling AI task: %s", task_id)
        with console.status("[bold cyan]Cancelling task..."):
            result = client.cancel_task(task_id)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            logger.info("AI task cancelled: %s, refund=%s", task_id, result.get('refund_amount', 0))
            console.print(f"[bold green]✓ Task cancelled[/]")
            if result.get('refund_amount'):
                console.print(f"Refund: {result['refund_amount']:.6f} XAI")
        else:
            logger.error("Task cancellation failed: %s", result.get('error', 'Unknown'))
            console.print(f"[bold red]✗ Failed:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('list')
@click.option('--status', type=click.Choice([s.value for s in TaskStatus]),
              help='Filter by status')
@click.option('--limit', default=20, help='Number of tasks to show')
@click.pass_context
def list_tasks(ctx: click.Context, status: Optional[str], limit: int):
    """
    List AI compute tasks

    Shows your submitted tasks with current status and costs.
    Filter by status to view specific task states.

    Example:
        xai ai list --status completed --limit 10
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    try:
        with console.status("[bold cyan]Fetching tasks..."):
            data = client.list_tasks(status=status, limit=limit)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        tasks = data.get('tasks', [])

        if not tasks:
            console.print("[yellow]No tasks found[/]")
            return

        # Tasks table
        title = f"AI Compute Tasks"
        if status:
            title += f" - {status.upper()}"
        title += f" ({len(tasks)} tasks)"

        table = Table(title=title, box=box.ROUNDED, show_lines=True)
        table.add_column("Task ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Cost", style="blue", justify="right")
        table.add_column("Submitted", style="dim")

        for task in tasks:
            task_id = task.get('task_id', 'N/A')[:20]
            task_type = task.get('task_type', 'N/A').upper()
            task_status = task.get('status', 'unknown')
            priority = task.get('priority', 'medium').upper()
            cost = task.get('actual_cost') or task.get('estimated_cost', 0)
            submitted = datetime.fromtimestamp(task.get('submitted_at', 0)).strftime('%m-%d %H:%M')

            status_color = {
                'pending': 'yellow',
                'assigned': 'blue',
                'in_progress': 'cyan',
                'completed': 'green',
                'failed': 'red',
                'cancelled': 'dim'
            }.get(task_status, 'white')

            table.add_row(
                task_id,
                task_type,
                f"[{status_color}]{task_status.upper()}[/]",
                priority,
                f"{cost:.4f} XAI",
                submitted
            )

        console.print(table)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('providers')
@click.option('--sort-by', default='reputation',
              type=click.Choice(['reputation', 'cost', 'speed', 'availability', 'tasks']),
              help='Sort providers by metric')
@click.option('--min-reputation', type=int, help='Minimum reputation score')
@click.option('--task-type', type=click.Choice([t.value for t in TaskType]),
              help='Filter by supported task type')
@click.pass_context
def list_providers(ctx: click.Context, sort_by: str, min_reputation: Optional[int],
                   task_type: Optional[str]):
    """
    List and rank AI compute providers

    Displays active providers with reputation scores, pricing,
    performance metrics, and supported models.

    Example:
        xai ai providers --sort-by reputation --min-reputation 90
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    try:
        with console.status("[bold cyan]Fetching AI providers..."):
            data = client.get_providers(sort_by=sort_by)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        providers = data.get('providers', [])

        # Apply filters
        if min_reputation:
            providers = [p for p in providers if p.get('reputation', 0) >= min_reputation]
        if task_type:
            providers = [p for p in providers
                        if task_type in p.get('supported_types', [])]

        if not providers:
            console.print("[yellow]No providers found matching criteria[/]")
            return

        # Providers table
        table = Table(
            title=f"AI Compute Providers (sorted by {sort_by}) - {len(providers)} active",
            box=box.ROUNDED,
            show_lines=True
        )
        table.add_column("Provider ID", style="cyan")
        table.add_column("Reputation", style="green", justify="right")
        table.add_column("Tasks", style="yellow", justify="right")
        table.add_column("Avg Cost", style="magenta", justify="right")
        table.add_column("Response", style="blue")
        table.add_column("Uptime", style="green")
        table.add_column("Models", style="cyan")

        for provider in providers[:20]:
            provider_id = provider.get('provider_id', 'N/A')[:16]
            reputation = provider.get('reputation', 0)
            tasks = provider.get('tasks_completed', 0)
            avg_cost = provider.get('avg_cost', 0)
            response_time = provider.get('avg_response_time', 'N/A')
            uptime = provider.get('availability', 'N/A')
            models = ', '.join(provider.get('models', [])[:2])

            # Reputation color coding
            rep_color = "green" if reputation >= 90 else "yellow" if reputation >= 70 else "red"

            table.add_row(
                provider_id,
                f"[{rep_color}]{reputation}%[/]",
                f"{tasks:,}",
                f"{avg_cost:.4f} XAI",
                response_time,
                uptime,
                models
            )

        console.print(table)

        if len(providers) > 20:
            console.print(f"\n[dim]Showing 20 of {len(providers)} providers[/]")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('provider-details')
@click.argument('provider_id')
@click.pass_context
def provider_details(ctx: click.Context, provider_id: str):
    """
    Get detailed provider information

    Shows complete provider profile including supported models,
    task types, pricing, performance history, and reputation details.

    Example:
        xai ai provider-details AI-NODE-001
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    try:
        with console.status(f"[bold cyan]Fetching provider {provider_id}..."):
            data = client.get_provider_details(provider_id)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        provider = data.get('provider', {})

        # Provider info panel
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Provider ID", provider.get('provider_id', 'N/A'))
        table.add_row("[bold cyan]Reputation Score", f"{provider.get('reputation', 0)}%")
        table.add_row("[bold cyan]Tasks Completed", f"{provider.get('tasks_completed', 0):,}")
        table.add_row("[bold cyan]Success Rate", f"{provider.get('success_rate', 0):.1f}%")
        table.add_row("[bold cyan]Avg Response Time", provider.get('avg_response_time', 'N/A'))
        table.add_row("[bold cyan]Avg Cost", f"{provider.get('avg_cost', 0):.4f} XAI")
        table.add_row("[bold cyan]Uptime", provider.get('availability', 'N/A'))
        table.add_row("[bold cyan]Registered Since",
                     datetime.fromtimestamp(provider.get('registered_at', 0)).strftime('%Y-%m-%d'))

        console.print(Panel(table, title="[bold green]Provider Profile",
                           border_style="green"))

        # Supported models
        if provider.get('models'):
            console.print("\n[bold]Supported Models:[/]")
            for model in provider['models']:
                console.print(f"  • {model}")

        # Supported task types
        if provider.get('supported_types'):
            console.print("\n[bold]Supported Task Types:[/]")
            for task_type in provider['supported_types']:
                console.print(f"  • {task_type.upper()}")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('earnings')
@click.option('--provider-id', required=True, help='AI provider ID')
@click.option('--period', default='30d',
              type=click.Choice(['24h', '7d', '30d', '90d', 'all']),
              help='Time period')
@click.pass_context
def provider_earnings(ctx: click.Context, provider_id: str, period: str):
    """
    Calculate AI provider earnings

    Shows total earnings, tasks completed, and breakdown by
    model and task type for the specified period.

    Example:
        xai ai earnings --provider-id AI-NODE-001 --period 30d
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    try:
        with console.status(f"[bold cyan]Calculating earnings for {period}..."):
            data = client.get_earnings(provider_id, period)

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        earnings = data.get('earnings', {})

        # Earnings summary
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Provider ID", provider_id[:40])
        table.add_row("[bold cyan]Period", period.upper())
        table.add_row("[bold green]Total Earnings",
                     f"{earnings.get('total_earnings', 0):.8f} XAI")
        table.add_row("[bold cyan]Tasks Completed",
                     f"{earnings.get('tasks_completed', 0):,}")
        table.add_row("[bold cyan]Avg Earnings/Task",
                     f"{earnings.get('avg_earnings_per_task', 0):.8f} XAI")
        table.add_row("[bold cyan]Pending Payout",
                     f"{earnings.get('pending_payout', 0):.8f} XAI")

        console.print(Panel(table, title="[bold green]Provider Earnings",
                           border_style="green"))

        # Model distribution
        if earnings.get('by_model'):
            console.print("\n[bold]Earnings by Model:[/]")
            for model, amount in earnings['by_model'].items():
                percentage = (amount / earnings['total_earnings'] * 100) if earnings['total_earnings'] > 0 else 0
                bar_length = int(percentage / 100 * 40)
                bar = "█" * bar_length + "░" * (40 - bar_length)
                console.print(f"  {model:20} {bar} {percentage:5.1f}% ({amount:.4f} XAI)")

        # Task type distribution
        if earnings.get('by_task_type'):
            console.print("\n[bold]Earnings by Task Type:[/]")
            for task_type, amount in earnings['by_task_type'].items():
                percentage = (amount / earnings['total_earnings'] * 100) if earnings['total_earnings'] > 0 else 0
                console.print(f"  {task_type.upper():20} {amount:.4f} XAI ({percentage:.1f}%)")

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('register-provider')
@click.option('--wallet', required=True, help='Provider wallet address')
@click.option('--models', required=True, help='Comma-separated model list (gpt-4,claude-3)')
@click.option('--endpoint', required=True, help='Provider API endpoint URL')
@click.option('--min-cost', type=float, default=0.01, help='Minimum task cost')
@click.option('--capacity', type=int, default=10, help='Concurrent task capacity')
@click.pass_context
def register_provider(ctx: click.Context, wallet: str, models: str,
                     endpoint: str, min_cost: float, capacity: int):
    """
    Register as AI compute provider

    Become a provider on the AI compute network and earn XAI
    by processing tasks. Requires staking and provider infrastructure.

    Example:
        xai ai register-provider --wallet ADDR --models "gpt-4,claude-3" --endpoint https://api.example.com
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    models_list = [m.strip() for m in models.split(',')]

    console.print("\n[bold cyan]AI Provider Registration[/]\n")

    table = Table(show_header=False, box=box.ROUNDED)
    table.add_row("[bold cyan]Wallet", wallet[:40] + "...")
    table.add_row("[bold cyan]Models", ', '.join(models_list))
    table.add_row("[bold cyan]Endpoint", endpoint)
    table.add_row("[bold cyan]Min Cost", f"{min_cost:.6f} XAI")
    table.add_row("[bold cyan]Capacity", f"{capacity} concurrent tasks")
    table.add_row("[bold yellow]Stake Required", "100 XAI (minimum)")

    console.print(table)

    console.print("\n[bold yellow]Provider Requirements:[/]")
    console.print("  • Minimum 100 XAI stake")
    console.print("  • 99% uptime SLA")
    console.print("  • API endpoint must pass health checks")
    console.print("  • Support for at least one AI model")

    if not Confirm.ask("\n[bold]Register as provider?[/]", default=False):
        console.print("[yellow]Registration cancelled[/]")
        return

    provider_data = {
        "wallet": wallet,
        "models": models_list,
        "endpoint": endpoint,
        "min_cost": min_cost,
        "capacity": capacity,
        "registered_at": time.time()
    }

    try:
        logger.info("Registering AI provider: wallet=%s, models=%s", wallet[:16], models_list)
        with console.status("[bold cyan]Registering provider..."):
            result = client.register_provider(provider_data)

        if ctx.obj['json_output']:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get('success'):
            provider_id = result.get('provider_id')
            logger.info("Provider registered successfully: provider_id=%s", provider_id)
            console.print(f"\n[bold green]✓ Provider registered successfully![/]")
            console.print(f"Provider ID: [cyan]{provider_id}[/]")
            console.print(f"Status: [yellow]{result.get('status', 'PENDING_VERIFICATION').upper()}[/]")
            console.print(f"\nYour provider will be verified and activated within 24 hours.")
        else:
            logger.error("Provider registration failed: %s", result.get('error', 'Unknown'))
            console.print(f"[bold red]✗ Registration failed:[/] {result.get('error', 'Unknown')}")
            sys.exit(1)

    except (click.ClickException, requests.RequestException, ValueError, KeyError) as exc:
        _handle_cli_error(exc)


@ai.command('marketplace')
@click.pass_context
def marketplace_stats(ctx: click.Context):
    """
    View AI marketplace statistics

    Shows network-wide stats including total tasks, active providers,
    total volume, and market trends.

    Example:
        xai ai marketplace
    """
    client = AIComputeClient(ctx.obj['client'].node_url)

    try:
        with console.status("[bold cyan]Fetching marketplace stats..."):
            data = client.get_marketplace_stats()

        if ctx.obj['json_output']:
            click.echo(json.dumps(data, indent=2))
            return

        stats = data.get('stats', {})

        # Marketplace overview
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_row("[bold cyan]Total Tasks", f"{stats.get('total_tasks', 0):,}")
        table.add_row("[bold cyan]Active Providers", f"{stats.get('active_providers', 0):,}")
        table.add_row("[bold green]Total Volume", f"{stats.get('total_volume', 0):.2f} XAI")
        table.add_row("[bold cyan]24h Volume", f"{stats.get('volume_24h', 0):.2f} XAI")
        table.add_row("[bold cyan]Avg Task Cost", f"{stats.get('avg_task_cost', 0):.6f} XAI")
        table.add_row("[bold cyan]Avg Completion Time", stats.get('avg_completion_time', 'N/A'))
        table.add_row("[bold cyan]Network Success Rate", f"{stats.get('success_rate', 0):.1f}%")

        console.print(Panel(table, title="[bold green]AI Marketplace Statistics",
                           border_style="green"))

        # Popular models
        if stats.get('popular_models'):
            console.print("\n[bold]Most Used Models:[/]")
            for i, (model, count) in enumerate(stats['popular_models'].items(), 1):
                console.print(f"  {i}. {model:20} - {count:,} tasks")

        # Task type distribution
        if stats.get('task_distribution'):
            console.print("\n[bold]Task Distribution:[/]")
            total_tasks = sum(stats['task_distribution'].values())
            for task_type, count in stats['task_distribution'].items():
                percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
                console.print(f"  {task_type.upper():20} - {count:,} tasks ({percentage:.1f}%)")

    except (click.ClickException, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        _handle_cli_error(exc)


if __name__ == '__main__':
    ai()

#!/usr/bin/env python3
"""
XAI Node Pruning CLI

Command-line interface for managing blockchain pruning operations.

Usage:
    xai-prune status              # Show current pruning status
    xai-prune run                 # Run pruning now
    xai-prune run --dry-run       # Show what would be pruned
    xai-prune run --keep-blocks 1000
    xai-prune run --keep-days 30
    xai-prune config              # Show current configuration
    xai-prune archive-stats       # Show archive statistics
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from xai.core.pruning import BlockPruningManager, PruneMode, PruningPolicy


def format_bytes(num_bytes: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def print_status(manager: BlockPruningManager) -> None:
    """Print current pruning status"""
    status = manager.get_status()

    print("\n=== XAI Blockchain Pruning Status ===\n")

    # Mode and configuration
    print(f"Mode: {status['mode'].upper()}")
    print(f"Enabled: {'Yes' if status['enabled'] else 'No'}")
    print(f"Would prune now: {'Yes' if status['would_prune'] else 'No'}")

    print("\nPolicy Configuration:")
    policy = status['policy']
    print(f"  Retain blocks: {policy['retain_blocks']}")
    print(f"  Retain days: {policy['retain_days']}")
    print(f"  Archive enabled: {'Yes' if policy['archive_enabled'] else 'No'}")
    print(f"  Keep headers: {'Yes' if policy['keep_headers'] else 'No'}")
    print(f"  Disk threshold: {policy['disk_threshold_gb']:.2f} GB")
    print(f"  Min finalized depth: {policy['min_finalized_depth']}")

    # Chain statistics
    print("\nChain Statistics:")
    chain = status['chain']
    print(f"  Total blocks: {chain['total_blocks']}")
    print(f"  Prunable height: {chain['prunable_height']}")
    print(f"  Eligible for pruning: {chain['eligible_blocks']} blocks")
    print(f"  Disk usage: {chain['disk_usage_gb']:.2f} GB")

    # Historical statistics
    print("\nPruning Statistics:")
    stats = status['stats']
    print(f"  Pruned blocks: {stats['pruned_blocks']}")
    print(f"  Archived blocks: {stats['archived_blocks']}")
    print(f"  Headers-only blocks: {stats['headers_only_blocks']}")
    print(f"  Disk space saved: {format_bytes(stats['disk_space_saved'])}")

    if stats['last_prune_time'] > 0:
        from datetime import datetime
        last_prune = datetime.fromtimestamp(stats['last_prune_time'])
        print(f"  Last pruned: {last_prune.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"  Last pruned: Never")

    print()


def print_config(manager: BlockPruningManager) -> None:
    """Print current configuration"""
    print("\n=== Pruning Configuration ===\n")

    print("Environment Variables:")
    print(f"  XAI_PRUNE_MODE: {os.getenv('XAI_PRUNE_MODE', 'none')}")
    print(f"  XAI_PRUNE_KEEP_BLOCKS: {os.getenv('XAI_PRUNE_KEEP_BLOCKS', '1000')}")
    print(f"  XAI_PRUNE_KEEP_DAYS: {os.getenv('XAI_PRUNE_KEEP_DAYS', '30')}")
    print(f"  XAI_PRUNE_AUTO: {os.getenv('XAI_PRUNE_AUTO', 'false')}")
    print(f"  XAI_PRUNE_ARCHIVE: {os.getenv('XAI_PRUNE_ARCHIVE', 'true')}")
    print(f"  XAI_PRUNE_ARCHIVE_PATH: {os.getenv('XAI_PRUNE_ARCHIVE_PATH', 'data/archive')}")
    print(f"  XAI_PRUNE_DISK_THRESHOLD_GB: {os.getenv('XAI_PRUNE_DISK_THRESHOLD_GB', '50.0')}")
    print(f"  XAI_PRUNE_MIN_FINALIZED_DEPTH: {os.getenv('XAI_PRUNE_MIN_FINALIZED_DEPTH', '100')}")
    print(f"  XAI_PRUNE_KEEP_HEADERS: {os.getenv('XAI_PRUNE_KEEP_HEADERS', 'true')}")

    print("\nCurrent Policy:")
    policy = manager.policy
    print(f"  Mode: {policy.mode.value}")
    print(f"  Retain blocks: {policy.retain_blocks}")
    print(f"  Retain days: {policy.retain_days}")
    print(f"  Archive before delete: {policy.archive_before_delete}")
    print(f"  Archive path: {policy.archive_path}")
    print(f"  Disk threshold: {policy.disk_threshold_gb} GB")
    print(f"  Min finalized depth: {policy.min_finalized_depth}")
    print(f"  Keep headers only: {policy.keep_headers_only}")

    print()


def run_prune(manager: BlockPruningManager, args: argparse.Namespace) -> int:
    """Run pruning operation"""

    # Override policy if arguments provided
    if args.keep_blocks or args.keep_days:
        from xai.core.pruning import PruneMode, PruningPolicy

        mode = PruneMode.BOTH if (args.keep_blocks and args.keep_days) else (
            PruneMode.BLOCKS if args.keep_blocks else PruneMode.DAYS
        )

        new_policy = PruningPolicy(
            mode=mode,
            retain_blocks=args.keep_blocks or manager.policy.retain_blocks,
            retain_days=args.keep_days or manager.policy.retain_days,
            archive_before_delete=manager.policy.archive_before_delete,
            archive_path=manager.policy.archive_path,
            disk_threshold_gb=manager.policy.disk_threshold_gb,
            min_finalized_depth=manager.policy.min_finalized_depth,
            keep_headers_only=manager.policy.keep_headers_only,
        )

        manager.set_policy(new_policy)
        print(f"Updated policy: mode={mode.value}, retain_blocks={new_policy.retain_blocks}, retain_days={new_policy.retain_days}")

    # Calculate prune height
    prune_height = manager.calculate_prune_height()

    if prune_height < 0:
        print("No blocks eligible for pruning.")
        return 0

    print(f"\nPruning blocks up to height {prune_height}")

    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    # Run pruning
    result = manager.prune_blocks(up_to_height=prune_height, dry_run=args.dry_run)

    print(f"\nResults:")
    print(f"  Blocks pruned: {result['pruned']}")
    print(f"  Blocks archived: {result['archived']}")
    print(f"  Space saved: {format_bytes(result['space_saved'])}")
    print(f"  Up to height: {result['up_to_height']}")

    if args.dry_run:
        print("\n(Dry run - no actual changes made)")

    print()
    return 0


def show_archive_stats(manager: BlockPruningManager) -> None:
    """Show archive statistics"""
    archive_dir = Path(manager.policy.archive_path)

    print(f"\n=== Archive Statistics ===\n")
    print(f"Archive directory: {archive_dir}")

    if not archive_dir.exists():
        print("Archive directory does not exist")
        return

    # Count archive files
    archive_files = list(archive_dir.glob("block_*.json.gz"))

    if not archive_files:
        print("No archived blocks found")
        return

    # Calculate total size
    total_size = sum(f.stat().st_size for f in archive_files)

    # Get height range
    heights = []
    for f in archive_files:
        try:
            height = int(f.stem.split('_')[1])
            heights.append(height)
        except (ValueError, IndexError):
            pass

    print(f"Archived blocks: {len(archive_files)}")
    print(f"Total archive size: {format_bytes(total_size)}")

    if heights:
        print(f"Height range: {min(heights)} - {max(heights)}")
        avg_size = total_size / len(heights)
        print(f"Average block size: {format_bytes(int(avg_size))}")

    print()


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="XAI Blockchain Pruning Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    Show current pruning status
  %(prog)s run --dry-run             Show what would be pruned
  %(prog)s run --keep-blocks 1000    Prune keeping last 1000 blocks
  %(prog)s run --keep-days 30        Prune keeping last 30 days
  %(prog)s config                    Show configuration
  %(prog)s archive-stats             Show archive statistics

Environment Variables:
  XAI_PRUNE_MODE              Pruning mode: none, blocks, days, both, space
  XAI_PRUNE_KEEP_BLOCKS       Number of blocks to retain (default: 1000)
  XAI_PRUNE_KEEP_DAYS         Number of days to retain (default: 30)
  XAI_PRUNE_AUTO              Enable automatic pruning (default: false)
  XAI_PRUNE_ARCHIVE           Archive blocks before deletion (default: true)
  XAI_PRUNE_ARCHIVE_PATH      Archive directory path
  XAI_PRUNE_DISK_THRESHOLD_GB Disk space threshold in GB
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Status command
    subparsers.add_parser('status', help='Show pruning status')

    # Config command
    subparsers.add_parser('config', help='Show configuration')

    # Archive stats command
    subparsers.add_parser('archive-stats', help='Show archive statistics')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run pruning operation')
    run_parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would be pruned')
    run_parser.add_argument('--keep-blocks', type=int, help='Override retain blocks setting')
    run_parser.add_argument('--keep-days', type=int, help='Override retain days setting')
    run_parser.add_argument('--data-dir', default='data', help='Data directory (default: data)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # For this CLI to work, we need a blockchain instance
    # In production, this would connect to the running node
    # For now, we'll create a mock or require the node to be running

    try:
        # Import blockchain - this is a simplified version for CLI
        # In production, would connect to running node via RPC
        print("Note: This CLI requires access to blockchain data")
        print("Ensure the node is stopped before running pruning operations\n")

        # Create minimal blockchain instance for pruning manager
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain(data_dir=getattr(args, 'data_dir', 'data'))
        manager = BlockPruningManager(blockchain, data_dir=getattr(args, 'data_dir', 'data'))

        if args.command == 'status':
            print_status(manager)
        elif args.command == 'config':
            print_config(manager)
        elif args.command == 'archive-stats':
            show_archive_stats(manager)
        elif args.command == 'run':
            return run_prune(manager, args)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

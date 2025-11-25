#!/usr/bin/env python3
"""
Consume `threshold_details.json` artifacts and append them to a history log or emit
Markdown summaries for tickets/dashboards.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from xai.tools.threshold_artifact import ThresholdDetails, append_history_entry, prune_history


def _detect_commit(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    env_commit = (
        os.environ.get("GITHUB_SHA")
        or os.environ.get("CI_COMMIT_SHA")
        or os.environ.get("DEPLOY_COMMIT")
    )
    if env_commit:
        return env_commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Append withdrawal threshold artifacts to the history log and/or emit Markdown summaries.",
    )
    parser.add_argument(
        "--details",
        type=Path,
        default=Path("threshold_details.json"),
        help="Path to threshold_details.json artifact.",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=Path("monitoring/withdrawal_threshold_history.jsonl"),
        help="JSONL file where history entries are appended.",
    )
    parser.add_argument(
        "--environment",
        default=os.environ.get("DEPLOY_ENVIRONMENT", "staging"),
        help="Deployment environment label stored with the history entry.",
    )
    parser.add_argument(
        "--commit",
        help="Explicit commit SHA to store with the entry (auto-detected when omitted).",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path to write a Markdown summary derived from the artifact.",
    )
    parser.add_argument(
        "--print-markdown",
        action="store_true",
        help="Print the Markdown summary to stdout.",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Only emit Markdown output without touching the history file.",
    )
    parser.add_argument(
        "--max-history-entries",
        type=int,
        default=None,
        help="If set, prune the history file to this many entries after appending.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    details = ThresholdDetails.from_path(args.details)
    commit = _detect_commit(args.commit)
    markdown = details.to_markdown(environment=args.environment, commit=commit)

    if not args.skip_history:
        entry = details.to_history_entry(environment=args.environment, commit=commit)
        append_history_entry(args.history_file, entry)
        if args.max_history_entries:
            prune_history(args.history_file, args.max_history_entries)

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")

    if args.print_markdown:
        print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

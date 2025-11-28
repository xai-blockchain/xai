#!/usr/bin/env python3
"""
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Optional

import requests

from xai.tools.threshold_artifact import ThresholdDetails


def _load_markdown(markdown_path: Optional[Path], details: ThresholdDetails, environment: str, commit: Optional[str]) -> str:
    if markdown_path and markdown_path.exists():
        return markdown_path.read_text(encoding="utf-8")
    return details.to_markdown(environment=environment, commit=commit)


def _build_comment(markdown: str, environment: str, generated_at: str) -> str:
    return f"## Withdrawal threshold calibration ({environment}, {generated_at})\n\n{markdown}\n"


def _detect_repo(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    if env_repo:
        return env_repo


def _detect_token(explicit: Optional[str]) -> str:
    if not token:
    return token


def _resolve_issue_number(value: Optional[int]) -> Optional[int]:
    if value is not None:
        return value
    env_value = os.environ.get("WITHDRAWAL_CALIBRATION_ISSUE")
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass
    return None


def _resolve_slack_webhook(value: Optional[str]) -> Optional[str]:
    return value or os.environ.get("WITHDRAWAL_CALIBRATION_SLACK_WEBHOOK")


def _resolve_jira_params(args) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    base = args.jira_base_url or os.environ.get("JIRA_BASE_URL")
    issue = args.jira_issue_key or os.environ.get("WITHDRAWAL_CALIBRATION_JIRA_ISSUE")
    email = args.jira_email or os.environ.get("JIRA_EMAIL")
    token = args.jira_api_token or os.environ.get("JIRA_API_TOKEN")
    return base, issue, email, token


    issue_number = _resolve_issue_number(args.issue_number)
    if issue_number is None:
        return
    token = _detect_token(args.token)
    url = f"{args.api_base.rstrip('/')}/repos/{repo}/issues/{issue_number}/comments"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={"body": comment},
        timeout=30,
    )
    if response.status_code >= 300:


def _post_slack(comment: str, webhook: str) -> None:
    response = requests.post(
        webhook,
        json={"text": comment},
        timeout=30,
    )
    if response.status_code >= 300:
        raise SystemExit(f"Failed to post Slack message ({response.status_code}): {response.text}")


def _post_jira(comment: str, base_url: str, issue_key: str, email: str, token: str) -> None:
    url = f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment"
    response = requests.post(
        url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        auth=(email, token),
        json={"body": comment},
        timeout=30,
    )
    if response.status_code >= 300:
        raise SystemExit(f"Failed to post Jira comment ({response.status_code}): {response.text}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser.add_argument("--details", type=Path, default=Path("threshold_details.json"))
    parser.add_argument("--markdown", type=Path, help="Existing Markdown summary to publish.")
    parser.add_argument("--environment", default=os.environ.get("DEPLOY_ENVIRONMENT", "staging"))
    parser.add_argument("--commit", help="Optional commit SHA for context.")
    parser.add_argument("--issue-number", type=int, help="Issue number that receives the comment.")
    parser.add_argument("--slack-webhook", help="Slack incoming webhook URL.")
    parser.add_argument("--jira-base-url", help="Base URL of the Jira Cloud instance.")
    parser.add_argument("--jira-issue-key", help="Jira issue key that should receive the comment.")
    parser.add_argument("--jira-email", help="Jira user email for authentication.")
    parser.add_argument("--jira-api-token", help="Jira API token for authentication.")
    parser.add_argument("--dry-run", action="store_true", help="Print the comment instead of calling the API.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.details.exists():
        raise SystemExit(f"{args.details} not found.")

    details = ThresholdDetails.from_path(args.details)
    markdown = _load_markdown(args.markdown, details, args.environment, args.commit)
    comment = _build_comment(markdown, args.environment, details.generated_at)

    if args.dry_run:
        print(comment)
        return 0

    targets = 0
    issue_number = _resolve_issue_number(args.issue_number)
    slack_webhook = _resolve_slack_webhook(args.slack_webhook)
    jira_base, jira_issue, jira_email, jira_token = _resolve_jira_params(args)

    if issue_number is not None:
        targets += 1

    if slack_webhook:
        _post_slack(comment, slack_webhook)
        targets += 1

    if all([jira_base, jira_issue, jira_email, jira_token]):
        _post_jira(comment, jira_base, jira_issue, jira_email, jira_token)
        targets += 1

    if targets == 0:
        raise SystemExit(
            "No publish target configured. Provide --issue-number/--slack-webhook or Jira parameters, or use --dry-run."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

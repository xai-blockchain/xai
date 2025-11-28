#!/usr/bin/env python3
"""Send nightly security audit summaries to Slack and Jira."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def _load_pip_audit(path: Path) -> str:
    if not path.exists():
        return "report missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "invalid JSON report"
    deps = data.get("dependencies", [])
    vuln_count = sum(len(dep.get("vulns", [])) for dep in deps)
    return f"{vuln_count} known vulnerabilities"


def _load_bandit(path: Path) -> str:
    if not path.exists():
        return "report missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "invalid JSON report"
    issues = data.get("results", [])
    return f"{len(issues)} findings"


def _post_slack(webhook: str, message: str) -> None:
    payload = {"text": message}
    response = requests.post(webhook, json=payload, timeout=10)
    response.raise_for_status()


def _post_jira_comment(base_url: str, issue: str, email: str, token: str, message: str) -> None:
    if not all([base_url, issue, email, token]):
        return
    url = f"{base_url.rstrip('/')}/rest/api/3/issue/{issue}/comment"
    response = requests.post(
        url,
        json={"body": message},
        auth=(email, token),
        timeout=10,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Send security audit summary notifications")
    parser.add_argument("--status", required=True, help="Overall workflow/job status")
    parser.add_argument("--pip-audit", default="pip-audit-report.json", help="Path to pip-audit JSON report")
    parser.add_argument("--bandit", default="bandit-report.json", help="Path to bandit JSON report")
    parser.add_argument("--slack-webhook", default=os.environ.get("WITHDRAWAL_CALIBRATION_SLACK_WEBHOOK"))
    parser.add_argument("--jira-base-url", default=os.environ.get("JIRA_BASE_URL"))
    parser.add_argument("--jira-issue", default=os.environ.get("WITHDRAWAL_CALIBRATION_JIRA_ISSUE"))
    parser.add_argument("--jira-email", default=os.environ.get("JIRA_EMAIL"))
    parser.add_argument("--jira-token", default=os.environ.get("JIRA_API_TOKEN"))
    parser.add_argument("--run-url", required=True, help="GitHub Actions run URL")
    parser.add_argument("--environment", default="staging", help="Environment label")
    args = parser.parse_args()

    pip_summary = _load_pip_audit(Path(args.pip_audit))
    bandit_summary = _load_bandit(Path(args.bandit))

    message = (
        f"Nightly security audit ({args.environment}) status: *{args.status.upper()}*\n"
        f"• pip-audit: {pip_summary}\n"
        f"• bandit: {bandit_summary}\n"
        f"• pytest: see workflow logs\n"
        f"Run: {args.run_url}"
    )

    if args.slack_webhook:
        try:
            _post_slack(args.slack_webhook, message)
        except Exception as exc:  # pragma: no cover
            print(f"Failed to send Slack notification: {exc}", file=sys.stderr)

    if args.jira_base_url and args.jira_issue and args.jira_email and args.jira_token:
        jira_message = message.replace("*", "")
        try:
            _post_jira_comment(
                base_url=args.jira_base_url,
                issue=args.jira_issue,
                email=args.jira_email,
                token=args.jira_token,
                message=jira_message,
            )
        except Exception as exc:  # pragma: no cover
            print(f"Failed to send Jira notification: {exc}", file=sys.stderr)

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

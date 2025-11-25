#!/usr/bin/env python3
"""
Security Alert System for XAI Blockchain

Manages alerts for security issues found during monitoring.
Supports email, Slack, and GitHub issues.

Usage:
    python scripts/security_alerts.py --config CONFIG --report REPORT
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class Alert:
    """Alert data class"""
    severity: str
    tool: str
    title: str
    description: str
    count: int
    timestamp: str


class AlertManager:
    """Manages security alerts"""

    def __init__(self, config: Dict):
        """Initialize alert manager"""
        self.config = config
        self.alerts: List[Alert] = []

    def add_alert(self, alert: Alert):
        """Add alert to queue"""
        self.alerts.append(alert)
        logger.info(f"Alert queued: {alert.severity} - {alert.title}")

    def process_alerts(self):
        """Process and send all queued alerts"""
        if not self.alerts:
            logger.info("No alerts to process")
            return

        logger.info(f"Processing {len(self.alerts)} alerts")

        for alert in self.alerts:
            self._route_alert(alert)

    def _route_alert(self, alert: Alert):
        """Route alert based on severity and configuration"""
        config = self.config.get('alerts', {})

        if alert.severity == 'critical':
            if config.get('email'):
                self._send_email_alert(alert)
            if config.get('slack'):
                self._send_slack_alert(alert)
            if config.get('github_issue'):
                self._create_github_issue(alert)

        elif alert.severity == 'high':
            if config.get('slack'):
                self._send_slack_alert(alert)
            if config.get('github_issue'):
                self._create_github_issue(alert)

        else:  # medium, low
            if config.get('slack'):
                self._send_slack_alert(alert)

    def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            sender_email = os.getenv('ALERT_EMAIL_FROM')
            sender_password = os.getenv('ALERT_EMAIL_PASSWORD')
            recipient_email = os.getenv('ALERT_EMAIL_TO')

            if not all([sender_email, sender_password, recipient_email]):
                logger.warning("Email configuration incomplete, skipping email alert")
                return

            message = MIMEMultipart('alternative')
            message['Subject'] = f"[{alert.severity.upper()}] Security Alert: {alert.title}"
            message['From'] = sender_email
            message['To'] = recipient_email

            text = f"""
Security Alert Notification

Severity: {alert.severity.upper()}
Tool: {alert.tool}
Title: {alert.title}
Description: {alert.description}
Count: {alert.count}
Timestamp: {alert.timestamp}

Please review the full security report and take appropriate action.
            """

            html = f"""
<html>
  <body>
    <h2 style="color: {'#d32f2f' if alert.severity == 'critical' else '#f57c00'}">{alert.severity.upper()} - Security Alert</h2>
    <p><strong>Title:</strong> {alert.title}</p>
    <p><strong>Tool:</strong> {alert.tool}</p>
    <p><strong>Description:</strong> {alert.description}</p>
    <p><strong>Count:</strong> {alert.count}</p>
    <p><strong>Timestamp:</strong> {alert.timestamp}</p>
    <p>Please review the full security report and take appropriate action.</p>
  </body>
</html>
            """

            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            message.attach(part1)
            message.attach(part2)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)

            logger.info(f"Email alert sent to {recipient_email}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _send_slack_alert(self, alert: Alert):
        """Send Slack notification"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return

            color_map = {
                'critical': '#d32f2f',
                'high': '#f57c00',
                'medium': '#fbc02d',
                'low': '#388e3c'
            }

            payload = {
                'attachments': [
                    {
                        'color': color_map.get(alert.severity, '#757575'),
                        'title': f"{alert.severity.upper()} - {alert.title}",
                        'text': alert.description,
                        'fields': [
                            {'title': 'Tool', 'value': alert.tool, 'short': True},
                            {'title': 'Count', 'value': str(alert.count), 'short': True},
                            {'title': 'Timestamp', 'value': alert.timestamp, 'short': False}
                        ]
                    }
                ]
            }

            import urllib.request
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                logger.info("Slack alert sent successfully")

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _create_github_issue(self, alert: Alert):
        """Create GitHub issue for critical/high severity alerts"""
        try:
            token = os.getenv('GITHUB_TOKEN')
            repo = os.getenv('GITHUB_REPOSITORY', 'decri/Crypto')

            if not token:
                logger.warning("GitHub token not configured")
                return

            issue_data = {
                'title': f"[SECURITY] {alert.severity.upper()}: {alert.title}",
                'body': f"""
## Security Alert

**Severity:** {alert.severity.upper()}
**Tool:** {alert.tool}
**Count:** {alert.count}
**Timestamp:** {alert.timestamp}

### Description
{alert.description}

### Action Items
- [ ] Review the vulnerability details
- [ ] Assess the risk to the system
- [ ] Plan remediation
- [ ] Document the fix
- [ ] Verify the fix with re-scan

---
*This issue was automatically created by the Security Alert System*
""",
                'labels': [f'security-{alert.severity}', 'automated']
            }

            result = subprocess.run(
                [
                    'gh', 'issue', 'create',
                    '--repo', repo,
                    '--title', issue_data['title'],
                    '--body', issue_data['body'],
                    '--label', ','.join(issue_data['labels'])
                ],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"GitHub issue created: {result.stdout.strip()}")
            else:
                logger.error(f"Failed to create GitHub issue: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")


class AlertProcessor:
    """Processes security reports and generates alerts"""

    def __init__(self, config: Dict):
        """Initialize alert processor"""
        self.config = config
        self.manager = AlertManager(config)

    def process_report(self, report_path: str):
        """Process security report and generate alerts"""
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)

            logger.info(f"Processing report: {report_path}")

            results = report.get('results', {})
            thresholds = self.config.get('severity_thresholds', {})

            for tool, result in results.items():
                self._analyze_tool_result(tool, result, thresholds)

            self.manager.process_alerts()

        except Exception as e:
            logger.error(f"Failed to process report: {e}")

    def _analyze_tool_result(self, tool: str, result: Dict, thresholds: Dict):
        """Analyze tool result and create alerts if needed"""
        vulnerabilities = result.get('vulnerabilities', [])
        vuln_count = len(vulnerabilities)

        if vuln_count == 0:
            return

        # Determine severity based on tool and count
        severity = self._determine_severity(tool, vuln_count, thresholds)

        if severity:
            alert = Alert(
                severity=severity,
                tool=tool,
                title=f"{tool.upper()}: {vuln_count} vulnerabilities found",
                description=f"Security scan with {tool} found {vuln_count} issues",
                count=vuln_count,
                timestamp=result.get('timestamp', datetime.now().isoformat())
            )
            self.manager.add_alert(alert)

    def _determine_severity(self, tool: str, count: int, thresholds: Dict) -> Optional[str]:
        """Determine alert severity based on vulnerability count"""
        if count >= thresholds.get('critical', 0):
            return 'critical'
        elif count >= thresholds.get('high', 5):
            return 'high'
        elif count >= thresholds.get('medium', 20):
            return 'medium'
        elif count >= thresholds.get('low', 100):
            return 'low'

        return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Security Alert System'
    )
    parser.add_argument(
        '--config',
        help='Configuration file path',
        default='.security/config.yml'
    )
    parser.add_argument(
        '--report',
        help='Security report path',
        required=True
    )

    args = parser.parse_args()

    # Load configuration
    import yaml
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Config not found: {args.config}, using defaults")
        config = {
            'severity_thresholds': {
                'critical': 0,
                'high': 5,
                'medium': 20,
                'low': 100
            },
            'alerts': {
                'email': False,
                'slack': False,
                'github_issue': True
            }
        }

    # Process report and send alerts
    processor = AlertProcessor(config)
    processor.process_report(args.report)


if __name__ == '__main__':
    main()

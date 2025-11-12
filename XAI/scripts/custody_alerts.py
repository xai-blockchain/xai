"""
Custody Alert System
Sends notifications when hot wallets need attention
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.hot_cold_wallet_manager import HotColdWalletManager
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class AlertSystem:
    """Handles custody alerts via multiple channels"""

    def __init__(self):
        self.manager = HotColdWalletManager()

        # Alert configuration (load from environment or config file)
        self.email_enabled = os.getenv('CUSTODY_ALERTS_EMAIL', 'false').lower() == 'true'
        self.email_to = os.getenv('CUSTODY_ALERT_EMAIL', '')
        self.email_from = os.getenv('CUSTODY_FROM_EMAIL', 'custody@aixn.exchange')

        # SMTP configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')

        # Slack webhook (optional)
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')

        # Discord webhook (optional)
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')

    def check_and_alert(self):
        """Check custody status and send alerts if needed"""

        report = self.manager.get_custody_report()
        refills = report['needs_action']['refills']
        sweeps = report['needs_action']['sweeps']

        alerts = []

        # Check for critical refills
        if refills:
            for refill in refills:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'REFILL_NEEDED',
                    'currency': refill['currency'],
                    'amount': refill['amount'],
                    'priority': refill['priority'],
                    'reason': refill['reason'],
                    'message': f"CRITICAL: {refill['currency']} hot wallet needs refill of {refill['amount']}"
                })

        # Check for recommended sweeps
        if sweeps:
            for sweep in sweeps:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'SWEEP_RECOMMENDED',
                    'currency': sweep['currency'],
                    'amount': sweep['amount'],
                    'priority': sweep['priority'],
                    'reason': sweep['reason'],
                    'message': f"WARNING: {sweep['currency']} hot wallet should be swept ({sweep['amount']} excess)"
                })

        # Send alerts if any
        if alerts:
            self.send_alerts(alerts, report)

        return alerts

    def send_alerts(self, alerts, report):
        """Send alerts via configured channels"""

        # Email alerts
        if self.email_enabled and self.email_to:
            try:
                self.send_email_alert(alerts, report)
                print(f"Email alert sent to {self.email_to}")
            except Exception as e:
                print(f"Failed to send email alert: {e}")

        # Slack alerts
        if self.slack_webhook:
            try:
                self.send_slack_alert(alerts, report)
                print("Slack alert sent")
            except Exception as e:
                print(f"Failed to send Slack alert: {e}")

        # Discord alerts
        if self.discord_webhook:
            try:
                self.send_discord_alert(alerts, report)
                print("Discord alert sent")
            except Exception as e:
                print(f"Failed to send Discord alert: {e}")

        # Console log (always)
        self.log_alert(alerts, report)

    def send_email_alert(self, alerts, report):
        """Send email notification"""

        critical_count = len([a for a in alerts if a['level'] == 'CRITICAL'])
        warning_count = len([a for a in alerts if a['level'] == 'WARNING'])

        subject = f"AIXN Custody Alert: {critical_count} Critical, {warning_count} Warnings"

        # Build email body
        body = f"""
AIXN Exchange - Custody Alert
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

============================================================
SUMMARY
============================================================
Total Alerts: {len(alerts)}
Critical (Refills): {critical_count}
Warnings (Sweeps): {warning_count}

============================================================
ALERTS
============================================================
"""

        for alert in alerts:
            body += f"""
[{alert['level']}] {alert['type']}
Currency: {alert['currency']}
Amount: {alert['amount']}
Priority: {alert['priority']}
Reason: {alert['reason']}
---
"""

        body += """
============================================================
CURRENT CUSTODY STATUS
============================================================
"""

        for currency, data in sorted(report['currencies'].items()):
            body += f"\n{currency}: Total={data['total']:.8f}, Hot={data['hot']:.8f} ({data['hot_percentage']:.2f}%), Cold={data['cold']:.8f}"

        body += """

============================================================
ACTION REQUIRED
============================================================
Log into custody management system to process refills/sweeps.
"""

        # Send email
        msg = MIMEMultipart()
        msg['From'] = self.email_from
        msg['To'] = self.email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls()

        if self.smtp_user and self.smtp_pass:
            server.login(self.smtp_user, self.smtp_pass)

        server.send_message(msg)
        server.quit()

    def send_slack_alert(self, alerts, report):
        """Send Slack notification"""
        import requests

        critical_count = len([a for a in alerts if a['level'] == 'CRITICAL'])
        warning_count = len([a for a in alerts if a['level'] == 'WARNING'])

        color = '#FF0000' if critical_count > 0 else '#FFA500'

        payload = {
            'text': f'AIXN Custody Alert',
            'attachments': [
                {
                    'color': color,
                    'title': f'{critical_count} Critical, {warning_count} Warnings',
                    'fields': [
                        {
                            'title': alert['type'],
                            'value': f"{alert['currency']}: {alert['message']}",
                            'short': False
                        }
                        for alert in alerts
                    ],
                    'footer': 'AIXN Custody System',
                    'ts': int(datetime.now().timestamp())
                }
            ]
        }

        requests.post(self.slack_webhook, json=payload)

    def send_discord_alert(self, alerts, report):
        """Send Discord notification"""
        import requests

        critical_count = len([a for a in alerts if a['level'] == 'CRITICAL'])
        warning_count = len([a for a in alerts if a['level'] == 'WARNING'])

        color = 16711680 if critical_count > 0 else 16744448  # Red or Orange

        fields = []
        for alert in alerts:
            fields.append({
                'name': f"[{alert['level']}] {alert['currency']}",
                'value': alert['message'],
                'inline': False
            })

        payload = {
            'embeds': [
                {
                    'title': 'AIXN Custody Alert',
                    'description': f'{critical_count} Critical Alerts, {warning_count} Warnings',
                    'color': color,
                    'fields': fields,
                    'footer': {
                        'text': 'AIXN Custody System'
                    },
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }

        requests.post(self.discord_webhook, json=payload)

    def log_alert(self, alerts, report):
        """Log alert to console and file"""

        log_file = f"custody_data/alerts/alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        log_data = {
            'timestamp': datetime.now().isoformat(),
            'alerts': alerts,
            'report_summary': {
                'initialized_currencies': report['initialized_currencies'],
                'refills_needed': len(report['needs_action']['refills']),
                'sweeps_recommended': len(report['needs_action']['sweeps'])
            }
        }

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"\nAlert logged to: {log_file}")


def main():
    print("=" * 80)
    print("AIXN Custody Alert System")
    print("=" * 80)
    print()

    alert_system = AlertSystem()
    alerts = alert_system.check_and_alert()

    if alerts:
        print(f"\nGenerated {len(alerts)} alert(s)")

        for alert in alerts:
            print(f"\n[{alert['level']}] {alert['currency']}")
            print(f"  {alert['message']}")
    else:
        print("No alerts - all wallets operating normally")

    print()


if __name__ == '__main__':
    main()

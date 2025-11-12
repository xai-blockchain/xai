"""
Daily Custody Monitoring Script
Checks for needed sweep and refill operations
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.hot_cold_wallet_manager import HotColdWalletManager
import json
from datetime import datetime

def main():
    print("=" * 80)
    print(f"AIXN Exchange - Custody Monitor Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    manager = HotColdWalletManager()

    # Get full custody report
    report = manager.get_custody_report()

    # Display current balances
    print("CURRENT CUSTODY BALANCES")
    print("-" * 80)
    print(f"{'Currency':<10} {'Total':>15} {'Hot':>15} {'Cold':>15} {'Hot %':>10}")
    print("-" * 80)

    for currency, data in sorted(report['currencies'].items()):
        hot_pct = data['hot_percentage']

        # Color code based on percentage
        status = ""
        if hot_pct < 5:
            status = " [LOW]"
        elif hot_pct > 15:
            status = " [HIGH]"

        print(f"{currency:<10} {data['total']:>15.8f} {data['hot']:>15.8f} "
              f"{data['cold']:>15.8f} {hot_pct:>9.2f}%{status}")

    print()

    # Check for refills needed
    refills = report['needs_action']['refills']
    sweeps = report['needs_action']['sweeps']

    if refills:
        print("=" * 80)
        print(f"CRITICAL: REFILLS NEEDED ({len(refills)})")
        print("=" * 80)
        print()

        for op in refills:
            print(f"Currency: {op['currency']}")
            print(f"  Amount Needed: {op['amount']}")
            print(f"  From: {op['from_address'][:30]}...")
            print(f"  To:   {op['to_address'][:30]}...")
            print(f"  Priority: {op['priority'].upper()}")
            print(f"  Reason: {op['reason']}")

            if 'warning' in op:
                print(f"  WARNING: {op['warning']}")

            print()

    else:
        print("No refills needed - all hot wallets adequately funded")
        print()

    # Check for sweeps needed
    if sweeps:
        print("=" * 80)
        print(f"SWEEPS RECOMMENDED ({len(sweeps)})")
        print("=" * 80)
        print()

        for op in sweeps:
            print(f"Currency: {op['currency']}")
            print(f"  Amount to Sweep: {op['amount']}")
            print(f"  From: {op['from_address'][:30]}...")
            print(f"  To:   {op['to_address'][:30]}...")
            print(f"  Priority: {op['priority'].upper()}")
            print(f"  Reason: {op['reason']}")
            print()

    else:
        print("No sweeps needed - hot wallets within normal range")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Currencies Managed: {report['initialized_currencies']}")
    print(f"Critical Refills Needed: {len(refills)}")
    print(f"Sweeps Recommended: {len(sweeps)}")
    print()

    # Action items
    if refills or sweeps:
        print("=" * 80)
        print("ACTION REQUIRED")
        print("=" * 80)
        print()

        if refills:
            print("IMMEDIATE ACTION: Process refills to prevent hot wallet depletion")
            print(f"  - {len(refills)} hot wallet(s) below minimum reserve")
            print(f"  - Risk: May be unable to process withdrawals")
            print()

        if sweeps:
            print("RECOMMENDED: Sweep excess funds to cold storage")
            print(f"  - {len(sweeps)} hot wallet(s) above maximum reserve")
            print(f"  - Benefit: Reduce online exposure, improve security")
            print()

    else:
        print("STATUS: All wallets operating within normal parameters")
        print()

    # Export report to JSON for logging
    report_file = f"custody_data/reports/custody_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_file}")
    print()

    # Return exit code based on criticality
    if refills:
        return 1  # Critical - refills needed
    elif sweeps:
        return 2  # Warning - sweeps recommended
    else:
        return 0  # All good


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

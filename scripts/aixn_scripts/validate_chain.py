"""
XAI Blockchain - Chain Validation Script

Standalone script to validate the XAI blockchain.
Can be run manually or integrated into startup scripts.

Usage:
    python scripts/validate_chain.py              # Validate with defaults
    python scripts/validate_chain.py --quiet      # Minimal output
    python scripts/validate_chain.py --report     # Save detailed report
"""

import sys
import os
import argparse
import json
from datetime import datetime

from src.aixn.core.blockchain_loader import load_blockchain_with_validation, BlockchainLoader
from src.aixn.core.blockchain_persistence import BlockchainStorage
from src.aixn.config_manager import Config


def main():
    """Main validation script"""
    parser = argparse.ArgumentParser(description="XAI Blockchain Validator")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output (quiet mode)")
    parser.add_argument(
        "--report", "-r", action="store_true", help="Save detailed validation report"
    )
    parser.add_argument("--data-dir", "-d", type=str, default=None, help="Custom data directory")
    parser.add_argument(
        "--max-supply", type=float, default=121000000.0, help="Maximum supply cap (default: 121M)"
    )
    parser.add_argument(
        "--genesis-hash", type=str, default=None, help="Expected genesis hash for strict validation"
    )

    args = parser.parse_args()

    # Print header
    if not args.quiet:
        print(f"\n{'='*70}")
        print(f"XAI BLOCKCHAIN VALIDATION TOOL")
        print(f"{'='*70}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Network: {Config.NETWORK_TYPE.value}")
        print(f"Max Supply: {args.max_supply:,.0f} XAI")
        if args.data_dir:
            print(f"Data Directory: {args.data_dir}")
        print(f"{'='*70}\n")

    # Load and validate
    try:
        loader = BlockchainLoader(
            data_dir=args.data_dir,
            max_supply=args.max_supply,
            expected_genesis_hash=args.genesis_hash,
        )

        success, blockchain_data, message = loader.load_and_validate(verbose=not args.quiet)

        # Get validation report
        report = loader.get_validation_report()

        # Save report if requested
        if args.report and report:
            storage = BlockchainStorage(args.data_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(storage.data_dir, f"validation_report_{timestamp}.json")

            with open(report_file, "w") as f:
                json.dump(report.to_dict(), f, indent=2)

            print(f"\nDetailed report saved to: {report_file}")

        # Print summary
        if success:
            if not args.quiet:
                print(f"\n{'='*70}")
                print(f"✓ VALIDATION SUCCESSFUL")
                print(f"{'='*70}")
                print(f"Status: PASS")
                print(f"Message: {message}")
                if report:
                    print(f"Blocks: {report.total_blocks:,}")
                    print(f"Transactions: {report.total_transactions:,}")
                    print(f"Total Supply: {report.total_supply:,.2f} XAI")
                    print(f"UTXO Addresses: {report.utxo_count:,}")
                    print(f"Validation Time: {report.validation_time:.2f}s")
                print(f"{'='*70}\n")
            else:
                print(f"✓ PASS - {message}")

            return 0  # Success exit code

        else:
            if not args.quiet:
                print(f"\n{'='*70}")
                print(f"✗ VALIDATION FAILED")
                print(f"{'='*70}")
                print(f"Status: FAIL")
                print(f"Message: {message}")
                if report:
                    print(f"\nIssues Found:")
                    print(f"  Critical: {len(report.get_critical_issues())}")
                    print(f"  Errors: {len(report.get_error_issues())}")
                    print(f"  Warnings: {len(report.get_warning_issues())}")

                    # Print critical issues
                    critical = report.get_critical_issues()
                    if critical:
                        print(f"\nCritical Issues:")
                        for issue in critical[:10]:
                            block_str = (
                                f"Block {issue.block_index}"
                                if issue.block_index is not None
                                else "Chain"
                            )
                            print(f"  - [{block_str}] {issue.description}")
                        if len(critical) > 10:
                            print(f"  ... and {len(critical) - 10} more")

                print(f"{'='*70}\n")
            else:
                print(f"✗ FAIL - {message}")

            return 1  # Failure exit code

    except Exception as e:
        print(f"\n✗ ERROR: Validation script failed: {str(e)}")
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 2  # Error exit code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

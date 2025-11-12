"""
Fee treasury reconciliation helper.

Compare the actual UTXO balance for `Config.TRADE_FEE_ADDRESS` against the sum of
wallet trade fees recorded in the ledger. Run this script during audits or as a
scheduled job to prove that donated tokens never escape the treasury.
"""

import os
import sys

SCRIPT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, SCRIPT_ROOT)
sys.path.insert(0, os.path.join(SCRIPT_ROOT, 'aixn'))

from core.blockchain import Blockchain
from config import Config


def main():
    blockchain = Blockchain()
    summary = blockchain.audit_fee_treasury()
    fee_address = getattr(Config, 'TRADE_FEE_ADDRESS', None)
    if not fee_address:
        print("No fee treasury address configured.")
        return 1

    print(f"Fee treasury reconciliation for {fee_address}:")
    print(f"  Actual balance:   {summary.get('actual_balance', 0):.8f} XAI")
    print(f"  Expected balance: {summary.get('expected_balance', 0):.8f} XAI")
    print(f"  Difference:       {summary.get('difference', 0):.8f} XAI")
    if abs(summary.get('difference', 0)) > 1e-4:
        print("  WARNING: difference exceeds tolerance; inspect logs.")
        return 2
    print("  Reconciliation OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

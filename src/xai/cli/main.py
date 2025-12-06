"""
Main CLI entry point for the XAI blockchain.

This module provides the primary CLI interface for the XAI blockchain.
Legacy wallet commands are preserved for backward compatibility.
"""

import sys
import os

# Try to import enhanced CLI first (requires click and rich)
try:
    from xai.cli.enhanced_cli import main as enhanced_main

    def main():
        """Main CLI entry point with enhanced interface"""
        # Check if user wants legacy CLI
        if '--legacy' in sys.argv or os.getenv('XAI_LEGACY_CLI'):
            sys.argv.remove('--legacy') if '--legacy' in sys.argv else None
            from xai.wallet.cli import main as wallet_main
            return wallet_main()

        return enhanced_main()

except ImportError:
    # Fallback to legacy wallet CLI if dependencies not available
    print("Enhanced CLI not available. Install dependencies with:", file=sys.stderr)
    print("  pip install click rich", file=sys.stderr)
    print("Falling back to legacy wallet CLI...\n", file=sys.stderr)

    from xai.wallet.cli import main as wallet_main

    def main():
        """Fallback to legacy wallet CLI"""
        return wallet_main()


if __name__ == "__main__":
    sys.exit(main() or 0)
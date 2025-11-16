"""
XAI Blockchain - Enhanced Loader with Validation

Loads blockchain from disk and performs comprehensive validation.
Provides automatic recovery options if validation fails.
"""

import os
import sys
import json
from typing import Tuple, Optional
from datetime import datetime


from aixn.core.blockchain_persistence import BlockchainStorage
from aixn.core.chain_validator import validate_blockchain_on_startup, ValidationReport


class BlockchainLoader:
    """
    Enhanced blockchain loader with validation and recovery

    Features:
    - Load blockchain from disk
    - Validate entire chain on startup
    - Automatic recovery from backups if corruption detected
    - Detailed validation reporting
    - Safe fallback to checkpoints
    """

    def __init__(
        self,
        data_dir: str = None,
        max_supply: float = 121000000.0,
        expected_genesis_hash: Optional[str] = None,
    ):
        """
        Initialize blockchain loader

        Args:
            data_dir: Custom data directory (uses default if None)
            max_supply: Maximum supply cap for validation
            expected_genesis_hash: Expected genesis hash for validation
        """
        self.storage = BlockchainStorage(data_dir)
        self.max_supply = max_supply
        self.expected_genesis_hash = expected_genesis_hash
        self.validation_report = None

    def load_and_validate(self, verbose: bool = True) -> Tuple[bool, Optional[dict], str]:
        """
        Load blockchain from disk and validate

        This is the main method to use on startup.
        It will:
        1. Load blockchain from disk
        2. Validate entire chain
        3. Attempt recovery if validation fails
        4. Return validated blockchain or error

        Args:
            verbose: Print detailed progress

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"XAI BLOCKCHAIN LOADER")
            print(f"{'='*70}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Data Directory: {self.storage.data_dir}")
            print(f"{'='*70}\n")

        # Step 1: Load blockchain from disk
        if verbose:
            print("Loading blockchain from disk...")

        success, blockchain_data, message = self.storage.load_from_disk()

        if not success:
            if verbose:
                print(f"✗ Failed to load blockchain: {message}")
            return False, None, f"Load failed: {message}"

        if verbose:
            print(f"✓ {message}")

        # Step 2: Validate the chain
        if verbose:
            print("\nValidating blockchain integrity...")

        is_valid, self.validation_report = validate_blockchain_on_startup(
            blockchain_data,
            max_supply=self.max_supply,
            expected_genesis_hash=self.expected_genesis_hash,
            verbose=verbose,
        )

        # Step 3: Handle validation results
        if is_valid:
            if verbose:
                print(f"\n{'='*70}")
                print(f"✓ BLOCKCHAIN LOADED AND VALIDATED SUCCESSFULLY")
                print(f"{'='*70}\n")

            # Save validation report
            self._save_validation_report(self.validation_report, "validation_success")

            return True, blockchain_data, "Blockchain loaded and validated successfully"

        else:
            # Validation failed - try recovery
            if verbose:
                print(f"\n{'='*70}")
                print(f"✗ VALIDATION FAILED")
                print(f"{'='*70}")
                print(f"Critical Issues: {len(self.validation_report.get_critical_issues())}")
                print(f"Errors: {len(self.validation_report.get_error_issues())}")
                print(f"Warnings: {len(self.validation_report.get_warning_issues())}")
                print(f"{'='*70}\n")

            # Save failed validation report
            self._save_validation_report(self.validation_report, "validation_failed")

            # Attempt recovery
            return self._attempt_recovery(verbose)

    def _attempt_recovery(self, verbose: bool = True) -> Tuple[bool, Optional[dict], str]:
        """
        Attempt to recover blockchain from backups or checkpoints

        Args:
            verbose: Print detailed progress

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        if verbose:
            print("\nAttempting blockchain recovery...\n")

        # Try backups first
        if verbose:
            print("Checking available backups...")

        backups = self.storage.list_backups()

        if backups:
            if verbose:
                print(f"Found {len(backups)} backup(s)")

            for i, backup in enumerate(backups, 1):
                if verbose:
                    print(f"\nTrying backup {i}/{len(backups)}: {backup['filename']}")
                    print(f"  Block Height: {backup['block_height']}")
                    print(f"  Timestamp: {backup['timestamp']}")

                # Try to restore from this backup
                success, blockchain_data, message = self.storage.restore_from_backup(
                    backup["filename"]
                )

                if not success:
                    if verbose:
                        print(f"  ✗ Failed to restore: {message}")
                    continue

                # Validate the restored backup
                if verbose:
                    print(f"  Validating restored backup...")

                is_valid, report = validate_blockchain_on_startup(
                    blockchain_data,
                    max_supply=self.max_supply,
                    expected_genesis_hash=self.expected_genesis_hash,
                    verbose=False,
                )

                if is_valid:
                    if verbose:
                        print(f"  ✓ Backup validated successfully!")
                        print(f"\n{'='*70}")
                        print(f"✓ RECOVERY SUCCESSFUL FROM BACKUP")
                        print(f"{'='*70}")
                        print(f"Restored from: {backup['filename']}")
                        print(f"Block Height: {backup['block_height']}")
                        print(f"{'='*70}\n")

                    # Save the recovered blockchain
                    self.storage.save_to_disk(blockchain_data, create_backup=False)

                    # Save recovery report
                    self._save_validation_report(report, "recovery_success")

                    return True, blockchain_data, f"Recovered from backup: {backup['filename']}"
                else:
                    if verbose:
                        print(f"  ✗ Backup validation failed")
        else:
            if verbose:
                print("No backups found")

        # Try checkpoints
        if verbose:
            print("\nChecking available checkpoints...")

        checkpoints = self.storage.list_checkpoints()

        if checkpoints:
            if verbose:
                print(f"Found {len(checkpoints)} checkpoint(s)")

            for i, checkpoint in enumerate(checkpoints, 1):
                if verbose:
                    print(f"\nTrying checkpoint {i}/{len(checkpoints)}: {checkpoint['filename']}")
                    print(f"  Block Height: {checkpoint['block_height']}")
                    print(f"  Timestamp: {checkpoint['timestamp']}")

                # Load checkpoint file manually
                checkpoint_path = os.path.join(self.storage.checkpoint_dir, checkpoint["filename"])

                try:
                    with open(checkpoint_path, "r") as f:
                        checkpoint_data = json.load(f)

                    blockchain_data = checkpoint_data.get("blockchain")

                    if not blockchain_data:
                        if verbose:
                            print(f"  ✗ Invalid checkpoint format")
                        continue

                    # Validate the checkpoint
                    if verbose:
                        print(f"  Validating checkpoint...")

                    is_valid, report = validate_blockchain_on_startup(
                        blockchain_data,
                        max_supply=self.max_supply,
                        expected_genesis_hash=self.expected_genesis_hash,
                        verbose=False,
                    )

                    if is_valid:
                        if verbose:
                            print(f"  ✓ Checkpoint validated successfully!")
                            print(f"\n{'='*70}")
                            print(f"✓ RECOVERY SUCCESSFUL FROM CHECKPOINT")
                            print(f"{'='*70}")
                            print(f"Restored from: {checkpoint['filename']}")
                            print(f"Block Height: {checkpoint['block_height']}")
                            print(f"{'='*70}\n")

                        # Save the recovered blockchain
                        self.storage.save_to_disk(blockchain_data, create_backup=False)

                        # Save recovery report
                        self._save_validation_report(report, "checkpoint_recovery")

                        return (
                            True,
                            blockchain_data,
                            f"Recovered from checkpoint: {checkpoint['filename']}",
                        )
                    else:
                        if verbose:
                            print(f"  ✗ Checkpoint validation failed")

                except Exception as e:
                    if verbose:
                        print(f"  ✗ Failed to load checkpoint: {str(e)}")
                    continue
        else:
            if verbose:
                print("No checkpoints found")

        # All recovery attempts failed
        if verbose:
            print(f"\n{'='*70}")
            print(f"✗ RECOVERY FAILED")
            print(f"{'='*70}")
            print("All recovery attempts exhausted.")
            print("\nRecommended actions:")
            print("1. Resync blockchain from network peers")
            print("2. Contact network administrators")
            print("3. Check for hardware/disk issues")
            print(f"{'='*70}\n")

        return False, None, "Recovery failed - all backups and checkpoints invalid or unavailable"

    def _save_validation_report(self, report: ValidationReport, report_type: str):
        """
        Save validation report to file

        Args:
            report: Validation report
            report_type: Type of report (e.g., 'validation_success', 'validation_failed')
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(
                self.storage.data_dir, f"validation_report_{report_type}_{timestamp}.json"
            )

            with open(report_file, "w") as f:
                json.dump(report.to_dict(), f, indent=2)

            print(f"Validation report saved: {os.path.basename(report_file)}")

        except Exception as e:
            print(f"Warning: Failed to save validation report: {e}")

    def get_validation_report(self) -> Optional[ValidationReport]:
        """
        Get the last validation report

        Returns:
            ValidationReport or None
        """
        return self.validation_report


def load_blockchain_with_validation(
    data_dir: str = None,
    max_supply: float = 121000000.0,
    expected_genesis_hash: Optional[str] = None,
    verbose: bool = True,
) -> Tuple[bool, Optional[dict], str]:
    """
    Convenience function to load and validate blockchain

    This is the recommended way to load blockchain on startup.

    Args:
        data_dir: Custom data directory
        max_supply: Maximum supply cap
        expected_genesis_hash: Expected genesis hash
        verbose: Print detailed progress

    Returns:
        tuple: (success: bool, blockchain_data: dict or None, message: str)
    """
    loader = BlockchainLoader(
        data_dir=data_dir, max_supply=max_supply, expected_genesis_hash=expected_genesis_hash
    )

    return loader.load_and_validate(verbose=verbose)


# Example usage
if __name__ == "__main__":
    print("XAI Blockchain Loader - Test Mode\n")

    # Load and validate blockchain
    success, blockchain_data, message = load_blockchain_with_validation(
        max_supply=121000000.0, verbose=True
    )

    if success:
        print(f"\n✓ SUCCESS: {message}")
        print(f"Blockchain ready to use!")
        print(f"Total blocks: {len(blockchain_data.get('chain', []))}")
        sys.exit(0)
    else:
        print(f"\n✗ FAILURE: {message}")
        print(f"Blockchain not available")
        sys.exit(1)

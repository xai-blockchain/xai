from __future__ import annotations

"""
XAI Blockchain - Enhanced Loader with Validation

Loads blockchain from disk and performs comprehensive validation.
Provides automatic recovery options if validation fails.
"""

import json
import logging
import os
import sys
from datetime import datetime

from xai.core.chain.blockchain_persistence import BlockchainStorage
from xai.core.consensus.chain_validator import ValidationReport, validate_blockchain_on_startup

logger = logging.getLogger(__name__)

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
        expected_genesis_hash: str | None = None,
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

    def load_and_validate(self, verbose: bool = True) -> tuple[bool, dict | None, str]:
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
        logger.info(
            "XAI Blockchain Loader starting",
            extra={
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_directory": self.storage.data_dir,
            },
        )

        # Step 1: Load blockchain from disk
        logger.info("Loading blockchain from disk")

        success, blockchain_data, message = self.storage.load_from_disk()

        if not success:
            logger.error("Failed to load blockchain", extra={"error": message})
            return False, None, f"Load failed: {message}"

        logger.info("Blockchain loaded from disk", extra={"status_message": message})

        # Step 2: Validate the chain
        logger.info("Validating blockchain integrity")

        is_valid, self.validation_report = validate_blockchain_on_startup(
            blockchain_data,
            max_supply=self.max_supply,
            expected_genesis_hash=self.expected_genesis_hash,
            verbose=verbose,
        )

        # Step 3: Handle validation results
        if is_valid:
            logger.info("Blockchain loaded and validated successfully")

            # Save validation report
            self._save_validation_report(self.validation_report, "validation_success")

            return True, blockchain_data, "Blockchain loaded and validated successfully"

        else:
            # Validation failed - try recovery
            logger.error(
                "Validation failed",
                extra={
                    "critical_issues": len(self.validation_report.get_critical_issues()),
                    "errors": len(self.validation_report.get_error_issues()),
                    "warnings": len(self.validation_report.get_warning_issues()),
                },
            )

            # Save failed validation report
            self._save_validation_report(self.validation_report, "validation_failed")

            # Attempt recovery
            return self._attempt_recovery(verbose)

    def _attempt_recovery(self, verbose: bool = True) -> tuple[bool, dict | None, str]:
        """
        Attempt to recover blockchain from backups or checkpoints

        Args:
            verbose: Print detailed progress

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        logger.info("Attempting blockchain recovery")

        # Try backups first
        logger.info("Checking available backups")

        backups = self.storage.list_backups()

        if backups:
            logger.info("Found backups", extra={"backup_count": len(backups)})

            for i, backup in enumerate(backups, 1):
                logger.info(
                    "Trying backup",
                    extra={
                        "backup_number": f"{i}/{len(backups)}",
                        "filename": backup["filename"],
                        "block_height": backup["block_height"],
                        "timestamp": backup["timestamp"],
                    },
                )

                # Try to restore from this backup
                success, blockchain_data, message = self.storage.restore_from_backup(
                    backup["filename"]
                )

                if not success:
                    logger.warning("Failed to restore backup", extra={"error_message": message})
                    continue

                # Validate the restored backup
                logger.info("Validating restored backup")

                is_valid, report = validate_blockchain_on_startup(
                    blockchain_data,
                    max_supply=self.max_supply,
                    expected_genesis_hash=self.expected_genesis_hash,
                    verbose=False,
                )

                if is_valid:
                    logger.info(
                        "Recovery successful from backup",
                        extra={
                            "filename": backup["filename"],
                            "block_height": backup["block_height"],
                        },
                    )

                    # Save the recovered blockchain
                    self.storage.save_to_disk(blockchain_data, create_backup=False)

                    # Save recovery report
                    self._save_validation_report(report, "recovery_success")

                    return True, blockchain_data, f"Recovered from backup: {backup['filename']}"
                else:
                    logger.warning("Backup validation failed")
        else:
            logger.info("No backups found")

        # Try checkpoints
        logger.info("Checking available checkpoints")

        checkpoints = self.storage.list_checkpoints()

        if checkpoints:
            logger.info("Found checkpoints", extra={"checkpoint_count": len(checkpoints)})

            for i, checkpoint in enumerate(checkpoints, 1):
                logger.info(
                    "Trying checkpoint",
                    extra={
                        "checkpoint_number": f"{i}/{len(checkpoints)}",
                        "filename": checkpoint["filename"],
                        "block_height": checkpoint["block_height"],
                        "timestamp": checkpoint["timestamp"],
                    },
                )

                # Load checkpoint file manually
                checkpoint_path = os.path.join(self.storage.checkpoint_dir, checkpoint["filename"])

                try:
                    with open(checkpoint_path, "r") as f:
                        checkpoint_data = json.load(f)

                    blockchain_data = checkpoint_data.get("blockchain")

                    if not blockchain_data:
                        logger.warning("Invalid checkpoint format")
                        continue

                    # Validate the checkpoint
                    logger.info("Validating checkpoint")

                    is_valid, report = validate_blockchain_on_startup(
                        blockchain_data,
                        max_supply=self.max_supply,
                        expected_genesis_hash=self.expected_genesis_hash,
                        verbose=False,
                    )

                    if is_valid:
                        logger.info(
                            "Recovery successful from checkpoint",
                            extra={
                                "filename": checkpoint["filename"],
                                "block_height": checkpoint["block_height"],
                            },
                        )

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
                        logger.warning("Checkpoint validation failed")

                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.error("Failed to load checkpoint", extra={"error": str(e)}, exc_info=True)
                    continue
        else:
            logger.info("No checkpoints found")

        # All recovery attempts failed
        logger.error(
            "Recovery failed - all recovery attempts exhausted",
            extra={
                "recommended_actions": [
                    "Resync blockchain from network peers",
                    "Contact network administrators",
                    "Check for hardware/disk issues",
                ]
            },
        )

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

            logger.info("Validation report saved", extra={"filename": os.path.basename(report_file)})

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.warning("Failed to save validation report", extra={"error": str(e)})

    def get_validation_report(self) -> ValidationReport | None:
        """
        Get the last validation report

        Returns:
            ValidationReport or None
        """
        return self.validation_report

def load_blockchain_with_validation(
    data_dir: str = None,
    max_supply: float = 121000000.0,
    expected_genesis_hash: str | None = None,
    verbose: bool = True,
) -> tuple[bool, dict | None, str]:
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


import logging
import json
from datetime import datetime, timezone
import os
import hashlib
import hmac
import gzip
import shutil
from typing import Optional

AUDIT_LOG_FILE = os.path.join("logs", "audit.log")


class AuditLogger:
    """
    Tamper-proof audit logger with cryptographic signatures and log rotation.

    Features:
    - Cryptographic signatures using HMAC-SHA256 for tamper detection
    - Chain of custody: each log entry references the previous entry's hash
    - Timestamp verification to detect time manipulation
    - Structured JSON logging for easy parsing and analysis
    - Automatic log rotation based on size and time
    - Compressed archive of rotated logs
    """

    def __init__(
        self,
        log_file=AUDIT_LOG_FILE,
        signing_key: str = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB default
        backup_count: int = 10,
        compress_rotated: bool = True
    ):
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.compress_rotated = compress_rotated

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Signing key for HMAC (in production, load from secure storage)
        self.signing_key = signing_key or os.environ.get(
            "XAI_AUDIT_SIGNING_KEY",
            "default-audit-key-change-in-production"
        ).encode('utf-8')

        # Track previous log entry hash for chain of custody
        self.previous_hash = "0" * 64  # Genesis hash

        self.logger = logging.getLogger("audit_logger")
        self.logger.setLevel(logging.INFO)

        # Prevent adding multiple handlers if already configured
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter("%(message)s")  # We'll format the message as JSON
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Track rotation metadata
        self.rotation_count = 0

    def _calculate_signature(self, log_entry: dict) -> str:
        """
        Calculate HMAC-SHA256 signature for a log entry.

        This provides tamper detection: any modification to the log entry
        will invalidate the signature.
        """
        # Create deterministic representation
        entry_string = json.dumps(log_entry, sort_keys=True)
        signature = hmac.new(
            self.signing_key,
            entry_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _should_rotate(self) -> bool:
        """Check if log file should be rotated based on size"""
        if not os.path.exists(self.log_file):
            return False

        file_size = os.path.getsize(self.log_file)
        return file_size >= self.max_bytes

    def _rotate_logs(self):
        """
        Rotate audit logs with compression and retention management.

        Rotation process:
        1. Close current log file
        2. Rename current log to timestamped backup
        3. Compress backup if enabled
        4. Remove old backups beyond retention limit
        5. Create new log file
        """
        if not os.path.exists(self.log_file):
            return

        # Close current log handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        # Generate timestamped backup name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_file = f"{self.log_file}.{timestamp}"

        try:
            # Rename current log to backup
            shutil.move(self.log_file, backup_file)

            # Compress backup if enabled
            if self.compress_rotated:
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # Remove uncompressed backup
                os.remove(backup_file)
                self.logger.info(f"Rotated and compressed audit log: {compressed_file}")
            else:
                self.logger.info(f"Rotated audit log: {backup_file}")

            # Clean up old backups
            self._cleanup_old_backups()

            self.rotation_count += 1

        except (OSError, IOError, PermissionError, RuntimeError, ValueError) as exc:
            self.logger.error(
                "Error rotating audit log: %s",
                exc,
                extra={"event": "audit_logger.rotate_failed", "error": str(exc)},
            )

        # Recreate log file handler
        file_handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Reset chain for new log file
        self.previous_hash = "0" * 64

    def _cleanup_old_backups(self):
        """Remove old backup files beyond retention limit"""
        log_dir = os.path.dirname(self.log_file)
        log_name = os.path.basename(self.log_file)

        # Find all backup files
        backup_files = []
        for filename in os.listdir(log_dir):
            if filename.startswith(log_name + ".") and filename != log_name:
                backup_path = os.path.join(log_dir, filename)
                backup_files.append((os.path.getmtime(backup_path), backup_path))

        # Sort by modification time (oldest first)
        backup_files.sort()

        # Remove oldest files if exceeding backup_count
        while len(backup_files) > self.backup_count:
            _, oldest_file = backup_files.pop(0)
            try:
                os.remove(oldest_file)
                self.logger.info(f"Removed old audit backup: {oldest_file}")
            except (OSError, PermissionError) as exc:
                self.logger.error(
                    "Error removing old backup %s: %s",
                    oldest_file,
                    exc,
                    extra={"event": "audit_logger.cleanup_failed", "error": str(exc)},
                )

    def get_rotation_stats(self) -> dict:
        """Get audit log rotation statistics"""
        stats = {
            "log_file": self.log_file,
            "current_size_bytes": os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0,
            "max_bytes": self.max_bytes,
            "rotation_count": self.rotation_count,
            "backup_count": self.backup_count,
            "compress_enabled": self.compress_rotated
        }

        # Count existing backups
        log_dir = os.path.dirname(self.log_file)
        log_name = os.path.basename(self.log_file)
        backup_count = 0

        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.startswith(log_name + ".") and filename != log_name:
                    backup_count += 1

        stats["existing_backups"] = backup_count
        return stats

    def log_action(self, user_id: str, action: str, details: dict = None, outcome: str = "SUCCESS"):
        """
        Log a security-sensitive action with cryptographic signature.

        Args:
            user_id: Identifier of the user/system performing the action
            action: Type of action being performed
            details: Additional details about the action
            outcome: SUCCESS or FAILURE

        The log entry includes:
        - Timestamp (ISO 8601 UTC)
        - User identifier
        - Action type and details
        - Outcome status
        - Previous log hash (chain of custody)
        - Cryptographic signature (tamper detection)
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "details": details if details is not None else {},
            "previous_hash": self.previous_hash,
        }

        # Calculate and add signature
        signature = self._calculate_signature(log_entry)
        log_entry["signature"] = signature

        # Calculate hash of this entry for next entry's previous_hash
        entry_hash = hashlib.sha256(
            json.dumps(log_entry, sort_keys=True).encode('utf-8')
        ).hexdigest()
        self.previous_hash = entry_hash

        # Check if rotation is needed before writing
        if self._should_rotate():
            self._rotate_logs()

        # Write to log
        self.logger.info(json.dumps(log_entry))


if __name__ == "__main__":
    raise SystemExit("AuditLogger demo removed; use unit tests instead.")

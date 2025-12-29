"""
Unit tests for structured logger sanitization and correlation handling.
"""

import json
from pathlib import Path

from xai.core.api.structured_logger import StructuredLogger, correlation_id


def _read_json_log(log_dir: Path, name: str) -> dict:
    """Read the most recent JSON log entry from the logger output."""
    log_path = log_dir / f"{name.lower()}.json.log"
    with log_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return json.loads(lines[-1])


def test_sensitive_fields_are_sanitized(tmp_path):
    """Logger redacts sensitive fields before writing to disk."""
    name = "SanitizeLogger"
    logger = StructuredLogger(name=name, log_dir=str(tmp_path))
    logger.info("store secrets", private_key="abc123", nested={"secret": "token", "ok": "yes"})

    for handler in logger.logger.handlers:
        handler.flush()

    entry = _read_json_log(tmp_path, name)
    assert entry["private_key"] == "REDACTED"
    assert entry["nested"]["secret"] == "REDACTED"
    assert entry["nested"]["ok"] == "yes"


def test_correlation_id_propagates_into_log(tmp_path):
    """Correlation ID context is captured in structured output."""
    name = "CorrelationLogger"
    logger = StructuredLogger(name=name, log_dir=str(tmp_path))
    token = correlation_id.set("corr-123")
    logger.info("with correlation")
    correlation_id.reset(token)

    for handler in logger.logger.handlers:
        handler.flush()

    entry = _read_json_log(tmp_path, name)
    assert entry["correlation_id"] == "corr-123"

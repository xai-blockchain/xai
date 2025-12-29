"""
Unit tests for anonymous logger sanitization and address truncation helpers.
"""

import logging
from pathlib import Path

from xai.core.security.anonymous_logger import AnonymousLogger


def _read_last_line(log_path: Path) -> str:
    with log_path.open("r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines[-1]


def test_truncate_and_sanitize(tmp_path):
    """Addresses are truncated and sensitive tokens are redacted."""
    logger = AnonymousLogger(log_dir=str(tmp_path), log_name="anon.log")
    logger.logger.setLevel(logging.INFO)

    logger.transaction_received("XAI1234567890ABCDE", "XAI0987654321FFFF", 1.5)
    logger.info("leak private_key=deadbeef")

    # First logged transaction line contains truncated addresses; last line contains sanitized message
    lines = (tmp_path / "anon.log").read_text().splitlines()
    assert any("XAI123...BCDE" in l and "XAI098...FFFF" in l for l in lines)
    assert "REDACTED" in lines[-1]

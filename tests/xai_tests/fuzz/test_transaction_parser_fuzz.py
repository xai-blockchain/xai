from __future__ import annotations

"""
Fuzzing tests for QR transaction parser safety.

These property-based tests ensure the mobile QR transaction parser can safely
roundtrip valid payloads and gracefully reject corrupted or random data without
crashing.
"""

import base64
import binascii
import json
import os
import random
import string
from typing import Any

import pytest

from xai.mobile.qr_transactions import TransactionQRGenerator

def _random_string(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))

def _random_tx_payload() -> dict[str, Any]:
    return {
        "from": f"XAI{_random_string(40)}",
        "to": f"XAI{_random_string(40)}",
        "amount": random.uniform(0.0001, 10_000),
        "nonce": random.randint(0, 1_000_000),
    }

def test_parse_transaction_qr_roundtrip_base64():
    """Base64-encoded QR payloads should roundtrip through the parser."""
    for _ in range(50):
        tx_payload = _random_tx_payload()
        data = json.dumps(tx_payload, sort_keys=True)
        encoded = base64.b64encode(data.encode()).decode()
        qr_data = f"xai:tx:{encoded}"

        parsed = TransactionQRGenerator.parse_transaction_qr(qr_data)
        assert parsed == json.loads(data)

def test_parse_transaction_qr_roundtrip_raw_json():
    """Parser should accept direct JSON payloads when base64 decoding fails."""
    for _ in range(50):
        tx_payload = _random_tx_payload()
        data = json.dumps(tx_payload)
        qr_data = f"xai:tx:{data}"
        parsed = TransactionQRGenerator.parse_transaction_qr(qr_data)
        assert parsed == tx_payload

def test_parse_transaction_qr_random_payloads_fail_gracefully():
    """Random payloads must raise ValueError/JSON errors without crashing."""
    random.seed(os.urandom(16))
    for _ in range(100):
        noise = _random_string(random.randint(0, 64))
        qr_data = f"xai:tx:{noise}"
        try:
            parsed = TransactionQRGenerator.parse_transaction_qr(qr_data)
            assert isinstance(parsed, dict)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
            continue

def test_parse_transaction_qr_requires_prefix():
    """Inputs without the xai transaction prefix must raise ValueError."""
    for _ in range(50):
        noise = _random_string(20)
        with pytest.raises(ValueError):
            TransactionQRGenerator.parse_transaction_qr(noise)

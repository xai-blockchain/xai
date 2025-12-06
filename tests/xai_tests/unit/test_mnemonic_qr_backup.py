import base64

import pytest

from xai.wallet.mnemonic_qr_backup import MnemonicQRBackupGenerator

MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)


def test_generate_bundle_contains_expected_metadata():
    generator = MnemonicQRBackupGenerator()
    bundle = generator.generate_bundle(
        MNEMONIC,
        passphrase="test-passphrase",
        metadata={"address": "XAI123", "note": "unit-test"},
    )

    payload = bundle.payload
    assert payload["format"] == generator.FORMAT_NAME
    assert payload["version"] == generator.FORMAT_VERSION
    assert payload["word_count"] == 24
    assert "passphrase" not in payload  # passphrase not embedded by default
    assert payload["passphrase_hint"].isalnum()
    assert payload["metadata"]["address"] == "XAI123"
    assert payload["metadata"]["note"] == "unit-test"

    # PNG base64 should decode without errors
    png_bytes = base64.b64decode(bundle.image_base64.encode("ascii"))
    assert png_bytes.startswith(b"\x89PNG")

    ascii_lines = [line for line in bundle.ascii_art.splitlines() if line.strip()]
    assert len(ascii_lines) >= 10


def test_invalid_mnemonic_raises_value_error():
    generator = MnemonicQRBackupGenerator()
    with pytest.raises(ValueError):
        generator.generate_bundle("this is not a valid mnemonic")

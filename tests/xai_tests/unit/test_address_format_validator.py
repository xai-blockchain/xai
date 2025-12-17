from xai.core.validation import AddressFormatValidator, validate_address


def test_address_validator_enforces_network_prefix():
    validator = AddressFormatValidator(expected_prefix="XAI")
    assert validator.validate("XAI" + "0" * 40) == "XAI" + "0" * 40

    wrong_prefix = "TXAI" + "0" * 40
    assert validator.is_valid(wrong_prefix) is False


def test_address_validator_allows_special_when_enabled():
    validator = AddressFormatValidator(allow_special=True)
    assert validator.validate("COINBASE") == "COINBASE"

    validator_no_special = AddressFormatValidator(allow_special=False)
    assert validator_no_special.is_valid("COINBASE") is False


def test_validate_address_uses_default_validator():
    addr = "TXAI" + "a" * 40
    # validate_address now returns checksummed format
    result = validate_address(addr)
    assert result.lower() == addr.lower()  # Same address, different case


def test_address_validator_legacy_support_toggle():
    legacy_addr = "XAI" + "b" * 30
    validator_legacy = AddressFormatValidator(allow_legacy=True)
    assert validator_legacy.validate(legacy_addr) == legacy_addr

    validator_strict = AddressFormatValidator(allow_legacy=False)
    assert validator_strict.is_valid(legacy_addr) is False

"""
Tests for P2WSH bech32 address derivation.
"""

from xai.core.utxo_address import redeem_script_to_p2wsh_address


def test_redeem_script_to_p2wsh():
    script = "OP_SHA256 deadbeef OP_EQUAL"
    addr = redeem_script_to_p2wsh_address(script, hrp="tb")  # testnet hrp
    assert addr.startswith("tb1")
    assert redeem_script_to_p2wsh_address("") is None

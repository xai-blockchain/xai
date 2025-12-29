"""
Tests for P2WSH bech32 address derivation.
"""

from xai.core.transactions.utxo_address import redeem_script_to_p2wsh_address


def test_redeem_script_to_p2wsh():
    script_hex = "a8" + "04deadbeef" + "88"
    addr = redeem_script_to_p2wsh_address(script_hex, hrp="tb")  # testnet hrp
    assert addr.startswith("tb1")
    assert redeem_script_to_p2wsh_address("") is None

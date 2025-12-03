"""
Unit tests for minimal ABI utilities.
"""

from xai.core.vm.evm.abi import function_selector, encode_call, encode_args, decode_address, decode_uint256


def test_function_selector_transfer():
    sig = "transfer(address,uint256)"
    sel = function_selector(sig)
    # ERC20 transfer selector is a9059cbb
    assert sel.hex() == "a9059cbb"


def test_encode_call_transfer():
    sig = "transfer(address,uint256)"
    to = "0x" + ("ab" * 20)
    amount = 12345678901234567890
    calldata = encode_call(sig, [to, amount])
    # First 4 bytes are selector
    assert calldata[:4].hex() == "a9059cbb"
    # Then 32-byte address (right padded in word, address is last 20 bytes)
    # Decode back to validate
    addr, off = decode_address(calldata, 4)
    assert addr.lower() == to.lower()
    val, off2 = decode_uint256(calldata, off)
    assert val == amount


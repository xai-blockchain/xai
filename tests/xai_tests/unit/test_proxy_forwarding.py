"""
Tests for proxy forwarding behavior (logical delegatecall simulation).
"""

from xai.core.contracts.proxy import TransparentProxy
from xai.core.vm.exceptions import VMExecutionError


class DummyImpl:
    def __init__(self, name: str):
        self.name = name


def test_transparent_proxy_delegate_forwarding_non_admin():
    admin = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    impl_addr = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    user = "0xcccccccccccccccccccccccccccccccccccccccc"

    proxy = TransparentProxy(admin=admin, implementation=impl_addr)

    implementations = {impl_addr: DummyImpl("ImplV1")}
    calldata = bytes.fromhex("deadbeef")

    result = proxy.delegate_call(user, calldata, implementations)
    assert isinstance(result, dict)
    assert result["delegate_to"].name == "ImplV1"
    assert result["implementation"] == impl_addr
    assert result["proxy"] == proxy.address
    assert result["calldata"] == calldata


def test_transparent_proxy_admin_blocked_from_delegate():
    admin = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    proxy = TransparentProxy(admin=admin, implementation="0x1111111111111111111111111111111111111111")
    try:
        proxy.delegate_call(admin, b"", {proxy.implementation: DummyImpl("Impl")})
        assert False, "Admin should not be allowed to delegate"
    except VMExecutionError as e:
        assert "Admin cannot call" in str(e)


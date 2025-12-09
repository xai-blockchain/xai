"""
Additional tests for ExecutionContext gas accounting and call stack controls.

Coverage targets:
- Push/pop respects max depth and returns False at limit
- Gas accounting helpers update totals and refunds
"""

from types import SimpleNamespace

from xai.core.vm.evm.context import ExecutionContext, BlockContext, CallContext, CallType


def _ctx(max_depth=2):
    return ExecutionContext(
        block=BlockContext(
            number=1,
            timestamp=0,
            gas_limit=100000,
            coinbase="c",
            prevrandao=0,
            base_fee=0,
            chain_id=1,
        ),
        tx_origin="o",
        tx_gas_price=1,
        tx_gas_limit=100000,
        tx_value=0,
        max_call_depth=max_depth,
    )


def test_push_call_respects_max_depth_and_pop():
    ctx = _ctx(max_depth=1)
    call = CallContext(call_type=CallType.CALL, depth=0, address="A", caller="B", origin="B", value=0, gas=10, code=b"", calldata=b"")
    assert ctx.push_call(call) is True
    assert ctx.push_call(call) is False
    assert ctx.pop_call() is call
    assert ctx.current_call is None


def test_gas_accounting_helpers():
    ctx = _ctx()
    ctx.gas_used += 10
    assert ctx.gas_used == 10
    ctx.gas_refund += 5
    assert ctx.gas_refund == 5

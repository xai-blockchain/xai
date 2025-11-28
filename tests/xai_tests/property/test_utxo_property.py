import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction


@given(
    initial_funds=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    spend_amount=st.floats(min_value=1.0, max_value=20.0, allow_nan=False, allow_infinity=False),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
@pytest.mark.asyncio
async def test_utxo_consistency_under_spend_and_mine(tmp_path, initial_funds, spend_amount):
    """
    Property-based sanity: fund wallet, spend once, mine, and ensure UTXO set stays consistent.
    """
    data_dir = tmp_path / "data"
    if data_dir.exists():
        import shutil
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    bc = Blockchain(data_dir=str(data_dir))

    sender = Wallet()
    recipient = Wallet()

    coinbase_tx = Transaction("COINBASE", sender.address, initial_funds)
    coinbase_tx.txid = coinbase_tx.calculate_hash()
    bc.pending_transactions.append(coinbase_tx)
    sender_identity = {"private_key": sender.private_key, "public_key": sender.public_key}
    mined = bc.mine_pending_transactions(sender.address, sender_identity)
    assert mined is not None

    # Spend less than balance to keep test stable
    amount = min(spend_amount, bc.get_balance(sender.address) * 0.8)
    tx = bc.create_transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=amount,
        fee=0.001,
        private_key=sender.private_key,
        public_key=sender.public_key,
    )
    assert tx is not None
    assert bc.add_transaction(tx) is True

    mined2 = bc.mine_pending_transactions(sender.address, sender_identity)
    assert mined2 is not None

    assert bc.utxo_manager.verify_utxo_consistency()["is_consistent"]

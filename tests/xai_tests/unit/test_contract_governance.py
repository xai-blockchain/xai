"""Tests covering smart-contract persistence and governance gating."""

import time
from typing import Any, Dict

from xai.core.blockchain import Blockchain
from xai.core.config import Config
from xai.core.governance_execution import ProposalType


def _save_contract_snapshot(blockchain: Blockchain) -> None:
    blockchain.storage.save_state_to_disk(
        blockchain.utxo_manager,
        blockchain.pending_transactions,
        blockchain.contracts,
        blockchain.contract_receipts,
    )


def test_contract_state_persistence(tmp_path):
    data_dir = str(tmp_path)
    blockchain = Blockchain(data_dir=data_dir)

    contract_address = "XAICONTRACT000000000000000000000000000000"
    contract_entry: Dict[str, Any] = {
        "creator": "XAI_CREATOR",
        "code": b"\x01\x02\x03\x04",
        "storage": {"counter": 7},
        "gas_limit": 120000,
        "balance": 0.0,
        "created_at": time.time(),
    }
    blockchain.contracts[contract_address] = dict(contract_entry)
    blockchain.contract_receipts.append({"txid": "receipt-most-recent", "contract": contract_address})

    _save_contract_snapshot(blockchain)

    reloaded = Blockchain(data_dir=data_dir)
    assert contract_address in reloaded.contracts
    restored = reloaded.contracts[contract_address]
    assert restored["creator"] == contract_entry["creator"]
    assert restored["storage"]["counter"] == contract_entry["storage"]["counter"]
    assert restored["code"] == contract_entry["code"]
    assert reloaded.contract_receipts[-1]["txid"] == "receipt-most-recent"


def test_smart_contract_manager_governance_gate(tmp_path):
    data_dir = str(tmp_path)
    prev_flag = Config.FEATURE_FLAGS.get("vm")
    Config.FEATURE_FLAGS["vm"] = True
    try:
        blockchain = Blockchain(data_dir=data_dir)
        assert blockchain.smart_contract_manager is None

        proposal_id_enable = f"test-smart-contracts-enable-{int(time.time()*1000)}"
        enable_result = blockchain.governance_executor.execute_proposal(
            proposal_id_enable,
            {
                "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
                "feature_name": "smart_contracts",
                "enabled": True,
            },
        )
        assert enable_result["success"]
        blockchain.sync_smart_contract_vm()
        assert blockchain.smart_contract_manager is not None

        proposal_id_disable = f"test-smart-contracts-disable-{int(time.time()*1000)}"
        disable_result = blockchain.governance_executor.execute_proposal(
            proposal_id_disable,
            {
                "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
                "feature_name": "smart_contracts",
                "enabled": False,
            },
        )
        assert disable_result["success"]
        blockchain.sync_smart_contract_vm()
        assert blockchain.smart_contract_manager is None
    finally:
        if prev_flag is None:
            Config.FEATURE_FLAGS.pop("vm", None)
        else:
            Config.FEATURE_FLAGS["vm"] = prev_flag


"""
Interface for blockchain data needed by the governance module.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

class GovernanceBlockchainInterface:
    """
    Interface for blockchain methods needed by the governance execution engine.
    """
    @property
    def difficulty(self) -> int:
        raise NotImplementedError

    @difficulty.setter
    def difficulty(self, value: int):
        raise NotImplementedError

    @property
    def initial_block_reward(self) -> float:
        raise NotImplementedError

    @initial_block_reward.setter
    def initial_block_reward(self, value: float):
        raise NotImplementedError

    @property
    def transaction_fee_percent(self) -> float:
        raise NotImplementedError

    @transaction_fee_percent.setter
    def transaction_fee_percent(self, value: float):
        raise NotImplementedError

    @property
    def halving_interval(self) -> int:
        raise NotImplementedError

    @halving_interval.setter
    def halving_interval(self, value: int):
        raise NotImplementedError

    @property
    def airdrop_manager(self) -> Any:
        raise NotImplementedError

    @property
    def governance_state(self) -> Any:
        raise NotImplementedError

    @property
    def chain(self) -> List[Any]:
        raise NotImplementedError

    @property
    def security_manager(self) -> Any:
        raise NotImplementedError

    @property
    def transactions_paused(self) -> bool:
        raise NotImplementedError

    @transactions_paused.setter
    def transactions_paused(self, value: bool):
        raise NotImplementedError

    @property
    def pending_transactions(self) -> List[Any]:
        raise NotImplementedError

    def get_transaction_by_id(self, tx_id: str) -> Optional[Any]:
        raise NotImplementedError

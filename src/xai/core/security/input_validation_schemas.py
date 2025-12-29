from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, confloat, conint, constr


class NodeTransactionInput(BaseModel):
    sender: str
    recipient: str
    amount: float
    fee: float = 0.0
    public_key: str
    nonce: int
    timestamp: float
    signature: str
    txid: str | None = Field(default=None, min_length=64, max_length=64)
    metadata: dict[str, Any] | None = None

class PeerTransactionInput(BaseModel):
    sender: str
    recipient: str
    amount: float
    fee: float = 0.0
    public_key: str
    tx_type: str
    nonce: int
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    timestamp: float | None = None
    signature: str
    txid: str | None = None
    metadata: dict[str, Any] | None = None

class FaucetClaimInput(BaseModel):
    address: str

class PeerBlockInput(BaseModel):
    index: int
    timestamp: float
    transactions: list[PeerTransactionInput]
    previous_hash: str
    merkle_root: str
    nonce: int
    hash: str
    difficulty: int

class PeerAddInput(BaseModel):
    url: constr(min_length=1)

class RecoverySetupInput(BaseModel):
    owner_address: str
    guardians: list[str]
    threshold: conint(gt=0)
    signature: str

class RecoveryRequestInput(BaseModel):
    owner_address: str
    new_address: str
    guardian_address: str
    signature: str

class RecoveryVoteInput(BaseModel):
    request_id: str
    guardian_address: str
    signature: str

class RecoveryCancelInput(BaseModel):
    request_id: str
    owner_address: str
    signature: str

class RecoveryExecuteInput(BaseModel):
    request_id: str
    executor_address: str

class CryptoDepositAddressInput(BaseModel):
    user_address: str
    currency: str

class ExchangeOrderInput(BaseModel):
    address: str
    order_type: str
    pair: str
    price: float
    amount: float

class ExchangeTransferInput(BaseModel):
    from_address: str
    to_address: str
    currency: str
    amount: float
    destination: str | None = None

class ExchangeCancelInput(BaseModel):
    order_id: str

class ExchangeCardPurchaseInput(BaseModel):
    from_address: str
    to_address: str
    usd_amount: float
    email: str
    card_id: str
    user_id: str
    payment_token: str

class TreasureCreateInput(BaseModel):
    creator: str
    amount: confloat(gt=0)
    puzzle_type: str
    puzzle_data: dict[str, Any]
    hint: str | None = None

class TreasureClaimInput(BaseModel):
    treasure_id: str
    claimer: str
    solution: str

class MiningRegisterInput(BaseModel):
    address: str

class MiningBonusClaimInput(BaseModel):
    address: str
    bonus_type: str

class ReferralCreateInput(BaseModel):
    address: str

class ReferralUseInput(BaseModel):
    new_address: str
    referral_code: str
    metadata: dict[str, Any] | None = None

class FraudCheckInput(BaseModel):
    payload: dict[str, Any]

class ContractDeployInput(BaseModel):
    sender: str
    bytecode: str
    gas_limit: int
    value: float = 0.0
    fee: float = 0.0
    public_key: str
    nonce: int | None = None
    signature: str
    metadata: dict[str, Any] | None = None
    
class ContractCallInput(BaseModel):
    sender: str
    contract_address: str
    payload: dict[str, Any] | None = None
    data: str | None = None
    gas_limit: int
    value: float = 0.0
    fee: float = 0.0
    public_key: str
    nonce: int | None = None
    signature: str
    metadata: dict[str, Any] | None = None

class ContractFeatureToggleInput(BaseModel):
    enabled: bool
    reason: str | None = None

from pydantic import BaseModel, Field, conint, constr, confloat
from typing import List, Optional, Dict, Any

class NodeTransactionInput(BaseModel):
    sender: str
    recipient: str
    amount: float
    fee: float = 0.0
    public_key: str
    nonce: int
    signature: str
    metadata: Optional[Dict[str, Any]] = None

class PeerTransactionInput(BaseModel):
    sender: str
    recipient: str
    amount: float
    fee: float = 0.0
    public_key: str
    tx_type: str
    nonce: int
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    timestamp: Optional[float] = None
    signature: str
    txid: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FaucetClaimInput(BaseModel):
    address: str

class PeerBlockInput(BaseModel):
    index: int
    timestamp: float
    transactions: List[PeerTransactionInput]
    previous_hash: str
    merkle_root: str
    nonce: int
    hash: str
    difficulty: int

class PeerAddInput(BaseModel):
    url: constr(min_length=1)

class RecoverySetupInput(BaseModel):
    owner_address: str
    guardians: List[str]
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
    destination: Optional[str] = None

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
    puzzle_data: Dict[str, Any]
    hint: Optional[str] = None

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

class FraudCheckInput(BaseModel):
    payload: Dict[str, Any]

class ContractDeployInput(BaseModel):
    sender: str
    bytecode: str
    gas_limit: int
    value: float = 0.0
    fee: float = 0.0
    public_key: str
    nonce: Optional[int] = None
    signature: str
    metadata: Optional[Dict[str, Any]] = None
    
class ContractCallInput(BaseModel):
    sender: str
    contract_address: str
    payload: Optional[Dict[str, Any]] = None
    data: Optional[str] = None
    gas_limit: int
    value: float = 0.0
    fee: float = 0.0
    public_key: str
    nonce: Optional[int] = None
    signature: str
    metadata: Optional[Dict[str, Any]] = None

class ContractFeatureToggleInput(BaseModel):
    enabled: bool
    reason: Optional[str] = None

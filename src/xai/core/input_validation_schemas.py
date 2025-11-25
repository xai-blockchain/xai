"""
XAI Blockchain - Comprehensive Input Validation Schemas

This module provides Pydantic models for strict input validation across all API endpoints.
Implements defense-in-depth validation with type checking, range validation, and format verification.

Security features:
- Type checking with Pydantic
- Range and length validation
- Format validation for addresses, hashes, signatures
- Cryptographic input validation
- Protection against injection attacks
- Request size limits
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator, RootModel
import re
import json
import time
from datetime import datetime

from xai.core.security_validation import SecurityValidator, ValidationError as SecurityValidationError
from xai.core.config import Config


# ==================== TRANSACTION VALIDATION ====================


class NodeTransactionInput(BaseModel):
    """Strict validation for the public /send endpoint payload."""

    sender: str = Field(..., min_length=10, max_length=120, description="Sender address")
    recipient: str = Field(..., min_length=10, max_length=120, description="Recipient address")
    amount: float = Field(..., gt=0, description="Amount denominated in XAI")
    fee: float = Field(default=0.0, ge=0, description="Transaction fee")
    public_key: str = Field(..., min_length=64, max_length=130, description="Hex-encoded public key")
    signature: str = Field(..., min_length=96, max_length=256, description="Hex-encoded signature")
    nonce: Optional[int] = Field(default=None, ge=0, description="Replay-protection nonce")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")

    @validator('sender')
    def validate_sender(cls, value: str):
        try:
            return SecurityValidator.validate_address(value, 'sender')
        except SecurityValidationError as exc:  # pragma: no cover - delegated logic
            raise ValueError(str(exc))

    @validator('recipient')
    def validate_recipient(cls, value: str):
        try:
            return SecurityValidator.validate_address(value, 'recipient')
        except SecurityValidationError as exc:
            raise ValueError(str(exc))

    @validator('amount')
    def enforce_amount(cls, value: float):
        try:
            return SecurityValidator.validate_amount(value, 'amount')
        except SecurityValidationError as exc:
            raise ValueError(str(exc))

    @validator('fee')
    def enforce_fee(cls, value: float):
        try:
            return SecurityValidator.validate_fee(value)
        except SecurityValidationError as exc:
            raise ValueError(str(exc))

    @validator('public_key')
    def validate_public_key(cls, value: str):
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('public_key must be hexadecimal')
        if len(value) not in (66, 128, 130):
            raise ValueError('public_key length is invalid')
        return value.lower()

    @validator('signature')
    def validate_signature(cls, value: str):
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        if len(value) < 96:
            raise ValueError('signature too short')
        if len(value) > 512:
            raise ValueError('signature too long')
        return value.lower()

    @validator('metadata')
    def validate_metadata(cls, value: Optional[Dict[str, Any]]):
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError('metadata must be an object')
        serialized = json.dumps(value)
        if len(serialized) > 4096:
            raise ValueError('metadata is too large')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class PeerTransactionInput(NodeTransactionInput):
    """Validation for transactions received from peers."""

    tx_type: str = Field(default='normal', max_length=32)
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: Optional[float] = Field(default=None)
    txid: Optional[str] = Field(default=None, min_length=64, max_length=64)

    @validator('tx_type')
    def validate_tx_type(cls, value: str) -> str:
        allowed = {'normal', 'airdrop', 'treasure', 'refund', 'timecapsule', 'contract_call', 'contract_deploy'}
        value = value.strip().lower()
        if value not in allowed:
            raise ValueError(f"tx_type must be one of: {', '.join(sorted(allowed))}")
        return value

    @validator('txid')
    def validate_txid(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]{64}', value):
            raise ValueError('txid must be hexadecimal')
        return value.lower()

    @validator('inputs', 'outputs')
    def validate_io(cls, value: List[Dict[str, Any]]):
        if len(value) > 1000:
            raise ValueError('Too many inputs/outputs supplied')
        return value


def _validate_contract_address(value: str) -> str:
    try:
        return SecurityValidator.validate_address(value, 'contract_address')
    except SecurityValidationError as exc:
        raise ValueError(str(exc))


class ContractAuthenticationInput(BaseModel):
    """Base authentication schema shared by contract endpoints."""

    sender: str = Field(..., min_length=10, max_length=120)
    public_key: str = Field(..., min_length=64, max_length=130, description="Hex-encoded public key")
    signature: str = Field(..., min_length=96, max_length=512, description="Hex-encoded signature")
    nonce: Optional[int] = Field(default=None, ge=0)
    fee: float = Field(default=0.0, ge=0.0)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @validator('sender')
    def validate_sender_address(cls, value: str) -> str:
        try:
            return SecurityValidator.validate_address(value, 'sender')
        except SecurityValidationError as exc:
            raise ValueError(str(exc))

    @validator('public_key')
    def validate_public_key(cls, value: str) -> str:
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('public_key must be hexadecimal')
        if len(value) not in (66, 128, 130):
            raise ValueError('public_key length is invalid')
        return value.lower()

    @validator('signature')
    def validate_signature(cls, value: str) -> str:
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        if len(value) < 96:
            raise ValueError('signature too short')
        if len(value) > 512:
            raise ValueError('signature too long')
        return value.lower()

    @validator('metadata')
    def validate_metadata(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError('metadata must be an object')
        serialized = json.dumps(value)
        if len(serialized) > 4096:
            raise ValueError('metadata is too large')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ContractDeployInput(ContractAuthenticationInput):
    """Validation for contract deployment requests."""

    value: float = Field(default=0.0, ge=0.0)
    gas_limit: int = Field(
        default=100000,
        ge=21000,
        le=Config.MAX_CONTRACT_GAS,
        description="Gas cap for deployment",
    )
    bytecode: str = Field(..., min_length=2, description="Hex-encoded contract bytecode")

    @validator('bytecode')
    def validate_bytecode(cls, value: str) -> str:
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('bytecode must be hexadecimal')
        if len(value) % 2 != 0:
            raise ValueError('bytecode must contain whole bytes')
        if len(value) > 16384:
            raise ValueError('bytecode exceeds maximum size')
        return value.lower()


class ContractCallInput(ContractAuthenticationInput):
    """Validation for contract call invocations."""

    contract_address: str = Field(..., min_length=10)
    value: float = Field(default=0.0, ge=0.0)
    gas_limit: int = Field(
        default=100000,
        ge=21000,
        le=Config.MAX_CONTRACT_GAS,
        description="Gas cap for contract call",
    )
    payload: Optional[Dict[str, Any]] = Field(default=None)
    data: Optional[str] = Field(default=None, description="Hex-encoded payload data")

    @validator('contract_address')
    def sanitize_contract_address(cls, value: str) -> str:
        return _validate_contract_address(value)

    @validator('data')
    def validate_data_hex(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('data must be hexadecimal')
        if len(value) % 2 != 0:
            raise ValueError('data must contain whole bytes')
        if len(value) > 8192:
            raise ValueError('data exceeds maximum size')
        return value.lower()

    @root_validator(skip_on_failure=True)
    def ensure_payload_or_data(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get('payload') and not values.get('data'):
            raise ValueError('Either payload or hex data must be provided')
        if values.get('payload') and values.get('data'):
            raise ValueError('Provide only one of payload or data')
        return values
class FaucetClaimInput(BaseModel):
    """Validation for faucet claim requests."""

    address: str = Field(..., min_length=4, max_length=120)

    @validator('address')
    def sanitize_address(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Address cannot be empty')
        if not re.fullmatch(r'[A-Za-z0-9]+', value):
            raise ValueError('Address must be alphanumeric')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


# ==================== RECOVERY VALIDATION ====================


def _validate_address(value: str, field_name: str) -> str:
    try:
        return SecurityValidator.validate_address(value, field_name)
    except SecurityValidationError as exc:
        raise ValueError(str(exc))


class RecoverySetupInput(BaseModel):
    owner_address: str
    guardians: List[str]
    threshold: int = Field(..., ge=1, le=50)
    signature: Optional[str] = Field(default=None, min_length=96, max_length=512)

    @validator('owner_address')
    def validate_owner(cls, value: str) -> str:
        return _validate_address(value, 'owner_address')

    @validator('guardians')
    def validate_guardians(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError('guardians list cannot be empty')
        unique = []
        for guardian in value:
            addr = _validate_address(guardian, 'guardian_address')
            if addr not in unique:
                unique.append(addr)
        return unique

    @validator('signature')
    def validate_signature(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        return value.lower()

    @root_validator(skip_on_failure=True)
    def ensure_threshold(cls, values):
        threshold = values.get('threshold')
        guardians = values.get('guardians') or []
        if threshold and guardians and threshold > len(guardians):
            raise ValueError('threshold cannot exceed number of guardians')
        return values

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class RecoveryRequestInput(BaseModel):
    owner_address: str
    new_address: str
    guardian_address: str
    signature: Optional[str] = Field(default=None, min_length=96, max_length=512)

    @validator('owner_address')
    def validate_owner(cls, value: str) -> str:
        return _validate_address(value, 'owner_address')

    @validator('new_address')
    def validate_new(cls, value: str) -> str:
        return _validate_address(value, 'new_address')

    @validator('guardian_address')
    def validate_guardian(cls, value: str) -> str:
        return _validate_address(value, 'guardian_address')

    @validator('signature')
    def validate_signature(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        return value.lower()

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class RecoveryVoteInput(BaseModel):
    request_id: str = Field(..., min_length=3, max_length=128)
    guardian_address: str
    signature: Optional[str] = Field(default=None, min_length=96, max_length=512)

    @validator('guardian_address')
    def validate_guardian(cls, value: str) -> str:
        return _validate_address(value, 'guardian_address')

    @validator('signature')
    def validate_signature(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        return value.lower()

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class RecoveryCancelInput(BaseModel):
    request_id: str = Field(..., min_length=3, max_length=128)
    owner_address: str
    signature: Optional[str] = Field(default=None, min_length=96, max_length=512)

    @validator('owner_address')
    def validate_owner(cls, value: str) -> str:
        return _validate_address(value, 'owner_address')

    @validator('signature')
    def validate_signature(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]+', value):
            raise ValueError('signature must be hexadecimal')
        return value.lower()

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class RecoveryExecuteInput(BaseModel):
    request_id: str = Field(..., min_length=3, max_length=128)
    executor_address: Optional[str] = None

    @validator('executor_address')
    def validate_executor(cls, value: Optional[str]):
        if value is None:
            return value
        return _validate_address(value, 'executor_address')

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


# ==================== CRYPTO DEPOSIT VALIDATION ====================


class CryptoDepositAddressInput(BaseModel):
    user_address: str
    currency: str = Field(..., min_length=2, max_length=10)

    @validator('user_address')
    def validate_user_address(cls, value: str) -> str:
        return _validate_address(value, 'user_address')

    @validator('currency')
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{2,10}', value):
            raise ValueError('currency must be alphanumeric (2-10 chars)')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ExchangeOrderInput(BaseModel):
    address: str
    order_type: str
    price: float = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    pair: str = Field(default="AXN/USD", min_length=3, max_length=15)

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    @validator('order_type')
    def validate_order_type(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"buy", "sell"}:
            raise ValueError('order_type must be "buy" or "sell"')
        return value

    @validator('pair')
    def validate_pair(cls, value: str) -> str:
        if '/' not in value:
            raise ValueError('pair must be in BASE/QUOTE format')
        base, quote = value.split('/', 1)
        if not re.fullmatch(r'[A-Z0-9]{2,6}', base.upper()) or not re.fullmatch(r'[A-Z0-9]{2,6}', quote.upper()):
            raise ValueError('invalid pair format')
        return f"{base.upper()}/{quote.upper()}"

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ExchangeTransferInput(BaseModel):
    address: str
    currency: str = Field(..., min_length=2, max_length=10)
    amount: float = Field(..., gt=0)
    destination: Optional[str] = None

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    @validator('currency')
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{2,10}', value):
            raise ValueError('currency must be alphanumeric (2-10 chars)')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ExchangeCancelInput(BaseModel):
    order_id: str = Field(..., min_length=5, max_length=128)

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ExchangeCardPurchaseInput(BaseModel):
    address: str
    usd_amount: float = Field(..., gt=0)
    email: str = Field(..., max_length=255)
    card_token: Optional[str] = Field(default=None, max_length=255)

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    @validator('email')
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError('Invalid email format')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


# ==================== GAMIFICATION / MINING VALIDATION ====================


class TreasureCreateInput(BaseModel):
    creator: str
    amount: float = Field(..., gt=0)
    puzzle_type: str = Field(..., min_length=3, max_length=64)
    puzzle_data: str = Field(..., min_length=3, max_length=4096)
    hint: Optional[str] = Field(default="", max_length=512)

    @validator('creator')
    def validate_creator(cls, value: str) -> str:
        return _validate_address(value, 'creator')

    @validator('puzzle_type')
    def validate_type(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_-]{3,64}', value):
            raise ValueError('puzzle_type must be 3-64 chars of a-z, 0-9, _, -')
        return value

    @validator('puzzle_data')
    def validate_data(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError('puzzle_data must be at least 3 characters')
        if len(value) > 4096:
            raise ValueError('puzzle_data too large (max 4096 chars)')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class TreasureClaimInput(BaseModel):
    treasure_id: str = Field(..., min_length=3, max_length=128)
    claimer: str
    solution: str = Field(..., min_length=1, max_length=2048)

    @validator('claimer')
    def validate_claimer(cls, value: str) -> str:
        return _validate_address(value, 'claimer')

    @validator('solution')
    def validate_solution(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('solution cannot be empty')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class MiningRegisterInput(BaseModel):
    address: str

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class MiningBonusClaimInput(BaseModel):
    address: str
    bonus_type: str = Field(..., min_length=3, max_length=64)

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    @validator('bonus_type')
    def validate_bonus(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_-]{3,64}', value):
            raise ValueError('bonus_type must be alphanumeric/underscore/hyphen (3-64 chars)')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ReferralCreateInput(BaseModel):
    address: str

    @validator('address')
    def validate_address(cls, value: str) -> str:
        return _validate_address(value, 'address')

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class ReferralUseInput(BaseModel):
    new_address: str
    referral_code: str = Field(..., min_length=3, max_length=64)

    @validator('new_address')
    def validate_new_address(cls, value: str) -> str:
        return _validate_address(value, 'new_address')

    @validator('referral_code')
    def validate_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{3,64}', value):
            raise ValueError('referral_code must be alphanumeric (3-64 chars)')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class PeerBlockInput(BaseModel):
    index: int = Field(..., ge=0)
    previous_hash: str = Field(..., min_length=64, max_length=64)
    difficulty: int = Field(default=4, ge=0, le=64)
    nonce: int = Field(default=0, ge=0)
    timestamp: float = Field(default_factory=time.time)
    hash: Optional[str] = Field(default=None, min_length=64, max_length=64)
    merkle_root: Optional[str] = Field(default=None, min_length=64, max_length=64)
    transactions: List[Dict[str, Any]] = Field(default_factory=list)

    @validator('previous_hash', 'hash', 'merkle_root')
    def validate_hash(cls, value: Optional[str]):
        if value is None:
            return value
        if not re.fullmatch(r'[0-9a-fA-F]{64}', value):
            raise ValueError('hash fields must be 64 hex characters')
        return value.lower()

    @validator('transactions')
    def validate_transactions(cls, value: List[Dict[str, Any]]):
        if not isinstance(value, list):
            raise ValueError('transactions must be a list')
        if len(value) > 5000:
            raise ValueError('transactions list too large')
        return value

    class Config:
        extra = 'allow'
        anystr_strip_whitespace = True


class PeerAddInput(BaseModel):
    url: str = Field(..., min_length=6, max_length=255)

    @validator('url')
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not re.match(r'^https?://', value):
            raise ValueError('url must start with http:// or https://')
        if any(part in value for part in ['\\', ' ']):
            raise ValueError('url cannot contain spaces or backslashes')
        return value

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True


class FraudCheckInput(RootModel[Dict[str, Any]]):
    @validator('root')
    def validate_payload(cls, value: Dict[str, Any]):
        if not isinstance(value, dict) or not value:
            raise ValueError('Fraud check payload must be a non-empty object')
        serialized = json.dumps(value)
        if len(serialized) > 10000:
            raise ValueError('Fraud check payload too large (max 10KB)')
        return value

    @property
    def payload(self) -> Dict[str, Any]:
        return self.root

    pass

class TransactionInput(BaseModel):
    """Validate transaction inputs"""

    to: str = Field(..., min_length=26, max_length=34, description="Recipient address")
    amount: float = Field(..., gt=0, le=121000000, description="Amount to send (XAI)")
    fee: Optional[float] = Field(default=0.0, ge=0, le=100000, description="Transaction fee")
    data: Optional[str] = Field(default=None, max_length=1000, description="Transaction data")
    timestamp: Optional[int] = Field(default=None, description="Transaction timestamp")

    @validator('to')
    def validate_address(cls, v):
        """Validate address format"""
        if not isinstance(v, str):
            raise ValueError('Address must be a string')
        # Basic address format check (Base58 without 0, O, I, l)
        if not re.match(r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$', v):
            raise ValueError('Invalid address format')
        return v

    @validator('amount')
    def validate_amount(cls, v):
        """Validate amount is positive and within limits"""
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 121000000:
            raise ValueError('Amount exceeds maximum supply')
        # Check for reasonable precision (max 8 decimal places)
        if len(str(v).split('.')[-1]) > 8:
            raise ValueError('Amount has too many decimal places')
        return v

    @validator('fee')
    def validate_fee(cls, v):
        """Validate fee is reasonable"""
        if v < 0:
            raise ValueError('Fee cannot be negative')
        if v > 100000:
            raise ValueError('Fee is unreasonably high')
        return v

    @validator('data')
    def validate_data(cls, v):
        """Validate transaction data"""
        if v is None:
            return v
        if len(v) > 1000:
            raise ValueError('Data exceeds maximum length')
        # Ensure it's valid hex or string
        try:
            # Try to decode as hex
            bytes.fromhex(v)
        except ValueError:
            # Allow regular strings
            if not isinstance(v, str):
                raise ValueError('Data must be hex string or regular string')
        return v

    class Config:
        schema_extra = {
            "example": {
                "to": "1A1z7agoat2oKMB48sTqxhq61bNmrX5Qe9",
                "amount": 10.5,
                "fee": 0.001,
                "data": "optional_transaction_data"
            }
        }


class SignatureInput(BaseModel):
    """Validate cryptographic signatures"""

    signature: str = Field(..., min_length=128, max_length=256, description="Hex-encoded signature")
    message_hash: str = Field(..., min_length=64, max_length=64, description="SHA256 hash of message")
    public_key: str = Field(..., min_length=64, max_length=130, description="Public key for verification")

    @validator('signature', 'message_hash')
    def validate_hex_string(cls, v):
        """Validate hex string format"""
        if not isinstance(v, str):
            raise ValueError('Must be a string')
        if not re.match(r'^[0-9a-fA-F]*$', v):
            raise ValueError('Must be valid hexadecimal')
        return v.lower()

    @validator('public_key')
    def validate_public_key(cls, v):
        """Validate public key format"""
        if not isinstance(v, str):
            raise ValueError('Public key must be a string')
        if not re.match(r'^[0-9a-fA-F]+$', v):
            raise ValueError('Public key must be hexadecimal')
        if len(v) not in [64, 130]:  # 32 or 65 bytes
            raise ValueError('Invalid public key length')
        return v.lower()

    class Config:
        schema_extra = {
            "example": {
                "signature": "30440220" + "0" * 120,
                "message_hash": "abc123" + "0" * 58,
                "public_key": "04" + "0" * 128
            }
        }


# ==================== WALLET VALIDATION ====================

class WalletCreationInput(BaseModel):
    """Validate wallet creation inputs"""

    name: str = Field(..., min_length=1, max_length=100, description="Wallet name")
    password: str = Field(..., min_length=12, max_length=256, description="Wallet password")
    backup_phrase: Optional[str] = Field(default=None, description="12/24 word mnemonic")

    @validator('name')
    def validate_name(cls, v):
        """Validate wallet name"""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Wallet name contains invalid characters')
        return v

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters')
        # Check for complexity
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numbers')
        return v

    @validator('backup_phrase')
    def validate_backup_phrase(cls, v):
        """Validate BIP39 mnemonic"""
        if v is None:
            return v
        words = v.lower().split()
        if len(words) not in [12, 24]:
            raise ValueError('Backup phrase must be 12 or 24 words')
        # Basic word validation
        if not all(re.match(r'^[a-z]+$', word) for word in words):
            raise ValueError('Backup phrase contains invalid words')
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "My_Wallet_1",
                "password": "SecurePassword123!",
                "backup_phrase": "word1 word2 word3 ... word12"
            }
        }


# ==================== MINING VALIDATION ====================

class MiningInput(BaseModel):
    """Validate mining parameters"""

    miner_address: str = Field(..., min_length=26, max_length=34, description="Miner reward address")
    difficulty: Optional[int] = Field(default=None, ge=1, le=256, description="Mining difficulty")
    max_iterations: Optional[int] = Field(default=None, ge=1, le=1000000, description="Maximum iterations")

    @validator('miner_address')
    def validate_miner_address(cls, v):
        """Validate miner address format"""
        if not re.match(r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$', v):
            raise ValueError('Invalid miner address format')
        return v

    class Config:
        schema_extra = {
            "example": {
                "miner_address": "1A1z7agoat2oKMB48sTqxhq61bNmrX5Qe9",
                "difficulty": 4,
                "max_iterations": 10000
            }
        }


# ==================== API KEY VALIDATION ====================

class APIKeyInput(BaseModel):
    """Validate API key creation/management"""

    key_name: str = Field(..., min_length=3, max_length=50, description="API key name")
    expiration_days: Optional[int] = Field(default=90, ge=1, le=3650, description="Expiration in days")
    allowed_endpoints: Optional[List[str]] = Field(default=None, description="Allowed endpoints")
    rate_limit: Optional[int] = Field(default=1000, ge=1, le=100000, description="Requests per hour")

    @validator('key_name')
    def validate_key_name(cls, v):
        """Validate API key name"""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError('Key name contains invalid characters')
        return v

    @validator('allowed_endpoints')
    def validate_endpoints(cls, v):
        """Validate allowed endpoints"""
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError('Endpoints must be a list')
        if len(v) > 50:
            raise ValueError('Too many endpoints specified')
        # Validate endpoint format
        for endpoint in v:
            if not re.match(r'^/[a-zA-Z0-9\-_/]*$', endpoint):
                raise ValueError(f'Invalid endpoint format: {endpoint}')
        return v

    class Config:
        schema_extra = {
            "example": {
                "key_name": "production-api-key",
                "expiration_days": 90,
                "allowed_endpoints": ["/send", "/balance", "/blocks"],
                "rate_limit": 5000
            }
        }


# ==================== PEER VALIDATION ====================

class PeerInput(BaseModel):
    """Validate peer connection parameters"""

    host: str = Field(..., min_length=7, max_length=253, description="Peer hostname or IP")
    port: int = Field(..., ge=1024, le=65535, description="Peer port number")
    tls_enabled: Optional[bool] = Field(default=True, description="Use TLS for connection")

    @validator('host')
    def validate_host(cls, v):
        """Validate hostname/IP format"""
        # Allow IPv4, IPv6, and hostnames
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
        hostname_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

        if re.match(ipv4_pattern, v):
            # Validate IPv4 ranges
            parts = [int(x) for x in v.split('.')]
            if all(0 <= part <= 255 for part in parts):
                return v
        elif re.match(ipv6_pattern, v):
            return v
        elif re.match(hostname_pattern, v) or v in ['localhost', '127.0.0.1']:
            return v

        raise ValueError('Invalid host format')

    class Config:
        schema_extra = {
            "example": {
                "host": "peer.example.com",
                "port": 8333,
                "tls_enabled": True
            }
        }


# ==================== QUERY VALIDATION ====================

class BlockQueryInput(BaseModel):
    """Validate block query parameters"""

    block_height: Optional[int] = Field(default=None, ge=0, description="Block height")
    block_hash: Optional[str] = Field(default=None, min_length=64, max_length=64, description="Block hash")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Result limit")
    offset: Optional[int] = Field(default=0, ge=0, le=1000000, description="Result offset")

    @validator('block_hash')
    def validate_block_hash(cls, v):
        """Validate block hash format"""
        if v is None:
            return v
        if not re.match(r'^[0-9a-fA-F]{64}$', v):
            raise ValueError('Invalid block hash format')
        return v.lower()

    @root_validator(skip_on_failure=True)
    def validate_query(cls, values):
        """Ensure at least one query parameter is provided"""
        if values.get('block_height') is None and values.get('block_hash') is None:
            # Allow for listing blocks
            pass
        return values

    class Config:
        schema_extra = {
            "example": {
                "block_height": 12345,
                "limit": 100,
                "offset": 0
            }
        }


# ==================== GOVERNANCE VALIDATION ====================

class GovernanceProposalInput(BaseModel):
    """Validate governance proposal inputs"""

    title: str = Field(..., min_length=5, max_length=200, description="Proposal title")
    description: str = Field(..., min_length=20, max_length=5000, description="Proposal description")
    proposal_type: str = Field(..., description="Proposal type")
    voting_period: Optional[int] = Field(default=604800, ge=3600, le=31536000, description="Voting period in seconds")

    @validator('title')
    def validate_title(cls, v):
        """Validate proposal title"""
        if not re.match(r'^[a-zA-Z0-9\s\-.,!?:]+$', v):
            raise ValueError('Title contains invalid characters')
        return v

    @validator('proposal_type')
    def validate_proposal_type(cls, v):
        """Validate proposal type"""
        valid_types = [
            'parameter_change',
            'security_update',
            'feature_proposal',
            'emergency_action',
            'funding_request'
        ]
        if v not in valid_types:
            raise ValueError(f'Invalid proposal type. Must be one of: {", ".join(valid_types)}')
        return v

    class Config:
        schema_extra = {
            "example": {
                "title": "Increase Mining Reward",
                "description": "Proposal to increase mining rewards by 10%...",
                "proposal_type": "parameter_change",
                "voting_period": 604800
            }
        }


# ==================== RATE LIMIT VALIDATION ====================

class RateLimitConfigInput(BaseModel):
    """Validate rate limit configuration"""

    endpoint: str = Field(..., min_length=1, max_length=200, description="API endpoint path")
    max_requests: int = Field(..., ge=1, le=1000000, description="Maximum requests")
    time_window_seconds: int = Field(..., ge=1, le=2592000, description="Time window in seconds (max 30 days)")

    @validator('endpoint')
    def validate_endpoint(cls, v):
        """Validate endpoint format"""
        if not re.match(r'^/[a-zA-Z0-9\-_/]*$', v):
            raise ValueError('Invalid endpoint format')
        return v

    class Config:
        schema_extra = {
            "example": {
                "endpoint": "/api/transactions",
                "max_requests": 1000,
                "time_window_seconds": 3600
            }
        }


# ==================== BATCH OPERATIONS ====================

class BatchTransactionInput(BaseModel):
    """Validate batch transaction operations"""

    transactions: List[TransactionInput] = Field(..., min_items=1, max_items=100, description="Batch transactions")

    @validator('transactions')
    def validate_batch_size(cls, v):
        """Validate batch size"""
        if len(v) > 100:
            raise ValueError('Batch size exceeds maximum of 100 transactions')
        return v

    class Config:
        schema_extra = {
            "example": {
                "transactions": [
                    {
                        "to": "1A1z7agoat2oKMB48sTqxhq61bNmrX5Qe9",
                        "amount": 10.5,
                        "fee": 0.001
                    }
                ]
            }
        }


# ==================== EXPORT FOR CONVENIENCE ====================

VALIDATION_SCHEMAS = {
    'transaction': TransactionInput,
    'signature': SignatureInput,
    'wallet_creation': WalletCreationInput,
    'mining': MiningInput,
    'api_key': APIKeyInput,
    'peer': PeerInput,
    'block_query': BlockQueryInput,
    'governance_proposal': GovernanceProposalInput,
    'rate_limit_config': RateLimitConfigInput,
    'batch_transactions': BatchTransactionInput,
}

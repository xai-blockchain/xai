"""
XAI Blockchain Node Utilities
Shared utility functions, helper methods, and constants for the blockchain node.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
import yaml


# ==================== CONSTANTS ====================

ALGO_FEATURES_ENABLED: bool = bool(int(os.getenv("XAI_ALGO_FEATURES", "0")))
NODE_VERSION: str = "2.0.0"
# Security fix: Use environment variable with secure default (127.0.0.1)
DEFAULT_HOST: str = os.getenv("XAI_DEFAULT_HOST", "127.0.0.1")
DEFAULT_PORT: int = int(os.getenv("XAI_DEFAULT_PORT", "8545"))
DEFAULT_MINER_ADDRESS: str = "DEFAULT_MINER"


# ==================== CONFIGURATION UTILITIES ====================


def get_allowed_origins() -> List[str]:
    """
    Get allowed CORS origins from configuration file.

    Returns:
        List of allowed origin URLs, empty list if config not found

    Example:
        >>> origins = get_allowed_origins()
        >>> print(origins)
        ['http://localhost:12080', 'https://app.xai.io']
    """
    cors_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cors.yaml")
    if os.path.exists(cors_config_path):
        with open(cors_config_path, "r") as f:
            cors_config = yaml.safe_load(f)
            return cors_config.get("origins", [])
    return []


def get_base_dir() -> str:
    """
    Get the base directory for blockchain data storage.

    Returns:
        Absolute path to the blockchain data directory

    Example:
        >>> base_dir = get_base_dir()
        >>> print(base_dir)
        '/path/to/Crypto/blockchain_data'
    """
    # Get project root (3 levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    base_dir = os.path.join(project_root, "blockchain_data")

    # Ensure directory exists
    os.makedirs(base_dir, exist_ok=True)

    return base_dir


# ==================== RESPONSE FORMATTING ====================


def format_success_response(data: Dict[str, Any], message: str = "") -> Dict[str, Any]:
    """
    Format a success API response.

    Args:
        data: Response data dictionary
        message: Optional success message

    Returns:
        Formatted response dictionary with success flag

    Example:
        >>> response = format_success_response({"balance": 100}, "Balance retrieved")
        >>> print(response)
        {'success': True, 'balance': 100, 'message': 'Balance retrieved'}
    """
    response: Dict[str, Any] = {"success": True, **data}
    if message:
        response["message"] = message
    return response


def format_error_response(error: str, status_code: int = 400) -> Dict[str, Any]:
    """
    Format an error API response.

    Args:
        error: Error message
        status_code: HTTP status code

    Returns:
        Formatted error dictionary

    Example:
        >>> response = format_error_response("Invalid address", 400)
        >>> print(response)
        {'success': False, 'error': 'Invalid address', 'status_code': 400}
    """
    return {"success": False, "error": error, "status_code": status_code}


# ==================== VALIDATION UTILITIES ====================


def is_valid_address(address: str) -> bool:
    """
    Validate blockchain address format.

    Args:
        address: Address string to validate

    Returns:
        True if address format is valid

    Example:
        >>> is_valid_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        True
        >>> is_valid_address("invalid")
        False
    """
    if not address or not isinstance(address, str):
        return False

    # Allow special addresses
    if address in ["COINBASE", "SYSTEM", "AIRDROP", DEFAULT_MINER_ADDRESS]:
        return True

    # Basic validation: length and characters
    # In production, this would use proper Base58Check validation
    if len(address) < 10 or len(address) > 100:
        return False

    return True


def is_valid_amount(amount: float) -> bool:
    """
    Validate transaction amount.

    Args:
        amount: Amount to validate

    Returns:
        True if amount is valid (positive number)

    Example:
        >>> is_valid_amount(10.5)
        True
        >>> is_valid_amount(-5)
        False
    """
    if not isinstance(amount, (int, float)):
        return False

    return amount > 0


def is_valid_order_type(order_type: str) -> bool:
    """
    Validate exchange order type.

    Args:
        order_type: Order type string

    Returns:
        True if order type is valid

    Example:
        >>> is_valid_order_type("buy")
        True
        >>> is_valid_order_type("invalid")
        False
    """
    return order_type in ["buy", "sell"]


def is_valid_currency(currency: str) -> bool:
    """
    Validate currency code.

    Args:
        currency: Currency code to validate

    Returns:
        True if currency is supported

    Example:
        >>> is_valid_currency("AXN")
        True
        >>> is_valid_currency("INVALID")
        False
    """
    supported_currencies = ["AXN", "BTC", "ETH", "USDT", "USD"]
    return currency in supported_currencies


def is_valid_trading_pair(pair: str) -> bool:
    """
    Validate trading pair format.

    Args:
        pair: Trading pair string (e.g., "AXN/USD")

    Returns:
        True if trading pair format is valid

    Example:
        >>> is_valid_trading_pair("AXN/USD")
        True
        >>> is_valid_trading_pair("INVALID")
        False
    """
    if "/" not in pair:
        return False

    parts = pair.split("/")
    if len(parts) != 2:
        return False

    base, quote = parts
    return is_valid_currency(base) and is_valid_currency(quote)


# ==================== DATA UTILITIES ====================


def calculate_block_reward(block_index: int) -> float:
    """
    Calculate mining reward for a given block height.

    Implements halving every 210,000 blocks (similar to Bitcoin).

    Args:
        block_index: Height of the block in the chain

    Returns:
        Block reward amount in AXN

    Example:
        >>> calculate_block_reward(0)
        50.0
        >>> calculate_block_reward(210000)
        25.0
    """
    initial_reward: float = 50.0
    halving_interval: int = 210000

    halvings = block_index // halving_interval
    reward = initial_reward / (2**halvings)

    # Minimum reward
    return max(reward, 0.00000001)


def calculate_difficulty(chain_length: int, target_block_time: float = 60.0) -> int:
    """
    Calculate mining difficulty based on blockchain state.

    Args:
        chain_length: Current length of the blockchain
        target_block_time: Target time between blocks in seconds

    Returns:
        Difficulty value (number of leading zeros required)

    Example:
        >>> calculate_difficulty(0)
        2
        >>> calculate_difficulty(1000)
        3
    """
    # Start with difficulty 2
    base_difficulty = 2

    # Increase difficulty every 100 blocks
    adjustment_interval = 100
    difficulty_increment = chain_length // adjustment_interval

    # Maximum difficulty of 6
    return min(base_difficulty + difficulty_increment, 6)


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
    """
    Validate that all required fields are present in data dictionary.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Returns:
        Error message if validation fails, None if successful

    Example:
        >>> data = {"name": "Alice", "age": 30}
        >>> validate_required_fields(data, ["name", "age"])
        None
        >>> validate_required_fields(data, ["name", "email"])
        'Missing required fields: email'
    """
    if not data:
        return "No data provided"

    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"

    return None


def paginate_list(items: List[Any], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """
    Paginate a list of items.

    Args:
        items: List of items to paginate
        limit: Maximum number of items per page
        offset: Starting index for pagination

    Returns:
        Dictionary with pagination info and items

    Example:
        >>> items = list(range(100))
        >>> result = paginate_list(items, limit=10, offset=20)
        >>> result['total']
        100
        >>> len(result['items'])
        10
    """
    total = len(items)
    paginated_items = items[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paginated_items,
        "has_more": offset + limit < total,
    }


# ==================== TIME UTILITIES ====================


def get_timestamp() -> float:
    """
    Get current timestamp.

    Returns:
        Current Unix timestamp as float

    Example:
        >>> timestamp = get_timestamp()
        >>> isinstance(timestamp, float)
        True
    """
    import time

    return time.time()


def format_timestamp(timestamp: float) -> str:
    """
    Format Unix timestamp to human-readable string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted datetime string

    Example:
        >>> format_timestamp(1234567890.0)
        '2009-02-13 23:31:30'
    """
    from datetime import datetime

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_timestamp_recent(timestamp: float, max_age_seconds: float = 300.0) -> bool:
    """
    Check if timestamp is within specified age.

    Args:
        timestamp: Unix timestamp to check
        max_age_seconds: Maximum age in seconds

    Returns:
        True if timestamp is recent enough

    Example:
        >>> import time
        >>> is_timestamp_recent(time.time())
        True
        >>> is_timestamp_recent(0)
        False
    """
    current_time = get_timestamp()
    age = current_time - timestamp
    return 0 <= age <= max_age_seconds


# ==================== ENDPOINT DOCUMENTATION ====================


def get_api_endpoints() -> Dict[str, str]:
    """
    Get dictionary of all API endpoints with descriptions.

    Returns:
        Dictionary mapping endpoint paths to descriptions
    """
    return {
        # Core endpoints
        "/": "GET - Node information and available endpoints",
        "/health": "GET - Health check for monitoring",
        "/metrics": "GET - Prometheus metrics",
        "/stats": "GET - Blockchain statistics",
        # Blockchain endpoints
        "/blocks": "GET - All blocks (paginated)",
        "/blocks/<index>": "GET - Specific block by index",
        "/transactions": "GET - Pending transactions",
        "/transaction/<txid>": "GET - Transaction details",
        # Wallet endpoints
        "/balance/<address>": "GET - Address balance",
        "/history/<address>": "GET - Transaction history",
        "/send": "POST - Send transaction",
        "/faucet/claim": "POST - Claim testnet faucet distribution",
        # Mining endpoints
        "/mine": "POST - Mine pending transactions",
        "/auto-mine/start": "POST - Start automatic mining",
        "/auto-mine/stop": "POST - Stop automatic mining",
        # P2P endpoints
        "/peers": "GET - Connected peers",
        "/peers/add": "POST - Add peer node",
        "/sync": "POST - Sync with network",
        # Algorithmic features
        "/algo/fee-estimate": "GET - Algorithmic fee recommendation",
        "/algo/fraud-check": "POST - Fraud detection analysis",
        "/algo/status": "GET - Algorithmic features status",
        # Gamification
        "/airdrop/winners": "GET - Recent airdrop winners",
        "/airdrop/user/<address>": "GET - Airdrop history for address",
        "/mining/streaks": "GET - Mining streak leaderboard",
        "/mining/streak/<address>": "GET - Mining streak for address",
        "/treasure/active": "GET - Active treasure hunts",
        "/treasure/create": "POST - Create treasure hunt",
        "/treasure/claim": "POST - Claim treasure by solving puzzle",
        "/treasure/details/<id>": "GET - Treasure hunt details",
        "/timecapsule/create": "POST - Create time-locked transaction",
        "/timecapsule/pending": "GET - List pending time capsules",
        "/timecapsule/<address>": "GET - User time capsules",
        "/refunds/stats": "GET - Fee refund statistics",
        "/refunds/<address>": "GET - Fee refund history",
        # Social recovery
        "/recovery/setup": "POST - Set up guardians for wallet",
        "/recovery/request": "POST - Request recovery to new address",
        "/recovery/vote": "POST - Guardian votes on recovery",
        "/recovery/status/<address>": "GET - Check recovery status",
        "/recovery/cancel": "POST - Cancel pending recovery",
        "/recovery/execute": "POST - Execute approved recovery",
        "/recovery/config/<address>": "GET - Get recovery configuration",
        "/recovery/guardian/<address>": "GET - Get guardian duties",
        "/recovery/requests": "GET - Get all recovery requests",
        "/recovery/stats": "GET - Social recovery statistics",
        # Mining bonuses
        "/mining/register": "POST - Register miner",
        "/mining/achievements/<address>": "GET - Mining achievements",
        "/mining/claim-bonus": "POST - Claim social bonus",
        "/mining/referral/create": "POST - Create referral code",
        "/mining/referral/use": "POST - Use referral code",
        "/mining/user-bonuses/<address>": "GET - Get user bonuses",
        "/mining/leaderboard": "GET - Mining bonus leaderboard",
        "/mining/stats": "GET - Mining bonus statistics",
        # Exchange endpoints
        "/exchange/orders": "GET - Current order book",
        "/exchange/place-order": "POST - Place buy/sell order",
        "/exchange/cancel-order": "POST - Cancel open order",
        "/exchange/my-orders/<address>": "GET - Get user orders",
        "/exchange/trades": "GET - Recent executed trades",
        "/exchange/price-history": "GET - Historical price data",
        "/exchange/stats": "GET - Exchange statistics",
        "/exchange/deposit": "POST - Deposit funds",
        "/exchange/withdraw": "POST - Withdraw funds",
        "/exchange/balance/<address>": "GET - User exchange balances",
        "/exchange/balance/<address>/<currency>": "GET - Currency balance",
        "/exchange/transactions/<address>": "GET - Transaction history",
        "/exchange/buy-with-card": "POST - Buy AXN with card",
        "/exchange/payment-methods": "GET - Supported payment methods",
        "/exchange/calculate-purchase": "POST - Calculate purchase amount",
        # Crypto deposits
        "/exchange/crypto/generate-address": "POST - Generate deposit address",
        "/exchange/crypto/addresses/<address>": "GET - Get deposit addresses",
        "/exchange/crypto/pending-deposits": "GET - Pending crypto deposits",
        "/exchange/crypto/deposit-history/<address>": "GET - Deposit history",
        "/exchange/crypto/stats": "GET - Crypto deposit statistics",
    }

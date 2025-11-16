"""
XAI Atomic Swap Protocol
HTLC-based atomic swaps for cross-chain trading
Free market pricing - no restrictions
"""

import hashlib
import time
from typing import Dict, Optional, Tuple
from enum import Enum
import secrets


class CoinType(Enum):
    """Supported coins for atomic swaps"""

    BTC = "Bitcoin"
    ETH = "Ethereum"
    LTC = "Litecoin"
    DOGE = "Dogecoin"
    XMR = "Monero"
    BCH = "BitcoinCash"
    USDT = "Tether"
    ZEC = "Zcash"
    DASH = "Dash"
    USDC = "USDCoin"
    DAI = "Dai"


class SwapProtocol(Enum):
    """Different protocols for different coin types"""

    HTLC_UTXO = "htlc_utxo"
    HTLC_ETHEREUM = "htlc_ethereum"
    HTLC_MONERO = "htlc_monero"


# Map coins to their protocols
COIN_PROTOCOLS = {
    CoinType.BTC: SwapProtocol.HTLC_UTXO,
    CoinType.LTC: SwapProtocol.HTLC_UTXO,
    CoinType.DOGE: SwapProtocol.HTLC_UTXO,
    CoinType.BCH: SwapProtocol.HTLC_UTXO,
    CoinType.ZEC: SwapProtocol.HTLC_UTXO,
    CoinType.DASH: SwapProtocol.HTLC_UTXO,
    CoinType.ETH: SwapProtocol.HTLC_ETHEREUM,
    CoinType.USDT: SwapProtocol.HTLC_ETHEREUM,
    CoinType.USDC: SwapProtocol.HTLC_ETHEREUM,
    CoinType.DAI: SwapProtocol.HTLC_ETHEREUM,
    CoinType.XMR: SwapProtocol.HTLC_MONERO,
}


class AtomicSwapHTLC:
    """
    Hash Time Locked Contract for Atomic Swaps
    """

    def __init__(self, coin_type: CoinType):
        self.coin_type = coin_type
        self.protocol = COIN_PROTOCOLS[coin_type]

    def create_swap_contract(
        self,
        axn_amount: float,
        other_coin_amount: float,
        counterparty_address: str,
        timelock_hours: int = 24,
    ) -> Dict:
        """
        Create a new atomic swap contract

        Args:
            axn_amount: Amount of XAI to swap
            other_coin_amount: Amount of other coin to receive
            counterparty_address: Address of trading partner
            timelock_hours: Hours until refund becomes available

        Returns:
            dict: Swap contract details
        """

        # Generate secret for HTLC
        secret = secrets.token_bytes(32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Calculate timelock (Unix timestamp)
        timelock = int(time.time()) + (timelock_hours * 3600)

        # Create contract based on protocol
        if self.protocol == SwapProtocol.HTLC_UTXO:
            contract = self._create_utxo_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )
        elif self.protocol == SwapProtocol.HTLC_ETHEREUM:
            contract = self._create_ethereum_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )
        elif self.protocol == SwapProtocol.HTLC_MONERO:
            contract = self._create_monero_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )

        contract.update(
            {
                "success": True,
                "secret": secret.hex(),  # Sender keeps this secret
                "secret_hash": secret_hash,
                "axn_amount": axn_amount,
                "other_coin": self.coin_type.name,
                "other_coin_amount": other_coin_amount,
                "timelock": timelock,
                "timelock_hours": timelock_hours,
            }
        )

        return contract

    def _create_utxo_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for UTXO-based coins
        (BTC, LTC, DOGE, BCH, ZEC, DASH)

        Bitcoin Script pseudocode:
        OP_IF
            OP_SHA256 <secret_hash> OP_EQUALVERIFY
            <recipient_pubkey> OP_CHECKSIG
        OP_ELSE
            <timelock> OP_CHECKLOCKTIMEVERIFY OP_DROP
            <sender_pubkey> OP_CHECKSIG
        OP_ENDIF
        """

        return {
            "contract_type": "HTLC_UTXO",
            "script_template": f"""
                OP_IF
                    OP_SHA256 {secret_hash} OP_EQUALVERIFY
                    {recipient} OP_CHECKSIG
                OP_ELSE
                    {timelock} OP_CHECKLOCKTIMEVERIFY OP_DROP
                    <sender_address> OP_CHECKSIG
                OP_ENDIF
            """,
            "claim_method": "Reveal secret to claim",
            "refund_method": f"Wait until {timelock} then claim refund",
            "supported_coins": ["BTC", "LTC", "DOGE", "BCH", "ZEC", "DASH"],
        }

    def _create_ethereum_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for Ethereum-based tokens
        (ETH, USDT, USDC, DAI)

        Solidity smart contract required
        """

        solidity_contract = f"""
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;

        contract AtomicSwapETH {{
            bytes32 public secretHash = 0x{secret_hash};
            address public recipient = {recipient};
            uint256 public timelock = {timelock};
            uint256 public amount = {amount} ether;

            function claim(bytes32 secret) external {{
                require(sha256(abi.encodePacked(secret)) == secretHash, "Invalid secret");
                require(msg.sender == recipient, "Not recipient");
                payable(recipient).transfer(amount);
            }}

            function refund() external {{
                require(block.timestamp >= timelock, "Timelock not expired");
                payable(msg.sender).transfer(amount);
            }}
        }}
        """

        return {
            "contract_type": "HTLC_ETHEREUM",
            "smart_contract": solidity_contract,
            "claim_method": "Call claim(secret) function",
            "refund_method": f"Call refund() after {timelock}",
            "supported_tokens": ["ETH", "USDT", "USDC", "DAI"],
            "gas_estimate": "~150,000 gas for claim, ~50,000 for refund",
        }

    def _create_monero_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for Monero (XMR)

        Monero requires special protocol:
        1. Use view keys for verification
        2. Adaptor signatures for atomicity
        3. Different cryptography (Ed25519)

        This is complex and requires Monero-specific implementation
        """

        return {
            "contract_type": "HTLC_MONERO",
            "protocol": "Adaptor Signatures + View Keys",
            "claim_method": "Submit adaptor signature with secret",
            "refund_method": f"Reclaim after timelock {timelock}",
            "supported_coins": ["XMR"],
            "complexity": "HIGH - Requires Monero daemon integration",
            "note": "Privacy-preserving atomic swaps using ring signatures",
        }

    def verify_swap_claim(
        self, secret: str, secret_hash: str, contract_data: Dict
    ) -> Tuple[bool, str]:
        """
        Verify that counterparty can claim their side of swap

        Args:
            secret: Revealed secret (hex string)
            secret_hash: Expected hash of secret
            contract_data: Contract details

        Returns:
            tuple: (is_valid, message)
        """

        # Verify secret matches hash
        revealed_hash = hashlib.sha256(bytes.fromhex(secret)).hexdigest()

        if revealed_hash != secret_hash:
            return False, "Secret does not match hash"

        # Check if timelock expired
        if time.time() > contract_data["timelock"]:
            return False, "Timelock expired - refund period active"

        return True, "Valid claim - swap can proceed"

    def get_supported_coins(self) -> Dict:
        """Get all supported coins"""

        return {
            "BTC": {"name": "Bitcoin", "protocol": "HTLC_UTXO"},
            "ETH": {"name": "Ethereum", "protocol": "HTLC_ETHEREUM"},
            "LTC": {"name": "Litecoin", "protocol": "HTLC_UTXO"},
            "DOGE": {"name": "Dogecoin", "protocol": "HTLC_UTXO"},
            "XMR": {"name": "Monero", "protocol": "HTLC_MONERO"},
            "BCH": {"name": "Bitcoin Cash", "protocol": "HTLC_UTXO"},
            "USDT": {"name": "Tether", "protocol": "HTLC_ETHEREUM"},
            "ZEC": {"name": "Zcash", "protocol": "HTLC_UTXO"},
            "DASH": {"name": "Dash", "protocol": "HTLC_UTXO"},
            "USDC": {"name": "USD Coin", "protocol": "HTLC_ETHEREUM"},
            "DAI": {"name": "Dai", "protocol": "HTLC_ETHEREUM"},
        }


# Trading pair manager
class MeshDEXPairManager:
    """Manages trading pairs"""

    def __init__(self):
        self.supported_pairs = self._initialize_pairs()

    def _initialize_pairs(self) -> Dict:
        """Initialize trading pairs"""

        pairs = {}
        for coin in CoinType:
            pair_name = f"XAI/{coin.name}"
            pairs[pair_name] = {
                "coin_type": coin,
                "protocol": COIN_PROTOCOLS[coin],
                "atomic_swap": AtomicSwapHTLC(coin),
                "active": True,
                "launch_phase": self._get_launch_phase(coin),
            }

        return pairs

    def _get_launch_phase(self, coin: CoinType) -> str:
        """Determine launch phase for each coin"""

        # Phase 1: UTXO coins (easiest to implement)
        phase1 = [
            CoinType.BTC,
            CoinType.LTC,
            CoinType.DOGE,
            CoinType.BCH,
            CoinType.ZEC,
            CoinType.DASH,
        ]

        # Phase 2: Ethereum tokens (requires bridge)
        phase2 = [CoinType.ETH, CoinType.USDT, CoinType.USDC, CoinType.DAI]

        # Phase 3: Monero (complex)
        phase3 = [CoinType.XMR]

        if coin in phase1:
            return "PHASE_1_LAUNCH"
        elif coin in phase2:
            return "PHASE_2_MONTH_3"
        elif coin in phase3:
            return "PHASE_3_MONTH_6"

    def create_swap(
        self, pair: str, axn_amount: float, other_amount: float, counterparty: str
    ) -> Dict:
        """
        Create atomic swap for any of the 11 pairs

        Args:
            pair: Trading pair (e.g., "XAI/BTC")
            axn_amount: Amount of XAI
            other_amount: Amount of other coin
            counterparty: Counterparty address

        Returns:
            dict: Swap contract details
        """

        if pair not in self.supported_pairs:
            return {
                "success": False,
                "error": "UNSUPPORTED_PAIR",
                "message": f"Pair {pair} not supported. Supported: {list(self.supported_pairs.keys())}",
            }

        pair_data = self.supported_pairs[pair]

        if not pair_data["active"]:
            return {
                "success": False,
                "error": "PAIR_INACTIVE",
                "message": f'Pair {pair} is not yet active. Launch phase: {pair_data["launch_phase"]}',
            }

        # Create atomic swap
        swap = pair_data["atomic_swap"].create_swap_contract(
            axn_amount=axn_amount, other_coin_amount=other_amount, counterparty_address=counterparty
        )

        return swap

    def get_all_pairs(self) -> Dict:
        """Get information about all 11 trading pairs"""

        result = {}
        for pair_name, pair_data in self.supported_pairs.items():
            coin = pair_data["coin_type"]
            result[pair_name] = {
                "coin": coin.value,
                "protocol": pair_data["protocol"].value,
                "active": pair_data["active"],
                "launch_phase": pair_data["launch_phase"],
            }

        return result


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("XAI Atomic Swap System")
    print("=" * 70)

    # Initialize DEX
    dex = MeshDEXPairManager()

    # Show supported pairs
    print("\nSupported Trading Pairs:")
    print("-" * 70)

    for pair, info in dex.get_all_pairs().items():
        status = "ACTIVE" if info["active"] else "INACTIVE"
        print(f"{pair:15} | {info['coin']:20} | {info['protocol']:20} | {status}")

    # Show supported coins
    print("\n\nSupported Coins:")
    print("-" * 70)

    btc_swap = AtomicSwapHTLC(CoinType.BTC)
    all_coins = btc_swap.get_supported_coins()

    for symbol, coin_data in all_coins.items():
        print(f"{symbol}: {coin_data['name']} ({coin_data['protocol']})")

    # Test creating a swap
    print("\n\nExample: Creating XAI/BTC Atomic Swap")
    print("-" * 70)

    swap_result = dex.create_swap(
        pair="XAI/BTC",
        axn_amount=1000,
        other_amount=0.005,
        counterparty="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    )

    if swap_result["success"]:
        print("Swap created successfully")
        print(f"Secret Hash: {swap_result['secret_hash'][:32]}...")
        print(f"Timelock: {swap_result['timelock_hours']} hours")
    else:
        print(f"Swap failed: {swap_result['message']}")

    # Test another swap (free market - no restrictions)
    print("\n\nSecond Swap Test (Free Market)")
    print("-" * 70)

    test_swap = dex.create_swap(
        pair="XAI/BTC",
        axn_amount=1000,
        other_amount=0.0038,
        counterparty="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    )

    if test_swap["success"]:
        print("Swap created successfully (no price restrictions)")
        print(f"Secret Hash: {test_swap['secret_hash'][:32]}...")
    else:
        print(f"Swap failed: {test_swap.get('message', 'Unknown error')}")

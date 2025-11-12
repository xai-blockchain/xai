"""
AXN Crypto Deposit Manager - Automated BTC/ETH/USDT Deposit Processing
Generates unique deposit addresses and monitors blockchain for incoming transactions
"""

import os
import json
import time
import hashlib
import requests
from decimal import Decimal
from typing import Dict, List, Optional
from threading import Thread, Lock


class CryptoDepositAddress:
    """Represents a unique deposit address for a user"""

    def __init__(self, user_address: str, currency: str, deposit_address: str):
        self.user_address = user_address  # AXN address
        self.currency = currency  # BTC, ETH, USDT
        self.deposit_address = deposit_address  # External crypto address
        self.created_at = time.time()
        self.total_deposited = Decimal('0')
        self.last_checked = 0

    def to_dict(self) -> dict:
        return {
            'user_address': self.user_address,
            'currency': self.currency,
            'deposit_address': self.deposit_address,
            'created_at': self.created_at,
            'total_deposited': float(self.total_deposited),
            'last_checked': self.last_checked
        }


class CryptoDepositManager:
    """Manages crypto deposit addresses and monitors blockchain for deposits"""

    def __init__(self, exchange_wallet_manager, data_dir: str = 'crypto_deposits'):
        self.exchange_wallet_manager = exchange_wallet_manager
        self.data_dir = data_dir
        self.deposit_addresses: Dict[str, List[CryptoDepositAddress]] = {}
        self.pending_deposits: List[dict] = []
        self.confirmed_deposits: List[dict] = []
        self.lock = Lock()

        # Master wallet addresses (exchange's hot wallets)
        self.master_wallets = {
            'BTC': os.getenv('BTC_MASTER_WALLET'),
            'ETH': os.getenv('ETH_MASTER_WALLET'),
            'USDT': os.getenv('USDT_MASTER_WALLET')  # ERC-20 USDT uses ETH address
        }

        # Blockchain API endpoints (using public explorers for now)
        self.blockchain_apis = {
            'BTC': 'https://blockchain.info',
            'ETH': 'https://api.etherscan.io/api',
            'USDT': 'https://api.etherscan.io/api'
        }

        # API keys (if available)
        self.etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', '')

        # Confirmation requirements
        self.required_confirmations = {
            'BTC': 6,      # ~60 minutes
            'ETH': 12,     # ~3 minutes
            'USDT': 12,    # ~3 minutes (ERC-20)
            'LTC': 6,      # ~15 minutes
            'BNB': 15,     # ~45 seconds (BSC is fast)
            'SOL': 32,     # ~13 seconds (Solana is very fast)
            'XRP': 1,      # ~4 seconds (XRP is instant)
            'DOGE': 6,     # ~6 minutes
            'SHIB': 12,    # ~3 minutes (ERC-20)
            'MATIC': 128,  # ~4 minutes (Polygon PoS)
            'DOT': 2,      # ~12 seconds
            'AVAX': 1,     # ~2 seconds (Avalanche C-Chain)
            'LINK': 12,    # ~3 minutes (ERC-20)
            'UNI': 12,     # ~3 minutes (ERC-20)
            'ADA': 15      # ~5 minutes
        }

        # Monitoring interval (seconds)
        self.monitor_interval = 60  # Check every 60 seconds
        self.monitoring_active = False

        self.load_data()

    def generate_deposit_address(self, user_address: str, currency: str) -> dict:
        """
        Generate unique deposit address for user

        For production: Use HD wallets (BIP32/BIP44) to generate real addresses
        For now: Use deterministic address generation from user_address
        """

        supported_currencies = ['BTC', 'ETH', 'USDT', 'LTC', 'BNB', 'SOL', 'XRP',
                               'DOGE', 'SHIB', 'MATIC', 'DOT', 'AVAX', 'LINK', 'UNI', 'ADA']

        if currency not in supported_currencies:
            return {'success': False, 'error': f'Unsupported currency: {currency}'}

        # Check if user already has deposit address for this currency
        with self.lock:
            if user_address in self.deposit_addresses:
                for addr in self.deposit_addresses[user_address]:
                    if addr.currency == currency:
                        return {
                            'success': True,
                            'deposit_address': addr.deposit_address,
                            'currency': currency,
                            'user_address': user_address,
                            'message': 'Existing deposit address',
                            'required_confirmations': self.required_confirmations[currency]
                        }

            # Generate new deposit address
            # NOTE: In production, use proper HD wallet derivation
            # For now, create deterministic address from hash
            seed = f"{user_address}_{currency}_{time.time()}"
            address_hash = hashlib.sha256(seed.encode()).hexdigest()

            if currency in ['BTC', 'LTC', 'DOGE']:
                # Bitcoin-like addresses (Bech32 format for BTC/LTC, base58 for DOGE)
                if currency == 'BTC':
                    deposit_address = f"bc1q{address_hash[:40]}"  # Bitcoin Bech32
                elif currency == 'LTC':
                    deposit_address = f"ltc1q{address_hash[:40]}"  # Litecoin Bech32
                elif currency == 'DOGE':
                    deposit_address = f"D{address_hash[:33]}"  # Dogecoin starts with D
            elif currency in ['ETH', 'USDT', 'SHIB', 'MATIC', 'LINK', 'UNI']:
                # Ethereum and ERC-20 tokens use same address format
                deposit_address = f"0x{address_hash[:40]}"
            elif currency == 'BNB':
                # Binance Smart Chain (similar to Ethereum)
                deposit_address = f"0x{address_hash[:40]}"
            elif currency == 'SOL':
                # Solana addresses (base58, 32-44 chars)
                deposit_address = f"{address_hash[:44]}"  # Simplified
            elif currency == 'XRP':
                # Ripple addresses start with 'r'
                deposit_address = f"r{address_hash[:33]}"
            elif currency == 'DOT':
                # Polkadot addresses (SS58 format, starts with 1)
                deposit_address = f"1{address_hash[:47]}"
            elif currency == 'AVAX':
                # Avalanche C-Chain (Ethereum-compatible)
                deposit_address = f"0x{address_hash[:40]}"
            elif currency == 'ADA':
                # Cardano addresses (Bech32, starts with addr1)
                deposit_address = f"addr1{address_hash[:55]}"

            # Create deposit address object
            addr_obj = CryptoDepositAddress(user_address, currency, deposit_address)

            if user_address not in self.deposit_addresses:
                self.deposit_addresses[user_address] = []

            self.deposit_addresses[user_address].append(addr_obj)
            self.save_data()

            return {
                'success': True,
                'deposit_address': deposit_address,
                'currency': currency,
                'user_address': user_address,
                'message': 'New deposit address generated',
                'required_confirmations': self.required_confirmations[currency],
                'warning': '⚠️ TESTNET: These are demo addresses. In production, use real HD wallet addresses.'
            }

    def get_user_deposit_addresses(self, user_address: str) -> dict:
        """Get all deposit addresses for a user"""
        with self.lock:
            addresses = self.deposit_addresses.get(user_address, [])
            return {
                'success': True,
                'user_address': user_address,
                'deposit_addresses': [addr.to_dict() for addr in addresses]
            }

    def check_btc_deposits(self, deposit_address: str) -> List[dict]:
        """Check Bitcoin blockchain for deposits to address"""
        try:
            # Using blockchain.info API
            url = f"{self.blockchain_apis['BTC']}/rawaddr/{deposit_address}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            transactions = []

            for tx in data.get('txs', []):
                # Check outputs for deposits to our address
                for out in tx.get('out', []):
                    if out.get('addr') == deposit_address:
                        transactions.append({
                            'tx_hash': tx['hash'],
                            'amount': Decimal(str(out['value'])) / Decimal('100000000'),  # Satoshis to BTC
                            'confirmations': tx.get('block_height', 0),
                            'timestamp': tx.get('time', time.time())
                        })

            return transactions

        except Exception as e:
            print(f"Error checking BTC deposits: {e}")
            return []

    def check_eth_deposits(self, deposit_address: str) -> List[dict]:
        """Check Ethereum blockchain for deposits to address"""
        try:
            # Using Etherscan API
            url = f"{self.blockchain_apis['ETH']}"
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': deposit_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'apikey': self.etherscan_api_key
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            transactions = []

            if data.get('status') == '1':
                for tx in data.get('result', []):
                    if tx.get('to', '').lower() == deposit_address.lower():
                        transactions.append({
                            'tx_hash': tx['hash'],
                            'amount': Decimal(tx['value']) / Decimal('1000000000000000000'),  # Wei to ETH
                            'confirmations': tx.get('confirmations', 0),
                            'timestamp': int(tx.get('timeStamp', time.time()))
                        })

            return transactions

        except Exception as e:
            print(f"Error checking ETH deposits: {e}")
            return []

    def check_usdt_deposits(self, deposit_address: str) -> List[dict]:
        """Check USDT (ERC-20) deposits to address"""
        try:
            # USDT contract address on Ethereum
            usdt_contract = '0xdac17f958d2ee523a2206206994597c13d831ec7'

            url = f"{self.blockchain_apis['USDT']}"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': usdt_contract,
                'address': deposit_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'apikey': self.etherscan_api_key
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            transactions = []

            if data.get('status') == '1':
                for tx in data.get('result', []):
                    if tx.get('to', '').lower() == deposit_address.lower():
                        transactions.append({
                            'tx_hash': tx['hash'],
                            'amount': Decimal(tx['value']) / Decimal('1000000'),  # USDT has 6 decimals
                            'confirmations': tx.get('confirmations', 0),
                            'timestamp': int(tx.get('timeStamp', time.time()))
                        })

            return transactions

        except Exception as e:
            print(f"Error checking USDT deposits: {e}")
            return []

    def monitor_deposits(self):
        """Main monitoring loop - checks all deposit addresses for new transactions"""
        print("🔍 Crypto deposit monitoring started...")

        while self.monitoring_active:
            try:
                with self.lock:
                    all_addresses = []
                    for user_addrs in self.deposit_addresses.values():
                        all_addresses.extend(user_addrs)

                print(f"Checking {len(all_addresses)} deposit addresses...")

                for addr in all_addresses:
                    # Check blockchain for deposits
                    if addr.currency == 'BTC':
                        transactions = self.check_btc_deposits(addr.deposit_address)
                    elif addr.currency == 'ETH':
                        transactions = self.check_eth_deposits(addr.deposit_address)
                    elif addr.currency == 'USDT':
                        transactions = self.check_usdt_deposits(addr.deposit_address)
                    else:
                        continue

                    # Process new deposits
                    for tx in transactions:
                        if tx['confirmations'] >= self.required_confirmations[addr.currency]:
                            self._process_confirmed_deposit(addr, tx)
                        else:
                            self._track_pending_deposit(addr, tx)

                    addr.last_checked = time.time()

                # Save state
                self.save_data()

            except Exception as e:
                print(f"Error in deposit monitoring: {e}")

            # Wait before next check
            time.sleep(self.monitor_interval)

    def _track_pending_deposit(self, addr: CryptoDepositAddress, tx: dict):
        """Track pending deposit (not enough confirmations yet)"""
        tx_id = f"{tx['tx_hash']}_{addr.deposit_address}"

        # Check if already tracked
        for pending in self.pending_deposits:
            if pending['tx_id'] == tx_id:
                pending['confirmations'] = tx['confirmations']
                return

        # Add to pending
        self.pending_deposits.append({
            'tx_id': tx_id,
            'tx_hash': tx['tx_hash'],
            'user_address': addr.user_address,
            'currency': addr.currency,
            'amount': float(tx['amount']),
            'confirmations': tx['confirmations'],
            'required_confirmations': self.required_confirmations[addr.currency],
            'timestamp': tx['timestamp']
        })

        print(f"⏳ Pending deposit: {tx['amount']} {addr.currency} ({tx['confirmations']}/{self.required_confirmations[addr.currency]} confirmations)")

    def _process_confirmed_deposit(self, addr: CryptoDepositAddress, tx: dict):
        """Process confirmed deposit - credit user's exchange wallet"""
        tx_id = f"{tx['tx_hash']}_{addr.deposit_address}"

        # Check if already processed
        for confirmed in self.confirmed_deposits:
            if confirmed['tx_id'] == tx_id:
                return  # Already credited

        # Credit user's exchange wallet
        result = self.exchange_wallet_manager.deposit(
            user_address=addr.user_address,
            currency=addr.currency,
            amount=float(tx['amount']),
            deposit_type='crypto_deposit',
            tx_hash=tx['tx_hash']
        )

        if result['success']:
            # Mark as confirmed
            self.confirmed_deposits.append({
                'tx_id': tx_id,
                'tx_hash': tx['tx_hash'],
                'user_address': addr.user_address,
                'currency': addr.currency,
                'amount': float(tx['amount']),
                'confirmations': tx['confirmations'],
                'credited_at': time.time(),
                'transaction': result.get('transaction', {})
            })

            # Remove from pending
            self.pending_deposits = [p for p in self.pending_deposits if p['tx_id'] != tx_id]

            # Update total deposited
            addr.total_deposited += tx['amount']

            print(f"✅ Credited: {tx['amount']} {addr.currency} to {addr.user_address}")
            print(f"   TX: {tx['tx_hash']}")
        else:
            print(f"❌ Failed to credit deposit: {result.get('error')}")

    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.monitoring_active:
            print("⚠️ Monitoring already active")
            return

        self.monitoring_active = True
        monitor_thread = Thread(target=self.monitor_deposits, daemon=True)
        monitor_thread.start()
        print("✅ Crypto deposit monitoring started in background")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        print("🛑 Crypto deposit monitoring stopped")

    def get_pending_deposits(self, user_address: Optional[str] = None) -> List[dict]:
        """Get pending deposits (optionally filtered by user)"""
        with self.lock:
            if user_address:
                return [p for p in self.pending_deposits if p['user_address'] == user_address]
            return self.pending_deposits.copy()

    def get_deposit_history(self, user_address: str, limit: int = 50) -> List[dict]:
        """Get confirmed deposit history for user"""
        with self.lock:
            user_deposits = [
                d for d in self.confirmed_deposits
                if d['user_address'] == user_address
            ]
            user_deposits.sort(key=lambda x: x['credited_at'], reverse=True)
            return user_deposits[:limit]

    def save_data(self):
        """Save deposit data to disk"""
        os.makedirs(self.data_dir, exist_ok=True)

        # Save deposit addresses
        addresses_file = os.path.join(self.data_dir, 'deposit_addresses.json')
        addresses_data = {}
        for user_addr, addrs in self.deposit_addresses.items():
            addresses_data[user_addr] = [addr.to_dict() for addr in addrs]

        with open(addresses_file, 'w') as f:
            json.dump(addresses_data, f, indent=2)

        # Save pending deposits
        pending_file = os.path.join(self.data_dir, 'pending_deposits.json')
        with open(pending_file, 'w') as f:
            json.dump(self.pending_deposits, f, indent=2)

        # Save confirmed deposits (keep last 10000)
        confirmed_file = os.path.join(self.data_dir, 'confirmed_deposits.json')
        with open(confirmed_file, 'w') as f:
            json.dump(self.confirmed_deposits[-10000:], f, indent=2)

    def load_data(self):
        """Load deposit data from disk"""
        addresses_file = os.path.join(self.data_dir, 'deposit_addresses.json')
        pending_file = os.path.join(self.data_dir, 'pending_deposits.json')
        confirmed_file = os.path.join(self.data_dir, 'confirmed_deposits.json')

        # Load deposit addresses
        if os.path.exists(addresses_file):
            with open(addresses_file, 'r') as f:
                addresses_data = json.load(f)

            for user_addr, addrs in addresses_data.items():
                self.deposit_addresses[user_addr] = []
                for addr_data in addrs:
                    addr = CryptoDepositAddress(
                        addr_data['user_address'],
                        addr_data['currency'],
                        addr_data['deposit_address']
                    )
                    addr.created_at = addr_data['created_at']
                    addr.total_deposited = Decimal(str(addr_data['total_deposited']))
                    addr.last_checked = addr_data['last_checked']
                    self.deposit_addresses[user_addr].append(addr)

        # Load pending deposits
        if os.path.exists(pending_file):
            with open(pending_file, 'r') as f:
                self.pending_deposits = json.load(f)

        # Load confirmed deposits
        if os.path.exists(confirmed_file):
            with open(confirmed_file, 'r') as f:
                self.confirmed_deposits = json.load(f)

    def get_stats(self) -> dict:
        """Get deposit statistics"""
        total_addresses = sum(len(addrs) for addrs in self.deposit_addresses.values())

        volume_by_currency = {}
        for deposit in self.confirmed_deposits:
            currency = deposit['currency']
            volume_by_currency[currency] = volume_by_currency.get(currency, 0) + deposit['amount']

        return {
            'total_users': len(self.deposit_addresses),
            'total_deposit_addresses': total_addresses,
            'pending_deposits': len(self.pending_deposits),
            'confirmed_deposits': len(self.confirmed_deposits),
            'volume_by_currency': volume_by_currency,
            'monitoring_active': self.monitoring_active,
            'last_check': max([addr.last_checked for addrs in self.deposit_addresses.values() for addr in addrs], default=0)
        }

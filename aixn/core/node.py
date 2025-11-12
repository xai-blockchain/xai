"""
XAI Blockchain Node - Full node implementation
Runs blockchain, mines blocks, handles transactions, P2P communication
"""

import json
import time
import threading
import requests
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from blockchain import Blockchain, Transaction
from ai_metrics import metrics
from wallet import Wallet, WalletManager
from social_recovery import SocialRecoveryManager
from mining_bonuses import MiningBonusManager
from exchange_wallet import ExchangeWalletManager
from crypto_deposit_manager import CryptoDepositManager
from trading import SwapOrderType
from wallet_trade_manager import WalletTradeManager
import sys
import os
from datetime import datetime, timezone
from hardware_wallet import HardwareWalletManager
from light_client_service import LightClientService
from mobile_wallet_bridge import MobileWalletBridge
from mobile_cache import MobileCacheService

AI_BLOCKCHAIN_DIR = os.path.join(os.path.dirname(__file__), '..', 'aixn-blockchain')
if AI_BLOCKCHAIN_DIR not in sys.path:
    sys.path.insert(0, AI_BLOCKCHAIN_DIR)

from ai_governance_dao import AIGovernanceDAO
from blockchain_ai_bridge import BlockchainAIBridge
from ai_safety_controls import AISafetyControls
from ai_safety_controls_api import add_safety_control_routes

# Import configuration (testnet/mainnet)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import Config

# Import security modules
from security_validation import SecurityValidator, ValidationError, validate_transaction_data
from rate_limiter import get_rate_limiter
from anonymous_logger import get_logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from fiat_unlock_governance import FiatUnlockGovernance
from aml_compliance import RegulatorDashboard, RiskLevel
from api_security import APISecurityManager, RateLimitExceeded
from account_abstraction import AccountAbstractionManager
from mini_app_registry import MiniAppRegistry

# Import algorithmic features
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from ai.fee_optimizer import AIFeeOptimizer
    from ai.fraud_detector import AIFraudDetector
    ALGO_FEATURES_ENABLED = True
    print("✅ Algorithmic features loaded: Fee Optimizer + Fraud Detector")
except ImportError as e:
    ALGO_FEATURES_ENABLED = False
    print(f"⚠️  Algorithmic features not available: {e}")

class BlockchainNode:
    """Full blockchain node with mining and networking"""

    def __init__(self, host=None, port=None, miner_address=None):
        # Network configuration from environment or defaults
        # Use environment variables for production: XAI_HOST, XAI_PORT
        self.host = host or os.getenv('XAI_HOST', '0.0.0.0')
        self.port = port or int(os.getenv('XAI_PORT', str(Config.DEFAULT_PORT)))
        self.blockchain = Blockchain()
        self.safety_controls = AISafetyControls(self.blockchain)
        self.peers = set()  # Connected peer nodes
        self.is_mining = False
        self.mining_thread = None

        # Initialize security
        self.validator = SecurityValidator()
        self.rate_limiter = get_rate_limiter()
        self.logger = get_logger()
        self.api_security = APISecurityManager()
        self.light_client_service = LightClientService(self.blockchain)

        # Initialize P2P security
        from p2p_security import P2PSecurityManager
        self.p2p_security = P2PSecurityManager()

        # AML/regulator monitoring
        self.regulator_dashboard = RegulatorDashboard(self.blockchain)

        # Initialize algorithmic features
        if ALGO_FEATURES_ENABLED:
            self.fee_optimizer = AIFeeOptimizer()
            self.fraud_detector = AIFraudDetector()
            print("🧠 Algorithmic intelligence initialized")
        else:
            self.fee_optimizer = None
            self.fraud_detector = None

        # Initialize social recovery manager
        self.recovery_manager = SocialRecoveryManager()
        print("Social Recovery system initialized")

        # Initialize mining bonus manager
        self.bonus_manager = MiningBonusManager(data_dir=os.path.join(os.path.dirname(__file__), '..', 'mining_data'))
        print("Mining Bonus system initialized")

        # Initialize exchange wallet manager
        self.exchange_wallet_manager = ExchangeWalletManager(data_dir=os.path.join(os.path.dirname(__file__), '..', 'exchange_data'))
        print("Exchange Wallet system initialized")

        trade_data_dir = os.path.join(os.path.dirname(__file__), '..', 'wallet_trade_data')
        self.wallet_trade_manager = WalletTradeManager(
            exchange_wallet_manager=self.exchange_wallet_manager,
            data_dir=trade_data_dir
        )
        print("Wallet trade engine initialized")

        # Payment/fiat services safety management
        self.card_payments_disabled = True
        governance_dir = os.path.join(Config.DATA_DIR, 'governance')
        governance_path = os.path.join(os.path.dirname(__file__), '..', governance_dir)
        self.fiat_unlock_manager = FiatUnlockGovernance(governance_path)
        self.fiat_rails_unlocked = self.fiat_unlock_manager.is_unlocked()

        # Initialize crypto deposit manager
        self.crypto_deposit_manager = CryptoDepositManager(
            self.exchange_wallet_manager,
            data_dir=os.path.join(os.path.dirname(__file__), '..', 'crypto_deposits')
        )
        self.crypto_deposit_manager.start_monitoring()
        print("Crypto Deposit Manager initialized and monitoring started")

        # Initialize wallet claim system
        from wallet_claim_system import WalletClaimSystem
        self.wallet_claim_system = WalletClaimSystem()

        # Wallet manager for embedded accounts
        wallet_dir = os.path.join(os.path.dirname(__file__), '..', 'wallets')
        self.wallet_manager = WalletManager(data_dir=wallet_dir)
        self.account_abstraction = AccountAbstractionManager(self.wallet_manager)

        # Hardware wallet manager + Ledger integration
        self.hardware_wallet_manager = HardwareWalletManager()
        try:
            from hardware_wallet_ledger import LedgerHardwareWallet
        except ImportError:
            LedgerHardwareWallet = None

        if LedgerHardwareWallet:
            try:
                ledger_wallet = LedgerHardwareWallet()
                ledger_wallet.connect()
                self.hardware_wallet_manager.register_device('ledger', ledger_wallet)
                print("Ledger hardware wallet registered.")
            except Exception as exc:
                print(f"Ledger hardware wallet unavailable: {exc}")

        self.mobile_wallet_bridge = MobileWalletBridge(
            blockchain=self.blockchain,
            validator=self.validator,
            fee_optimizer=getattr(self, 'fee_optimizer', None)
        )
        self.mobile_cache_service = MobileCacheService(self)
        self.mini_app_registry = MiniAppRegistry()

        # Generate unique node ID
        self.node_id = self._generate_node_id()

        # Track node start time for uptime-based wallet assignment
        self.node_start_time = time.time()
        self.uptime_wallet_claimed = False

        # Check for bonus wallet assignment (immediate premium wallets)
        self._check_bonus_wallet()

        # Start uptime wallet checker thread
        self._start_uptime_wallet_checker()

        # Start governance AI bridge
        self.governance_dao = AIGovernanceDAO(self.blockchain)
        self.ai_bridge = BlockchainAIBridge(
            blockchain=self.blockchain,
            governance_dao=self.governance_dao,
            development_pool=self.blockchain.ai_pool
        )
        self._start_ai_bridge_loop()

        # Set up miner wallet
        if miner_address:
            self.miner_address = miner_address
        else:
            # Create default miner wallet
            miner_wallet = Wallet()
            self.miner_address = miner_wallet.address
            print(f"Miner Address: {self.miner_address}")

        # Flask app for API
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        add_safety_control_routes(self.app, self)

    def setup_routes(self):
        """Setup API endpoints"""

        @self.app.before_request
        def enforce_api_security():
            """Apply rate limits and payload validation globally."""
            if request.path.startswith('/ws') or request.path.startswith('/metrics'):
                return
            try:
                self.api_security.enforce_request()
            except RateLimitExceeded as exc:
                return jsonify({'success': False, 'error': 'RATE_LIMIT_EXCEEDED', 'message': str(exc)}), 429
            except ValidationError as exc:
                return jsonify({'success': False, 'error': 'INVALID_REQUEST', 'message': str(exc)}), 400

        # Error handler for validation errors
        @self.app.errorhandler(ValidationError)
        def handle_validation_error(error):
            return jsonify({'error': str(error)}), 400

        @self.app.route('/', methods=['GET'])
        def index():
            return jsonify({
                'status': 'online',
                'node': 'XAI Full Node',
                'version': '2.0.0',
                'algorithmic_features': ALGO_FEATURES_ENABLED,
                'endpoints': {
                    '/stats': 'GET - Blockchain statistics',
                    '/blocks': 'GET - All blocks',
                    '/blocks/<index>': 'GET - Specific block',
                    '/transactions': 'GET - Pending transactions',
                    '/transaction/<txid>': 'GET - Transaction details',
                    '/balance/<address>': 'GET - Address balance',
                    '/history/<address>': 'GET - Transaction history',
                    '/send': 'POST - Send transaction',
                    '/mine': 'POST - Mine pending transactions',
                    '/peers': 'GET - Connected peers',
                    '/sync': 'POST - Sync with network',
                    '/algo/fee-estimate': 'GET - Algorithmic fee recommendation',
                    '/algo/fraud-check': 'POST - Fraud detection analysis',
                    '/algo/status': 'GET - Algorithmic features status',
                    '/airdrop/winners': 'GET - Recent airdrop winners',
                    '/mining/streaks': 'GET - Mining streak leaderboard',
                    '/mining/streak/<address>': 'GET - Mining streak for address',
                    '/treasure/active': 'GET - Active treasure hunts',
                    '/treasure/create': 'POST - Create treasure hunt',
                    '/treasure/claim': 'POST - Claim treasure by solving puzzle',
                    '/treasure/details/<id>': 'GET - Treasure hunt details',
                    '/timecapsule/create': 'POST - Create time-locked transaction',
                    '/timecapsule/pending': 'GET - List pending time capsules',
                    '/timecapsule/<address>': 'GET - User time capsules',
                    '/refunds/stats': 'GET - Fee refund statistics',
                    '/refunds/<address>': 'GET - Fee refund history for address',
                    '/recovery/setup': 'POST - Set up guardians for a wallet',
                    '/recovery/request': 'POST - Request recovery to new address',
                    '/recovery/vote': 'POST - Guardian votes on recovery request',
                    '/recovery/status/<address>': 'GET - Check recovery status',
                    '/recovery/cancel': 'POST - Cancel pending recovery',
                    '/recovery/execute': 'POST - Execute approved recovery after waiting period',
                    '/recovery/config/<address>': 'GET - Get recovery configuration',
                    '/recovery/guardian/<address>': 'GET - Get guardian duties',
                    '/recovery/requests': 'GET - Get all recovery requests',
                    '/recovery/stats': 'GET - Get social recovery statistics',
                    '/mining/register': 'POST - Register miner and check early adopter bonus',
                    '/mining/achievements/<address>': 'GET - Check mining achievements',
                    '/mining/claim-bonus': 'POST - Claim social bonus',
                    '/mining/referral/create': 'POST - Create referral code',
                    '/mining/referral/use': 'POST - Use referral code',
                    '/mining/user-bonuses/<address>': 'GET - Get all bonuses for user',
                    '/mining/leaderboard': 'GET - Mining bonus leaderboard',
                    '/mining/stats': 'GET - Mining bonus system statistics',
                    '/consensus/stats': 'GET - Advanced consensus statistics',
                    '/consensus/finality/<block_index>': 'GET - Block finality information',
                    '/consensus/orphans': 'GET - Orphan block pool statistics',
                    '/consensus/difficulty': 'GET - Difficulty adjustment information',
                    '/consensus/propagation': 'GET - Block propagation statistics',
                    '/consensus/peer-performance': 'GET - Peer performance metrics'
                }
            })

        @self.app.route('/regulator/flagged', methods=['GET'])
        def regulator_flagged_transactions():
            """Expose high-risk transactions to compliance tooling."""
            dashboard = getattr(self, 'regulator_dashboard', None)
            if not dashboard:
                return jsonify({'success': False, 'error': 'REGULATOR_UNAVAILABLE'}), 503
            limit = request.args.get('limit', default=100, type=int)
            min_score = request.args.get('min_score', default=61, type=int)
            flagged = dashboard.get_flagged_transactions(min_score=min_score, limit=limit)
            return jsonify({
                'success': True,
                'flagged_transactions': flagged,
                'min_score': min_score
            })

        @self.app.route('/regulator/high-risk', methods=['GET'])
        def regulator_high_risk():
            """Expose addresses with consistently elevated risk."""
            dashboard = getattr(self, 'regulator_dashboard', None)
            if not dashboard:
                return jsonify({'success': False, 'error': 'REGULATOR_UNAVAILABLE'}), 503
            min_score = request.args.get('min_score', default=70, type=int)
            high_risk = dashboard.get_high_risk_addresses(min_score=min_score)
            return jsonify({
                'success': True,
                'high_risk_addresses': high_risk,
                'min_score': min_score
            })

        @self.app.route('/mini-apps/manifest', methods=['GET'])
        def mini_apps_manifest():
            """Return the mini-app manifest that embeds via iframes or React components."""
            dashboard = getattr(self, 'regulator_dashboard', None)
            registry = getattr(self, 'mini_app_registry', None) or MiniAppRegistry()
            address = request.args.get('address', '').strip()

            risk_context = {
                "address": address,
                "risk_score": 0,
                "risk_level": RiskLevel.CLEAN.value,
                "flag_reasons": [],
                "last_seen": None
            }

            if address:
                try:
                    self.validator.validate_address(address)
                except ValidationError as ve:
                    return jsonify({
                        'success': False,
                        'error': 'INVALID_ADDRESS',
                        'message': str(ve)
                    }), 400
                if dashboard:
                    risk_context = dashboard.get_address_risk_profile(address)

            manifest = registry.build_manifest(risk_context)
            return jsonify({
                'success': True,
                'address': address or None,
                'aml_context': risk_context,
                'mini_apps': manifest,
            })

        @self.app.route('/light-client/headers', methods=['GET'])
        def light_client_headers():
            """Return compact block headers for mobile clients."""
            count = request.args.get('count', default=20, type=int)
            start_index = request.args.get('start', default=None, type=int)
            summary = self.light_client_service.get_recent_headers(count=count, start_index=start_index)
            return jsonify({'success': True, **summary})

        @self.app.route('/light-client/checkpoint', methods=['GET'])
        def light_client_checkpoint():
            """Return the latest checkpoint summary for SPV wallets."""
            checkpoint = self.light_client_service.get_checkpoint()
            return jsonify({'success': True, **checkpoint})

        @self.app.route('/light-client/tx-proof/<txid>', methods=['GET'])
        def light_client_tx_proof(txid):
            """Return a merkle proof for a confirmed transaction."""
            proof = self.light_client_service.get_transaction_proof(txid)
            if not proof:
                return jsonify({'success': False, 'error': 'TX_NOT_FOUND'}), 404
            return jsonify({'success': True, 'proof': proof})

        @self.app.route('/mobile/transactions/draft', methods=['POST'])
        def mobile_tx_draft():
            payload = request.get_json() or {}
            try:
                draft = self.mobile_wallet_bridge.create_draft(payload)
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
            return jsonify({'success': True, 'draft': draft})

        @self.app.route('/mobile/transactions/draft/<draft_id>', methods=['GET'])
        def mobile_tx_get_draft(draft_id):
            draft = self.mobile_wallet_bridge.get_draft(draft_id)
            if not draft:
                return jsonify({'success': False, 'error': 'DRAFT_NOT_FOUND'}), 404
            return jsonify({'success': True, 'draft': draft})

        @self.app.route('/mobile/transactions/commit', methods=['POST'])
        def mobile_tx_commit():
            payload = request.get_json() or {}
            draft_id = payload.get('draft_id')
            signature = payload.get('signature')
            public_key = payload.get('public_key')
            if not all([draft_id, signature, public_key]):
                return jsonify({'success': False, 'error': 'draft_id, signature, and public_key are required'}), 400
            try:
                tx = self.mobile_wallet_bridge.commit_draft(draft_id, signature, public_key)
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
            return jsonify({'success': True, 'txid': tx.txid})

        @self.app.route('/mobile/cache/summary', methods=['GET'])
        def mobile_cache_summary():
            address = request.args.get('address', '').strip()
            try:
                summary = self.mobile_cache_service.build_summary(address or None)
                return jsonify({'success': True, 'summary': summary})
            except Exception as exc:  # pragma: no cover
                if hasattr(self, 'logger'):
                    self.logger.error(f"Mobile cache summary failed: {exc}")
                return jsonify({
                    'success': False,
                    'error': 'MOBILE_CACHE_ERROR',
                    'message': str(exc)
                }), 500

        @self.app.route('/ai/bridge/status', methods=['GET'])
        def ai_bridge_status():
            """Get quick summary of the AI bridge queue"""

            total_queued = len(self.ai_bridge.proposal_task_map)
            total_completed = len(self.blockchain.ai_pool.completed_tasks)

            return jsonify({
                'queued_proposals': total_queued,
                'completed_tasks': total_completed,
                'bridge_recognized': len(self.ai_bridge.queued_proposals)
            }), 200

        @self.app.route('/ai/bridge/tasks', methods=['GET'])
        def ai_bridge_tasks():
            """List currently queued AI tasks and their proposals"""

            completed_ids = {task.task_id for task in self.blockchain.ai_pool.completed_tasks}
            tasks = []

            for proposal_id, task_id in self.ai_bridge.proposal_task_map.items():
                proposal = self.governance_dao.proposals.get(proposal_id)
                state = 'completed' if task_id in completed_ids else 'queued'

                tasks.append({
                    'proposal_id': proposal_id,
                    'task_id': task_id,
                    'status': state,
                    'category': getattr(proposal.category, 'value', None) if proposal else None,
                    'votes_for': getattr(proposal, 'votes_for', None) if proposal else None,
                    'estimated_tokens': getattr(proposal, 'estimated_tokens', None) if proposal else None,
                    'assigned_model': getattr(proposal, 'assigned_ai_model', None) if proposal else None
                })

            return jsonify({
                'total_tasks': len(tasks),
                'tasks': tasks
            }), 200

        @self.app.route('/ai/metrics', methods=['GET'])
        def ai_metrics():
            """Get snapshot of AI metrics"""
            return jsonify(metrics.get_snapshot()), 200

        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get blockchain statistics"""
            stats = self.blockchain.get_stats()
            stats['miner_address'] = self.miner_address
            stats['peers'] = len(self.peers)
            stats['is_mining'] = self.is_mining
            stats['node_uptime'] = time.time() - self.start_time

            return jsonify(stats)

        @self.app.route('/blocks', methods=['GET'])
        def get_blocks():
            """Get all blocks"""
            limit = request.args.get('limit', default=10, type=int)
            offset = request.args.get('offset', default=0, type=int)

            blocks = [block.to_dict() for block in self.blockchain.chain]
            blocks.reverse()  # Most recent first

            return jsonify({
                'total': len(blocks),
                'limit': limit,
                'offset': offset,
                'blocks': blocks[offset:offset+limit]
            })

        @self.app.route('/blocks/<int:index>', methods=['GET'])
        def get_block(index):
            """Get specific block"""
            if index < 0 or index >= len(self.blockchain.chain):
                return jsonify({'error': 'Block not found'}), 404

            return jsonify(self.blockchain.chain[index].to_dict())

        @self.app.route('/transactions', methods=['GET'])
        def get_pending_transactions():
            """Get pending transactions"""
            return jsonify({
                'count': len(self.blockchain.pending_transactions),
                'transactions': [tx.to_dict() for tx in self.blockchain.pending_transactions]
            })

        @self.app.route('/transaction/<txid>', methods=['GET'])
        def get_transaction(txid):
            """Get transaction by ID"""
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.txid == txid:
                        return jsonify({
                            'found': True,
                            'block': block.index,
                            'confirmations': len(self.blockchain.chain) - block.index,
                            'transaction': tx.to_dict()
                        })

            # Check pending
            for tx in self.blockchain.pending_transactions:
                if tx.txid == txid:
                    return jsonify({
                        'found': True,
                        'status': 'pending',
                        'transaction': tx.to_dict()
                    })

            return jsonify({'found': False, 'error': 'Transaction not found'}), 404

        @self.app.route('/balance/<address>', methods=['GET'])
        def get_balance(address):
            """Get address balance"""
            # Validate address
            address = self.validator.validate_address(address)

            balance = self.blockchain.get_balance(address)
            return jsonify({
                'address': address,
                'balance': balance
            })

        @self.app.route('/history/<address>', methods=['GET'])
        def get_history(address):
            """Get transaction history for address"""
            history = self.blockchain.get_transaction_history(address)
            return jsonify({
                'address': address,
                'transaction_count': len(history),
                'transactions': history
            })

        @self.app.route('/send', methods=['POST'])
        def send_transaction():
            """Submit new transaction"""
            data = request.json

            # Rate limiting
            rate_ok, rate_msg = self.rate_limiter.check_rate_limit(
                request_identifier=data.get('sender', 'unknown'),
                endpoint='/send'
            )
            if not rate_ok:
                self.logger.rate_limit_exceeded('/send')
                return jsonify({'error': rate_msg}), 429

            required_fields = ['sender', 'recipient', 'amount', 'private_key']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                # Validate transaction data
                validated = validate_transaction_data(data)

                # Derive public key from private key
                import ecdsa
                sk = ecdsa.SigningKey.from_string(bytes.fromhex(validated['private_key']), curve=ecdsa.SECP256k1)
                vk = sk.get_verifying_key()
                public_key = vk.to_string().hex()

                # Get next nonce for sender
                nonce = self.blockchain.nonce_tracker.get_next_nonce(validated['sender'])

                # Create transaction with public key and nonce
                tx = Transaction(
                    sender=validated['sender'],
                    recipient=validated['recipient'],
                    amount=validated['amount'],
                    fee=validated['fee'],
                    public_key=public_key,
                    nonce=nonce
                )

                # Sign transaction
                tx.sign_transaction(validated['private_key'])

                # Add to blockchain
                if self.blockchain.add_transaction(tx):
                    # Log transaction
                    self.logger.transaction_received(
                        validated['sender'],
                        validated['recipient'],
                        validated['amount']
                    )

                    # Broadcast to peers
                    self.broadcast_transaction(tx)

                    return jsonify({
                        'success': True,
                        'txid': tx.txid,
                        'message': 'Transaction submitted successfully'
                    })
                else:
                    self.logger.validation_failed('Transaction blockchain validation failed')
                    return jsonify({
                        'success': False,
                        'error': 'Transaction validation failed'
                    }), 400

            except ValidationError as e:
                self.logger.validation_failed(str(e))
                raise
            except Exception as e:
                self.logger.error(f'Transaction error: {str(e)}')
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mine', methods=['POST'])
        def mine_block():
            """Mine pending transactions"""
            # Rate limiting
            rate_ok, rate_msg = self.rate_limiter.check_rate_limit(
                request_identifier=self.miner_address,
                endpoint='/mine'
            )
            if not rate_ok:
                self.logger.rate_limit_exceeded('/mine')
                return jsonify({'error': rate_msg}), 429

            if not self.blockchain.pending_transactions:
                return jsonify({'error': 'No pending transactions to mine'}), 400

            try:
                block = self.blockchain.mine_pending_transactions(self.miner_address)

                # Log block mining
                self.logger.block_mined(
                    block.index,
                    block.hash,
                    len(block.transactions)
                )

                # Broadcast new block to peers
                self.broadcast_block(block)

                response = {
                    'success': True,
                    'block': block.to_dict(),
                    'message': f'Block {block.index} mined successfully',
                    'reward': self.blockchain.block_reward
                }

                # AUTO-CHECK: Check if miner has unclaimed wallet
                # This ensures browser miners don't miss out!
                try:
                    # Check if wallet already exists
                    premium_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_og_wallet.json')
                    standard_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_early_adopter_wallet.json')

                    has_wallet = os.path.exists(premium_wallet_file) or os.path.exists(standard_wallet_file)

                    if not has_wallet:
                        # Try to claim wallet using miner address as identifier
                        miner_id = self.miner_address

                        # Try premium first
                        premium_result = self.wallet_claim_system.claim_premium_wallet(
                            node_id=miner_id,
                            proof_of_mining=None
                        )

                        if premium_result['success']:
                            self._save_bonus_wallet(premium_result['wallet'], tier=premium_result['tier'])
                            response['bonus_wallet'] = {
                                'claimed': True,
                                'tier': 'premium',
                                'address': premium_result['wallet']['address'],
                                'file': 'xai_og_wallet.json',
                                'message': '🎁 CONGRATULATIONS! Premium wallet auto-assigned!',
                                'remaining_premium': premium_result.get('remaining_premium', 0)
                            }
                        else:
                            # Premium exhausted, notify about uptime requirement
                            response['wallet_notification'] = {
                                'message': '🎁 WALLET AVAILABLE! Run node for 30 minutes to claim early adopter wallet',
                                'action': 'Call POST /claim-wallet with your miner address after 30 minutes'
                            }

                except Exception as e:
                    # Don't fail mining if wallet check fails
                    print(f"[WARNING] Wallet auto-check failed: {e}")

                return jsonify(response)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/auto-mine/start', methods=['POST'])
        def start_auto_mining():
            """Start automatic mining"""
            if self.is_mining:
                return jsonify({'message': 'Mining already active'})

            self.start_mining()
            return jsonify({'message': 'Auto-mining started'})

        @self.app.route('/auto-mine/stop', methods=['POST'])
        def stop_auto_mining():
            """Stop automatic mining"""
            if not self.is_mining:
                return jsonify({'message': 'Mining not active'})

            self.stop_mining()
            return jsonify({'message': 'Auto-mining stopped'})

        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            """Get connected peers"""
            return jsonify({
                'count': len(self.peers),
                'peers': list(self.peers)
            })

        @self.app.route('/peers/add', methods=['POST'])
        def add_peer():
            """Add peer node"""
            data = request.json
            if 'url' not in data:
                return jsonify({'error': 'Missing peer URL'}), 400

            self.add_peer(data['url'])
            return jsonify({'message': f'Peer {data["url"]} added'})

        @self.app.route('/sync', methods=['POST'])
        def sync_blockchain():
            """Synchronize blockchain with peers"""
            synced = self.sync_with_network()
            return jsonify({
                'synced': synced,
                'chain_length': len(self.blockchain.chain)
            })

        # Algorithmic Feature Endpoints
        @self.app.route('/algo/fee-estimate', methods=['GET'])
        def estimate_fee():
            """Get algorithmic fee recommendation"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({'error': 'Algorithmic features not enabled'}), 503

            priority = request.args.get('priority', 'normal')
            pending_count = len(self.blockchain.pending_transactions)

            recommendation = self.fee_optimizer.predict_optimal_fee(
                pending_tx_count=pending_count,
                priority=priority
            )

            return jsonify(recommendation)

        @self.app.route('/algo/fraud-check', methods=['POST'])
        def check_fraud():
            """Check transaction for fraud indicators"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({'error': 'Algorithmic features not enabled'}), 503

            data = request.json
            if not data:
                return jsonify({'error': 'Missing transaction data'}), 400

            analysis = self.fraud_detector.analyze_transaction(data)
            return jsonify(analysis)

        @self.app.route('/algo/status', methods=['GET'])
        def algo_status():
            """Get algorithmic features status"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({
                    'enabled': False,
                    'features': []
                })

            return jsonify({
                'enabled': True,
                'features': [
                    {
                        'name': 'Fee Optimizer',
                        'description': 'Statistical fee prediction using EMA',
                        'status': 'active',
                        'transactions_analyzed': len(self.fee_optimizer.fee_history),
                        'confidence': min(100, len(self.fee_optimizer.fee_history) * 2)
                    },
                    {
                        'name': 'Fraud Detector',
                        'description': 'Pattern-based fraud detection',
                        'status': 'active',
                        'addresses_tracked': len(self.fraud_detector.address_history),
                        'flagged_addresses': len(self.fraud_detector.flagged_addresses)
                    }
                ]
            })

        # Social Recovery Endpoints

        @self.app.route('/recovery/setup', methods=['POST'])
        def setup_recovery():
            """Set up guardians for a wallet"""
            data = request.json

            required_fields = ['owner_address', 'guardians', 'threshold']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.recovery_manager.setup_guardians(
                    owner_address=data['owner_address'],
                    guardian_addresses=data['guardians'],
                    threshold=int(data['threshold']),
                    signature=data.get('signature')
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Server error: {str(e)}'}), 500

        @self.app.route('/recovery/request', methods=['POST'])
        def request_recovery():
            """Initiate a recovery request"""
            data = request.json

            required_fields = ['owner_address', 'new_address', 'guardian_address']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.recovery_manager.initiate_recovery(
                    owner_address=data['owner_address'],
                    new_address=data['new_address'],
                    guardian_address=data['guardian_address'],
                    signature=data.get('signature')
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Server error: {str(e)}'}), 500

        @self.app.route('/recovery/vote', methods=['POST'])
        def vote_recovery():
            """Guardian votes on a recovery request"""
            data = request.json

            required_fields = ['request_id', 'guardian_address']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.recovery_manager.vote_recovery(
                    request_id=data['request_id'],
                    guardian_address=data['guardian_address'],
                    signature=data.get('signature')
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Server error: {str(e)}'}), 500

        @self.app.route('/recovery/status/<address>', methods=['GET'])
        def get_recovery_status(address):
            """Get recovery status for an address"""
            try:
                status = self.recovery_manager.get_recovery_status(address)
                return jsonify({
                    'success': True,
                    'address': address,
                    'status': status
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/recovery/cancel', methods=['POST'])
        def cancel_recovery():
            """Cancel a pending recovery request"""
            data = request.json

            required_fields = ['request_id', 'owner_address']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.recovery_manager.cancel_recovery(
                    request_id=data['request_id'],
                    owner_address=data['owner_address'],
                    signature=data.get('signature')
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Server error: {str(e)}'}), 500

        @self.app.route('/recovery/execute', methods=['POST'])
        def execute_recovery():
            """Execute an approved recovery after waiting period"""
            data = request.json

            if 'request_id' not in data:
                return jsonify({'error': 'Missing request_id'}), 400

            try:
                result = self.recovery_manager.execute_recovery(
                    request_id=data['request_id'],
                    executor_address=data.get('executor_address')
                )

                # If execution successful, we should transfer funds
                # This is a placeholder - actual implementation would:
                # 1. Get balance of old address
                # 2. Create transaction from old to new address
                # 3. Add to pending transactions
                # For now, we just return the result

                return jsonify(result)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Server error: {str(e)}'}), 500

        @self.app.route('/recovery/config/<address>', methods=['GET'])
        def get_recovery_config(address):
            """Get recovery configuration for an address"""
            try:
                config = self.recovery_manager.get_recovery_config(address)
                if config:
                    return jsonify({
                        'success': True,
                        'address': address,
                        'config': config
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No recovery configuration found'
                    }), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/recovery/guardian/<address>', methods=['GET'])
        def get_guardian_duties(address):
            """Get guardian duties for an address"""
            try:
                duties = self.recovery_manager.get_guardian_duties(address)
                return jsonify({
                    'success': True,
                    'duties': duties
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/recovery/requests', methods=['GET'])
        def get_recovery_requests():
            """Get all recovery requests with optional status filter"""
            try:
                status_filter = request.args.get('status')
                requests_list = self.recovery_manager.get_all_requests(status=status_filter)
                return jsonify({
                    'success': True,
                    'count': len(requests_list),
                    'requests': requests_list
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/recovery/stats', methods=['GET'])
        def get_recovery_stats():
            """Get social recovery statistics"""
            try:
                stats = self.recovery_manager.get_stats()
                return jsonify({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Gamification Endpoints

        @self.app.route('/airdrop/winners', methods=['GET'])
        def get_airdrop_winners():
            """Get recent airdrop winners"""
            limit = request.args.get('limit', default=10, type=int)
            recent_airdrops = self.blockchain.airdrop_manager.get_recent_airdrops(limit)
            return jsonify({
                'success': True,
                'airdrops': recent_airdrops
            })

        @self.app.route('/airdrop/user/<address>', methods=['GET'])
        def get_user_airdrops(address):
            """Get airdrop history for specific address"""
            history = self.blockchain.airdrop_manager.get_user_airdrop_history(address)
            total_received = sum(a['amount'] for a in history)
            return jsonify({
                'success': True,
                'address': address,
                'total_airdrops': len(history),
                'total_received': total_received,
                'history': history
            })

        @self.app.route('/mining/streaks', methods=['GET'])
        def get_mining_streaks():
            """Get mining streak leaderboard"""
            limit = request.args.get('limit', default=10, type=int)
            sort_by = request.args.get('sort_by', default='current_streak')

            leaderboard = self.blockchain.streak_tracker.get_leaderboard(limit, sort_by)
            return jsonify({
                'success': True,
                'leaderboard': leaderboard
            })

        @self.app.route('/mining/streak/<address>', methods=['GET'])
        def get_miner_streak(address):
            """Get mining streak for specific address"""
            stats = self.blockchain.streak_tracker.get_miner_stats(address)
            if not stats:
                return jsonify({
                    'success': False,
                    'error': 'No mining history found for this address'
                }), 404

            return jsonify({
                'success': True,
                'address': address,
                'stats': stats
            })

        @self.app.route('/treasure/active', methods=['GET'])
        def get_active_treasures():
            """List all active (unclaimed) treasure hunts"""
            treasures = self.blockchain.treasure_manager.get_active_treasures()
            return jsonify({
                'success': True,
                'count': len(treasures),
                'treasures': treasures
            })

        @self.app.route('/treasure/create', methods=['POST'])
        def create_treasure():
            """Create a new treasure hunt"""
            data = request.json

            required_fields = ['creator', 'amount', 'puzzle_type', 'puzzle_data']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                treasure_id = self.blockchain.treasure_manager.create_treasure_hunt(
                    creator_address=data['creator'],
                    amount=float(data['amount']),
                    puzzle_type=data['puzzle_type'],
                    puzzle_data=data['puzzle_data'],
                    hint=data.get('hint', '')
                )

                return jsonify({
                    'success': True,
                    'treasure_id': treasure_id,
                    'message': 'Treasure hunt created successfully'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/treasure/claim', methods=['POST'])
        def claim_treasure():
            """Claim a treasure by solving the puzzle"""
            data = request.json

            required_fields = ['treasure_id', 'claimer', 'solution']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                success, amount = self.blockchain.treasure_manager.claim_treasure(
                    treasure_id=data['treasure_id'],
                    claimer_address=data['claimer'],
                    solution=data['solution']
                )

                if success:
                    # Create transaction for claimed treasure
                    treasure_tx = Transaction(
                        "COINBASE",
                        data['claimer'],
                        amount,
                        tx_type="treasure"
                    )
                    treasure_tx.txid = treasure_tx.calculate_hash()
                    self.blockchain.pending_transactions.append(treasure_tx)

                    return jsonify({
                        'success': True,
                        'amount': amount,
                        'message': 'Treasure claimed successfully!'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Incorrect solution'
                    }), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/treasure/details/<treasure_id>', methods=['GET'])
        def get_treasure_details(treasure_id):
            """Get details of a specific treasure hunt"""
            treasure = self.blockchain.treasure_manager.get_treasure_details(treasure_id)
            if not treasure:
                return jsonify({'error': 'Treasure not found'}), 404

            return jsonify({
                'success': True,
                'treasure': treasure
            })

        @self.app.route('/timecapsule/create', methods=['POST'])
        def create_timecapsule():
            """Create a time-locked transaction"""
            data = request.json

            required_fields = ['sender', 'recipient', 'amount', 'unlock_timestamp']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                capsule_id = self.blockchain.timecapsule_manager.create_time_capsule(
                    sender=data['sender'],
                    recipient=data['recipient'],
                    amount=float(data['amount']),
                    unlock_timestamp=float(data['unlock_timestamp']),
                    message=data.get('message', ''),
                    private_key=data.get('private_key')
                )

                from datetime import datetime
                unlock_date = datetime.fromtimestamp(data['unlock_timestamp']).strftime('%Y-%m-%d %H:%M:%S')

                return jsonify({
                    'success': True,
                    'capsule_id': capsule_id,
                    'unlock_date': unlock_date,
                    'message': 'Time capsule created successfully'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/timecapsule/pending', methods=['GET'])
        def get_pending_timecapsules():
            """List all pending (locked) time capsules"""
            capsules = self.blockchain.timecapsule_manager.get_pending_capsules()
            return jsonify({
                'success': True,
                'count': len(capsules),
                'capsules': capsules
            })

        @self.app.route('/timecapsule/<address>', methods=['GET'])
        def get_user_timecapsules(address):
            """Get time capsules for a specific user"""
            capsules = self.blockchain.timecapsule_manager.get_user_capsules(address)
            return jsonify({
                'success': True,
                'address': address,
                'sent': capsules['sent'],
                'received': capsules['received']
            })

        @self.app.route('/refunds/stats', methods=['GET'])
        def get_refund_stats():
            """Get overall fee refund statistics"""
            stats = self.blockchain.fee_refund_calculator.get_refund_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })

        @self.app.route('/refunds/<address>', methods=['GET'])
        def get_user_refunds(address):
            """Get fee refund history for specific address"""
            history = self.blockchain.fee_refund_calculator.get_user_refund_history(address)
            total_refunded = sum(r['amount'] for r in history)
            return jsonify({
                'success': True,
                'address': address,
                'total_refunds': len(history),
                'total_refunded': total_refunded,
                'history': history
            })

        # Mining Bonus Endpoints

        @self.app.route('/mining/register', methods=['POST'])
        def register_miner():
            """Register a new miner and check for early adopter bonus"""
            data = request.json

            if 'address' not in data:
                return jsonify({'error': 'Missing address field'}), 400

            try:
                result = self.bonus_manager.register_miner(data['address'])
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/achievements/<address>', methods=['GET'])
        def get_achievements(address):
            """Check mining achievements for an address"""
            blocks_mined = request.args.get('blocks_mined', default=0, type=int)
            streak_days = request.args.get('streak_days', default=0, type=int)

            try:
                result = self.bonus_manager.check_achievements(address, blocks_mined, streak_days)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/claim-bonus', methods=['POST'])
        def claim_bonus():
            """Claim a social bonus"""
            data = request.json

            required_fields = ['address', 'bonus_type']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.bonus_manager.claim_bonus(data['address'], data['bonus_type'])
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/referral/create', methods=['POST'])
        def create_referral_code():
            """Create a referral code for a miner"""
            data = request.json

            if 'address' not in data:
                return jsonify({'error': 'Missing address field'}), 400

            try:
                result = self.bonus_manager.create_referral_code(data['address'])
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/referral/use', methods=['POST'])
        def use_referral_code():
            """Use a referral code to register a new miner"""
            data = request.json

            required_fields = ['new_address', 'referral_code']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.bonus_manager.use_referral_code(data['new_address'], data['referral_code'])
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/user-bonuses/<address>', methods=['GET'])
        def get_user_bonuses(address):
            """Get all bonuses and rewards for a user"""
            try:
                result = self.bonus_manager.get_user_bonuses(address)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/leaderboard', methods=['GET'])
        def get_bonus_leaderboard():
            """Get mining bonus leaderboard"""
            limit = request.args.get('limit', default=10, type=int)

            try:
                leaderboard = self.bonus_manager.get_leaderboard(limit)
                return jsonify({
                    'success': True,
                    'limit': limit,
                    'leaderboard': leaderboard
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/mining/stats', methods=['GET'])
        def get_mining_bonus_stats():
            """Get mining bonus system statistics"""
            try:
                stats = self.bonus_manager.get_stats()
                return jsonify({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ==================== ADVANCED CONSENSUS ENDPOINTS ====================

        @self.app.route('/consensus/stats', methods=['GET'])
        def get_consensus_stats():
            """Get advanced consensus statistics"""
            try:
                stats = self.blockchain.get_consensus_stats()
                return jsonify({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/consensus/finality/<int:block_index>', methods=['GET'])
        def get_block_finality(block_index):
            """Get finality information for a specific block"""
            try:
                if block_index < 0 or block_index >= len(self.blockchain.chain):
                    return jsonify({'error': 'Block not found'}), 404

                finality_info = self.blockchain.get_block_finality(block_index)
                return jsonify({
                    'success': True,
                    'block_index': block_index,
                    'finality': finality_info
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/consensus/orphans', methods=['GET'])
        def get_orphan_stats():
            """Get orphan block pool statistics"""
            try:
                stats = self.blockchain.consensus_manager.orphan_pool.get_stats()
                return jsonify({
                    'success': True,
                    'orphan_pool': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/consensus/difficulty', methods=['GET'])
        def get_difficulty_info():
            """Get difficulty adjustment information"""
            try:
                stats = self.blockchain.consensus_manager.difficulty_adjuster.get_difficulty_stats(self.blockchain)
                return jsonify({
                    'success': True,
                    'difficulty_info': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/consensus/propagation', methods=['GET'])
        def get_propagation_stats():
            """Get block propagation statistics"""
            try:
                stats = self.blockchain.consensus_manager.propagation_monitor.get_network_stats()
                return jsonify({
                    'success': True,
                    'propagation_stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/consensus/peer-performance', methods=['GET'])
        def get_peer_performance():
            """Get performance metrics for all peers"""
            try:
                peer_stats = {}
                for peer in self.peers:
                    peer_stats[peer] = self.blockchain.consensus_manager.propagation_monitor.get_peer_performance(peer)

                return jsonify({
                    'success': True,
                    'peer_performance': peer_stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ==================== EXCHANGE API ENDPOINTS ====================

        @self.app.route('/exchange/orders', methods=['GET'])
        def get_order_book():
            """Get current order book (buy and sell orders)"""
            try:
                # Load orders from blockchain data
                orders_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'orders.json')
                if os.path.exists(orders_file):
                    with open(orders_file, 'r') as f:
                        all_orders = json.load(f)
                else:
                    all_orders = {'buy': [], 'sell': []}

                # Filter only open orders
                buy_orders = [o for o in all_orders.get('buy', []) if o['status'] == 'open']
                sell_orders = [o for o in all_orders.get('sell', []) if o['status'] == 'open']

                # Sort orders (buy: highest first, sell: lowest first)
                buy_orders.sort(key=lambda x: x['price'], reverse=True)
                sell_orders.sort(key=lambda x: x['price'])

                return jsonify({
                    'success': True,
                    'buy_orders': buy_orders[:20],  # Top 20
                    'sell_orders': sell_orders[:20],
                    'total_buy_orders': len(buy_orders),
                    'total_sell_orders': len(sell_orders)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/place-order', methods=['POST'])
        def place_order():
            """Place a buy or sell order with balance verification"""
            data = request.json

            required_fields = ['address', 'order_type', 'price', 'amount']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                # Validate order
                if data['order_type'] not in ['buy', 'sell']:
                    return jsonify({'error': 'Invalid order type'}), 400

                price = float(data['price'])
                amount = float(data['amount'])

                if price <= 0 or amount <= 0:
                    return jsonify({'error': 'Price and amount must be positive'}), 400

                # Parse trading pair (default XAI/USD)
                pair = data.get('pair', 'XAI/USD')
                base_currency, quote_currency = pair.split('/')

                # Calculate total cost
                total_cost = price * amount

                # Verify user has sufficient balance
                user_address = data['address']
                if data['order_type'] == 'buy':
                    # Buying base currency (XAI), need quote currency (USD/BTC/ETH)
                    balance_info = self.exchange_wallet_manager.get_balance(user_address, quote_currency)
                    if balance_info['available'] < total_cost:
                        return jsonify({
                            'success': False,
                            'error': f'Insufficient {quote_currency} balance. Need {total_cost:.2f}, have {balance_info["available"]:.2f}'
                        }), 400

                    # Lock the quote currency
                    if not self.exchange_wallet_manager.lock_for_order(user_address, quote_currency, total_cost):
                        return jsonify({'success': False, 'error': 'Failed to lock funds'}), 500

                else:  # sell
                    # Selling base currency (XAI), need base currency
                    balance_info = self.exchange_wallet_manager.get_balance(user_address, base_currency)
                    if balance_info['available'] < amount:
                        return jsonify({
                            'success': False,
                            'error': f'Insufficient {base_currency} balance. Need {amount:.2f}, have {balance_info["available"]:.2f}'
                        }), 400

                    # Lock the base currency
                    if not self.exchange_wallet_manager.lock_for_order(user_address, base_currency, amount):
                        return jsonify({'success': False, 'error': 'Failed to lock funds'}), 500

                # Create order
                order = {
                    'id': f"{user_address}_{int(time.time() * 1000)}",
                    'address': user_address,
                    'order_type': data['order_type'],
                    'pair': pair,
                    'base_currency': base_currency,
                    'quote_currency': quote_currency,
                    'price': price,
                    'amount': amount,
                    'remaining': amount,
                    'total': total_cost,
                    'status': 'open',
                    'timestamp': time.time()
                }

                # Save order
                orders_dir = os.path.join(os.path.dirname(__file__), '..', 'exchange_data')
                os.makedirs(orders_dir, exist_ok=True)
                orders_file = os.path.join(orders_dir, 'orders.json')

                if os.path.exists(orders_file):
                    with open(orders_file, 'r') as f:
                        all_orders = json.load(f)
                else:
                    all_orders = {'buy': [], 'sell': []}

                all_orders[data['order_type']].append(order)

                with open(orders_file, 'w') as f:
                    json.dump(all_orders, f, indent=2)

                # Try to match order immediately
                matched = self._match_orders(order, all_orders)

                # Get updated balances
                balances = self.exchange_wallet_manager.get_all_balances(user_address)

                return jsonify({
                    'success': True,
                    'order': order,
                    'matched': matched,
                    'balances': balances['available_balances'],
                    'message': f"{data['order_type'].capitalize()} order placed successfully"
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/cancel-order', methods=['POST'])
        def cancel_order():
            """Cancel an open order"""
            data = request.json

            if 'order_id' not in data:
                return jsonify({'error': 'Missing order_id'}), 400

            try:
                orders_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'orders.json')

                if not os.path.exists(orders_file):
                    return jsonify({'error': 'Order not found'}), 404

                with open(orders_file, 'r') as f:
                    all_orders = json.load(f)

                # Find and cancel order
                found = False
                for order_type in ['buy', 'sell']:
                    for order in all_orders[order_type]:
                        if order['id'] == data['order_id']:
                            if order['status'] == 'open':
                                order['status'] = 'cancelled'
                                found = True
                                break
                    if found:
                        break

                if not found:
                    return jsonify({'error': 'Order not found or already completed'}), 404

                with open(orders_file, 'w') as f:
                    json.dump(all_orders, f, indent=2)

                return jsonify({
                    'success': True,
                    'message': 'Order cancelled successfully'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/my-orders/<address>', methods=['GET'])
        def get_my_orders(address):
            """Get all orders for a specific address"""
            try:
                orders_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'orders.json')

                if not os.path.exists(orders_file):
                    return jsonify({
                        'success': True,
                        'orders': []
                    })

                with open(orders_file, 'r') as f:
                    all_orders = json.load(f)

                # Filter orders for this address
                user_orders = []
                for order_type in ['buy', 'sell']:
                    for order in all_orders[order_type]:
                        if order['address'] == address:
                            user_orders.append(order)

                # Sort by timestamp (newest first)
                user_orders.sort(key=lambda x: x['timestamp'], reverse=True)

                return jsonify({
                    'success': True,
                    'orders': user_orders
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/trades', methods=['GET'])
        def get_recent_trades():
            """Get recent executed trades"""
            limit = request.args.get('limit', default=50, type=int)

            try:
                trades_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'trades.json')

                if not os.path.exists(trades_file):
                    return jsonify({
                        'success': True,
                        'trades': []
                    })

                with open(trades_file, 'r') as f:
                    all_trades = json.load(f)

                # Get most recent trades
                all_trades.sort(key=lambda x: x['timestamp'], reverse=True)

                return jsonify({
                    'success': True,
                    'trades': all_trades[:limit]
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/price-history', methods=['GET'])
        def get_price_history():
            """Get historical price data for charts"""
            timeframe = request.args.get('timeframe', default='24h', type=str)

            try:
                trades_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'trades.json')

                if not os.path.exists(trades_file):
                    return jsonify({
                        'success': True,
                        'prices': [],
                        'volumes': []
                    })

                with open(trades_file, 'r') as f:
                    all_trades = json.load(f)

                # Filter trades by timeframe
                now = time.time()
                timeframe_seconds = {
                    '1h': 3600,
                    '24h': 86400,
                    '7d': 604800,
                    '30d': 2592000
                }.get(timeframe, 86400)

                cutoff_time = now - timeframe_seconds
                recent_trades = [t for t in all_trades if t['timestamp'] >= cutoff_time]

                # Aggregate by time intervals
                interval_seconds = {
                    '1h': 300,      # 5 minutes
                    '24h': 1800,    # 30 minutes
                    '7d': 3600,     # 1 hour
                    '30d': 3600     # 1 hour
                }.get(timeframe, 1800)

                price_data = []
                volume_data = []

                if recent_trades:
                    recent_trades.sort(key=lambda x: x['timestamp'])

                    current_interval = int(recent_trades[0]['timestamp'] / interval_seconds) * interval_seconds
                    interval_prices = []
                    interval_volume = 0

                    for trade in recent_trades:
                        trade_interval = int(trade['timestamp'] / interval_seconds) * interval_seconds

                        if trade_interval > current_interval:
                            if interval_prices:
                                price_data.append({
                                    'time': current_interval,
                                    'price': sum(interval_prices) / len(interval_prices)
                                })
                                volume_data.append({
                                    'time': current_interval,
                                    'volume': interval_volume
                                })

                            current_interval = trade_interval
                            interval_prices = []
                            interval_volume = 0

                        interval_prices.append(trade['price'])
                        interval_volume += trade['amount']

                    # Add last interval
                    if interval_prices:
                        price_data.append({
                            'time': current_interval,
                            'price': sum(interval_prices) / len(interval_prices)
                        })
                        volume_data.append({
                            'time': current_interval,
                            'volume': interval_volume
                        })

                return jsonify({
                    'success': True,
                    'timeframe': timeframe,
                    'prices': price_data,
                    'volumes': volume_data
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/stats', methods=['GET'])
        def get_exchange_stats():
            """Get exchange statistics (24h volume, current price, etc.)"""
            try:
                trades_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'trades.json')
                orders_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_data', 'orders.json')

                stats = {
                    'current_price': 0.05,  # Default starting price
                    'volume_24h': 0,
                    'change_24h': 0,
                    'high_24h': 0,
                    'low_24h': 0,
                    'total_trades': 0,
                    'active_orders': 0
                }

                # Calculate stats from trades
                if os.path.exists(trades_file):
                    with open(trades_file, 'r') as f:
                        all_trades = json.load(f)

                    if all_trades:
                        now = time.time()
                        trades_24h = [t for t in all_trades if t['timestamp'] >= now - 86400]

                        stats['total_trades'] = len(all_trades)
                        stats['current_price'] = all_trades[-1]['price'] if all_trades else 0.05

                        if trades_24h:
                            stats['volume_24h'] = sum(t['amount'] for t in trades_24h)
                            stats['high_24h'] = max(t['price'] for t in trades_24h)
                            stats['low_24h'] = min(t['price'] for t in trades_24h)

                            if len(trades_24h) > 1:
                                first_price = trades_24h[0]['price']
                                last_price = trades_24h[-1]['price']
                                stats['change_24h'] = ((last_price - first_price) / first_price) * 100

                # Count active orders
                if os.path.exists(orders_file):
                    with open(orders_file, 'r') as f:
                        all_orders = json.load(f)

                    for order_type in ['buy', 'sell']:
                        stats['active_orders'] += len([o for o in all_orders.get(order_type, []) if o['status'] == 'open'])

                return jsonify({
                    'success': True,
                    'stats': stats
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/deposit', methods=['POST'])
        def deposit_funds():
            """Deposit funds into exchange wallet"""
            data = request.json

            required_fields = ['address', 'currency', 'amount']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.exchange_wallet_manager.deposit(
                    user_address=data['address'],
                    currency=data['currency'],
                    amount=float(data['amount']),
                    deposit_type=data.get('deposit_type', 'manual'),
                    tx_hash=data.get('tx_hash')
                )

                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/withdraw', methods=['POST'])
        def withdraw_funds():
            """Withdraw funds from exchange wallet"""
            data = request.json

            required_fields = ['address', 'currency', 'amount', 'destination']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            try:
                result = self.exchange_wallet_manager.withdraw(
                    user_address=data['address'],
                    currency=data['currency'],
                    amount=float(data['amount']),
                    destination=data['destination']
                )

                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/balance/<address>', methods=['GET'])
        def get_user_balance(address):
            """Get all balances for a user"""
            try:
                balances = self.exchange_wallet_manager.get_all_balances(address)
                return jsonify({
                    'success': True,
                    'address': address,
                    'balances': balances
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/balance/<address>/<currency>', methods=['GET'])
        def get_currency_balance(address, currency):
            """Get balance for specific currency"""
            try:
                balance = self.exchange_wallet_manager.get_balance(address, currency)
                return jsonify({
                    'success': True,
                    'address': address,
                    **balance
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/transactions/<address>', methods=['GET'])
        def get_transactions(address):
            """Get transaction history for user"""
            try:
                limit = int(request.args.get('limit', 50))
                transactions = self.exchange_wallet_manager.get_transaction_history(address, limit)

                return jsonify({
                    'success': True,
                    'address': address,
                    'transactions': transactions
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/buy-with-card', methods=['POST'])
        def buy_with_card():
            """Buy XAI with credit/debit card (temporarily disabled)"""
            return jsonify({
                'success': False,
                'error': 'CARD_PAYMENTS_DISABLED',
                'message': self._fiat_lock_message()
            }), 503

        @self.app.route('/exchange/payment-methods', methods=['GET'])
        def get_payment_methods():
            """Get supported payment methods (card/bank disabled)"""
            return jsonify({
                'success': False,
                'error': 'PAYMENT_METHODS_DISABLED',
                'message': self._fiat_lock_message()
            }), 503

        @self.app.route('/exchange/calculate-purchase', methods=['POST'])
        def calculate_purchase():
            """Calculate XAI amount for USD purchase (temporarily disabled)"""
            return jsonify({
                'success': False,
                'error': 'CALCULATE_PURCHASE_DISABLED',
                'message': self._fiat_lock_message()
            }), 503

        # ==================== WALLET TRADE API ====================

        @self.app.route('/wallet-trades/orders', methods=['GET'])
        def wallet_trade_orders():
            limit_param = request.args.get('limit')
            try:
                limit = int(limit_param) if limit_param else None
            except ValueError:
                return jsonify({'error': 'Invalid limit value'}), 400

            orders = self.wallet_trade_manager.list_open_orders(limit=limit)
            return jsonify({'success': True, 'orders': orders})

        @self.app.route('/wallet-trades/orders/<address>', methods=['GET'])
        def wallet_orders_for_address(address):
            orders = self.wallet_trade_manager.get_wallet_orders(address)
            return jsonify({'success': True, 'orders': orders})

        @self.app.route('/wallet-trades/matches/<address>', methods=['GET'])
        def wallet_matches_for_address(address):
            matches = self.wallet_trade_manager.get_wallet_matches(address)
            status_filter = request.args.get('status')
            if status_filter:
                matches = [m for m in matches if m.get('status') == status_filter.lower()]
            return jsonify({'success': True, 'matches': matches})

        @self.app.route('/wallet-trades/place-order', methods=['POST'])
        def place_wallet_trade_order():
            data = request.json or {}
            required = ['address', 'token_offered', 'amount_offered', 'token_requested', 'price']
            missing = [field for field in required if field not in data]
            if missing:
                return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400

            try:
                order_type = data.get('order_type', 'sell')
                order_type_enum = SwapOrderType(order_type.lower())
                amount_requested = data.get('amount_requested')
                expiry = float(data['expiry']) if data.get('expiry') else None
                order, matches = self.wallet_trade_manager.place_order(
                    maker_address=data['address'],
                    token_offered=data['token_offered'],
                    amount_offered=float(data['amount_offered']),
                    token_requested=data['token_requested'],
                    amount_requested=float(amount_requested) if amount_requested else None,
                    price=float(data['price']),
                    order_type=order_type_enum,
                    expiry=expiry,
                    fee=float(data.get('fee', 0.0)),
                    maker_public_key=data.get('public_key', ''),
                    metadata=data.get('metadata'),
                )
                response = {
                    'success': True,
                    'order': order.to_dict(),
                    'matches': [m.to_dict() for m in matches]
                }
                return jsonify(response)

            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
            except Exception as exc:
                return jsonify({'error': str(exc)}), 500

        @self.app.route('/wallet-trades/settle', methods=['POST'])
        def settle_wallet_trade():
            data = request.json or {}
            match_id = data.get('match_id')
            secret = data.get('secret')
            if not match_id or not secret:
                return jsonify({'error': 'match_id and secret are required'}), 400

            try:
                match = self.wallet_trade_manager.settle_match(match_id, secret)
                return jsonify({'success': True, 'match': match.to_dict()})
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
            except Exception as exc:
                return jsonify({'error': str(exc)}), 500

        @self.app.route('/wallet-trades/refund', methods=['POST'])
        def refund_wallet_trade():
            data = request.json or {}
            match_id = data.get('match_id')
            if not match_id:
                return jsonify({'error': 'match_id is required'}), 400

            try:
                match = self.wallet_trade_manager.refund_match(match_id)
                return jsonify({'success': True, 'match': match.to_dict()})
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
            except Exception as exc:
                return jsonify({'error': str(exc)}), 500

        # ==================== CRYPTO DEPOSIT API ENDPOINTS ====================

        @self.app.route('/exchange/crypto/generate-address', methods=['POST'])
        def generate_crypto_deposit_address():
            """Generate unique deposit address for BTC/ETH/USDT"""
            data = request.json

            required_fields = ['user_address', 'currency']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields: user_address, currency'}), 400

            try:
                result = self.crypto_deposit_manager.generate_deposit_address(
                    user_address=data['user_address'],
                    currency=data['currency']
                )
                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/crypto/addresses/<address>', methods=['GET'])
        def get_crypto_deposit_addresses(address):
            """Get all crypto deposit addresses for user"""
            try:
                result = self.crypto_deposit_manager.get_user_deposit_addresses(address)
                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/crypto/pending-deposits', methods=['GET'])
        def get_pending_crypto_deposits():
            """Get pending crypto deposits (optionally filtered by user)"""
            try:
                user_address = request.args.get('user_address')
                pending = self.crypto_deposit_manager.get_pending_deposits(user_address)

                return jsonify({
                    'success': True,
                    'pending_deposits': pending,
                    'count': len(pending)
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/crypto/deposit-history/<address>', methods=['GET'])
        def get_crypto_deposit_history(address):
            """Get confirmed crypto deposit history for user"""
            try:
                limit = int(request.args.get('limit', 50))
                history = self.crypto_deposit_manager.get_deposit_history(address, limit)

                return jsonify({
                    'success': True,
                    'address': address,
                    'deposits': history,
                    'count': len(history)
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/exchange/crypto/stats', methods=['GET'])
        def get_crypto_deposit_stats():
            """Get crypto deposit system statistics"""
            try:
                stats = self.crypto_deposit_manager.get_stats()
                return jsonify({
                    'success': True,
                    'stats': stats
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ================================================================
        # TESTNET FAUCET (only enabled on testnet)
        # ================================================================
        if Config.FAUCET_ENABLED:
            @self.app.route('/faucet/claim', methods=['POST'])
            def claim_testnet_faucet():
                """
                Claim free testnet XAI (TESTNET ONLY!)

                Request:
                {
                  "address": "TXAI..."
                }

                Response:
                {
                  "success": true,
                  "amount": 100.0,
                  "txid": "...",
                  "message": "Testnet faucet claim successful"
                }
                """
                data = request.get_json()

                if not data or 'address' not in data:
                    return jsonify({'error': 'Missing address'}), 400

                address = data['address']

                # Rate limiting (10 per day for faucet)
                rate_ok, rate_msg = self.rate_limiter.check_rate_limit(
                    request_identifier=address,
                    endpoint='/faucet/claim'
                )
                if not rate_ok:
                    self.logger.rate_limit_exceeded('/faucet/claim')
                    return jsonify({'error': rate_msg}), 429

                # Validate address
                try:
                    address = self.validator.validate_address(address)
                except ValidationError as e:
                    return jsonify({'error': str(e)}), 400

                # Verify address has correct testnet prefix
                if not address.startswith(Config.ADDRESS_PREFIX):
                    return jsonify({
                        'error': f'Invalid address. Testnet addresses must start with {Config.ADDRESS_PREFIX}'
                    }), 400

                # Create faucet transaction
                faucet_tx = Transaction(
                    sender="TESTNET_FAUCET",
                    recipient=address,
                    amount=Config.FAUCET_AMOUNT,
                    fee=0.0
                )
                faucet_tx.txid = faucet_tx.calculate_hash()

                # Add to pending transactions
                self.blockchain.pending_transactions.append(faucet_tx)

                # Log faucet claim
                self.logger.info(f'Faucet claim: {address[:6]}...{address[-4:]} ({Config.FAUCET_AMOUNT} XAI)')

                return jsonify({
                    'success': True,
                    'amount': Config.FAUCET_AMOUNT,
                    'txid': faucet_tx.txid,
                    'message': f'Testnet faucet claim successful! {Config.FAUCET_AMOUNT} XAI will be added to your address after the next block.',
                    'note': 'This is testnet XAI - it has no real value!'
                })

            print(f"✅ Testnet faucet enabled: {Config.FAUCET_AMOUNT} XAI per claim")

    def _match_orders(self, new_order, all_orders):
        """Internal method to match buy/sell orders and execute balance transfers"""
        try:
            matched_trades = []

            if new_order['order_type'] == 'buy':
                # Match with sell orders
                matching_orders = [o for o in all_orders['sell'] if o['status'] == 'open' and o['price'] <= new_order['price']]
                matching_orders.sort(key=lambda x: x['price'])  # Lowest price first
            else:
                # Match with buy orders
                matching_orders = [o for o in all_orders['buy'] if o['status'] == 'open' and o['price'] >= new_order['price']]
                matching_orders.sort(key=lambda x: x['price'], reverse=True)  # Highest price first

            for match_order in matching_orders:
                if new_order['remaining'] <= 0:
                    break

                # Calculate trade amount
                trade_amount = min(new_order['remaining'], match_order['remaining'])
                trade_price = match_order['price']  # Use existing order price
                trade_total = trade_price * trade_amount

                # Determine buyer and seller
                buyer_addr = new_order['address'] if new_order['order_type'] == 'buy' else match_order['address']
                seller_addr = match_order['address'] if new_order['order_type'] == 'buy' else new_order['address']

                # Get currencies from orders (they should match)
                base_currency = new_order.get('base_currency', 'XAI')
                quote_currency = new_order.get('quote_currency', 'USD')

                # Execute balance transfer
                trade_result = self.exchange_wallet_manager.execute_trade(
                    buyer_address=buyer_addr,
                    seller_address=seller_addr,
                    base_currency=base_currency,
                    quote_currency=quote_currency,
                    base_amount=trade_amount,
                    quote_amount=trade_total
                )

                if not trade_result['success']:
                    print(f"Trade execution failed: {trade_result.get('error')}")
                    continue  # Skip this match if balance transfer failed

                # Unlock the locked balances that were used in the trade
                if new_order['order_type'] == 'buy':
                    self.exchange_wallet_manager.unlock_from_order(buyer_addr, quote_currency, trade_total)
                    self.exchange_wallet_manager.unlock_from_order(seller_addr, base_currency, trade_amount)
                else:
                    self.exchange_wallet_manager.unlock_from_order(seller_addr, base_currency, trade_amount)
                    self.exchange_wallet_manager.unlock_from_order(buyer_addr, quote_currency, trade_total)

                # Create trade record
                trade = {
                    'id': f"trade_{int(time.time() * 1000)}",
                    'pair': f"{base_currency}/{quote_currency}",
                    'buyer': buyer_addr,
                    'seller': seller_addr,
                    'price': trade_price,
                    'amount': trade_amount,
                    'total': trade_total,
                    'timestamp': time.time()
                }

                matched_trades.append(trade)

                # Update order remainings
                new_order['remaining'] -= trade_amount
                match_order['remaining'] -= trade_amount

                # Update order statuses
                if new_order['remaining'] <= 0:
                    new_order['status'] = 'filled'
                if match_order['remaining'] <= 0:
                    match_order['status'] = 'filled'

            # Save trades
            if matched_trades:
                trades_dir = os.path.join(os.path.dirname(__file__), '..', 'exchange_data')
                trades_file = os.path.join(trades_dir, 'trades.json')

                if os.path.exists(trades_file):
                    with open(trades_file, 'r') as f:
                        all_trades = json.load(f)
                else:
                    all_trades = []

                all_trades.extend(matched_trades)

                with open(trades_file, 'w') as f:
                    json.dump(all_trades, f, indent=2)

                # Update orders file
                orders_file = os.path.join(trades_dir, 'orders.json')
                with open(orders_file, 'w') as f:
                    json.dump(all_orders, f, indent=2)

            return len(matched_trades) > 0

        except Exception as e:
            print(f"Error matching orders: {e}")
            return False

        # Setup Wallet Claiming API (ensures no early adopters miss out!)
        from core.wallet_claiming_api import setup_wallet_claiming_api
        self.wallet_claiming_tracker = setup_wallet_claiming_api(self.app, self)
        print("✓ Wallet Claiming API initialized (browser miners protected!)")
        self.mobile_cache_service = MobileCacheService(self)

        # Setup Token Burning API (utility token economics with 100% anonymity!)
        from core.burning_api_endpoints import setup_burning_api
        self.burning_engine = setup_burning_api(self.app, self)
        # NO treasury - dev funded by pre-mine (10M XAI) + donated AI API minutes!

    def _fiat_lock_message(self) -> str:
        """Return the current fiat lock notice."""
        status = self.fiat_unlock_manager.get_status()
        if status.get("unlocked"):
            return (
                "Card rails unlocked via governance or time-based auto-unlock. "
                "Use the standard exchange endpoints."
            )

        return (
            f"Card rails locked until {Config.FIAT_REENABLE_DATE.strftime('%Y-%m-%d')} UTC "
            f"(governance vote window opens {Config.FIAT_UNLOCK_GOVERNANCE_START.strftime('%Y-%m-%d')} UTC). "
            f"Support: {status['votes_for']} / {status['required_votes']} votes "
            f"({status['support_ratio']*100:.1f}% positive). "
            "Call POST /governance/fiat-unlock/vote to cast your vote."
        )

    def _generate_node_id(self) -> str:
        """
        Generate unique node ID for wallet assignment

        Returns:
            Unique node identifier
        """
        import socket
        import hashlib
        import uuid

        try:
            # Get system identifiers
            hostname = socket.gethostname()
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0,2*6,2)][::-1])
            timestamp = str(time.time())

            # Create unique hash
            node_string = f"{hostname}_{mac}_{timestamp}"
            node_id = hashlib.sha256(node_string.encode()).hexdigest()[:16]

            return node_id

        except Exception as e:
            # Fallback to random ID
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

    def _check_bonus_wallet(self):
        """
        Check if node qualifies for bonus wallet assignment
        Displays opt-in message if wallet available
        """

        # Check if wallet already claimed for this node (check both possible filenames)
        premium_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_og_wallet.json')
        standard_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_early_adopter_wallet.json')

        wallet_file = None
        if os.path.exists(premium_wallet_file):
            wallet_file = premium_wallet_file
        elif os.path.exists(standard_wallet_file):
            wallet_file = standard_wallet_file

        if wallet_file:
            # Already have a wallet
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)

            print("\n" + "=" * 70)
            print("You have a bonus wallet!")
            print("=" * 70)
            print(f"Address: {wallet_data['address']}")
            print(f"Balance: {wallet_data.get('balance', 'Check blockchain')} XAI")
            print(f"Wallet file: {os.path.basename(wallet_file)}")
            print("=" * 70 + "\n")
            return

        # Check if premium wallets available (immediate assignment)
        try:
            # Try to claim premium wallet (node operator)
            result = self.wallet_claim_system.claim_premium_wallet(
                node_id=self.node_id,
                proof_of_mining=""  # No proof needed for node operator tier
            )

            if result['success']:
                self._display_wallet_bonus(result)
                self._save_bonus_wallet(result['wallet'], tier=result['tier'])
                return

        except Exception:
            pass

        try:
            bonus_result = self.wallet_claim_system.claim_bonus_wallet(
                miner_id=self.node_id,
                proof_of_mining=""
            )
            if bonus_result['success'] and bonus_result.get('tier') != 'empty':
                self._display_wallet_bonus(bonus_result)
                self._save_bonus_wallet(bonus_result['wallet'], tier=bonus_result['tier'])
                return
        except Exception:
            pass

        # Premium/bonus wallets exhausted - user will qualify for uptime-based wallet
        print("\n[INFO] Premium & bonus wallets claimed. Run node for 30 minutes to qualify for early adopter wallet!")

    def _display_wallet_bonus(self, claim_result):
        """
        Display bonus wallet information to user

        Args:
            claim_result: Result from wallet claim system
        """

        wallet = claim_result['wallet']
        tier = claim_result['tier']

        # Determine wallet filename based on tier
        wallet_filename = 'xai_og_wallet.json' if tier == 'premium' else 'xai_early_adopter_wallet.json'

        print("\n" + "=" * 70)
        print("       CONGRATULATIONS!")
        print("=" * 70)
        print()
        print("You started a XAI coin node!")
        print()
        print("Find your bonus wallet here as a thank you:")
        print()
        print(f"  Tier: {tier.upper()}")
        print(f"  Address: {wallet['address']}")
        print()
        print("How to access your wallet:")
        print(f"  1. Your private key is saved in: {wallet_filename}")
        print("  2. Check balance: /balance/<your_address>")
        print("  3. Send coins: /send endpoint with your private key")
        print("  4. BACKUP YOUR PRIVATE KEY IMMEDIATELY!")
        print()

        if tier == 'premium':
            print("PREMIUM WALLET BONUSES:")
            print("  - Monthly reward: 200 XAI (requires 30-day uptime)")
            print("  - Keep your node running 24/7 to qualify")
            print()

        if claim_result.get('remaining_premium') is not None:
            remaining = claim_result['remaining_premium']
            print(f"  Remaining premium wallets: {remaining}")
        elif claim_result.get('remaining_standard') is not None:
            remaining = claim_result['remaining_standard']
            print(f"  Remaining standard wallets: {remaining}")

        print()
        print("=" * 70 + "\n")

    def _save_bonus_wallet(self, wallet_data, tier='standard'):
        """
        Save bonus wallet to file

        Args:
            wallet_data: Wallet information from claim
            tier: Wallet tier (premium/standard/micro)
        """

        # Premium wallets get special filename
        if tier == 'premium':
            wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_og_wallet.json')
        elif tier == 'bonus':
            wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_bonus_wallet.json')
        else:
            wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_early_adopter_wallet.json')

        save_data = {
            'address': wallet_data['address'],
            'private_key': wallet_data['private_key'],
            'public_key': wallet_data['public_key'],
            'balance': wallet_data.get('total_balance', wallet_data.get('balance', 0)),
            'claimed_at': time.time(),
            'node_id': self.node_id,
            'tier': tier
        }

        with open(wallet_file, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"[SAVED] Wallet information saved to: {os.path.basename(wallet_file)}")
        print("[WARNING] BACKUP THIS FILE IMMEDIATELY! Loss of private key = loss of funds!\n")

    def _start_uptime_wallet_checker(self):
        """
        Start background thread to check for uptime-based wallet assignment
        Checks after 30 minutes of uptime
        """
        uptime_thread = threading.Thread(target=self._check_uptime_wallet, daemon=True)
        uptime_thread.start()

    def _start_ai_bridge_loop(self, interval: int = 30):
        """Run the AI bridge loop in a background thread."""
        self._ai_bridge_stop_event = threading.Event()
        bridge_thread = threading.Thread(
            target=self._run_ai_bridge_loop,
            args=(interval,),
            daemon=True
        )
        bridge_thread.start()
        self._ai_bridge_thread = bridge_thread

    def _check_uptime_wallet(self):
        """
        Check if node qualifies for uptime-based wallet after 30 minutes
        """
        # Wait 30 minutes
        required_uptime = 30 * 60  # 30 minutes in seconds
        time.sleep(required_uptime)

        # Check if already claimed (check both possible filenames)
        premium_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_og_wallet.json')
        standard_wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_early_adopter_wallet.json')

        if os.path.exists(premium_wallet_file) or os.path.exists(standard_wallet_file):
            return  # Already have wallet

        if self.uptime_wallet_claimed:
            return  # Already processed

        # Try to claim standard wallet
        try:
            result = self.wallet_claim_system.claim_standard_wallet(self.node_id)

            if result['success']:
                self.uptime_wallet_claimed = True
                self._display_early_adopter_wallet(result)
                self._save_bonus_wallet(result['wallet'], tier=result['tier'])
                return

        except Exception as e:
            pass

        # Try micro wallet as fallback
        try:
            result = self.wallet_claim_system.claim_micro_wallet(self.node_id)

            if result['success']:
                self.uptime_wallet_claimed = True
                self._display_early_adopter_wallet(result)
                self._save_bonus_wallet(result['wallet'], tier=result['tier'])
                return

        except Exception as e:
            pass

        # No wallets available
        print("\n[INFO] All early adopter wallets have been claimed. Mine to earn XAI!")

    def _run_ai_bridge_loop(self, interval: int):
        """Background loop that periodically syncs the AI bridge."""

        while not getattr(self, '_ai_bridge_stop_event', threading.Event()).is_set():
            try:
                created = self.ai_bridge.sync_full_proposals()
                if created:
                    self.logger.info("AI bridge queued %d proposals", len(created))
            except Exception as exc:
                self.logger.error("AI bridge sync failed: %s", exc)
            time.sleep(interval)

    def _display_early_adopter_wallet(self, claim_result):
        """
        Display early adopter wallet information (after 30 min uptime)

        Args:
            claim_result: Result from wallet claim system
        """

        wallet = claim_result['wallet']
        tier = claim_result['tier']

        print("\n" + "=" * 70)
        print("       WELCOME TO XAI COIN!")
        print("=" * 70)
        print()
        print("Here is your early adopter bonus wallet:")
        print()
        print(f"  Address: {wallet['address']}")
        print()
        print("How to access your wallet:")
        print("  1. Your private key is saved in: xai_early_adopter_wallet.json")
        print("  2. Check balance: /balance/<your_address>")
        print("  3. Send coins: /send endpoint with your private key")
        print("  4. BACKUP YOUR PRIVATE KEY IMMEDIATELY!")
        print()

        if claim_result.get('remaining_standard') is not None:
            remaining = claim_result['remaining_standard']
            print(f"  Remaining early adopter wallets: {remaining}")
        elif claim_result.get('remaining_micro') is not None:
            remaining = claim_result['remaining_micro']
            print(f"  Remaining early adopter wallets: {remaining}")

        print()
        print("Thank you for supporting XAI!")
        print("=" * 70 + "\n")

    def start_mining(self):
        """Start automatic mining in background thread"""
        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        print("⛏️  Auto-mining started")

    def stop_mining(self):
        """Stop automatic mining"""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("⏸️  Auto-mining stopped")

    def _mine_continuously(self):
        """Continuously mine blocks"""
        while self.is_mining:
            if self.blockchain.pending_transactions:
                print(f"Mining block with {len(self.blockchain.pending_transactions)} transactions...")
                block = self.blockchain.mine_pending_transactions(self.miner_address)
                print(f"✅ Block {block.index} mined! Hash: {block.hash}")

                # Broadcast to peers
                self.broadcast_block(block)

            time.sleep(1)  # Small delay between mining attempts

    def add_peer(self, peer_url: str):
        """Add peer node with security checks"""
        # Extract IP from URL (simplified)
        import re
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', peer_url)
        ip_address = ip_match.group(1) if ip_match else "unknown"

        # Security check
        can_accept, error = self.p2p_security.can_accept_peer(peer_url, ip_address)
        if not can_accept:
            print(f"Peer rejected: {peer_url} - {error}")
            return False

        if peer_url not in self.peers:
            # Check max peers limit
            from p2p_security import P2PSecurityConfig
            if len(self.peers) >= P2PSecurityConfig.MAX_PEERS_TOTAL:
                print(f"Max peers reached ({P2PSecurityConfig.MAX_PEERS_TOTAL})")
                return False

            self.peers.add(peer_url)
            self.p2p_security.track_peer_connection(peer_url, ip_address)
            print(f"Added peer: {peer_url}")
            self.logger.peer_connected(len(self.peers))

        return True

    def broadcast_transaction(self, transaction: Transaction):
        """Broadcast transaction to all peers"""
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/transaction/receive",
                    json=transaction.to_dict(),
                    timeout=2
                )
            except:
                pass

    def broadcast_block(self, block):
        """Broadcast new block to all peers"""
        # Record block first seen (for propagation monitoring)
        self.blockchain.consensus_manager.propagation_monitor.record_block_first_seen(block.hash)

        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/block/receive",
                    json=block.to_dict(),
                    timeout=2
                )
            except:
                pass

    def sync_with_network(self) -> bool:
        """Sync blockchain with network"""
        longest_chain = None
        max_length = len(self.blockchain.chain)

        # Query all peers
        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/blocks", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    chain_length = data['total']

                    if chain_length > max_length:
                        # This chain is longer, get full chain
                        full_response = requests.get(
                            f"{peer}/blocks?limit={chain_length}",
                            timeout=10
                        )
                        if full_response.status_code == 200:
                            longest_chain = full_response.json()['blocks']
                            max_length = chain_length

            except Exception as e:
                print(f"Error syncing with {peer}: {e}")

        # Replace chain if we found a longer valid one
        if longest_chain and len(longest_chain) > len(self.blockchain.chain):
            # Validate new chain before replacing
            # (In production, implement full chain validation)
            print(f"Syncing blockchain... New length: {len(longest_chain)}")
            return True

        return False

    def run(self, debug=False):
        """Start the node"""
        self.start_time = time.time()

        print("=" * 60)
        print("XAI BLOCKCHAIN NODE")
        print("=" * 60)
        print(f"Network: {Config.NETWORK_TYPE.value.upper()}")
        print(f"Address Prefix: {Config.ADDRESS_PREFIX}")
        if Config.FAUCET_ENABLED:
            print(f"Faucet: ENABLED ({Config.FAUCET_AMOUNT} XAI per claim)")
        print(f"Miner Address: {self.miner_address}")
        print(f"Listening on: http://{self.host}:{self.port}")
        print(f"Blockchain height: {len(self.blockchain.chain)}")
        print(f"Network difficulty: {self.blockchain.difficulty}")
        print(f"Max Supply: {Config.MAX_SUPPLY:,.0f} XAI")
        print("=" * 60)

        # Log node startup
        network_type = Config.NETWORK_TYPE.value if hasattr(Config.NETWORK_TYPE, 'value') else 'mainnet'
        self.logger.node_started(network_type, self.port)

        # Start auto-mining by default
        self.start_mining()

        # Run Flask app
        try:
            self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        finally:
            # Log node shutdown
            self.logger.node_stopped()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='XAI Blockchain Node')
    parser.add_argument('--port', type=int, help='Port to listen on (env: XAI_PORT)')
    parser.add_argument('--host', help='Host to bind to (env: XAI_HOST)')
    parser.add_argument('--miner', help='Miner wallet address')
    parser.add_argument('--peers', nargs='+', help='Peer node URLs')

    args = parser.parse_args()

    # Create and run node
    node = BlockchainNode(host=args.host, port=args.port, miner_address=args.miner)

    # Add peers if specified
    if args.peers:
        for peer in args.peers:
            node.add_peer(peer)

    # Start the node
    node.run()

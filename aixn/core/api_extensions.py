"""
XAI Blockchain API Extensions

Adds missing endpoints for:
1. Mining control (start/stop/status)
2. Governance & voting
3. Node operator questioning
4. WebSocket real-time updates
5. Wallet creation

These extend the base node API with functionality needed for:
- Browser mining plugins
- Desktop miners
- Node operator dashboards
"""

import time
import json
import threading
import logging
import requests
from typing import Dict
from flask import Flask, jsonify, request, Response
from flask_sock import Sock
import hashlib
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from config import Config
from security_validation import SecurityValidator, ValidationError

logger = logging.getLogger(__name__)

trade_orders_counter = Counter('xai_trade_orders_total', 'Total trade orders submitted')
trade_matches_counter = Counter('xai_trade_matches_total', 'Total trade matches created')
trade_secrets_counter = Counter('xai_trade_secrets_revealed_total', 'Secrets revealed for matches')
walletconnect_sessions_counter = Counter('xai_walletconnect_sessions_total', 'WalletConnect sessions registered')
miner_active_gauge = Gauge('xai_miner_active_count', 'Number of miners currently running')


class APIExtensions:
    """
    Extended API endpoints for mining, governance, and real-time updates
    """

    def __init__(self, node):
        """
        Initialize API extensions

        Args:
            node: BlockchainNode instance
        """
        self.node = node
        self.app = node.app

        # WebSocket support
        self.sock = Sock(self.app)
        self.ws_clients = []  # Connected WebSocket clients
        self.ws_subscriptions = {}  # client_id -> [channels]

        # Wallet-trade gossip peers (hostname -> last_seen)
        self.trade_peers: Dict[str, float] = {}
        for peer in Config.WALLET_TRADE_PEERS:
            self._register_trade_peer(peer)

        # Mining state
        self.mining_threads = {}  # miner_address -> thread info
        self.mining_stats = {}  # miner_address -> stats

        # Setup new routes
        self.setup_mining_routes()
        self.setup_governance_routes()
        self.setup_questioning_routes()
        self.setup_wallet_routes()
        self.setup_wallet_trades_routes()
        self.setup_personal_ai_routes()
        self.setup_websocket_routes()

        # Start background tasks
        self.start_background_tasks()

    def setup_mining_routes(self):
        """Setup mining control endpoints"""

        @self.app.route('/mining/start', methods=['POST'])
        def start_mining():
            """Start continuous mining"""
            data = request.json

            miner_address = data.get('miner_address')
            threads = data.get('threads', 1)
            intensity = data.get('intensity', 'medium')

            if not miner_address:
                return jsonify({'error': 'miner_address required'}), 400

            # Validate intensity
            intensity_levels = {'low': 1, 'medium': 2, 'high': 4}
            if intensity not in intensity_levels:
                return jsonify({'error': 'intensity must be low, medium, or high'}), 400

            # Start mining thread
            if miner_address in self.mining_threads:
                return jsonify({'error': 'Mining already active for this address'}), 400

            # Initialize stats
            self.mining_stats[miner_address] = {
                'started_at': time.time(),
                'blocks_mined': 0,
                'xai_earned': 0,
                'shares_submitted': 0,
                'shares_accepted': 0,
                'hashrate_history': []
            }

            # Start mining
            self.node.is_mining = True
            mining_thread = threading.Thread(
                target=self._mining_worker,
                args=(miner_address, threads, intensity_levels[intensity]),
                daemon=True
            )
            mining_thread.start()

            self.mining_threads[miner_address] = {
                'thread': mining_thread,
                'threads': threads,
                'intensity': intensity,
                'started_at': time.time()
            }

            miner_active_gauge.set(len(self.mining_threads))

            # Broadcast to WebSocket clients
            self.broadcast_ws({
                'channel': 'mining',
                'event': 'started',
                'data': {
                    'miner_address': miner_address,
                    'threads': threads,
                    'intensity': intensity
                }
            })

            return jsonify({
                'success': True,
                'message': 'Mining started',
                'miner_address': miner_address,
                'threads': threads,
                'intensity': intensity,
                'expected_hashrate': f"{threads * intensity_levels[intensity] * 100} MH/s"
            })

        @self.app.route('/mining/stop', methods=['POST'])
        def stop_mining():
            """Stop mining"""
            data = request.json
            miner_address = data.get('miner_address')

            if not miner_address or miner_address not in self.mining_threads:
                return jsonify({'error': 'No active mining for this address'}), 400

            # Stop mining
            self.node.is_mining = False
            del self.mining_threads[miner_address]
            miner_active_gauge.set(len(self.mining_threads))

            # Get final stats
            stats = self.mining_stats.get(miner_address, {})
            duration = time.time() - stats.get('started_at', time.time())

            # Broadcast to WebSocket clients
            self.broadcast_ws({
                'channel': 'mining',
                'event': 'stopped',
                'data': {
                    'miner_address': miner_address,
                    'total_blocks_mined': stats.get('blocks_mined', 0),
                    'total_xai_earned': stats.get('xai_earned', 0)
                }
            })

            return jsonify({
                'success': True,
                'message': 'Mining stopped',
                'total_blocks_mined': stats.get('blocks_mined', 0),
                'total_xai_earned': stats.get('xai_earned', 0),
                'mining_duration': duration
            })

        @self.app.route('/mining/status', methods=['GET'])
        def mining_status():
            """Get mining status"""
            miner_address = request.args.get('address')

            if not miner_address:
                return jsonify({'error': 'address parameter required'}), 400

            is_mining = miner_address in self.mining_threads
            stats = self.mining_stats.get(miner_address, {})

            if not is_mining:
                return jsonify({
                    'is_mining': False,
                    'miner_address': miner_address
                })

            # Calculate hashrate
            recent_hashrates = stats.get('hashrate_history', [])[-10:]
            avg_hashrate = sum(recent_hashrates) / len(recent_hashrates) if recent_hashrates else 0

            return jsonify({
                'is_mining': True,
                'miner_address': miner_address,
                'threads': self.mining_threads[miner_address]['threads'],
                'intensity': self.mining_threads[miner_address]['intensity'],
                'hashrate': f"{recent_hashrates[-1] if recent_hashrates else 0:.1f} MH/s",
                'avg_hashrate': f"{avg_hashrate:.1f} MH/s",
                'blocks_mined_today': stats.get('blocks_mined', 0),
                'xai_earned_today': stats.get('xai_earned', 0),
                'shares_submitted': stats.get('shares_submitted', 0),
                'shares_accepted': stats.get('shares_accepted', 0),
                'acceptance_rate': (stats.get('shares_accepted', 0) / max(stats.get('shares_submitted', 1), 1)) * 100,
                'current_difficulty': self.node.blockchain.difficulty,
                'uptime': time.time() - stats.get('started_at', time.time())
            })

    def setup_governance_routes(self):
        """Setup governance and voting endpoints"""

        @self.app.route('/governance/proposals/submit', methods=['POST'])
        def submit_proposal():
            """Submit AI development proposal"""
            data = request.json

            # Create proposal (would integrate with governance_dao)
            proposal_id = hashlib.sha256(f"{time.time()}{data.get('title')}".encode()).hexdigest()[:16]

            # In production, this would call governance_dao.submit_proposal()
            return jsonify({
                'success': True,
                'proposal_id': proposal_id,
                'status': 'security_review',
                'message': 'Proposal submitted for security analysis'
            })

        @self.app.route('/governance/proposals', methods=['GET'])
        def get_proposals():
            """Get proposals by status"""
            status = request.args.get('status', 'community_vote')
            limit = request.args.get('limit', 10, type=int)

            # In production, query from governance_dao
            # For now, return sample data
            return jsonify({
                'count': 0,
                'proposals': []
            })

        @self.app.route('/governance/vote', methods=['POST'])
        def submit_vote():
            """Vote on proposal"""
            data = request.json

            proposal_id = data.get('proposal_id')
            voter_address = data.get('voter_address')
            vote = data.get('vote')

            # In production, integrate with enhanced_voting_system
            return jsonify({
                'success': True,
                'proposal_id': proposal_id,
                'vote': vote,
                'voting_power': 7503.5,
                'breakdown': {
                    'coin_power': 7000,
                    'donation_power': 503.5
                }
            })

        @self.app.route('/governance/voting-power/<address>', methods=['GET'])
        def get_voting_power(address):
            """Calculate voting power"""
            balance = self.node.blockchain.get_balance(address)

            # In production, integrate with enhanced_voting_system
            coin_power = balance * 0.70
            donation_power = 0  # Would query from AI donation history

            return jsonify({
                'address': address,
                'xai_balance': balance,
                'voting_power': {
                    'coin_power': coin_power,
                    'donation_power': donation_power,
                    'total': coin_power + donation_power
                }
            })

    def setup_questioning_routes(self):
        """Setup node operator questioning endpoints"""

        @self.app.route('/questioning/submit', methods=['POST'])
        def submit_question():
            """AI submits question"""
            data = request.json

            question_id = hashlib.sha256(f"{time.time()}{data.get('question_text')}".encode()).hexdigest()[:16]

            # Broadcast to WebSocket clients
            self.broadcast_ws({
                'channel': 'questioning',
                'event': 'new_question',
                'data': {
                    'question_id': question_id,
                    'question_text': data.get('question_text'),
                    'priority': data.get('priority'),
                    'min_operators': data.get('min_operators', 25)
                }
            })

            return jsonify({
                'success': True,
                'question_id': question_id,
                'status': 'open_for_voting',
                'voting_opened_at': time.time()
            })

        @self.app.route('/questioning/answer', methods=['POST'])
        def submit_answer():
            """Node operator submits answer"""
            data = request.json

            # In production, integrate with ai_node_operator_questioning
            return jsonify({
                'success': True,
                'question_id': data.get('question_id'),
                'total_votes': 18,
                'min_required': 25,
                'consensus_reached': False
            })

        @self.app.route('/questioning/pending', methods=['GET'])
        def get_pending_questions():
            """Get questions needing answers"""
            # In production, query from questioning system
            return jsonify({
                'count': 0,
                'questions': []
            })

    def setup_wallet_routes(self):
        """Setup wallet creation endpoints"""

        @self.app.route('/wallet/create', methods=['POST'])
        def create_wallet():
            """Create new wallet"""
            from wallet import Wallet

            wallet = Wallet()

            return jsonify({
                'success': True,
                'address': wallet.address,
                'public_key': wallet.public_key.hex(),
                'private_key': wallet.private_key.hex(),
                'warning': 'Save private key securely. Cannot be recovered.'
            })

        @self.app.route('/wallet/embedded/create', methods=['POST'])
        def create_embedded_wallet():
            """Create an embedded wallet alias (email/social)"""
            if not hasattr(self.node, 'account_abstraction'):
                return jsonify({'success': False, 'error': 'EMBEDDED_NOT_ENABLED'}), 503
            payload = request.get_json(silent=True) or {}
            alias = payload.get('alias')
            contact = payload.get('contact')
            secret = payload.get('secret')
            if not all([alias, contact, secret]):
                return jsonify({'success': False, 'error': 'alias, contact, and secret required'}), 400
            try:
                record = self.node.account_abstraction.create_embedded_wallet(alias, contact, secret)
            except ValueError as exc:
                return jsonify({'success': False, 'error': 'ALIAS_EXISTS', 'message': str(exc)}), 400
            token = self.node.account_abstraction.get_session_token(alias)
            return jsonify({
                'success': True,
                'alias': alias,
                'contact': contact,
                'address': record.address,
                'session_token': token
            })

        @self.app.route('/wallet/embedded/login', methods=['POST'])
        def login_embedded_wallet():
            if not hasattr(self.node, 'account_abstraction'):
                return jsonify({'success': False, 'error': 'EMBEDDED_NOT_ENABLED'}), 503
            payload = request.get_json(silent=True) or {}
            alias = payload.get('alias')
            secret = payload.get('secret')
            if not all([alias, secret]):
                return jsonify({'success': False, 'error': 'alias and secret required'}), 400
            token = self.node.account_abstraction.authenticate(alias, secret)
            if not token:
                return jsonify({'success': False, 'error': 'AUTH_FAILED'}), 403
            record = self.node.account_abstraction.get_record(alias)
            return jsonify({
                'success': True,
                'alias': alias,
                'address': record.address if record else None,
                'session_token': token
            })

    def setup_wallet_trades_routes(self):
        """Setup wallet trading endpoints (WalletConnect style)"""

        @self.app.route('/wallet-trades/wc/handshake', methods=['POST'])
        def walletconnect_handshake():
            data = request.json or {}
            wallet_address = data.get('wallet_address')
            if not wallet_address:
                return jsonify({'success': False, 'error': 'wallet_address required'}), 400

            handshake = self.node.blockchain.trade_manager.begin_walletconnect_handshake(wallet_address)
            walletconnect_sessions_counter.inc()
            return jsonify(handshake)

        @self.app.route('/wallet-trades/wc/confirm', methods=['POST'])
        def walletconnect_confirm():
            data = request.json or {}
            handshake_id = data.get('handshake_id')
            wallet_address = data.get('wallet_address')
            client_public = data.get('client_public')
            if not all([handshake_id, wallet_address, client_public]):
                return jsonify({'success': False, 'error': 'handshake_id, wallet_address, and client_public required'}), 400

            session = self.node.blockchain.trade_manager.complete_walletconnect_handshake(
                handshake_id, wallet_address, client_public
            )
            if not session:
                return jsonify({'success': False, 'error': 'handshake failed'}), 400
            return jsonify({'success': True, 'session_token': session['session_token']})

        @self.app.route('/wallet-seeds/snapshot', methods=['GET'])
        def wallet_seeds_snapshot():
            manifest_path = os.path.join(os.getcwd(), 'premine_manifest.json')
            summary_path = os.path.join(os.getcwd(), 'premine_wallets_SUMMARY.json')
            if not os.path.exists(manifest_path) or not os.path.exists(summary_path):
                return jsonify({'success': False, 'error': 'Manifest or summary not found'}), 404
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            return jsonify({
                'success': True,
                'manifest': manifest,
                'summary': summary
            })

        @self.app.route('/wallet-trades/register', methods=['POST'])
        def register_trade_session():
            """Create WalletConnect-style session (token + secret)"""
            data = request.json or {}
            wallet_address = data.get('wallet_address')
            if not wallet_address:
                return jsonify({'success': False, 'error': 'wallet_address required'}), 400

            session = self.node.blockchain.register_trade_session(wallet_address)
            self.node.blockchain.record_trade_event('session_registered', {
                'wallet_address': wallet_address,
                'session_token': session['session_token']
            })
            return jsonify({'success': True, **session})

        @self.app.route('/wallet-trades/orders', methods=['GET'])
        def list_trade_orders():
            orders = self.node.blockchain.get_trade_orders()
            return jsonify({'success': True, 'orders': orders})

        @self.app.route('/wallet-trades/orders', methods=['POST'])
        def create_trade_order():
            order_data = request.json or {}
            result = self.node.blockchain.submit_trade_order(order_data)

            trade_orders_counter.inc()

            event = {
                'channel': 'wallet-trades',
                'event': 'order_created' if result.get('status') == 'pending' else 'match_ready',
                'data': result
            }
            self.broadcast_ws(event)

            if result.get('status') != 'pending':
                trade_matches_counter.inc()

            order_obj = self.node.blockchain.trade_manager.get_order(result['order_id'])
            gossip_payload = {
                'type': 'order',
                'order': order_obj.to_dict() if order_obj else order_data
            }
            self._gossip_trade_event(gossip_payload)

            return jsonify(result)

        @self.app.route('/wallet-trades/gossip', methods=['POST'])
        def inbound_gossip():
            event = request.json or {}
            token = request.headers.get('X-Wallet-Trade-Secret')
            host = request.remote_addr
            if token != Config.WALLET_TRADE_PEER_SECRET:
                logger.warning(f"Rejected gossip from {host} due to missing/invalid secret")
                return jsonify({'success': False, 'error': 'Invalid peer secret'}), 403
            self._register_trade_peer(request.host_url[:-1])
            result = self.node.blockchain.trade_manager.ingest_gossip(event)
            return jsonify(result)

        @self.app.route('/wallet-trades/snapshot', methods=['GET'])
        def snapshot_orderbook():
            snapshot = self.node.blockchain.trade_manager.snapshot()
            return jsonify({'success': True, 'snapshot': snapshot})

        @self.app.route('/wallet-trades/peers/register', methods=['POST'])
        def register_trade_peer():
            data = request.json or {}
            host = data.get('host')
            secret = data.get('secret')
            if not host:
                return jsonify({'success': False, 'error': 'host required'}), 400
            if secret != Config.WALLET_TRADE_PEER_SECRET:
                return jsonify({'success': False, 'error': 'invalid secret'}), 403
            self._register_trade_peer(host)
            return jsonify({'success': True, 'host': host})

        @self.app.route('/wallet-trades/orders/<order_id>', methods=['GET'])
        def get_trade_order(order_id):
            order = self.node.blockchain.trade_manager.get_order(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            return jsonify({'success': True, 'order': order.to_dict()})

        @self.app.route('/wallet-trades/matches', methods=['GET'])
        def list_trade_matches():
            matches = self.node.blockchain.get_trade_matches()
            return jsonify({'success': True, 'matches': matches})

        @self.app.route('/wallet-trades/matches/<match_id>', methods=['GET'])
        def get_trade_match(match_id):
            match = self.node.blockchain.trade_manager.get_match(match_id)
            if not match:
                return jsonify({'success': False, 'error': 'Match not found'}), 404
            return jsonify({'success': True, 'match': match.to_dict()})

        @self.app.route('/wallet-trades/matches/<match_id>/secret', methods=['POST'])
        def submit_trade_secret(match_id):
            payload = request.json or {}
            secret = payload.get('secret')
            if not secret:
                return jsonify({'success': False, 'message': 'secret required'}), 400

            response = self.node.blockchain.reveal_trade_secret(match_id, secret)
            if response['success']:
                self.broadcast_ws({
                    'channel': 'wallet-trades',
                    'event': 'match_settlement',
                    'data': {'match_id': match_id}
                })
                trade_secrets_counter.inc()

            return jsonify(response)

        @self.app.route('/wallet-trades/backfill', methods=['GET'])
        def trade_backfill():
            limit = int(request.args.get('limit', 25))
            signed_events = self.node.blockchain.trade_manager.signed_event_batch(limit)
            return jsonify({
                'success': True,
                'events': signed_events,
                'public_key': signed_events[0]['public_key'] if signed_events else self.node.blockchain.trade_manager.audit_signer.public_key()
            })

        @self.app.route('/wallet-trades/gossip', methods=['POST'])
        def gossip_trade_event():
            event = request.json or {}
            result = self.node.blockchain.trade_manager.ingest_gossip(event)
            if result.get('success'):
                self.broadcast_ws({
                    'channel': 'wallet-trades',
                    'event': 'gossip',
                    'data': event
                })
            return jsonify(result)

        @self.app.route('/metrics', methods=['GET'])
        def metrics():
            data = generate_latest()
            return Response(data, mimetype=CONTENT_TYPE_LATEST)

        @self.app.route('/wallet-trades/history', methods=['GET'])
        def get_trade_history():
            history = self.node.blockchain.trade_history
            return jsonify({'success': True, 'history': history})

    def setup_personal_ai_routes(self):
        """Add gateways for Personal AI helper endpoints"""

        @self.app.route('/personal-ai/atomic-swap', methods=['POST'])
        def personal_atomic_swap():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            swap_details = payload.get('swap_details') or payload
            result = ctx['personal_ai'].execute_atomic_swap_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                swap_details=swap_details,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/smart-contract/create', methods=['POST'])
        def personal_contract_create():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            description = payload.get('contract_description') or payload.get('description', '')
            contract_type = payload.get('contract_type')
            result = ctx['personal_ai'].create_smart_contract_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                contract_description=description,
                contract_type=contract_type,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/smart-contract/deploy', methods=['POST'])
        def personal_contract_deploy():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            result = ctx['personal_ai'].deploy_smart_contract_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                contract_code=payload.get('contract_code', ''),
                constructor_params=payload.get('constructor_params'),
                testnet=payload.get('testnet', True),
                signature=payload.get('signature'),
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/transaction/optimize', methods=['POST'])
        def personal_transaction_optimize():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            transaction = payload.get('transaction') or payload
            if not transaction:
                return jsonify({'success': False, 'error': 'transaction required', 'message': 'Provide a transaction payload'}), 400
            result = ctx['personal_ai'].optimize_transaction_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                transaction=transaction,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/analyze', methods=['POST'])
        def personal_analyze():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            query = payload.get('query')
            if not query:
                return jsonify({'success': False, 'error': 'query required', 'message': 'Provide a query to analyze'}), 400
            result = ctx['personal_ai'].analyze_blockchain_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                query=query,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/wallet/analyze', methods=['POST'])
        def personal_wallet_analyze():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            analysis_type = payload.get('analysis_type', 'portfolio_optimization')
            result = ctx['personal_ai'].wallet_analysis_with_ai(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                analysis_type=analysis_type,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/wallet/recovery', methods=['POST'])
        def personal_wallet_recovery():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            recovery_details = payload.get('recovery_details') or payload
            guardians = recovery_details.get('guardians', [])
            for guardian in guardians:
                try:
                    self.node.validator.validate_address(guardian)
                except ValidationError as ve:
                    return jsonify({'success': False, 'error': 'INVALID_GUARDIAN_ADDRESS', 'message': str(ve)}), 400
            result = ctx['personal_ai'].wallet_recovery_advice(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                recovery_details=recovery_details,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/node/setup', methods=['POST'])
        def personal_node_setup():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            setup_request = payload.get('setup_request') or payload
            region = setup_request.get('preferred_region', '')
            try:
                if region:
                    self.node.validator.validate_string(region, 'preferred_region', max_length=100)
            except ValidationError as ve:
                return jsonify({'success': False, 'error': 'INVALID_REGION', 'message': str(ve)}), 400
            result = ctx['personal_ai'].node_setup_recommendations(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                setup_request=setup_request,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/personal-ai/liquidity/alert', methods=['POST'])
        def personal_liquidity_alert():
            ctx = self._personal_ai_context()
            if not ctx['success']:
                return jsonify(ctx), 400
            payload = request.get_json(silent=True) or {}
            pool_name = payload.get('pool_name')
            if not pool_name:
                return jsonify({'success': False, 'error': 'pool_name required', 'message': 'Specify the liquidity pool name'}), 400
            try:
                self.node.validator.validate_string(pool_name, 'pool_name', max_length=120)
            except ValidationError as ve:
                return jsonify({'success': False, 'error': 'INVALID_POOL_NAME', 'message': str(ve)}), 400
            alert_details = payload.get('alert_details') or payload
            result = ctx['personal_ai'].liquidity_alert_response(
                user_address=ctx['user_address'],
                ai_provider=ctx['ai_provider'],
                ai_model=ctx['ai_model'],
                user_api_key=ctx['user_api_key'],
                pool_name=pool_name,
                alert_details=alert_details,
                assistant_name=ctx.get('assistant_name'),
            )
            return self._personal_ai_response(result)

        @self.app.route('/governance/fiat-unlock/vote', methods=['POST'])
        def governance_fiat_unlock_vote():
            payload = request.json or {}
            address = payload.get('governance_address') or payload.get('user_address')
            support = payload.get('support', True)
            reason = payload.get('reason')
            if not address:
                return jsonify({'success': False, 'error': 'governance_address required'}), 400
            try:
                self.node.validator.validate_address(address)
            except ValidationError as ve:
                return jsonify({'success': False, 'error': 'INVALID_ADDRESS', 'message': str(ve)}), 400

            try:
                status = self.node.fiat_unlock_manager.cast_vote(address, bool(support), reason)
            except ValueError as ve:
                return jsonify({'success': False, 'error': 'VOTING_NOT_OPEN', 'message': str(ve)}), 400
            return jsonify({'success': True, 'status': status})

        @self.app.route('/governance/fiat-unlock/status', methods=['GET'])
        def governance_fiat_unlock_status():
            status = self.node.fiat_unlock_manager.get_status()
            return jsonify({'success': True, 'status': status})

        @self.app.route('/personal-ai/assistants', methods=['GET'])
        def personal_ai_assistants():
            assistant_layer = getattr(self.node, 'personal_ai', None)
            if not assistant_layer:
                return jsonify({'success': False, 'error': 'PERSONAL_AI_DISABLED'}), 503
            return jsonify({
                'success': True,
                'assistants': assistant_layer.list_micro_assistants()
            })

    def _personal_ai_context(self):
        headers = request.headers
        user_address = headers.get('X-User-Address')
        ai_provider = headers.get('X-AI-Provider', 'anthropic')
        ai_model = headers.get('X-AI-Model', 'claude-opus-4')
        user_api_key = headers.get('X-User-API-Key')
        assistant_name = headers.get('X-AI-Assistant', '').strip()

        if not all([user_address, ai_provider, ai_model, user_api_key]):
            missing = [
                key for key, value in [
                    ('X-User-Address', user_address),
                    ('X-AI-Provider', ai_provider),
                    ('X-AI-Model', ai_model),
                    ('X-User-API-Key', user_api_key),
                ] if not value
            ]
            return {
                'success': False,
                'error': 'MISSING_HEADERS',
                'message': f'Missing headers: {", ".join(missing)}'
            }

        try:
            self.node.validator.validate_address(user_address)
        except ValidationError as ve:
            return {
                'success': False,
                'error': 'INVALID_ADDRESS',
                'message': str(ve)
            }

        personal_ai = getattr(self.node, 'personal_ai', None)
        if not personal_ai:
            return {
                'success': False,
                'error': 'PERSONAL_AI_DISABLED',
                'message': 'Personal AI assistant is not configured on this node.'
            }

        return {
            'success': True,
            'personal_ai': personal_ai,
            'user_address': user_address,
            'ai_provider': ai_provider,
            'ai_model': ai_model,
            'user_api_key': user_api_key,
            'assistant_name': assistant_name or None,
        }

    def _personal_ai_response(self, result):
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    def setup_websocket_routes(self):
        """Setup WebSocket endpoints for real-time updates"""

        @self.sock.route('/ws')
        def websocket_handler(ws):
            """WebSocket connection handler"""
            client_id = hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:16]
            self.ws_clients.append({'id': client_id, 'ws': ws})
            self.ws_subscriptions[client_id] = []

            print(f"WebSocket client {client_id} connected")

            try:
                while True:
                    message = ws.receive()
                    if message:
                        data = json.loads(message)
                        self._handle_ws_message(client_id, ws, data)

            except Exception as e:
                print(f"WebSocket error for {client_id}: {e}")

            finally:
                # Cleanup
                self.ws_clients = [c for c in self.ws_clients if c['id'] != client_id]
                if client_id in self.ws_subscriptions:
                    del self.ws_subscriptions[client_id]
                print(f"WebSocket client {client_id} disconnected")

    def _handle_ws_message(self, client_id, ws, data):
        """Handle WebSocket message from client"""
        action = data.get('action')
        channel = data.get('channel')

        if action == 'subscribe' and channel:
            if client_id not in self.ws_subscriptions:
                self.ws_subscriptions[client_id] = []

            if channel not in self.ws_subscriptions[client_id]:
                self.ws_subscriptions[client_id].append(channel)
                ws.send(json.dumps({
                    'success': True,
                    'message': f'Subscribed to {channel}'
                }))

        elif action == 'unsubscribe' and channel:
            if client_id in self.ws_subscriptions:
                if channel in self.ws_subscriptions[client_id]:
                    self.ws_subscriptions[client_id].remove(channel)
                    ws.send(json.dumps({
                        'success': True,
                        'message': f'Unsubscribed from {channel}'
                    }))

    def broadcast_ws(self, message):
        """Broadcast message to subscribed WebSocket clients"""
        channel = message.get('channel')

        for client in self.ws_clients:
            client_id = client['id']
            if channel in self.ws_subscriptions.get(client_id, []):
                try:
                    client['ws'].send(json.dumps(message))
                except Exception as e:
                    print(f"Failed to send to client {client_id}: {e}")

    def _register_trade_peer(self, host: str):
        normalized = host.rstrip('/')
        if not normalized:
            return
        self.trade_peers[normalized] = time.time()
        logger.info(f"Registered wallet-trade peer {normalized}")

    def _gossip_trade_event(self, event: Dict[str, Any]):
        for host, _ in list(self.trade_peers.items()):
            try:
                url = f"{host}/wallet-trades/gossip"
                requests.post(
                    url,
                    json=event,
                    headers={'X-Wallet-Trade-Secret': Config.WALLET_TRADE_PEER_SECRET},
                    timeout=3
                )
                self.trade_peers[host] = time.time()
                logger.info(f"Gossiped trade event to {host}")
            except Exception as exc:
                logger.warning(f"Trade gossip to {host} failed: {exc}")

    def _mining_worker(self, miner_address, threads, intensity):
        """Background mining worker"""
        print(f"Mining worker started for {miner_address} ({threads} threads, intensity {intensity})")

        while self.node.is_mining and miner_address in self.mining_threads:
            try:
                # Mine a block
                if self.node.blockchain.pending_transactions:
                    block = self.node.blockchain.mine_pending_transactions(miner_address)

                    # Update stats
                    if miner_address in self.mining_stats:
                        self.mining_stats[miner_address]['blocks_mined'] += 1
                        self.mining_stats[miner_address]['xai_earned'] += self.node.blockchain.block_reward
                        self.mining_stats[miner_address]['shares_accepted'] += 1

                    # Broadcast new block
                    self.broadcast_ws({
                        'channel': 'blocks',
                        'event': 'new_block',
                        'data': {
                            'index': block.index,
                            'hash': block.hash,
                            'miner': miner_address,
                            'reward': self.node.blockchain.block_reward,
                            'transactions': len(block.transactions)
                        }
                    })

                    print(f"Block {block.index} mined by {miner_address}")

                # Calculate hashrate (simplified)
                hashrate = threads * intensity * 100
                if miner_address in self.mining_stats:
                    self.mining_stats[miner_address]['hashrate_history'].append(hashrate)
                    self.mining_stats[miner_address]['shares_submitted'] += 1

                # Broadcast mining update
                self.broadcast_ws({
                    'channel': 'mining',
                    'event': 'hashrate_update',
                    'data': {
                        'miner_address': miner_address,
                        'current_hashrate': f"{hashrate} MH/s",
                        'shares_accepted': self.mining_stats[miner_address]['shares_accepted'],
                        'timestamp': time.time()
                    }
                })

                # Sleep based on intensity (lower = longer sleep)
                time.sleep(max(1, 5 - intensity))

            except Exception as e:
                print(f"Mining error for {miner_address}: {e}")
                time.sleep(5)

        print(f"Mining worker stopped for {miner_address}")

    def start_background_tasks(self):
        """Start background monitoring tasks"""

        def stats_updater():
            """Periodically broadcast stats to WebSocket clients"""
            while True:
                time.sleep(10)  # Every 10 seconds

                # Broadcast blockchain stats
                stats = self.node.blockchain.get_stats()
                self.broadcast_ws({
                    'channel': 'stats',
                    'event': 'update',
                    'data': stats
                })

        stats_thread = threading.Thread(target=stats_updater, daemon=True)
        stats_thread.start()


# Integration with existing node
def extend_node_api(node):
    """
    Extend existing BlockchainNode with new API endpoints

    Args:
        node: BlockchainNode instance

    Returns:
        APIExtensions instance
    """
    extensions = APIExtensions(node)
    print("✅ API Extensions loaded:")
    print("   - Mining control (/mining/start, /mining/stop, /mining/status)")
    print("   - Governance API (/governance/*)")
    print("   - Questioning API (/questioning/*)")
    print("   - Wallet API (/wallet/create)")
    print("   - WebSocket API (/ws)")
    return extensions


# Usage in node.py:
# from api_extensions import extend_node_api
# extensions = extend_node_api(node)

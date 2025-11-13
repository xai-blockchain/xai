"""
XAI Blockchain - Wallet Claiming API

Multiple ways to claim early adopter wallets:
1. Explicit claiming via /claim-wallet endpoint
2. Automatic check after mining
3. Persistent notifications until claimed

Includes Time Capsule Protocol integration
"""

from flask import jsonify, request
from datetime import datetime
import os
import json
from typing import Optional

class WalletClaimingTracker:
    """Tracks unclaimed wallets and sends persistent notifications"""

    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.data_dir = data_dir
        self.pending_claims_file = os.path.join(data_dir, 'pending_wallet_claims.json')
        self.pending_claims = {}

        self._load_pending_claims()

    def _load_pending_claims(self):
        """Load pending wallet claims"""
        if os.path.exists(self.pending_claims_file):
            with open(self.pending_claims_file, 'r') as f:
                self.pending_claims = json.load(f)
        else:
            self.pending_claims = {}

    def _save_pending_claims(self):
        """Save pending claims"""
        with open(self.pending_claims_file, 'w') as f:
            json.dump(self.pending_claims, f, indent=2)

    def register_eligible_claimer(self, identifier: str, context: str = 'unknown'):
        """
        Register someone as eligible to claim wallet

        Args:
            identifier: Node ID, miner address, or unique identifier
            context: How they became eligible (node_start, first_mine, etc.)
        """
        if identifier not in self.pending_claims:
            self.pending_claims[identifier] = {
                'identifier': identifier,
                'registered_utc': datetime.utcnow().timestamp(),
                'context': context,
                'notification_count': 0,
                'last_notification_utc': None,
                'claimed': False,
                'dismissed': False,
                'last_dismissed_utc': None
            }
            self._save_pending_claims()

    def mark_claimed(self, identifier: str):
        """Mark wallet as claimed"""
        if identifier in self.pending_claims:
            self.pending_claims[identifier]['claimed'] = True
            self.pending_claims[identifier]['claimed_utc'] = datetime.utcnow().timestamp()
            self._save_pending_claims()

    def get_unclaimed_notification(self, identifier: str) -> dict:
        """Get notification for unclaimed wallet"""
        if identifier not in self.pending_claims:
            return None

        claim = self.pending_claims[identifier]
        if claim['claimed']:
            return None

        now = datetime.utcnow().timestamp()
        freq = 30 * 86400 if claim.get('dismissed') else 86400
        last = claim.get('last_notification_utc')
        if last and (now - last) < freq:
            return None

        claim['notification_count'] += 1
        claim['last_notification_utc'] = now
        self._save_pending_claims()

        reminder = (
            'Daily reminder: your pre-loaded wallet is safe & secure and waiting to be claimed.'
            if not claim.get('dismissed') else
            'Monthly reminder: your wallet is still ready whenever you return.'
        )

        return {
            'message': '🎁 UNCLAIMED WALLET AVAILABLE!',
            'details': reminder,
            'action': 'Call POST /claim-wallet to claim your wallet or POST /claim-wallet/notification/dismiss to postpone',
            'notification_number': claim['notification_count']
        }

    def dismiss_notification(self, identifier: str) -> bool:
        if identifier not in self.pending_claims:
            return False
        claim = self.pending_claims[identifier]
        claim['dismissed'] = True
        claim['last_dismissed_utc'] = datetime.utcnow().timestamp()
        self._save_pending_claims()
        return True

    def pending_claims_summary(self) -> list:
        """Return a snapshot of all pending wallet claims for dashboards."""
        now = datetime.utcnow().timestamp()
        summary = []
        for claim in self.pending_claims.values():
            if claim.get('claimed'):
                continue
            freq = 30 * 86400 if claim.get('dismissed') else 86400
            last_notified = claim.get('last_notification_utc') or claim.get('registered_utc') or now
            next_due = last_notified + freq
            summary.append({
                'identifier': claim['identifier'],
                'context': claim.get('context'),
                'notification_count': claim.get('notification_count', 0),
                'dismissed': claim.get('dismissed', False),
                'last_notification_utc': claim.get('last_notification_utc'),
                'next_notification_due': next_due,
                'next_notification_due_iso': datetime.utcfromtimestamp(next_due).isoformat() + 'Z'
            })
        return summary

def setup_wallet_claiming_api(app, node):
    """
    Setup wallet claiming API endpoints

    Args:
        app: Flask app instance
        node: XAI Node instance
    """

    # Initialize tracker
    tracker = WalletClaimingTracker(node.data_dir if hasattr(node, 'data_dir') else None)

    @app.route('/claim-wallet', methods=['POST'])
    def claim_wallet():
        """
        Explicit wallet claiming endpoint

        Body:
        {
          "identifier": "node_id or miner_address",
          "uptime_minutes": 30  # Optional: how long node has been running
        }

        Response:
        {
          "success": true,
          "tier": "premium|standard|micro",
          "wallet": {...},
          "time_capsule_offer": {...}  # If eligible
        }
        """
        data = request.get_json()

        if not data or 'identifier' not in data:
            return jsonify({'error': 'Missing identifier'}), 400

        identifier = data['identifier']
        uptime_minutes = data.get('uptime_minutes', 0)
        tracker.register_eligible_claimer(identifier, context='claim_wallet')

        # Check if already claimed
        wallet_files = ['xai_og_wallet.json', 'xai_early_adopter_wallet.json']
        for wallet_file in wallet_files:
            full_path = os.path.join(os.path.dirname(__file__), '..', wallet_file)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    existing_wallet = json.load(f)
                    if existing_wallet.get('node_id') == identifier:
                        return jsonify({
                            'success': False,
                            'error': 'Wallet already claimed',
                            'wallet_file': wallet_file,
                            'address': existing_wallet['address']
                        })

        # Try to claim premium wallet first (immediate)
        try:
            result = node.wallet_claim_system.claim_premium_wallet(
                node_id=identifier,
                proof_of_mining=None  # No proof needed
            )

            if result['success']:
                # Save wallet
                node._save_bonus_wallet(result['wallet'], tier=result['tier'])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                return jsonify({
                    'success': True,
                    'tier': 'premium',
                    'wallet': {
                        'address': result['wallet']['address'],
                        'file': 'xai_og_wallet.json'
                    },
                    'message': 'CONGRATULATIONS! Premium wallet claimed!',
                    'remaining_premium': result.get('remaining_premium', 0)
                })

        except Exception:
            pass  # Try standard/micro

        try:
            bonus_result = node.wallet_claim_system.claim_bonus_wallet(
                miner_id=identifier
            )

            if bonus_result['success'] and bonus_result.get('tier') != 'empty':
                node._save_bonus_wallet(bonus_result['wallet'], tier=bonus_result['tier'])
                tracker.mark_claimed(identifier)
                response = {
                    'success': True,
                    'tier': bonus_result['tier'],
                    'wallet': bonus_result['wallet'],
                    'message': bonus_result.get('message', 'Bonus wallet claimed!')
                }
                if 'remaining_bonus' in bonus_result:
                    response['remaining_bonus'] = bonus_result['remaining_bonus']
                return jsonify(response)

        except Exception:
            pass

        # Check uptime requirement for standard/micro (30 minutes)
        if uptime_minutes < 30:
            tracker.register_eligible_claimer(identifier, 'pending_uptime')
            return jsonify({
                'success': True,
                'tier': 'pending',
                'required_uptime_minutes': 30,
                'current_uptime_minutes': uptime_minutes,
                'message': f'Run your node for {30 - uptime_minutes} more minutes to unlock your wallet'
            }), 200

        # Try standard wallet
        try:
            result = node.wallet_claim_system.claim_standard_wallet(identifier)

            if result['success']:
                # Save wallet
                node._save_bonus_wallet(result['wallet'], tier=result['tier'])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                response = {
                    'success': True,
                    'tier': 'standard',
                    'wallet': {
                        'address': result['wallet']['address'],
                        'balance': result['wallet']['balance'],
                        'file': 'xai_early_adopter_wallet.json'
                    },
                    'message': 'WELCOME TO XAI COIN! Standard wallet claimed!',
                    'remaining_standard': result.get('remaining_standard', 0)
                }

                # Add time capsule offer if eligible
                if 'time_capsule_offer' in result:
                    response['time_capsule_offer'] = result['time_capsule_offer']
                    response['message'] += '\n\n🎁 SPECIAL OFFER AVAILABLE! Check time_capsule_offer field.'

                return jsonify(response)

        except Exception as e:
            pass  # Try micro

        # Try micro wallet
        try:
            result = node.wallet_claim_system.claim_micro_wallet(identifier)

            if result['success']:
                # Save wallet
                node._save_bonus_wallet(result['wallet'], tier=result['tier'])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                return jsonify({
                    'success': True,
                    'tier': 'micro',
                    'wallet': {
                        'address': result['wallet']['address'],
                        'balance': result['wallet']['balance'],
                        'file': 'xai_early_adopter_wallet.json'
                    },
                    'message': 'WELCOME TO XAI COIN! Micro wallet claimed!',
                    'remaining_micro': result.get('remaining_micro', 0)
                })

        except Exception as e:
            pass

        return jsonify({
            'success': True,
            'tier': 'empty',
            'message': 'All allocated early adopter wallets have been issued; an empty wallet is reserved for you.'
        }), 200

    @app.route('/check-unclaimed-wallet/<identifier>', methods=['GET'])
    def check_unclaimed_wallet(identifier):
        """
        Check if user has unclaimed wallet

        Response:
        {
          "unclaimed": true/false,
          "notification": {...}
        }
        """
        notification = tracker.get_unclaimed_notification(identifier)

        if notification:
            return jsonify({
                'unclaimed': True,
                'notification': notification
            })
        else:
            return jsonify({
                'unclaimed': False,
                'message': 'No unclaimed wallet or already claimed'
            })

    @app.route('/claim-wallet/notification/dismiss', methods=['POST'])
    def dismiss_wallet_notification():
        data = request.get_json() or {}
        identifier = data.get('identifier')
        if not identifier:
            return jsonify({'success': False, 'error': 'Missing identifier'}), 400
        tracker.dismiss_notification(identifier)
        return jsonify({'success': True, 'message': 'Notifications dismissed; monthly reminders will resume.'}), 200

    @app.route('/wallet-claims/summary', methods=['GET'])
    def wallet_claims_summary():
        summary = tracker.pending_claims_summary()
        return jsonify({
            'success': True,
            'pending_count': len(summary),
            'pending': summary
        })

    @app.route('/accept-time-capsule', methods=['POST'])
    def accept_time_capsule():
        """
        Accept time capsule protocol offer

        Body:
        {
          "wallet_address": "AIXN...",
          "accept": true/false
        }

        Response:
        {
          "success": true,
          "message": "Time Capsule Protocol Initiated",
          "locked_wallet": {...},
          "replacement_wallet": {...}
        }
        """
        data = request.get_json()

        if not data or 'wallet_address' not in data:
            return jsonify({'error': 'Missing wallet_address'}), 400

        wallet_address = data['wallet_address']
        accept = data.get('accept', False)

        # Load wallet data
        wallet_file = os.path.join(os.path.dirname(__file__), '..', 'xai_early_adopter_wallet.json')
        if not os.path.exists(wallet_file):
            return jsonify({'error': 'Wallet file not found'}), 404

        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)

        if wallet_data['address'] != wallet_address:
            return jsonify({'error': 'Wallet address mismatch'}), 400

        # Check eligibility
        if not wallet_data.get('time_capsule_eligible', False):
            return jsonify({'error': 'Wallet not eligible for time capsule protocol'}), 400

        if not accept:
            return jsonify({
                'success': True,
                'message': 'Time capsule protocol declined',
                'wallet_unchanged': True
            })

        # Initiate time capsule
        from aixn.core.time_capsule_protocol import TimeCapsuleProtocol

        time_capsule = TimeCapsuleProtocol(blockchain=node.blockchain if hasattr(node, 'blockchain') else None)

        result = time_capsule.initiate_time_capsule(wallet_data, user_accepted=True)

        if not result['success']:
            return jsonify(result), 400

        # Replace wallet file with replacement wallet
        with open(wallet_file, 'w') as f:
            json.dump(result['replacement_wallet'], f, indent=2)

        print(result['protocol_message'])

        return jsonify({
            'success': True,
            'message': 'Time Capsule Protocol Engaged',
            'locked_wallet': result['locked_wallet'],
            'replacement_wallet': {
                'address': result['replacement_wallet']['address'],
                'balance': 0,
                'file': 'xai_early_adopter_wallet.json (updated)'
            },
            'unlock_message': f"You may claim your wallet with {result['locked_wallet']['amount']} XAI on {result['locked_wallet']['unlock_date_utc']}"
        })

    return tracker

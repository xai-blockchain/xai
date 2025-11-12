"""Minimal mining bonus manager stub used for local testing."""


class MiningBonusManager:
    """Simple stub replicating wallet bonus API for tests."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir

    def register_miner(self, address):
        return {'success': True, 'miner': address}

    def check_achievements(self, address, blocks_mined, streak_days):
        return {'success': True, 'achievements': []}

    def claim_bonus(self, address, bonus_type):
        return {'success': True, 'bonus_type': bonus_type}

    def create_referral_code(self, address):
        return {'success': True, 'referral_code': f'XAI-{address[:6]}'}

    def use_referral_code(self, new_address, referral_code):
        return {'success': True, 'rewarded': new_address}

    def get_user_bonuses(self, address):
        return {'success': True, 'bonuses': []}

    def get_leaderboard(self, limit=10):
        return {'success': True, 'leaderboard': []}

    def get_stats(self):
        return {'miners': 0, 'total_rewards': 0}

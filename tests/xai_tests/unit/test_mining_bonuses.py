"""
Unit tests for Mining Bonuses module

Tests early adopter bonuses, achievements, referrals, and social bonuses
"""

import json
import pytest
import tempfile
import shutil
import time
from pathlib import Path

from xai.core.mining_bonuses import MiningBonusManager


class TestMiningBonusManager:
    """Test mining bonus manager"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create MiningBonusManager with temp storage"""
        return MiningBonusManager(data_dir=temp_dir)

    def test_init(self, manager):
        """Test initialization"""
        assert manager.early_adopter_tiers[100] == 100
        assert manager.achievement_bonuses["first_block"] == 5
        assert manager.referral_bonuses["refer_friend"] == 10

    def test_register_miner_first_time(self, manager):
        """Test registering new miner"""
        result = manager.register_miner("XAI_MINER1")

        assert result["success"] is True
        assert result["registration_number"] == 1
        assert result["early_adopter_bonus"] == 100

    def test_register_miner_already_registered(self, manager):
        """Test registering already registered miner"""
        manager.register_miner("XAI_MINER1")
        result = manager.register_miner("XAI_MINER1")

        assert result["success"] is False

    def test_early_adopter_tier_100(self, manager):
        """Test first 100 miners get 100 AXN"""
        result = manager.register_miner("XAI_MINER1")
        assert result["early_adopter_bonus"] == 100

    def test_early_adopter_tier_1000(self, manager):
        """Test miners 101-1000 get 50 AXN"""
        # Register 100 miners first
        for i in range(100):
            manager.register_miner(f"XAI_{i}")

        result = manager.register_miner("XAI_MINER_101")
        assert result["early_adopter_bonus"] == 50

    def test_check_achievements_first_block(self, manager):
        """Test first block achievement"""
        manager.register_miner("XAI_MINER")

        result = manager.check_achievements("XAI_MINER", blocks_mined=1, streak_days=0)

        assert result["success"] is True
        assert any(a["type"] == "first_block" for a in result["new_achievements"])

    def test_check_achievements_ten_blocks(self, manager):
        """Test 10 blocks achievement"""
        manager.register_miner("XAI_MINER")

        result = manager.check_achievements("XAI_MINER", blocks_mined=10, streak_days=0)

        achievements = result["new_achievements"]
        assert any(a["type"] == "ten_blocks" for a in achievements)

    def test_check_achievements_hundred_blocks(self, manager):
        """Test 100 blocks achievement"""
        manager.register_miner("XAI_MINER")

        result = manager.check_achievements("XAI_MINER", blocks_mined=100, streak_days=0)

        achievements = result["new_achievements"]
        assert any(a["type"] == "hundred_blocks" for a in achievements)

    def test_check_achievements_seven_day_streak(self, manager):
        """Test 7-day streak achievement"""
        manager.register_miner("XAI_MINER")

        result = manager.check_achievements("XAI_MINER", blocks_mined=50, streak_days=7)

        achievements = result["new_achievements"]
        assert any(a["type"] == "seven_day_streak" for a in achievements)

    def test_check_achievements_not_registered(self, manager):
        """Test achievements for unregistered miner"""
        result = manager.check_achievements("XAI_UNKNOWN", blocks_mined=10, streak_days=0)

        assert "error" in result

    def test_claim_bonus_tweet_verification(self, manager):
        """Test claiming tweet verification bonus"""
        manager.register_miner("XAI_MINER")

        result = manager.claim_bonus("XAI_MINER", "tweet_verification")

        assert result["success"] is True
        assert result["amount"] == 5

    def test_claim_bonus_discord_join(self, manager):
        """Test claiming Discord join bonus"""
        manager.register_miner("XAI_MINER")

        result = manager.claim_bonus("XAI_MINER", "discord_join")

        assert result["success"] is True
        assert result["amount"] == 2

    def test_claim_bonus_already_claimed(self, manager):
        """Test claiming bonus twice"""
        manager.register_miner("XAI_MINER")
        manager.claim_bonus("XAI_MINER", "tweet_verification")

        result = manager.claim_bonus("XAI_MINER", "tweet_verification")

        assert result["success"] is False

    def test_claim_bonus_unknown_type(self, manager):
        """Test claiming unknown bonus type"""
        manager.register_miner("XAI_MINER")

        result = manager.claim_bonus("XAI_MINER", "unknown_bonus")

        assert result["success"] is False

    def test_create_referral_code(self, manager):
        """Test creating referral code"""
        manager.register_miner("XAI_REFERRER")

        result = manager.create_referral_code("XAI_REFERRER")

        assert result["success"] is True
        assert "referral_code" in result
        assert len(result["referral_code"]) == 8

    def test_create_referral_code_already_exists(self, manager):
        """Test creating referral code when already exists"""
        manager.register_miner("XAI_REFERRER")
        manager.create_referral_code("XAI_REFERRER")

        result = manager.create_referral_code("XAI_REFERRER")

        assert result["success"] is True
        assert "already exists" in result["message"]

    def test_use_referral_code(self, manager):
        """Test using referral code"""
        manager.register_miner("XAI_REFERRER")
        ref_result = manager.create_referral_code("XAI_REFERRER")
        code = ref_result["referral_code"]

        result = manager.use_referral_code("XAI_NEW", code)

        assert result["success"] is True
        assert result["referrer_bonus"] == 10

    def test_use_referral_code_invalid(self, manager):
        """Test using invalid referral code"""
        result = manager.use_referral_code("XAI_NEW", "INVALID")

        assert result["success"] is False

    def test_check_referral_milestone(self, manager):
        """Test referral milestone bonus"""
        # Setup referral
        manager.register_miner("XAI_REFERRER")
        ref_result = manager.create_referral_code("XAI_REFERRER")
        manager.use_referral_code("XAI_FRIEND", ref_result["referral_code"])

        # Check milestone
        result = manager.check_referral_milestone(
            "XAI_REFERRER",
            "XAI_FRIEND",
            blocks_mined=10
        )

        assert result["success"] is True
        assert result["referrer_bonus"] == 25

    def test_check_referral_milestone_not_reached(self, manager):
        """Test milestone not yet reached"""
        manager.register_miner("XAI_REFERRER")
        ref_result = manager.create_referral_code("XAI_REFERRER")
        manager.use_referral_code("XAI_FRIEND", ref_result["referral_code"])

        result = manager.check_referral_milestone(
            "XAI_REFERRER",
            "XAI_FRIEND",
            blocks_mined=5
        )

        assert result["success"] is False

    def test_get_user_bonuses(self, manager):
        """Test getting user bonuses"""
        manager.register_miner("XAI_MINER")
        manager.claim_bonus("XAI_MINER", "tweet_verification")

        result = manager.get_user_bonuses("XAI_MINER")

        assert result["success"] is True
        assert "miner_stats" in result
        assert "social_bonuses" in result

    def test_get_leaderboard(self, manager):
        """Test getting bonus leaderboard"""
        for i in range(5):
            manager.register_miner(f"XAI_{i}")
            manager.claim_bonus(f"XAI_{i}", "tweet_verification")

        leaderboard = manager.get_leaderboard(limit=3)

        assert len(leaderboard) <= 3

    def test_get_stats(self, manager):
        """Test getting system statistics"""
        manager.register_miner("XAI_MINER1")
        manager.register_miner("XAI_MINER2")

        stats = manager.get_stats()

        assert stats["total_registered_miners"] == 2
        assert "early_adopter_tiers" in stats

    def test_bonus_cap_blocks_excess_awards(self, temp_dir):
        """Ensure supply cap prevents inflationary bonuses."""
        manager = MiningBonusManager(data_dir=temp_dir)
        manager.max_bonus_supply = 50

        result = manager.register_miner("XAI_CAP_LIMIT")

        assert result["success"] is True
        assert result["early_adopter_bonus"] == 0
        assert "bonus_error" in result

    def test_bonus_claim_fails_when_cap_reached(self, temp_dir):
        """Ensure claiming bonuses fails once cap is exhausted."""
        manager = MiningBonusManager(data_dir=temp_dir)
        manager.max_bonus_supply = 105
        manager.register_miner("XAI_CAP_USER")
        tweet_result = manager.claim_bonus("XAI_CAP_USER", "tweet_verification")
        assert tweet_result["success"] is True

        second_claim = manager.claim_bonus("XAI_CAP_USER", "discord_join")

        assert second_claim["success"] is False
        assert "error" in second_claim

    def test_bonus_configuration_bounds_enforced(self, tmp_path):
        """Configuration exceeding cap should fail immediately."""
        low_cap_dir = tmp_path / "low_cap_bonus"
        low_cap_dir.mkdir()
        with pytest.raises(ValueError):
            MiningBonusManager(data_dir=str(low_cap_dir), max_bonus_supply=1000)

    def test_bonus_config_overrides_applied(self, tmp_path):
        """Custom configuration from bonus_config.json should be respected."""
        config_dir = tmp_path / "override_bonus"
        config_dir.mkdir()
        config_path = config_dir / "bonus_config.json"
        config = {
            "early_adopter_tiers": {"50": 25, "500": 5},
            "achievement_bonuses": {"first_block": 2},
            "referral_bonuses": {"refer_friend": 4},
            "social_bonuses": {"tweet_verification": 1.5},
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

        manager = MiningBonusManager(data_dir=str(config_dir), max_bonus_supply=250000)

        assert manager.early_adopter_tiers[50] == 25
        assert manager.early_adopter_tiers[500] == 5
        assert manager.achievement_bonuses["first_block"] == 2
        assert manager.referral_bonuses["refer_friend"] == 4
        assert manager.social_bonuses["tweet_verification"] == 1.5

    def test_bonus_config_invalid_values_raise(self, tmp_path):
        """Invalid configuration values should fail validation."""
        config_dir = tmp_path / "invalid_bonus"
        config_dir.mkdir()
        config_path = config_dir / "bonus_config.json"
        config_path.write_text(
            json.dumps({"early_adopter_tiers": {"100": -5}}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            MiningBonusManager(data_dir=str(config_dir), max_bonus_supply=10000)

    def test_update_miner_stats(self, manager):
        """Test updating miner statistics"""
        manager.register_miner("XAI_MINER")

        manager.update_miner_stats(
            "XAI_MINER",
            blocks_mined=50,
            streak_days=5,
            mining_reward=500.0
        )

        assert manager.miners["XAI_MINER"]["blocks_mined"] == 50
        assert manager.miners["XAI_MINER"]["current_streak"] == 5

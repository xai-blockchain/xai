"""
Test suite for XAI Blockchain - XAIToken functionality.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from xai_token import XAIToken

class TestXAIToken:
    """Tests for the XAIToken class."""

    def test_initialization(self):
        """Test XAIToken initializes with default or provided values."""
        token = XAIToken()
        assert token.total_supply == 0
        assert token.supply_cap == 121_000_000
        assert token.balances == {}
        assert token.vesting_schedules == {}

        token_custom = XAIToken(initial_supply=1000, supply_cap=200_000_000)
        assert token_custom.total_supply == 1000
        assert token_custom.supply_cap == 200_000_000

    def test_mint_tokens_success(self):
        """Test successful minting of tokens."""
        token = XAIToken(initial_supply=0, supply_cap=100)
        assert token.mint("address1", 50) is True
        assert token.total_supply == 50
        assert token.balances["address1"] == 50

        assert token.mint("address2", 30) is True
        assert token.total_supply == 80
        assert token.balances["address2"] == 30
        assert token.balances["address1"] == 50 # Ensure other balances are unaffected

    def test_mint_tokens_exceed_cap(self):
        """Test minting fails when exceeding supply cap."""
        token = XAIToken(initial_supply=90, supply_cap=100)
        assert token.mint("address1", 20) is False
        assert token.total_supply == 90 # Supply should not change
        assert "address1" not in token.balances # No new balance entry

    def test_mint_tokens_zero_or_negative_amount(self):
        """Test minting fails for zero or negative amounts."""
        token = XAIToken(initial_supply=0, supply_cap=100)
        assert token.mint("address1", 0) is False
        assert token.total_supply == 0
        assert token.mint("address1", -10) is False
        assert token.total_supply == 0

    def test_create_vesting_schedule_success(self):
        """Test successful creation of a vesting schedule."""
        token = XAIToken(initial_supply=1000, supply_cap=100_000_000)
        token.balances["vesting_address"] = 500 # Fund the address for vesting
        
        cliff_duration = 3600 # 1 hour
        total_duration = 7200 # 2 hours
        assert token.create_vesting_schedule("vesting_address", 100, cliff_duration, total_duration) is True
        
        schedule = token.vesting_schedules["vesting_address"]
        assert schedule["amount"] == 100
        assert schedule["released"] == 0
        assert schedule["cliff_end"] > time.time()
        assert schedule["end_date"] > schedule["cliff_end"]

    def test_create_vesting_schedule_insufficient_balance(self):
        """Test creating vesting schedule fails with insufficient balance."""
        token = XAIToken(initial_supply=100, supply_cap=100_000_000)
        token.balances["vesting_address"] = 50 # Not enough for 100
        
        assert token.create_vesting_schedule("vesting_address", 100, 3600, 7200) is False
        assert "vesting_address" not in token.vesting_schedules

    def test_get_token_metrics(self):
        """Test retrieval of token metrics."""
        token = XAIToken(initial_supply=1000, supply_cap=121_000_000)
        token.balances["address1"] = 500
        token.balances["address2"] = 500
        
        # Create a vesting schedule to affect circulating supply
        token.balances["vesting_address"] = 200 # Ensure balance for vesting
        token.create_vesting_schedule("vesting_address", 100, 3600, 7200)

        metrics = token.get_token_metrics()
        assert metrics["total_supply"] == 1000
        assert metrics["supply_cap"] == 121_000_000
        # Circulating supply should be total_supply - vested_amount (100 in this case)
        assert metrics["circulating_supply"] == 900

    def test_calculate_circulating_supply_no_vesting(self):
        """Test circulating supply calculation without any vesting schedules."""
        token = XAIToken(initial_supply=1000, supply_cap=121_000_000)
        assert token.calculate_circulating_supply() == 1000

    def test_calculate_circulating_supply_with_vesting(self):
        """Test circulating supply calculation with active vesting schedules."""
        token = XAIToken(initial_supply=1000, supply_cap=121_000_000)
        token.balances["vesting_address1"] = 200
        token.create_vesting_schedule("vesting_address1", 100, 3600, 7200) # 100 vested
        
        token.balances["vesting_address2"] = 150
        token.create_vesting_schedule("vesting_address2", 50, 3600, 7200) # 50 vested
        
        # Total vested = 100 + 50 = 150
        # Circulating = 1000 - 150 = 850
        assert token.calculate_circulating_supply() == 850

    def test_calculate_circulating_supply_with_released_vesting(self):
        """Test circulating supply calculation with partially released vested tokens."""
        token = XAIToken(initial_supply=1000, supply_cap=121_000_000)
        token.balances["vesting_address"] = 200
        token.create_vesting_schedule("vesting_address", 100, 3600, 7200)
        
        # Manually simulate some tokens being released
        token.vesting_schedules["vesting_address"]["released"] = 40
        
        # Total vested = 100 - 40 = 60
        # Circulating = 1000 - 60 = 940
        assert token.calculate_circulating_supply() == 940


"""Simple coverage test for time_capsule module"""
import pytest
import time
from unittest.mock import Mock, patch
from xai.core.time_capsule import (
    TimeCapsuleType,
    TimeCapsule,
)


def test_time_capsule_type():
    """Test TimeCapsuleType constants"""
    assert TimeCapsuleType.XAI_ONLY == "xai_only"
    assert TimeCapsuleType.CROSS_CHAIN == "cross_chain"


def test_time_capsule_init():
    """Test TimeCapsule initialization"""
    unlock_time = int(time.time()) + 3600  # 1 hour from now

    capsule = TimeCapsule(
        capsule_id="capsule_1",
        creator="creator_addr",
        beneficiary="beneficiary_addr",
        unlock_time=unlock_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
        amount=100.0,
    )

    assert capsule.capsule_id == "capsule_1"
    assert capsule.creator == "creator_addr"
    assert capsule.beneficiary == "beneficiary_addr"
    assert capsule.unlock_time == unlock_time
    assert capsule.amount == 100.0


def test_time_capsule_unlocked():
    """Test is_unlocked for past time"""
    past_time = int(time.time()) - 3600  # 1 hour ago

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=past_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    assert capsule.is_unlocked() is True


def test_time_capsule_locked():
    """Test is_unlocked for future time"""
    future_time = int(time.time()) + 3600  # 1 hour from now

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=future_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    assert capsule.is_unlocked() is False


def test_time_remaining():
    """Test time_remaining method"""
    future_time = int(time.time()) + 7200  # 2 hours

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=future_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    remaining = capsule.time_remaining()
    assert remaining > 0
    assert remaining <= 7200


def test_days_remaining():
    """Test days_remaining method"""
    future_time = int(time.time()) + 86400  # 1 day

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=future_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    days = capsule.days_remaining()
    assert days > 0
    assert days <= 1.0


def test_to_dict():
    """Test to_dict method"""
    unlock_time = int(time.time()) + 3600

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=unlock_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
        amount=50.0,
        coin_type="XAI",
        message="Test message",
    )

    data = capsule.to_dict()

    assert data["capsule_id"] == "c1"
    assert data["creator"] == "a1"
    assert data["beneficiary"] == "a2"
    assert data["amount"] == 50.0
    assert "unlock_date" in data
    assert "is_unlocked" in data
    assert "time_remaining_seconds" in data
    assert "days_remaining" in data


def test_from_dict():
    """Test from_dict class method"""
    unlock_time = int(time.time()) + 3600

    data = {
        "capsule_id": "c1",
        "creator": "a1",
        "beneficiary": "a2",
        "unlock_time": unlock_time,
        "capsule_type": TimeCapsuleType.XAI_ONLY,
        "amount": 100.0,
        "coin_type": "XAI",
        "message": "Hello",
    }

    capsule = TimeCapsule.from_dict(data)

    assert capsule.capsule_id == "c1"
    assert capsule.creator == "a1"
    assert capsule.amount == 100.0


def test_time_capsule_with_htlc():
    """Test TimeCapsule with HTLC details"""
    unlock_time = int(time.time()) + 3600

    htlc_details = {
        "hash": "abc123",
        "chain": "BTC",
    }

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=unlock_time,
        capsule_type=TimeCapsuleType.CROSS_CHAIN,
        htlc_details=htlc_details,
    )

    assert capsule.htlc_details == htlc_details


def test_time_capsule_with_metadata():
    """Test TimeCapsule with metadata"""
    unlock_time = int(time.time()) + 3600

    metadata = {
        "purpose": "savings",
        "notes": "test",
    }

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=unlock_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
        metadata=metadata,
    )

    assert capsule.metadata == metadata


def test_claimed_status():
    """Test claimed status tracking"""
    unlock_time = int(time.time()) + 3600

    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=unlock_time,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    assert capsule.claimed is False
    assert capsule.claimed_time is None

    # Simulate claiming
    capsule.claimed = True
    capsule.claimed_time = int(time.time())

    assert capsule.claimed is True
    assert capsule.claimed_time > 0


def test_created_time():
    """Test created_time is set"""
    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=int(time.time()) + 3600,
        capsule_type=TimeCapsuleType.XAI_ONLY,
    )

    assert capsule.created_time > 0
    assert capsule.created_time <= int(time.time())


def test_from_dict_with_defaults():
    """Test from_dict with minimal data"""
    data = {
        "capsule_id": "c1",
        "creator": "a1",
        "beneficiary": "a2",
        "unlock_time": int(time.time()) + 3600,
    }

    capsule = TimeCapsule.from_dict(data)

    assert capsule.capsule_type == TimeCapsuleType.XAI_ONLY
    assert capsule.amount == 0
    assert capsule.coin_type == "XAI"


def test_to_dict_comprehensive():
    """Test to_dict returns all fields"""
    capsule = TimeCapsule(
        capsule_id="c1",
        creator="a1",
        beneficiary="a2",
        unlock_time=int(time.time()) + 3600,
        capsule_type=TimeCapsuleType.CROSS_CHAIN,
        amount=100.0,
        coin_type="BTC",
        message="Test",
        htlc_details={"hash": "123"},
        metadata={"key": "value"},
    )

    data = capsule.to_dict()

    assert "htlc_details" in data
    assert "metadata" in data
    assert "created_time" in data
    assert "claimed" in data

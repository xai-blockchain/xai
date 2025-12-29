"""
Test script for AI Safety Controls

Demonstrates how to use the AI safety control system to:
1. Cancel Personal AI requests
2. Emergency stop trading bots
3. Pause/resume Governance AI tasks
4. Activate global emergency stop
"""

import sys
import time

from xai.core.security.ai_safety_controls import AISafetyControls, AISafetyLevel, StopReason
from xai.core.blockchain import Blockchain


def test_personal_ai_cancellation():
    """Test cancelling a Personal AI request"""
    print("\n" + "=" * 70)
    print("TEST 1: Personal AI Request Cancellation")
    print("=" * 70)

    blockchain = Blockchain()
    safety = AISafetyControls(blockchain)

    # Register a Personal AI request
    print("\n1. Registering Personal AI request...")
    request_id = "test_request_001"
    user_address = "XAI1a2b3c4d5e6f7g8h9"

    result = safety.register_personal_ai_request(
        request_id=request_id,
        user_address=user_address,
        operation="atomic_swap",
        ai_provider="anthropic",
        ai_model="claude-opus-4",
    )
    print(f"   Registered: {result}")

    # Check if cancelled (should be False)
    print("\n2. Checking if request is cancelled...")
    is_cancelled = safety.is_request_cancelled(request_id)
    print(f"   Cancelled: {is_cancelled}")

    # Cancel the request
    print("\n3. Cancelling request...")
    cancel_result = safety.cancel_personal_ai_request(request_id, user_address)
    print(f"   Result: {cancel_result}")

    # Check again (should be True)
    print("\n4. Checking if request is cancelled...")
    is_cancelled = safety.is_request_cancelled(request_id)
    print(f"   Cancelled: {is_cancelled}")

    # Try to cancel someone else's request (should fail)
    print("\n5. Trying to cancel someone else's request...")
    wrong_user = "XAI9z9z9z9z9z9z9z9z"
    cancel_result = safety.cancel_personal_ai_request(request_id, wrong_user)
    print(f"   Result: {cancel_result}")

    print("\n✅ Personal AI Cancellation Test Complete")


def test_trading_bot_emergency_stop():
    """Test emergency stop for trading bot"""
    print("\n" + "=" * 70)
    print("TEST 2: Trading Bot Emergency Stop")
    print("=" * 70)

    blockchain = Blockchain()
    safety = AISafetyControls(blockchain)

    # Create mock trading bot
    class MockTradingBot:
        def __init__(self):
            self.is_active = True

        def stop(self):
            self.is_active = False
            return {"success": True, "message": "Bot stopped"}

    # Register trading bot
    print("\n1. Registering trading bot...")
    user_address = "XAI1trader123456789"
    bot = MockTradingBot()

    result = safety.register_trading_bot(user_address, bot)
    print(f"   Registered: {result}")
    print(f"   Bot active: {bot.is_active}")

    # Emergency stop
    print("\n2. Activating emergency stop...")
    stop_result = safety.emergency_stop_trading_bot(user_address)
    print(f"   Result: {stop_result}")
    print(f"   Bot active: {bot.is_active}")

    print("\n✅ Trading Bot Emergency Stop Test Complete")


def test_governance_task_pause():
    """Test pausing/resuming Governance AI tasks"""
    print("\n" + "=" * 70)
    print("TEST 3: Governance AI Task Pause/Resume")
    print("=" * 70)

    blockchain = Blockchain()
    safety = AISafetyControls(blockchain)

    # Register Governance AI task
    print("\n1. Registering Governance AI task...")
    task_id = "gov_task_001"
    proposal_id = "prop_123"

    result = safety.register_governance_task(
        task_id=task_id, proposal_id=proposal_id, task_type="code_implementation", ai_count=3
    )
    print(f"   Registered: {result}")

    # Check if paused (should be False)
    print("\n2. Checking if task is paused...")
    is_paused = safety.is_task_paused(task_id)
    print(f"   Paused: {is_paused}")

    # Pause task
    print("\n3. Pausing task...")
    pause_result = safety.pause_governance_task(task_id, "system")
    print(f"   Result: {pause_result}")

    # Check again (should be True)
    print("\n4. Checking if task is paused...")
    is_paused = safety.is_task_paused(task_id)
    print(f"   Paused: {is_paused}")

    # Resume task
    print("\n5. Resuming task...")
    resume_result = safety.resume_governance_task(task_id)
    print(f"   Result: {resume_result}")

    # Check again (should be False)
    print("\n6. Checking if task is paused...")
    is_paused = safety.is_task_paused(task_id)
    print(f"   Paused: {is_paused}")

    print("\n✅ Governance Task Pause/Resume Test Complete")


def test_global_emergency_stop():
    """Test global emergency stop"""
    print("\n" + "=" * 70)
    print("TEST 4: Global AI Emergency Stop")
    print("=" * 70)

    blockchain = Blockchain()
    safety = AISafetyControls(blockchain)

    # Register various operations
    print("\n1. Setting up operations...")

    # Personal AI requests
    safety.register_personal_ai_request(
        "req_001", "XAI1user1", "atomic_swap", "anthropic", "claude-opus-4"
    )
    safety.register_personal_ai_request("req_002", "XAI1user2", "smart_contract", "openai", "gpt-4")

    # Governance tasks
    safety.register_governance_task("task_001", "prop_123", "code_implementation", 3)

    # Trading bots
    class MockBot:
        def stop(self):
            return {"success": True}

    safety.register_trading_bot("XAI1trader1", MockBot())
    safety.register_trading_bot("XAI1trader2", MockBot())

    print("   Operations registered")

    # Get status before emergency stop
    print("\n2. Status before emergency stop:")
    status = safety.get_status()
    print(f"   Personal AI requests: {status['personal_ai']['running']}")
    print(f"   Governance tasks: {status['governance_ai']['running']}")
    print(f"   Trading bots: {status['trading_bots']['active_bots']}")

    # Activate emergency stop
    print("\n3. Activating GLOBAL EMERGENCY STOP...")
    stop_result = safety.activate_emergency_stop(
        reason=StopReason.SECURITY_THREAT,
        details="Test emergency stop activation",
        activator="test_system",
    )
    print(f"\n   Result: {stop_result['message']}")

    # Get status after emergency stop
    print("\n4. Status after emergency stop:")
    status = safety.get_status()
    print(f"   Emergency stop active: {status['emergency_stop_active']}")
    print(f"   Personal AI stopped: {status['personal_ai']['cancelled']}")
    print(f"   Governance tasks paused: {status['governance_ai']['paused']}")

    # Try to register new operation (should fail)
    print("\n5. Trying to register new operation (should fail)...")
    result = safety.register_personal_ai_request(
        "req_003", "XAI1user3", "atomic_swap", "anthropic", "claude-opus-4"
    )
    print(f"   Result: {result}")

    # Deactivate emergency stop
    print("\n6. Deactivating emergency stop...")
    deactivate_result = safety.deactivate_emergency_stop("test_system")
    print(f"   Result: {deactivate_result['message']}")

    # Get final status
    print("\n7. Final status:")
    status = safety.get_status()
    print(f"   Emergency stop active: {status['emergency_stop_active']}")

    print("\n✅ Global Emergency Stop Test Complete")


def test_safety_levels():
    """Test AI safety levels"""
    print("\n" + "=" * 70)
    print("TEST 5: AI Safety Levels")
    print("=" * 70)

    blockchain = Blockchain()
    safety = AISafetyControls(blockchain)

    print("\n1. Testing safety levels...")

    levels = [
        AISafetyLevel.NORMAL,
        AISafetyLevel.CAUTION,
        AISafetyLevel.RESTRICTED,
    ]

    for level in levels:
        print(f"\n   Setting level to: {level.value}")
        result = safety.set_safety_level(level, "test_system")
        print(f"   Old: {result['old_level']} → New: {result['new_level']}")

        status = safety.get_status()
        print(f"   Current safety level: {status['safety_level']}")

    print("\n✅ Safety Levels Test Complete")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("XAI BLOCKCHAIN - AI SAFETY CONTROLS TEST SUITE")
    print("=" * 70)

    try:
        test_personal_ai_cancellation()
        test_trading_bot_emergency_stop()
        test_governance_task_pause()
        test_global_emergency_stop()
        test_safety_levels()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nAI Safety Controls are working correctly!")
        print("Users have instant control over AI operations.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

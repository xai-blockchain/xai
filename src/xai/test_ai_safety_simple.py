"""
Simple AI Safety Controls Test

Tests the core safety control functionality without blockchain dependencies.
"""


# Mock blockchain for testing
class MockBlockchain:
    def __init__(self):
        self.chain = []


def test_safety_controls():
    """Test AI safety controls"""
    print("\n" + "=" * 70)
    print("XAI BLOCKCHAIN - AI SAFETY CONTROLS TEST")
    print("=" * 70)

    # Import safety controls
    from src.xai.core.ai_safety_controls import AISafetyControls, AISafetyLevel, StopReason

    print("\n[OK] Successfully imported AISafetyControls")

    blockchain = MockBlockchain()
    safety = AISafetyControls(blockchain)

    print("[OK] Successfully created AISafetyControls instance")

    # Test 1: Register Personal AI request
    print("\n" + "-" * 70)
    print("TEST 1: Personal AI Request Registration & Cancellation")
    print("-" * 70)

    request_id = "test_request_001"
    user_address = "XAI1test123456789"

    result = safety.register_personal_ai_request(
        request_id=request_id,
        user_address=user_address,
        operation="atomic_swap",
        ai_provider="anthropic",
        ai_model="claude-opus-4",
    )
    print(f"[OK] Registered request: {result}")

    is_cancelled = safety.is_request_cancelled(request_id)
    print(f"   Cancelled before: {is_cancelled}")
    assert not is_cancelled, "Request should not be cancelled yet"

    cancel_result = safety.cancel_personal_ai_request(request_id, user_address)
    print(f"[OK] Cancelled request: {cancel_result['success']}")
    assert cancel_result["success"], "Cancellation should succeed"

    is_cancelled = safety.is_request_cancelled(request_id)
    print(f"   Cancelled after: {is_cancelled}")
    assert is_cancelled, "Request should be cancelled now"

    # Test 2: Governance task pause/resume
    print("\n" + "-" * 70)
    print("TEST 2: Governance AI Task Pause/Resume")
    print("-" * 70)

    task_id = "gov_task_001"
    result = safety.register_governance_task(
        task_id=task_id, proposal_id="prop_123", task_type="code_implementation", ai_count=3
    )
    print(f"[OK] Registered task: {result}")

    pause_result = safety.pause_governance_task(task_id, "system")
    print(f"[OK] Paused task: {pause_result['success']}")
    assert pause_result["success"], "Pause should succeed"

    is_paused = safety.is_task_paused(task_id)
    print(f"   Paused: {is_paused}")
    assert is_paused, "Task should be paused"

    resume_result = safety.resume_governance_task(task_id)
    print(f"[OK] Resumed task: {resume_result['success']}")
    assert resume_result["success"], "Resume should succeed"

    is_paused = safety.is_task_paused(task_id)
    print(f"   Paused: {is_paused}")
    assert not is_paused, "Task should not be paused"

    # Test 3: Safety levels
    print("\n" + "-" * 70)
    print("TEST 3: AI Safety Levels")
    print("-" * 70)

    for level in [AISafetyLevel.NORMAL, AISafetyLevel.CAUTION, AISafetyLevel.RESTRICTED]:
        level_result = safety.set_safety_level(level, "test_system")
        print(f"[OK] Set level to {level.value}: {level_result['success']}")
        assert level_result["new_level"] == level.value, f"Level should be {level.value}"

    # Test 4: Status retrieval
    print("\n" + "-" * 70)
    print("TEST 4: Safety Status")
    print("-" * 70)

    status = safety.get_status()
    print(f"[OK] Retrieved status:")
    print(f"   Safety level: {status['safety_level']}")
    print(f"   Emergency stop: {status['emergency_stop_active']}")
    print(f"   Personal AI requests: {status['personal_ai']['total_requests']}")
    print(f"   Governance tasks: {status['governance_ai']['total_tasks']}")

    # Test 5: Global emergency stop
    print("\n" + "-" * 70)
    print("TEST 5: Global Emergency Stop")
    print("-" * 70)

    safety.register_personal_ai_request("req_002", "XAI1user2", "smart_contract", "openai", "gpt-4")
    safety.register_governance_task("task_002", "prop_456", "testing", 2)

    print("   Registered test operations")

    stop_result = safety.activate_emergency_stop(
        reason=StopReason.SECURITY_THREAT, details="Test emergency stop", activator="test_system"
    )
    print(f"[OK] Emergency stop activated: {stop_result['success']}")
    assert stop_result["success"], "Emergency stop should succeed"

    status = safety.get_status()
    assert status["emergency_stop_active"], "Emergency stop should be active"
    print(f"   Emergency stop active: {status['emergency_stop_active']}")

    result = safety.register_personal_ai_request(
        "req_003", "XAI1user3", "atomic_swap", "anthropic", "claude-opus-4"
    )
    print(f"   Registration during emergency stop: {result}")
    assert not result, "Registration should fail during emergency stop"

    deactivate_result = safety.deactivate_emergency_stop("test_system")
    print(f"[OK] Emergency stop deactivated: {deactivate_result['success']}")
    assert deactivate_result["success"], "Deactivation should succeed"

    status = safety.get_status()
    assert not status["emergency_stop_active"], "Emergency stop should be inactive"
    print(f"   Emergency stop active: {status['emergency_stop_active']}")

    # Final summary
    print("\n" + "=" * 70)
    print("[OK] ALL TESTS PASSED")
    print("=" * 70)
    print("\nAI Safety Controls Summary:")
    print("- Personal AI request cancellation: [OK] Working")
    print("- Governance AI task pause/resume: [OK] Working")
    print("- Safety levels: [OK] Working")
    print("- Status retrieval: [OK] Working")
    print("- Global emergency stop: [OK] Working")
    print("\nUsers have instant control over AI operations!")

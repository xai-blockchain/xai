"""
Test vesting curve precision with large token amounts.

Verifies that the fix for floating-point precision loss maintains
accuracy for billion-token vestings with 18 decimal places.
"""

import pytest
from decimal import Decimal

from xai.core.defi.vesting import (
    VestingCurve,
    VestingCurveType,
    VestingSchedule,
    VestingVault,
    VestingStatus,
)


class TestVestingCurvePrecision:
    """Test precision of vesting curve calculations."""

    def test_exponential_curve_precision_small_amount(self):
        """Test exponential curve with small amounts (baseline)."""
        curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=3.0,
        )

        # Calculate vested fraction at 50% time
        fraction = curve.calculate_vested_fraction(0.5)

        # Should be deterministic and precise
        assert isinstance(fraction, float)
        assert 0.0 <= fraction <= 1.0

        # For exponential curve with k=3, at t=0.5:
        # (1 - e^(-3*0.5)) / (1 - e^(-3)) = (1 - e^(-1.5)) / (1 - e^(-3))
        # ≈ 0.7768698398515702 / 0.9502129316321361 ≈ 0.8176
        assert 0.81 < fraction < 0.82

    def test_exponential_curve_precision_large_amount(self):
        """Test exponential curve precision with billion-token amounts."""
        curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=3.0,
        )

        # Simulate a 1 billion token vesting with 18 decimals
        # Total amount: 1,000,000,000 * 10^18 = 10^27
        total_amount = 10**27

        # Calculate vested amount at various time fractions
        test_points = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]

        for t in test_points:
            fraction = curve.calculate_vested_fraction(t)
            vested_amount = int(total_amount * fraction)

            # Verify no precision loss - amount should be non-zero
            # and reasonable for the time fraction
            assert vested_amount > 0, f"Zero vested amount at t={t}"
            assert vested_amount <= total_amount, f"Vested exceeds total at t={t}"

            # For exponential curve, vesting should accelerate
            # so later fractions should have higher vested amounts
            if t > 0.5:
                assert fraction > 0.5, f"Expected >50% vested at t={t}"

    def test_logarithmic_curve_precision_large_amount(self):
        """Test logarithmic curve precision with billion-token amounts."""
        curve = VestingCurve(
            curve_type=VestingCurveType.LOGARITHMIC,
            curve_factor=3.0,
        )

        total_amount = 10**27

        test_points = [0.1, 0.25, 0.5, 0.75, 0.9]

        for t in test_points:
            fraction = curve.calculate_vested_fraction(t)
            vested_amount = int(total_amount * fraction)

            assert vested_amount > 0, f"Zero vested amount at t={t}"
            assert vested_amount <= total_amount, f"Vested exceeds total at t={t}"

            # Logarithmic curve front-loads vesting
            if t > 0.5:
                assert fraction > 0.6, f"Expected >60% vested at t={t} for log curve"

    def test_precision_consistency_across_calls(self):
        """Verify that multiple calls with same input produce identical results."""
        curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=3.0,
        )

        # Call multiple times with same input
        results = [curve.calculate_vested_fraction(0.5) for _ in range(10)]

        # All results should be identical (no floating-point drift)
        assert len(set(results)) == 1, "Results should be deterministic"

    def test_precision_edge_cases(self):
        """Test precision at edge cases (t=0, t=1, very small t)."""
        curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=3.0,
        )

        # At t=0, should be exactly 0
        assert curve.calculate_vested_fraction(0.0) == 0.0

        # At t=1, should be exactly 1
        assert curve.calculate_vested_fraction(1.0) == 1.0

        # Very small t should give non-zero but small result
        small_t = 0.000001
        small_fraction = curve.calculate_vested_fraction(small_t)
        assert 0.0 < small_fraction < 0.01

    def test_precision_with_extreme_curve_factors(self):
        """Test precision with extreme curve factor values."""
        total_amount = 10**27

        # Very steep curve (k=10)
        steep_curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=10.0,
        )

        fraction_steep = steep_curve.calculate_vested_fraction(0.5)
        vested_steep = int(total_amount * fraction_steep)
        assert vested_steep > 0

        # Very gentle curve (k=0.5)
        gentle_curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=0.5,
        )

        fraction_gentle = gentle_curve.calculate_vested_fraction(0.5)
        vested_gentle = int(total_amount * fraction_gentle)
        assert vested_gentle > 0

        # Steep curve should vest more by midpoint than gentle
        assert fraction_steep > fraction_gentle

    def test_no_token_loss_over_full_vesting(self):
        """Verify that sum of all vested amounts equals total (no loss)."""
        curve = VestingCurve(
            curve_type=VestingCurveType.EXPONENTIAL,
            curve_factor=3.0,
        )

        total_amount = 10**27
        num_steps = 100

        # Calculate vested amount at each step
        vested_increments = []
        previous_vested = 0

        for i in range(num_steps + 1):
            t = i / num_steps
            fraction = curve.calculate_vested_fraction(t)
            vested = int(total_amount * fraction)

            increment = vested - previous_vested
            if increment > 0:
                vested_increments.append(increment)

            previous_vested = vested

        # Sum of all increments should equal total (or very close)
        total_vested = sum(vested_increments)

        # Allow for minor rounding (should be within 0.01% of total)
        acceptable_error = total_amount // 10000  # 0.01%
        assert abs(total_amount - total_vested) < acceptable_error


class TestVestingSchedulePrecision:
    """Test VestingSchedule with large amounts."""

    def test_large_amount_vesting_calculation(self):
        """Test vesting schedule with billion-token amounts."""
        import time

        # 1 billion tokens with 18 decimals
        total_amount = 10**27

        schedule = VestingSchedule(
            beneficiary="0xbeneficiary",
            total_amount=total_amount,
            start_time=time.time(),
            cliff_duration=0,
            vesting_duration=365 * 24 * 3600,  # 1 year
            curve=VestingCurve(
                curve_type=VestingCurveType.EXPONENTIAL,
                curve_factor=3.0,
            ),
        )

        # Test vested amount at 50% through vesting
        half_year = schedule.start_time + (365 * 24 * 3600 // 2)
        vested = schedule.get_vested_amount(half_year)

        # Should have vested a significant amount
        assert vested > 0, "Should have vested non-zero amount"
        assert vested < total_amount, "Should not have vested all tokens"

        # For exponential curve, should have vested >50% at t=0.5
        assert vested > total_amount // 2, "Should have vested >50% for exponential"

    def test_precision_maintains_claimable_accuracy(self):
        """Verify claimable amount calculations maintain precision."""
        import time

        total_amount = 10**27
        start_time = time.time()

        schedule = VestingSchedule(
            beneficiary="0xuser",
            total_amount=total_amount,
            start_time=start_time,
            cliff_duration=0,
            vesting_duration=100,  # 100 seconds for easy testing
            curve=VestingCurve(curve_type=VestingCurveType.LINEAR),
        )

        # Claim at 25% through vesting
        at_25_percent = start_time + 25
        claimable_1 = schedule.get_claimable_amount(at_25_percent)

        # Should be ~25% of total
        expected = total_amount // 4
        tolerance = total_amount // 1000  # 0.1% tolerance

        assert abs(claimable_1 - expected) < tolerance

        # Simulate claiming
        schedule.claimed_amount = claimable_1

        # At 50%, should have additional 25% claimable
        at_50_percent = start_time + 50
        claimable_2 = schedule.get_claimable_amount(at_50_percent)

        assert abs(claimable_2 - expected) < tolerance

    def test_no_precision_loss_with_multiple_claims(self):
        """Verify that multiple claims don't accumulate precision errors."""
        import time

        total_amount = 10**27
        start_time = time.time()

        schedule = VestingSchedule(
            beneficiary="0xuser",
            total_amount=total_amount,
            start_time=start_time,
            cliff_duration=0,
            vesting_duration=1000,
            curve=VestingCurve(
                curve_type=VestingCurveType.EXPONENTIAL,
                curve_factor=3.0,
            ),
        )

        # Make 10 claims at different points
        total_claimed = 0
        time_points = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

        for t_offset in time_points:
            at_time = start_time + t_offset
            claimable = schedule.get_claimable_amount(at_time)

            if claimable > 0:
                schedule.claimed_amount += claimable
                total_claimed += claimable

        # After all claims, total claimed should equal total amount
        # (allowing for minor rounding)
        acceptable_error = total_amount // 10000  # 0.01%
        assert abs(total_amount - total_claimed) < acceptable_error

        # Verify claimed amount matches
        assert abs(schedule.claimed_amount - total_claimed) < acceptable_error


class TestVestingVaultPrecision:
    """Test VestingVault with large amounts."""

    def test_vault_with_large_batch_vesting(self):
        """Test vault managing multiple large vesting schedules."""
        vault = VestingVault(
            owner="0xowner",
            token="XAI",
        )

        # Create 100 schedules each with 1 billion tokens
        amount_per_schedule = 10**27
        num_schedules = 100

        beneficiaries = [f"0xbeneficiary{i}" for i in range(num_schedules)]
        amounts = [amount_per_schedule] * num_schedules

        schedule_ids = vault.create_batch_schedules(
            caller="0xowner",
            beneficiaries=beneficiaries,
            amounts=amounts,
            cliff_duration=0,
            vesting_duration=365 * 24 * 3600,
            curve_type=VestingCurveType.EXPONENTIAL,
        )

        assert len(schedule_ids) == num_schedules

        # Verify total locked amount
        expected_total = amount_per_schedule * num_schedules
        assert vault.total_locked == expected_total

        # Verify each schedule has correct amount
        for schedule_id in schedule_ids:
            schedule = vault.schedules[schedule_id]
            assert schedule.total_amount == amount_per_schedule

    def test_vault_stats_precision_with_large_amounts(self):
        """Test vault statistics maintain precision with large amounts."""
        vault = VestingVault(
            owner="0xowner",
            token="XAI",
        )

        total_amount = 10**28  # 10 billion tokens with 18 decimals

        schedule_id = vault.create_schedule(
            caller="0xowner",
            beneficiary="0xuser",
            amount=total_amount,
            cliff_duration=0,
            vesting_duration=100,
        )

        stats = vault.get_vault_stats()

        assert stats["total_locked"] == total_amount
        assert stats["total_claimed"] == 0
        assert stats["total_schedules"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

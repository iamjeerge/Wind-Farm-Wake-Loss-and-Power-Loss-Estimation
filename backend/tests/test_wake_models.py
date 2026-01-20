"""Tests for wake models."""

import math

import pytest

from app.models.turbine import Turbine
from app.models.wake import WakeParameters
from app.services.wake.jensen import JensenWakeModel
from app.services.wake.bastankhah import BastankhahWakeModel
from app.services.wake.superposition import WakeSuperposition


class TestJensenWakeModel:
    """Tests for Jensen wake model."""

    def test_wake_radius_expansion(self, sample_turbine: Turbine) -> None:
        """Test that wake expands linearly with distance."""
        model = JensenWakeModel()

        r0 = sample_turbine.rotor_radius
        r1 = model.calculate_wake_radius(sample_turbine, 500)
        r2 = model.calculate_wake_radius(sample_turbine, 1000)

        # Wake should expand linearly
        assert r1 > r0
        assert r2 > r1
        # r = r0 + k*x, so (r1-r0) should be half of (r2-r0)
        assert abs((r1 - r0) * 2 - (r2 - r0)) < 0.1

    def test_velocity_deficit_decreases_with_distance(
        self, sample_turbine: Turbine
    ) -> None:
        """Test that velocity deficit decreases with distance."""
        model = JensenWakeModel()

        deficit_500 = model.get_deficit_at_distance(sample_turbine, 500)
        deficit_1000 = model.get_deficit_at_distance(sample_turbine, 1000)
        deficit_2000 = model.get_deficit_at_distance(sample_turbine, 2000)

        assert deficit_500 > deficit_1000 > deficit_2000
        assert 0 < deficit_2000 < 1

    def test_deficit_bounded_zero_one(self, sample_turbine: Turbine) -> None:
        """Test that velocity deficit is always between 0 and 1."""
        model = JensenWakeModel()

        for distance in [100, 500, 1000, 5000, 10000]:
            deficit = model.get_deficit_at_distance(sample_turbine, distance)
            assert 0 <= deficit <= 1

    def test_no_wake_upstream(self, sample_layout) -> None:
        """Test that upstream turbines don't experience wake."""
        model = JensenWakeModel()

        # Wind from south (180°), so T1 is upstream of T4, T7
        t1 = sample_layout.turbines[0]  # Bottom row
        t7 = sample_layout.turbines[6]  # Top row

        result = model.calculate_velocity_deficit(t1, t7, 180.0, 10.0)

        # T7 is downstream, should be in wake
        assert result.is_in_wake or result.distance > 0

        # Reverse: T7 should not affect T1 with wind from south
        result_reverse = model.calculate_velocity_deficit(t7, t1, 180.0, 10.0)
        assert not result_reverse.is_in_wake


class TestBastankhahWakeModel:
    """Tests for Bastankhah Gaussian wake model."""

    def test_gaussian_profile(self, sample_turbine: Turbine) -> None:
        """Test Gaussian deficit profile (maximum at centerline)."""
        model = BastankhahWakeModel()

        centerline = model.get_deficit_at_distance(sample_turbine, 500, 0.0)
        offset_50m = model.get_deficit_at_distance(sample_turbine, 500, 50.0)
        offset_100m = model.get_deficit_at_distance(sample_turbine, 500, 100.0)

        assert centerline > offset_50m > offset_100m

    def test_deficit_decreases_with_distance(
        self, sample_turbine: Turbine
    ) -> None:
        """Test that deficit decreases with downstream distance."""
        model = BastankhahWakeModel()

        d500 = model.get_deficit_at_distance(sample_turbine, 500, 0.0)
        d1000 = model.get_deficit_at_distance(sample_turbine, 1000, 0.0)
        d2000 = model.get_deficit_at_distance(sample_turbine, 2000, 0.0)

        assert d500 > d1000 > d2000

    def test_turbulence_intensity_effect(self, sample_turbine: Turbine) -> None:
        """Test that higher TI leads to faster wake recovery."""
        low_ti_params = WakeParameters(turbulence_intensity=0.04)
        high_ti_params = WakeParameters(turbulence_intensity=0.12)

        low_ti_model = BastankhahWakeModel(low_ti_params)
        high_ti_model = BastankhahWakeModel(high_ti_params)

        # At same distance, higher TI should have lower deficit (faster recovery)
        low_ti_deficit = low_ti_model.get_deficit_at_distance(sample_turbine, 1000, 0.0)
        high_ti_deficit = high_ti_model.get_deficit_at_distance(sample_turbine, 1000, 0.0)

        assert high_ti_deficit < low_ti_deficit


class TestWakeSuperposition:
    """Tests for wake superposition methods."""

    def test_quadratic_superposition(self) -> None:
        """Test quadratic (RSS) superposition."""
        from app.models.wake import WakeResult
        from uuid import uuid4

        superposition = WakeSuperposition(method="quadratic")

        # Create mock wake results
        wake1 = WakeResult(
            upstream_turbine_id=uuid4(),
            downstream_turbine_id=uuid4(),
            wind_direction=270.0,
            wind_speed=10.0,
            distance=500,
            distance_rotor_diameters=4.0,
            lateral_offset=0,
            wake_radius=100,
            velocity_deficit=0.3,
            effective_wind_speed=7.0,
            overlap_fraction=1.0,
            is_in_wake=True,
        )

        wake2 = WakeResult(
            upstream_turbine_id=uuid4(),
            downstream_turbine_id=uuid4(),
            wind_direction=270.0,
            wind_speed=10.0,
            distance=700,
            distance_rotor_diameters=5.5,
            lateral_offset=0,
            wake_radius=120,
            velocity_deficit=0.2,
            effective_wind_speed=8.0,
            overlap_fraction=1.0,
            is_in_wake=True,
        )

        combined = superposition.combine_deficits([wake1, wake2])

        # RSS: sqrt(0.3² + 0.2²) = sqrt(0.09 + 0.04) = sqrt(0.13) ≈ 0.36
        expected = math.sqrt(0.3**2 + 0.2**2)
        assert abs(combined - expected) < 0.01

    def test_combined_deficit_bounded(self) -> None:
        """Test that combined deficit doesn't exceed 1."""
        from app.models.wake import WakeResult
        from uuid import uuid4

        superposition = WakeSuperposition(method="linear")

        # Create many wakes with high deficits
        wakes = []
        for _ in range(5):
            wakes.append(
                WakeResult(
                    upstream_turbine_id=uuid4(),
                    downstream_turbine_id=uuid4(),
                    wind_direction=270.0,
                    wind_speed=10.0,
                    distance=500,
                    distance_rotor_diameters=4.0,
                    lateral_offset=0,
                    wake_radius=100,
                    velocity_deficit=0.4,
                    effective_wind_speed=6.0,
                    overlap_fraction=1.0,
                    is_in_wake=True,
                )
            )

        combined = superposition.combine_deficits(wakes)

        # Even with linear sum of 2.0, should be bounded at 1.0
        assert combined <= 1.0


class TestPhysicsValidation:
    """Physics validation tests."""

    def test_energy_conservation(self, sample_layout) -> None:
        """Test that wake-affected power is always <= free-stream power."""
        from app.services.simulation.simulator import Simulator
        from app.models.simulation import SimulationConfig

        simulator = Simulator(SimulationConfig())
        result = simulator.run_single_condition(sample_layout, 270.0, 10.0)

        assert result.total_wake_affected_power <= result.total_free_stream_power
        for t in result.turbine_results:
            assert t.wake_affected_power <= t.free_stream_power

    def test_wake_decay_reasonable(self, sample_turbine: Turbine) -> None:
        """Test that wake decays to reasonable levels at far distances."""
        model = JensenWakeModel()

        # At 20D downstream, deficit should be small
        distance_20d = 20 * sample_turbine.rotor_diameter
        deficit = model.get_deficit_at_distance(sample_turbine, distance_20d)

        assert deficit < 0.1  # Less than 10% deficit at 20D

    def test_thrust_coefficient_effect(self, sample_turbine: Turbine) -> None:
        """Test that higher Ct leads to higher deficit."""
        model = JensenWakeModel()

        # Low Ct turbine
        low_ct = Turbine(**sample_turbine.model_dump())
        low_ct.thrust_coefficient = 0.4

        # High Ct turbine
        high_ct = Turbine(**sample_turbine.model_dump())
        high_ct.thrust_coefficient = 0.9

        deficit_low = model.get_deficit_at_distance(low_ct, 500)
        deficit_high = model.get_deficit_at_distance(high_ct, 500)

        assert deficit_high > deficit_low

"""Bastankhah Gaussian wake model implementation."""

from __future__ import annotations

import math

from app.models.turbine import Turbine
from app.models.wake import WakeParameters, WakeResult
from app.services.wake.base import BaseWakeModel


class BastankhahWakeModel(BaseWakeModel):
    """
    Bastankhah & Porté-Agel Gaussian wake model.

    This model provides a more realistic Gaussian velocity deficit profile
    compared to the Jensen top-hat model. It's based on the self-similar
    Gaussian wake assumption.

    Velocity deficit formula:
        Δu/u₀ = (1 - √(1 - Cₜ/(8(σ/D)²))) * exp(-r²/(2σ²))

    Where:
        - σ = k*x + σ₀: Wake width (standard deviation)
        - σ₀ = D * √(Cₜ/8): Initial wake width
        - k*: Wake expansion rate (depends on turbulence intensity)

    References:
        Bastankhah, M., & Porté-Agel, F. (2014). A new analytical model for
        wind-turbine wakes. Renewable Energy, 70, 116-123.
    """

    def __init__(self, params: WakeParameters | None = None) -> None:
        """Initialize Bastankhah wake model."""
        super().__init__(params)
        self.ti = self.params.turbulence_intensity
        self.stability = self.params.atmospheric_stability

    def _calculate_wake_expansion_rate(self, turbulence_intensity: float) -> float:
        """
        Calculate wake expansion rate k* based on turbulence intensity.

        k* ≈ 0.38 * TI (empirical relationship)

        Args:
            turbulence_intensity: Ambient turbulence intensity (0-1)

        Returns:
            Wake expansion rate k*
        """
        # Base expansion rate from empirical fit
        k_star = 0.38 * turbulence_intensity

        # Stability correction
        # Stable atmosphere: reduced expansion
        # Unstable atmosphere: increased expansion
        stability_factor = 1.0 + 0.2 * self.stability

        return k_star * stability_factor

    def _calculate_initial_wake_width(self, turbine: Turbine) -> float:
        """
        Calculate initial wake width σ₀.

        σ₀ = D * √(Cₜ/8)

        Args:
            turbine: Turbine producing wake

        Returns:
            Initial wake width in meters
        """
        ct = turbine.thrust_coefficient
        d = turbine.rotor_diameter

        # Ensure valid Ct for square root
        ct = min(ct, 0.999)

        return d * math.sqrt(ct / 8)

    def _calculate_wake_width(
        self,
        turbine: Turbine,
        distance: float,
    ) -> float:
        """
        Calculate wake width (standard deviation) at distance x.

        σ = k* * x + σ₀

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters

        Returns:
            Wake width (σ) in meters
        """
        k_star = self._calculate_wake_expansion_rate(self.ti)
        sigma_0 = self._calculate_initial_wake_width(turbine)

        return k_star * distance + sigma_0

    def calculate_velocity_deficit(
        self,
        upstream: Turbine,
        downstream: Turbine,
        wind_direction: float,
        wind_speed: float,
    ) -> WakeResult:
        """
        Calculate velocity deficit using Bastankhah Gaussian model.

        Args:
            upstream: Upstream turbine producing wake
            downstream: Downstream turbine affected by wake
            wind_direction: Wind direction in degrees
            wind_speed: Free-stream wind speed in m/s

        Returns:
            WakeResult with wake characteristics
        """
        # Get relative position
        downstream_dist, lateral_offset = self.get_downstream_position(
            upstream, downstream, wind_direction
        )

        # Initialize result
        result = WakeResult(
            upstream_turbine_id=upstream.id,
            downstream_turbine_id=downstream.id,
            wind_direction=wind_direction,
            wind_speed=wind_speed,
            distance=abs(downstream_dist),
            distance_rotor_diameters=abs(downstream_dist) / upstream.rotor_diameter,
            lateral_offset=lateral_offset,
            wake_radius=0.0,
            velocity_deficit=0.0,
            effective_wind_speed=wind_speed,
            overlap_fraction=0.0,
            is_in_wake=False,
        )

        # Check if downstream is actually downstream
        if downstream_dist <= 0:
            return result

        # Minimum distance for valid calculation (near-wake region not modeled)
        min_distance = 2 * upstream.rotor_diameter
        if downstream_dist < min_distance:
            # Use simplified near-wake approximation
            downstream_dist = min_distance

        # Calculate wake width at downstream position
        sigma = self._calculate_wake_width(upstream, downstream_dist)

        # Wake radius defined as 2σ (contains ~95% of deficit)
        wake_radius = 2 * sigma
        result.wake_radius = wake_radius

        # Calculate overlap fraction
        overlap = self.calculate_overlap_fraction(downstream, wake_radius, lateral_offset)
        result.overlap_fraction = overlap

        # Check if in wake zone (significant overlap)
        if overlap < 0.01:
            return result

        result.is_in_wake = True

        # Calculate Gaussian velocity deficit
        ct = upstream.thrust_coefficient
        d = upstream.rotor_diameter

        # Ensure valid parameters
        ct = min(ct, 0.999)
        sigma_ratio = sigma / d

        # Core deficit term
        # C = 1 - √(1 - Cₜ/(8(σ/D)²))
        discriminant = 1 - ct / (8 * sigma_ratio**2)
        if discriminant <= 0:
            # Very high thrust or narrow wake - use limit
            core_deficit = 1.0
        else:
            core_deficit = 1 - math.sqrt(discriminant)

        # Gaussian radial profile
        # exp(-r²/(2σ²))
        if sigma > 0:
            radial_factor = math.exp(-(lateral_offset**2) / (2 * sigma**2))
        else:
            radial_factor = 1.0 if lateral_offset < d / 2 else 0.0

        velocity_deficit = core_deficit * radial_factor

        # Apply rotor-averaging for partial wake interaction
        # This averages the deficit over the rotor area
        if overlap < 1.0:
            velocity_deficit = self._rotor_average_deficit(
                downstream, sigma, lateral_offset, core_deficit
            )

        # Ensure deficit is bounded [0, 1]
        velocity_deficit = max(0.0, min(1.0, velocity_deficit))
        result.velocity_deficit = velocity_deficit

        # Calculate effective wind speed
        result.effective_wind_speed = wind_speed * (1 - velocity_deficit)

        return result

    def _rotor_average_deficit(
        self,
        downstream: Turbine,
        sigma: float,
        lateral_offset: float,
        core_deficit: float,
    ) -> float:
        """
        Calculate rotor-averaged velocity deficit.

        Integrates Gaussian deficit over rotor area using numerical approximation.

        Args:
            downstream: Downstream turbine
            sigma: Wake width (σ)
            lateral_offset: Lateral offset from wake centerline
            core_deficit: Core deficit value

        Returns:
            Rotor-averaged velocity deficit
        """
        # Simple 5-point approximation across rotor
        r_rotor = downstream.rotor_radius
        n_points = 5

        total_deficit = 0.0
        for i in range(n_points):
            # Sample points across rotor diameter
            offset = lateral_offset + r_rotor * (2 * i / (n_points - 1) - 1)
            radial_factor = math.exp(-(offset**2) / (2 * sigma**2))
            total_deficit += core_deficit * radial_factor

        return total_deficit / n_points

    def calculate_wake_radius(
        self,
        turbine: Turbine,
        distance: float,
    ) -> float:
        """
        Calculate wake radius (2σ) at given distance.

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters

        Returns:
            Wake radius in meters
        """
        if distance <= 0:
            return turbine.rotor_radius

        sigma = self._calculate_wake_width(turbine, distance)
        return 2 * sigma

    def get_deficit_at_distance(
        self,
        turbine: Turbine,
        distance: float,
        lateral_offset: float = 0.0,
    ) -> float:
        """
        Get velocity deficit at given position.

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters
            lateral_offset: Lateral offset from centerline in meters

        Returns:
            Velocity deficit ratio (0-1)
        """
        if distance <= 0:
            return 0.0

        ct = min(turbine.thrust_coefficient, 0.999)
        d = turbine.rotor_diameter

        sigma = self._calculate_wake_width(turbine, distance)
        sigma_ratio = sigma / d

        discriminant = 1 - ct / (8 * sigma_ratio**2)
        if discriminant <= 0:
            core_deficit = 1.0
        else:
            core_deficit = 1 - math.sqrt(discriminant)

        radial_factor = math.exp(-(lateral_offset**2) / (2 * sigma**2))

        return core_deficit * radial_factor

    def get_thrust_coefficient(
        self,
        wind_speed: float,
        rated_speed: float = 12.0,
        ct_rated: float = 0.8,
    ) -> float:
        """
        Get thrust coefficient based on wind speed.

        Uses simplified model where Ct is constant below rated
        and decreases above rated speed.

        Args:
            wind_speed: Wind speed in m/s
            rated_speed: Rated wind speed in m/s
            ct_rated: Ct at rated conditions

        Returns:
            Thrust coefficient
        """
        if wind_speed <= rated_speed:
            return ct_rated
        else:
            # Ct decreases proportional to 1/v² above rated
            return ct_rated * (rated_speed / wind_speed) ** 2

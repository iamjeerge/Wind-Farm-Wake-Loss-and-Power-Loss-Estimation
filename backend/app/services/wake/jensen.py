"""Jensen wake model implementation."""

from __future__ import annotations

import math

from app.models.turbine import Turbine
from app.models.wake import WakeParameters, WakeResult
from app.services.wake.base import BaseWakeModel


class JensenWakeModel(BaseWakeModel):
    """
    Jensen (Park) wake model implementation.

    The Jensen model assumes linear wake expansion with a constant
    wake decay coefficient k. It's one of the simplest and most
    widely used wake models.

    Velocity deficit formula:
        Δu/u₀ = (1 - √(1 - Cₜ)) * (D / (D + 2kx))²

    Where:
        - Δu: Velocity deficit
        - u₀: Free-stream velocity
        - Cₜ: Thrust coefficient
        - D: Rotor diameter
        - k: Wake decay coefficient
        - x: Downstream distance

    References:
        Jensen, N.O. (1983). A note on wind generator interaction.
        Risø National Laboratory, Roskilde, Denmark.
    """

    def __init__(self, params: WakeParameters | None = None) -> None:
        """Initialize Jensen wake model."""
        super().__init__(params)
        # Default wake decay coefficient
        self.k = self.params.wake_decay_coefficient

    def calculate_velocity_deficit(
        self,
        upstream: Turbine,
        downstream: Turbine,
        wind_direction: float,
        wind_speed: float,
    ) -> WakeResult:
        """
        Calculate velocity deficit using Jensen model.

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

        # Calculate wake radius at downstream position
        wake_radius = self.calculate_wake_radius(upstream, downstream_dist)
        result.wake_radius = wake_radius

        # Calculate overlap fraction
        overlap = self.calculate_overlap_fraction(downstream, wake_radius, lateral_offset)
        result.overlap_fraction = overlap

        # Check if in wake zone
        if overlap <= 0:
            return result

        result.is_in_wake = True

        # Calculate velocity deficit using Jensen formula
        ct = upstream.thrust_coefficient
        d = upstream.rotor_diameter
        x = downstream_dist

        # Jensen deficit at wake center
        # Δu/u₀ = (1 - √(1 - Cₜ)) * (D / (D + 2kx))²
        deficit_factor = 1 - math.sqrt(1 - ct)
        expansion_factor = (d / (d + 2 * self.k * x)) ** 2
        centerline_deficit = deficit_factor * expansion_factor

        # Apply Gaussian lateral profile (modification of basic Jensen)
        # deficit(r) = deficit_centerline * exp(-(r/σ)²)
        if lateral_offset > 0 and wake_radius > 0:
            sigma = wake_radius / 2  # Standard deviation of Gaussian
            lateral_factor = math.exp(-((lateral_offset / sigma) ** 2))
            velocity_deficit = centerline_deficit * lateral_factor
        else:
            velocity_deficit = centerline_deficit

        # Weight by overlap fraction for partial wake interaction
        velocity_deficit *= overlap

        # Ensure deficit is bounded [0, 1]
        velocity_deficit = max(0.0, min(1.0, velocity_deficit))
        result.velocity_deficit = velocity_deficit

        # Calculate effective wind speed
        result.effective_wind_speed = wind_speed * (1 - velocity_deficit)

        return result

    def calculate_wake_radius(
        self,
        turbine: Turbine,
        distance: float,
    ) -> float:
        """
        Calculate wake radius using linear expansion.

        r_wake = r_rotor + k * x

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters

        Returns:
            Wake radius in meters
        """
        if distance <= 0:
            return turbine.rotor_radius

        return turbine.rotor_radius + self.k * distance

    def get_deficit_at_distance(
        self,
        turbine: Turbine,
        distance: float,
    ) -> float:
        """
        Get centerline velocity deficit at given distance.

        Useful for plotting wake decay.

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters

        Returns:
            Velocity deficit ratio (0-1)
        """
        if distance <= 0:
            return 0.0

        ct = turbine.thrust_coefficient
        d = turbine.rotor_diameter

        deficit_factor = 1 - math.sqrt(1 - ct)
        expansion_factor = (d / (d + 2 * self.k * distance)) ** 2

        return deficit_factor * expansion_factor

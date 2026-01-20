"""Power calculation service."""

from __future__ import annotations

from uuid import UUID

from app.models.power import TurbinePowerResult
from app.models.turbine import PowerCurve, Turbine
from app.models.wake import WakeResult
from app.services.loaders.power_curve_loader import PowerCurveLoader


class PowerCalculator:
    """Service for calculating turbine power output."""

    def __init__(self) -> None:
        """Initialize power calculator."""
        self._power_curve_loader = PowerCurveLoader()
        self._generic_curves: dict[float, PowerCurve] = {}

    def calculate_power(
        self,
        turbine: Turbine,
        wind_speed: float,
        wind_direction: float,
        wake_results: list[WakeResult] | None = None,
        combined_deficit: float = 0.0,
    ) -> TurbinePowerResult:
        """
        Calculate power output for a single turbine.

        Args:
            turbine: Turbine to calculate power for
            wind_speed: Free-stream wind speed in m/s
            wind_direction: Wind direction in degrees
            wake_results: Optional list of wake effects on this turbine
            combined_deficit: Pre-calculated combined velocity deficit

        Returns:
            TurbinePowerResult with power values and losses
        """
        # Get or create power curve
        power_curve = self._get_power_curve(turbine)

        # Calculate effective wind speed
        if combined_deficit > 0:
            effective_speed = wind_speed * (1 - combined_deficit)
        else:
            effective_speed = wind_speed

        # Calculate free-stream power (no wake effects)
        free_stream_power = self._power_curve_loader.get_power(
            wind_speed, power_curve, str(turbine.id)
        )

        # Calculate wake-affected power
        wake_affected_power = self._power_curve_loader.get_power(
            effective_speed, power_curve, str(turbine.id)
        )

        # Calculate losses
        power_loss = free_stream_power - wake_affected_power
        if free_stream_power > 0:
            power_loss_percent = (power_loss / free_stream_power) * 100
        else:
            power_loss_percent = 0.0

        # Get upstream turbines
        upstream_turbines: list[UUID] = []
        if wake_results:
            upstream_turbines = [
                w.upstream_turbine_id
                for w in wake_results
                if w.is_in_wake and w.velocity_deficit > 0
            ]

        # Determine operating status
        is_operating = self._is_operating(effective_speed, power_curve)

        return TurbinePowerResult(
            turbine_id=turbine.id,
            turbine_name=turbine.name,
            wind_direction=wind_direction,
            free_stream_speed=wind_speed,
            effective_speed=effective_speed,
            free_stream_power=free_stream_power,
            wake_affected_power=wake_affected_power,
            rated_power=turbine.rated_power,
            power_loss=power_loss,
            power_loss_percent=power_loss_percent,
            upstream_turbines=upstream_turbines,
            combined_velocity_deficit=combined_deficit,
            is_operating=is_operating,
        )

    def _get_power_curve(self, turbine: Turbine) -> PowerCurve:
        """
        Get power curve for turbine, creating generic if needed.

        Args:
            turbine: Turbine to get curve for

        Returns:
            PowerCurve object
        """
        if turbine.power_curve is not None:
            return turbine.power_curve

        # Use or create generic curve based on rated power
        rated_power = turbine.rated_power
        if rated_power not in self._generic_curves:
            self._generic_curves[rated_power] = (
                PowerCurveLoader.create_generic_power_curve(rated_power)
            )

        return self._generic_curves[rated_power]

    def _is_operating(self, wind_speed: float, power_curve: PowerCurve) -> bool:
        """
        Check if turbine is operating at given wind speed.

        Args:
            wind_speed: Wind speed in m/s
            power_curve: Turbine power curve

        Returns:
            True if within operating range
        """
        return power_curve.cut_in_speed <= wind_speed <= power_curve.cut_out_speed

    def calculate_theoretical_power(
        self,
        wind_speed: float,
        rotor_area: float,
        air_density: float = 1.225,
        power_coefficient: float = 0.45,
    ) -> float:
        """
        Calculate theoretical power using Betz limit.

        P = 0.5 * ρ * A * v³ * Cp

        Args:
            wind_speed: Wind speed in m/s
            rotor_area: Rotor swept area in m²
            air_density: Air density in kg/m³
            power_coefficient: Power coefficient (max ~0.59 Betz limit)

        Returns:
            Power in kW
        """
        power_watts = 0.5 * air_density * rotor_area * (wind_speed**3) * power_coefficient
        return power_watts / 1000  # Convert to kW

    def estimate_power_from_speed_ratio(
        self,
        rated_power: float,
        wind_speed: float,
        rated_speed: float,
    ) -> float:
        """
        Estimate power using simplified cubic relationship.

        Below rated: P = Prated * (v/vrated)³
        At/above rated: P = Prated

        Args:
            rated_power: Rated power in kW
            wind_speed: Wind speed in m/s
            rated_speed: Rated wind speed in m/s

        Returns:
            Estimated power in kW
        """
        if wind_speed <= 0:
            return 0.0

        if wind_speed >= rated_speed:
            return rated_power

        return rated_power * (wind_speed / rated_speed) ** 3

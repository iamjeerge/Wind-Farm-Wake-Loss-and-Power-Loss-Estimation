"""Annual Energy Production calculator."""

from __future__ import annotations

from app.models.simulation import AEPResult, DirectionalResult, SimulationResults
from app.models.turbine import TurbineLayout
from app.models.wind import WindData
from app.services.loaders.wind_loader import WindLoader


class AEPCalculator:
    """
    Service for calculating Annual Energy Production (AEP).

    AEP is calculated by integrating power output over the joint
    probability distribution of wind speed and direction.

    AEP = Σ_direction Σ_speed P(direction) * P(speed|direction) * Power(direction, speed) * 8760
    """

    # Hours in a year
    HOURS_PER_YEAR = 8760

    def __init__(self) -> None:
        """Initialize AEP calculator."""
        pass

    def calculate_aep(
        self,
        simulation_results: SimulationResults,
        layout: TurbineLayout,
        wind_data: WindData,
    ) -> AEPResult:
        """
        Calculate Annual Energy Production from simulation results.

        Args:
            simulation_results: Results from directional sweep simulation
            layout: Wind farm layout
            wind_data: Wind data (rose and Weibull)

        Returns:
            AEPResult with gross and net AEP
        """
        gross_energy = 0.0  # MWh without wake losses
        net_energy = 0.0  # MWh with wake losses

        # Per-turbine tracking
        turbine_gross: dict[str, float] = {t.name: 0.0 for t in layout.turbines}
        turbine_net: dict[str, float] = {t.name: 0.0 for t in layout.turbines}

        for dir_result in simulation_results.directional_results:
            direction_prob = dir_result.direction_probability

            # Get Weibull for this direction
            weibull = wind_data.get_weibull(dir_result.direction)

            for farm_result in dir_result.farm_results:
                # Get speed probability from Weibull
                # Approximate bin probability using bin width
                speed = farm_result.wind_speed
                speed_prob = self._get_speed_probability(speed, weibull)

                # Joint probability
                joint_prob = direction_prob * speed_prob

                # Convert power (kW) to energy (MWh) over year
                # Energy = Power * Hours * Probability
                gross_mwh = (
                    farm_result.total_free_stream_power
                    / 1000  # kW to MW
                    * self.HOURS_PER_YEAR
                    * joint_prob
                )
                net_mwh = (
                    farm_result.total_wake_affected_power / 1000 * self.HOURS_PER_YEAR * joint_prob
                )

                gross_energy += gross_mwh
                net_energy += net_mwh

                # Track per-turbine
                for turbine_result in farm_result.turbine_results:
                    name = turbine_result.turbine_name
                    turbine_gross[name] += (
                        turbine_result.free_stream_power / 1000 * self.HOURS_PER_YEAR * joint_prob
                    )
                    turbine_net[name] += (
                        turbine_result.wake_affected_power / 1000 * self.HOURS_PER_YEAR * joint_prob
                    )

        # Calculate metrics
        wake_loss = gross_energy - net_energy
        if gross_energy > 0:
            wake_loss_percent = (wake_loss / gross_energy) * 100
        else:
            wake_loss_percent = 0.0

        # Capacity factors
        total_rated_mw = layout.total_rated_power / 1000
        max_possible_mwh = total_rated_mw * self.HOURS_PER_YEAR

        if max_possible_mwh > 0:
            gross_cf = (gross_energy / max_possible_mwh) * 100
            net_cf = (net_energy / max_possible_mwh) * 100
        else:
            gross_cf = 0.0
            net_cf = 0.0

        # Full load hours
        if total_rated_mw > 0:
            gross_flh = gross_energy / total_rated_mw
            net_flh = net_energy / total_rated_mw
        else:
            gross_flh = 0.0
            net_flh = 0.0

        # Per-turbine wake losses
        turbine_wake_loss = {
            name: turbine_gross[name] - turbine_net[name] for name in turbine_gross
        }

        return AEPResult(
            gross_aep_mwh=gross_energy,
            net_aep_mwh=net_energy,
            wake_loss_mwh=wake_loss,
            wake_loss_percent=wake_loss_percent,
            gross_capacity_factor=gross_cf,
            net_capacity_factor=net_cf,
            gross_full_load_hours=gross_flh,
            net_full_load_hours=net_flh,
            turbine_aep=turbine_net,
            turbine_wake_loss=turbine_wake_loss,
        )

    def _get_speed_probability(
        self,
        speed: float,
        weibull: "WeibullParameters",
        bin_width: float = 1.0,
    ) -> float:
        """
        Get probability for a wind speed bin.

        Uses Weibull CDF to calculate probability of speed falling
        in the bin [speed - width/2, speed + width/2].

        Args:
            speed: Center of wind speed bin
            weibull: Weibull parameters
            bin_width: Width of speed bin in m/s

        Returns:
            Probability of wind speed in bin
        """
        low = max(0, speed - bin_width / 2)
        high = speed + bin_width / 2

        return weibull.cdf(high) - weibull.cdf(low)

    def calculate_monthly_energy(
        self,
        aep_result: AEPResult,
        monthly_factors: list[float] | None = None,
    ) -> list[float]:
        """
        Estimate monthly energy production.

        Args:
            aep_result: Annual energy result
            monthly_factors: Optional monthly scaling factors (12 values summing to ~1)
                           If None, assumes uniform distribution

        Returns:
            List of 12 monthly energy values in MWh
        """
        if monthly_factors is None:
            # Default: equal distribution
            monthly_factors = [1.0 / 12] * 12
        elif len(monthly_factors) != 12:
            raise ValueError("Must provide 12 monthly factors")

        # Normalize factors
        total = sum(monthly_factors)
        factors = [f / total for f in monthly_factors]

        return [aep_result.net_aep_mwh * f for f in factors]

    def calculate_uncertainty(
        self,
        aep_result: AEPResult,
        wind_uncertainty: float = 0.05,
        wake_model_uncertainty: float = 0.10,
    ) -> dict[str, float]:
        """
        Estimate AEP uncertainty.

        Args:
            aep_result: AEP results
            wind_uncertainty: Wind resource uncertainty (standard: 5%)
            wake_model_uncertainty: Wake model uncertainty (standard: 10%)

        Returns:
            Dictionary with P50, P75, P90 AEP estimates
        """
        import math

        # Combined uncertainty (simplified RSS)
        total_uncertainty = math.sqrt(wind_uncertainty**2 + wake_model_uncertainty**2)

        # Exceedance probabilities (assuming normal distribution)
        # P50 = median = net AEP
        # P75 = 75% chance of exceeding this value
        # P90 = 90% chance of exceeding this value

        # Z-scores for exceedance levels
        z_50 = 0.0
        z_75 = 0.674  # 75th percentile
        z_90 = 1.282  # 90th percentile

        net_aep = aep_result.net_aep_mwh
        sigma = net_aep * total_uncertainty

        return {
            "p50_mwh": net_aep - z_50 * sigma,
            "p75_mwh": net_aep - z_75 * sigma,
            "p90_mwh": net_aep - z_90 * sigma,
            "uncertainty_percent": total_uncertainty * 100,
        }


# Import at end for type hints
from app.models.wind import WeibullParameters

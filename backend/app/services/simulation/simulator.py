"""Main simulation orchestrator."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

from app.models.power import FarmPowerResult, TurbinePowerResult
from app.models.simulation import (
    DirectionalResult,
    SimulationConfig,
    SimulationResults,
    SimulationRun,
    SimulationStatus,
)
from app.models.turbine import TurbineLayout
from app.models.wake import WakeGeometry, WakeModelType, WakeParameters, WakeResult
from app.models.wind import WindData
from app.services.power.farm_aggregator import FarmAggregator
from app.services.power.power_calculator import PowerCalculator
from app.services.wake.bastankhah import BastankhahWakeModel
from app.services.wake.geometry import WakeGeometryGenerator
from app.services.wake.jensen import JensenWakeModel
from app.services.wake.superposition import WakeSuperposition


class Simulator:
    """Main simulation orchestrator for wake loss calculations."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        """
        Initialize simulator.

        Args:
            config: Simulation configuration
        """
        self.config = config or SimulationConfig()
        self._setup_services()

    def _setup_services(self) -> None:
        """Initialize required services based on configuration."""
        # Wake model
        if self.config.wake_params.model_type == WakeModelType.BASTANKHAH:
            self.wake_model = BastankhahWakeModel(self.config.wake_params)
        else:
            self.wake_model = JensenWakeModel(self.config.wake_params)

        # Other services
        self.superposition = WakeSuperposition(self.config.wake_params.superposition)
        self.power_calculator = PowerCalculator()
        self.farm_aggregator = FarmAggregator()
        self.geometry_generator = WakeGeometryGenerator(
            self.wake_model, self.config.wake_params
        )

    def run(
        self,
        layout: TurbineLayout,
        wind_data: WindData,
        progress_callback: Callable[[float], None] | None = None,
    ) -> SimulationResults:
        """
        Run full simulation across all directions and speeds.

        Args:
            layout: Wind farm layout
            wind_data: Wind data (rose and speed distribution)
            progress_callback: Optional callback for progress updates

        Returns:
            SimulationResults with all directional results and AEP
        """
        start_time = time.time()

        # Generate direction bins
        directions = self._generate_direction_bins()
        total_steps = len(directions)

        directional_results: list[DirectionalResult] = []

        for i, direction in enumerate(directions):
            # Get probability for this direction
            direction_prob = wind_data.wind_rose.get_probability(direction)

            # Skip directions with negligible probability
            if direction_prob < 0.001:
                continue

            # Run simulation for this direction
            dir_result = self._simulate_direction(
                layout, wind_data, direction, direction_prob
            )
            directional_results.append(dir_result)

            # Update progress
            if progress_callback:
                progress = (i + 1) / total_steps * 100
                progress_callback(progress)

        # Calculate summary statistics
        overall_loss = self._calculate_overall_wake_loss(directional_results)
        worst_dir, best_dir = self._find_extreme_directions(directional_results)

        computation_time = time.time() - start_time

        return SimulationResults(
            directional_results=directional_results,
            aep=None,  # AEP calculated separately
            overall_wake_loss_percent=overall_loss,
            worst_direction=worst_dir,
            best_direction=best_dir,
            computation_time_seconds=computation_time,
        )

    def run_single_condition(
        self,
        layout: TurbineLayout,
        wind_direction: float,
        wind_speed: float,
    ) -> FarmPowerResult:
        """
        Run simulation for a single wind condition.

        Args:
            layout: Wind farm layout
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s

        Returns:
            FarmPowerResult for this condition
        """
        turbine_results: list[TurbinePowerResult] = []

        # Calculate wake effects for all turbine pairs
        all_wake_results = self._calculate_all_wakes(layout, wind_direction, wind_speed)

        # Calculate power for each turbine
        for turbine in layout.turbines:
            # Get wakes affecting this turbine
            affecting_wakes = all_wake_results.get(turbine.id, [])

            # Combine wake deficits
            combined_deficit = self.superposition.combine_deficits(affecting_wakes)

            # Calculate power
            power_result = self.power_calculator.calculate_power(
                turbine,
                wind_speed,
                wind_direction,
                affecting_wakes,
                combined_deficit,
            )
            turbine_results.append(power_result)

        # Aggregate farm results
        return self.farm_aggregator.aggregate(
            turbine_results, wind_direction, wind_speed
        )

    def _simulate_direction(
        self,
        layout: TurbineLayout,
        wind_data: WindData,
        direction: float,
        direction_prob: float,
    ) -> DirectionalResult:
        """
        Run simulation for a single direction across all wind speeds.

        Args:
            layout: Wind farm layout
            wind_data: Wind data
            direction: Wind direction in degrees
            direction_prob: Probability of this direction

        Returns:
            DirectionalResult with all speed results
        """
        # Get Weibull for this direction
        weibull = wind_data.get_weibull(direction)

        # Generate wind speed bins
        speed_bins = self._generate_speed_bins(weibull)

        farm_results: list[FarmPowerResult] = []

        for speed, _ in speed_bins:
            result = self.run_single_condition(layout, direction, speed)
            farm_results.append(result)

        # Generate wake geometries if enabled
        wake_geometries: list[WakeGeometry] = []
        if self.config.include_wake_geometry:
            wake_geometries = self.geometry_generator.generate_all_wakes(
                layout, direction
            )

        # Calculate directional statistics
        mean_loss = self._calculate_mean_wake_loss(farm_results)
        mean_power = sum(r.total_wake_affected_power for r in farm_results) / len(
            farm_results
        )

        return DirectionalResult(
            direction=direction,
            direction_probability=direction_prob,
            farm_results=farm_results,
            wake_geometries=wake_geometries,
            mean_wake_loss_percent=mean_loss,
            mean_power_output=mean_power,
        )

    def _calculate_all_wakes(
        self,
        layout: TurbineLayout,
        wind_direction: float,
        wind_speed: float,
    ) -> dict[str, list[WakeResult]]:
        """
        Calculate wake effects for all turbine pairs.

        Returns dictionary mapping downstream turbine ID to list of wake effects.
        """
        wake_results: dict[str, list[WakeResult]] = {
            str(t.id): [] for t in layout.turbines
        }

        # Check all pairs
        for upstream in layout.turbines:
            for downstream in layout.turbines:
                if upstream.id == downstream.id:
                    continue

                # Check if downstream is actually downstream
                if not self.wake_model.is_downstream(
                    upstream, downstream, wind_direction
                ):
                    continue

                # Calculate wake effect
                wake_result = self.wake_model.calculate_velocity_deficit(
                    upstream, downstream, wind_direction, wind_speed
                )

                if wake_result.is_in_wake:
                    wake_results[str(downstream.id)].append(wake_result)

        return wake_results

    def _generate_direction_bins(self) -> list[float]:
        """Generate direction bins for simulation."""
        step = self.config.direction_step
        directions = []
        d = self.config.direction_start
        while d < self.config.direction_end:
            directions.append(d)
            d += step
        return directions

    def _generate_speed_bins(
        self, weibull: "WeibullParameters"
    ) -> list[tuple[float, float]]:
        """Generate wind speed bins with probabilities."""
        from app.services.loaders.wind_loader import WindLoader

        return WindLoader.generate_speed_bins(
            weibull,
            self.config.wind_speed_bins,
            self.config.wind_speed_min,
            self.config.wind_speed_max,
        )

    def _calculate_mean_wake_loss(
        self, farm_results: list[FarmPowerResult]
    ) -> float:
        """Calculate mean wake loss across wind speeds."""
        if not farm_results:
            return 0.0
        return sum(r.farm_wake_loss_percent for r in farm_results) / len(farm_results)

    def _calculate_overall_wake_loss(
        self, directional_results: list[DirectionalResult]
    ) -> float:
        """Calculate overall probability-weighted wake loss."""
        if not directional_results:
            return 0.0

        total_weighted_loss = sum(
            r.mean_wake_loss_percent * r.direction_probability
            for r in directional_results
        )
        total_prob = sum(r.direction_probability for r in directional_results)

        if total_prob > 0:
            return total_weighted_loss / total_prob
        return 0.0

    def _find_extreme_directions(
        self, directional_results: list[DirectionalResult]
    ) -> tuple[float, float]:
        """Find directions with highest and lowest wake losses."""
        if not directional_results:
            return 0.0, 0.0

        worst = max(directional_results, key=lambda r: r.mean_wake_loss_percent)
        best = min(directional_results, key=lambda r: r.mean_wake_loss_percent)

        return worst.direction, best.direction


# Import at end to avoid circular imports
from app.models.wind import WeibullParameters

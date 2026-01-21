"""Farm-level power aggregation service."""

from __future__ import annotations

from app.models.power import FarmPowerResult, TurbinePowerResult


class FarmAggregator:
    """Service for aggregating power results across the farm."""

    def __init__(self) -> None:
        """Initialize farm aggregator."""
        pass

    def aggregate(
        self,
        turbine_results: list[TurbinePowerResult],
        wind_direction: float,
        wind_speed: float,
    ) -> FarmPowerResult:
        """
        Aggregate turbine results into farm-level metrics.

        Args:
            turbine_results: List of per-turbine power results
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s

        Returns:
            FarmPowerResult with aggregated metrics
        """
        if not turbine_results:
            return FarmPowerResult(
                wind_direction=wind_direction,
                wind_speed=wind_speed,
                turbine_results=[],
                total_free_stream_power=0.0,
                total_wake_affected_power=0.0,
                total_rated_power=0.0,
                total_power_loss=0.0,
                farm_wake_loss_percent=0.0,
                capacity_factor=0.0,
                turbines_operating=0,
                turbines_in_wake=0,
                max_individual_loss_percent=0.0,
                avg_individual_loss_percent=0.0,
            )

        # Calculate totals
        total_free_stream = sum(t.free_stream_power for t in turbine_results)
        total_wake_affected = sum(t.wake_affected_power for t in turbine_results)
        total_rated = sum(t.rated_power for t in turbine_results)
        total_loss = total_free_stream - total_wake_affected

        # Calculate percentages
        if total_free_stream > 0:
            farm_wake_loss_percent = (total_loss / total_free_stream) * 100
        else:
            farm_wake_loss_percent = 0.0

        if total_rated > 0:
            capacity_factor = (total_wake_affected / total_rated) * 100
        else:
            capacity_factor = 0.0

        # Count statistics
        turbines_operating = sum(1 for t in turbine_results if t.is_operating)
        turbines_in_wake = sum(1 for t in turbine_results if t.combined_velocity_deficit > 0)

        # Individual loss statistics
        loss_percents = [t.power_loss_percent for t in turbine_results if t.is_operating]
        if loss_percents:
            max_loss = max(loss_percents)
            avg_loss = sum(loss_percents) / len(loss_percents)
        else:
            max_loss = 0.0
            avg_loss = 0.0

        return FarmPowerResult(
            wind_direction=wind_direction,
            wind_speed=wind_speed,
            turbine_results=turbine_results,
            total_free_stream_power=total_free_stream,
            total_wake_affected_power=total_wake_affected,
            total_rated_power=total_rated,
            total_power_loss=total_loss,
            farm_wake_loss_percent=farm_wake_loss_percent,
            capacity_factor=capacity_factor,
            turbines_operating=turbines_operating,
            turbines_in_wake=turbines_in_wake,
            max_individual_loss_percent=max_loss,
            avg_individual_loss_percent=avg_loss,
        )

    def calculate_weighted_average(
        self,
        farm_results: list[FarmPowerResult],
        weights: list[float],
    ) -> dict[str, float]:
        """
        Calculate weighted average metrics across multiple conditions.

        Args:
            farm_results: List of farm results for different conditions
            weights: Probability weights for each condition

        Returns:
            Dictionary with weighted metrics
        """
        if not farm_results or not weights:
            return {
                "weighted_power": 0.0,
                "weighted_loss": 0.0,
                "weighted_loss_percent": 0.0,
                "weighted_capacity_factor": 0.0,
            }

        if len(farm_results) != len(weights):
            raise ValueError("Number of results must match number of weights")

        # Normalize weights
        total_weight = sum(weights)
        if total_weight <= 0:
            total_weight = 1.0
        norm_weights = [w / total_weight for w in weights]

        # Calculate weighted sums
        weighted_power = sum(
            r.total_wake_affected_power * w for r, w in zip(farm_results, norm_weights)
        )
        weighted_free_stream = sum(
            r.total_free_stream_power * w for r, w in zip(farm_results, norm_weights)
        )
        weighted_loss = sum(r.total_power_loss * w for r, w in zip(farm_results, norm_weights))
        weighted_cf = sum(r.capacity_factor * w for r, w in zip(farm_results, norm_weights))

        if weighted_free_stream > 0:
            weighted_loss_percent = (weighted_loss / weighted_free_stream) * 100
        else:
            weighted_loss_percent = 0.0

        return {
            "weighted_power": weighted_power,
            "weighted_free_stream_power": weighted_free_stream,
            "weighted_loss": weighted_loss,
            "weighted_loss_percent": weighted_loss_percent,
            "weighted_capacity_factor": weighted_cf,
        }

    def rank_turbines_by_loss(
        self,
        turbine_results: list[TurbinePowerResult],
        metric: str = "power_loss",
    ) -> list[dict[str, float | str]]:
        """
        Rank turbines by wake loss.

        Args:
            turbine_results: List of turbine results
            metric: Ranking metric ('power_loss', 'power_loss_percent', 'deficit')

        Returns:
            Ranked list of turbine loss summaries
        """
        if metric == "power_loss":
            sorted_results = sorted(turbine_results, key=lambda t: t.power_loss, reverse=True)
        elif metric == "power_loss_percent":
            sorted_results = sorted(
                turbine_results, key=lambda t: t.power_loss_percent, reverse=True
            )
        elif metric == "deficit":
            sorted_results = sorted(
                turbine_results, key=lambda t: t.combined_velocity_deficit, reverse=True
            )
        else:
            sorted_results = turbine_results

        return [
            {
                "rank": i + 1,
                "name": t.turbine_name,
                "power_loss_kw": t.power_loss,
                "power_loss_percent": t.power_loss_percent,
                "velocity_deficit": t.combined_velocity_deficit,
                "effective_speed": t.effective_speed,
            }
            for i, t in enumerate(sorted_results)
        ]

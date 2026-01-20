"""Power calculation domain models."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class TurbinePowerResult(BaseModel):
    """Power calculation result for a single turbine."""

    turbine_id: UUID = Field(description="Turbine identifier")
    turbine_name: str = Field(description="Turbine name")

    # Wind conditions
    wind_direction: float = Field(ge=0, lt=360, description="Wind direction in degrees")
    free_stream_speed: float = Field(ge=0, description="Free-stream wind speed in m/s")
    effective_speed: float = Field(ge=0, description="Wake-affected effective wind speed in m/s")

    # Power values
    free_stream_power: float = Field(ge=0, description="Power without wake effects in kW")
    wake_affected_power: float = Field(ge=0, description="Power with wake effects in kW")
    rated_power: float = Field(ge=0, description="Turbine rated power in kW")

    # Loss metrics
    power_loss: float = Field(ge=0, description="Absolute power loss in kW")
    power_loss_percent: Annotated[
        float, Field(ge=0, le=100, description="Relative power loss in %")
    ]

    # Wake information
    upstream_turbines: list[UUID] = Field(
        default_factory=list, description="IDs of turbines affecting this one"
    )
    combined_velocity_deficit: float = Field(
        default=0.0, ge=0, le=1, description="Combined velocity deficit from all wakes"
    )

    # Status
    is_operating: bool = Field(
        default=True, description="Whether turbine is operating (within cut-in/cut-out)"
    )


class FarmPowerResult(BaseModel):
    """Aggregated power result for the entire farm."""

    wind_direction: float = Field(ge=0, lt=360, description="Wind direction in degrees")
    wind_speed: float = Field(ge=0, description="Wind speed in m/s")

    # Turbine results
    turbine_results: list[TurbinePowerResult] = Field(
        description="Per-turbine power results"
    )

    # Aggregated values
    total_free_stream_power: float = Field(ge=0, description="Total power without wakes in kW")
    total_wake_affected_power: float = Field(ge=0, description="Total power with wakes in kW")
    total_rated_power: float = Field(ge=0, description="Total rated power in kW")

    # Loss metrics
    total_power_loss: float = Field(ge=0, description="Total power loss in kW")
    farm_wake_loss_percent: Annotated[
        float, Field(ge=0, le=100, description="Farm-level wake loss in %")
    ]
    capacity_factor: Annotated[
        float, Field(ge=0, le=100, description="Capacity factor in %")
    ]

    # Statistics
    turbines_operating: int = Field(ge=0, description="Number of operating turbines")
    turbines_in_wake: int = Field(ge=0, description="Number of turbines affected by wakes")
    max_individual_loss_percent: float = Field(
        ge=0, le=100, description="Maximum individual turbine loss in %"
    )
    avg_individual_loss_percent: float = Field(
        ge=0, le=100, description="Average individual turbine loss in %"
    )

    @property
    def turbine_count(self) -> int:
        """Get total turbine count."""
        return len(self.turbine_results)

    def get_turbine_ranking(self, by: str = "power_loss") -> list[TurbinePowerResult]:
        """Get turbines ranked by specified metric."""
        if by == "power_loss":
            return sorted(self.turbine_results, key=lambda t: t.power_loss, reverse=True)
        elif by == "power_loss_percent":
            return sorted(
                self.turbine_results, key=lambda t: t.power_loss_percent, reverse=True
            )
        elif by == "power":
            return sorted(
                self.turbine_results, key=lambda t: t.wake_affected_power, reverse=True
            )
        else:
            return self.turbine_results


class PowerResult(BaseModel):
    """Complete power calculation result including multiple conditions."""

    farm_results: list[FarmPowerResult] = Field(description="Results per wind condition")

    # Weighted aggregates (if probabilities provided)
    weighted_total_power: float | None = Field(
        default=None, description="Probability-weighted total power in kW"
    )
    weighted_wake_loss: float | None = Field(
        default=None, description="Probability-weighted wake loss in kW"
    )
    weighted_wake_loss_percent: float | None = Field(
        default=None, description="Probability-weighted wake loss percentage"
    )

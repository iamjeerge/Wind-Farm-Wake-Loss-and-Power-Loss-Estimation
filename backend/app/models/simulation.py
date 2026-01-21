"""Simulation domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.power import FarmPowerResult
from app.models.turbine import TurbineLayout
from app.models.wake import WakeGeometry, WakeModelType, WakeParameters
from app.models.wind import WindData


class SimulationStatus(str, Enum):
    """Simulation execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationConfig(BaseModel):
    """Configuration for a simulation run."""

    # Wake model settings
    wake_params: WakeParameters = Field(
        default_factory=WakeParameters, description="Wake model parameters"
    )

    # Direction sweep settings
    direction_resolution: int = Field(
        default=36,
        ge=4,
        le=360,
        description="Number of direction bins for sweep (e.g., 36 = 10° steps)",
    )
    direction_start: float = Field(
        default=0.0, ge=0, lt=360, description="Starting direction in degrees"
    )
    direction_end: float = Field(
        default=360.0, ge=0, le=360, description="Ending direction in degrees"
    )

    # Wind speed settings
    wind_speed_bins: int = Field(default=25, ge=5, le=50, description="Number of wind speed bins")
    wind_speed_min: float = Field(
        default=3.0, ge=0, le=10, description="Minimum wind speed (cut-in) in m/s"
    )
    wind_speed_max: float = Field(
        default=25.0, ge=15, le=35, description="Maximum wind speed (cut-out) in m/s"
    )

    # Computation options
    include_wake_geometry: bool = Field(
        default=True, description="Generate wake geometry for visualization"
    )
    compute_aep: bool = Field(default=True, description="Compute Annual Energy Production")

    @property
    def direction_step(self) -> float:
        """Get direction step size in degrees."""
        return (self.direction_end - self.direction_start) / self.direction_resolution

    @property
    def wind_speed_step(self) -> float:
        """Get wind speed step size in m/s."""
        return (self.wind_speed_max - self.wind_speed_min) / self.wind_speed_bins


class DirectionalResult(BaseModel):
    """Results for a single wind direction."""

    direction: float = Field(ge=0, lt=360, description="Wind direction in degrees")
    direction_probability: float = Field(ge=0, le=1, description="Probability of this direction")

    # Power results across wind speeds
    farm_results: list[FarmPowerResult] = Field(description="Farm results per wind speed bin")

    # Wake geometries for visualization
    wake_geometries: list[WakeGeometry] = Field(
        default_factory=list, description="Wake geometries for this direction"
    )

    # Aggregated metrics for this direction
    mean_wake_loss_percent: float = Field(
        ge=0, le=100, description="Mean wake loss for this direction"
    )
    mean_power_output: float = Field(ge=0, description="Mean power output in kW")


class AEPResult(BaseModel):
    """Annual Energy Production results."""

    # Without wake losses
    gross_aep_mwh: float = Field(ge=0, description="Gross AEP without wake losses in MWh")

    # With wake losses
    net_aep_mwh: float = Field(ge=0, description="Net AEP with wake losses in MWh")

    # Loss metrics
    wake_loss_mwh: float = Field(ge=0, description="Energy lost to wakes in MWh")
    wake_loss_percent: Annotated[
        float, Field(ge=0, le=100, description="Wake loss as percentage of gross AEP")
    ]

    # Capacity factors
    gross_capacity_factor: Annotated[
        float, Field(ge=0, le=100, description="Gross capacity factor in %")
    ]
    net_capacity_factor: Annotated[
        float, Field(ge=0, le=100, description="Net capacity factor in %")
    ]

    # Full load hours
    gross_full_load_hours: float = Field(ge=0, le=8760, description="Gross full load hours")
    net_full_load_hours: float = Field(ge=0, le=8760, description="Net full load hours")

    # Per-turbine AEP
    turbine_aep: dict[str, float] = Field(
        default_factory=dict, description="AEP per turbine in MWh"
    )
    turbine_wake_loss: dict[str, float] = Field(
        default_factory=dict, description="Wake loss per turbine in MWh"
    )


class SimulationResults(BaseModel):
    """Complete simulation results."""

    # Directional results
    directional_results: list[DirectionalResult] = Field(description="Results per wind direction")

    # AEP results
    aep: AEPResult | None = Field(default=None, description="Annual Energy Production results")

    # Summary statistics
    overall_wake_loss_percent: float = Field(
        ge=0, le=100, description="Overall weighted wake loss percentage"
    )
    worst_direction: float = Field(ge=0, lt=360, description="Direction with highest wake losses")
    best_direction: float = Field(ge=0, lt=360, description="Direction with lowest wake losses")

    # Computation metadata
    computation_time_seconds: float = Field(ge=0, description="Total computation time")


class SimulationRun(BaseModel):
    """Complete simulation run record."""

    id: UUID = Field(default_factory=uuid4, description="Unique simulation identifier")
    name: str = Field(default="Simulation", description="Simulation name")

    # Input data
    layout: TurbineLayout = Field(description="Wind farm layout")
    wind_data: WindData = Field(description="Wind data")
    config: SimulationConfig = Field(description="Simulation configuration")

    # Status
    status: SimulationStatus = Field(
        default=SimulationStatus.PENDING, description="Simulation status"
    )
    progress: float = Field(default=0.0, ge=0, le=100, description="Progress percentage")
    error_message: str | None = Field(default=None, description="Error message if failed")

    # Results
    results: SimulationResults | None = Field(default=None, description="Simulation results")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

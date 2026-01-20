"""Wake model domain models."""

from __future__ import annotations

from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class WakeModelType(str, Enum):
    """Supported wake model types."""

    JENSEN = "jensen"
    BASTANKHAH = "bastankhah"


class WakeParameters(BaseModel):
    """Parameters for wake calculations."""

    model_type: WakeModelType = Field(
        default=WakeModelType.JENSEN, description="Wake model to use"
    )

    # Jensen model parameters
    wake_decay_coefficient: float = Field(
        default=0.04,
        ge=0.01,
        le=0.15,
        description="Wake decay coefficient (k). 0.04 offshore, 0.075 onshore",
    )

    # Bastankhah model parameters
    turbulence_intensity: float = Field(
        default=0.06,
        ge=0.01,
        le=0.30,
        description="Ambient turbulence intensity (TI)",
    )
    atmospheric_stability: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Atmospheric stability parameter (-1=stable, 0=neutral, 1=unstable)",
    )

    # Common parameters
    air_density: float = Field(
        default=1.225, ge=0.9, le=1.5, description="Air density in kg/m³"
    )

    # Superposition method
    superposition: str = Field(
        default="quadratic",
        description="Wake superposition method: 'linear', 'quadratic', 'max'",
    )


class WakeResult(BaseModel):
    """Wake effect result for a single turbine pair."""

    upstream_turbine_id: UUID = Field(description="ID of the upstream turbine")
    downstream_turbine_id: UUID = Field(description="ID of the downstream turbine")
    wind_direction: float = Field(ge=0, lt=360, description="Wind direction in degrees")
    wind_speed: float = Field(ge=0, description="Free-stream wind speed in m/s")

    # Wake characteristics
    distance: float = Field(ge=0, description="Distance between turbines in meters")
    distance_rotor_diameters: float = Field(
        ge=0, description="Distance in rotor diameters"
    )
    lateral_offset: float = Field(description="Lateral offset from wake centerline in meters")
    wake_radius: float = Field(ge=0, description="Wake radius at downstream position in meters")

    # Velocity deficit
    velocity_deficit: Annotated[
        float, Field(ge=0, le=1, description="Velocity deficit ratio (0-1)")
    ]
    effective_wind_speed: float = Field(
        ge=0, description="Effective wind speed at downstream turbine in m/s"
    )

    # Wake overlap
    overlap_fraction: Annotated[
        float, Field(ge=0, le=1, description="Fraction of rotor area affected by wake")
    ]
    is_in_wake: bool = Field(description="Whether downstream turbine is in wake zone")


class WakeGeometry(BaseModel):
    """Wake geometry for visualization."""

    turbine_id: UUID = Field(description="ID of the turbine producing the wake")
    wind_direction: float = Field(ge=0, lt=360, description="Wind direction in degrees")

    # Wake cone/ellipse geometry
    origin_x: float = Field(description="Wake origin X coordinate")
    origin_y: float = Field(description="Wake origin Y coordinate")
    length: float = Field(ge=0, description="Wake length in meters")
    initial_radius: float = Field(ge=0, description="Initial wake radius in meters")
    final_radius: float = Field(ge=0, description="Final wake radius in meters")
    expansion_angle: float = Field(ge=0, lt=90, description="Wake expansion angle in degrees")

    # Deficit profile along centerline
    centerline_deficit: list[tuple[float, float]] = Field(
        default_factory=list,
        description="(distance, deficit) pairs along wake centerline",
    )

    # Polygon vertices for rendering
    polygon_vertices: list[tuple[float, float]] = Field(
        default_factory=list, description="(x, y) vertices of wake polygon"
    )

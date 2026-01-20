"""Turbine domain models."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class PowerCurvePoint(BaseModel):
    """Single point on a turbine power curve."""

    wind_speed: Annotated[float, Field(ge=0, le=50, description="Wind speed in m/s")]
    power: Annotated[float, Field(ge=0, description="Power output in kW")]

    class Config:
        frozen = True


class PowerCurve(BaseModel):
    """Turbine power curve with cut-in, rated, and cut-out speeds."""

    points: Annotated[list[PowerCurvePoint], Field(min_length=2, description="Power curve points")]
    cut_in_speed: Annotated[float, Field(ge=0, le=10, description="Cut-in wind speed in m/s")]
    rated_speed: Annotated[float, Field(ge=5, le=20, description="Rated wind speed in m/s")]
    cut_out_speed: Annotated[float, Field(ge=15, le=35, description="Cut-out wind speed in m/s")]

    @model_validator(mode="after")
    def validate_speeds(self) -> "PowerCurve":
        """Validate that speeds are in correct order."""
        if not (self.cut_in_speed < self.rated_speed < self.cut_out_speed):
            raise ValueError("Speeds must be: cut_in < rated < cut_out")
        return self

    @field_validator("points")
    @classmethod
    def validate_points_sorted(cls, v: list[PowerCurvePoint]) -> list[PowerCurvePoint]:
        """Ensure power curve points are sorted by wind speed."""
        sorted_points = sorted(v, key=lambda p: p.wind_speed)
        return sorted_points


class TurbineCreate(BaseModel):
    """Input model for creating a turbine."""

    name: Annotated[str, Field(min_length=1, max_length=100, description="Turbine identifier")]
    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in degrees")]
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in degrees")]
    hub_height: Annotated[float, Field(ge=30, le=200, description="Hub height in meters")]
    rotor_diameter: Annotated[float, Field(ge=20, le=250, description="Rotor diameter in meters")]
    rated_power: Annotated[float, Field(ge=100, le=20000, description="Rated power in kW")]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Strip whitespace and validate name."""
        return v.strip()


class Turbine(TurbineCreate):
    """Complete turbine model with computed properties."""

    id: UUID = Field(default_factory=uuid4, description="Unique turbine identifier")

    # Local Cartesian coordinates (computed from lat/lon)
    x: float = Field(default=0.0, description="Local X coordinate in meters")
    y: float = Field(default=0.0, description="Local Y coordinate in meters")

    # Optional power curve
    power_curve: PowerCurve | None = Field(default=None, description="Turbine power curve")

    # Thrust coefficient (can be constant or speed-dependent)
    thrust_coefficient: float = Field(
        default=0.8, ge=0, le=1, description="Thrust coefficient (Ct)"
    )

    @property
    def rotor_radius(self) -> float:
        """Get rotor radius in meters."""
        return self.rotor_diameter / 2

    @property
    def rotor_area(self) -> float:
        """Get rotor swept area in square meters."""
        import math

        return math.pi * self.rotor_radius**2

    class Config:
        frozen = False


class TurbineLayout(BaseModel):
    """Collection of turbines representing a wind farm layout."""

    turbines: Annotated[
        list[Turbine], Field(min_length=1, max_length=500, description="List of turbines")
    ]
    name: str = Field(default="Wind Farm", description="Layout name")
    reference_latitude: float | None = Field(
        default=None, description="Reference latitude for coordinate transformation"
    )
    reference_longitude: float | None = Field(
        default=None, description="Reference longitude for coordinate transformation"
    )

    @model_validator(mode="after")
    def compute_local_coordinates(self) -> "TurbineLayout":
        """Compute local x,y coordinates for all turbines from lat/lon."""
        if not self.turbines:
            return self
        
        # Use reference point or compute center
        ref_lat = self.reference_latitude
        ref_lon = self.reference_longitude
        
        if ref_lat is None:
            ref_lat = sum(t.latitude for t in self.turbines) / len(self.turbines)
        if ref_lon is None:
            ref_lon = sum(t.longitude for t in self.turbines) / len(self.turbines)
        
        # Convert each turbine's lat/lon to local x,y coordinates
        for turbine in self.turbines:
            x, y = self._latlon_to_xy(turbine.latitude, turbine.longitude, ref_lat, ref_lon)
            turbine.x = x
            turbine.y = y
        
        return self

    @staticmethod
    def _latlon_to_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
        """
        Convert lat/lon to local x,y coordinates in meters.
        
        Uses equirectangular approximation which is accurate for small areas.
        X is East-West (positive = East)
        Y is North-South (positive = North)
        """
        # Earth radius in meters
        R = 6371000
        
        # Convert to radians
        lat_rad = math.radians(lat)
        ref_lat_rad = math.radians(ref_lat)
        
        # Delta in degrees
        dlat = lat - ref_lat
        dlon = lon - ref_lon
        
        # Convert to meters
        # Y: 1 degree latitude ≈ 111km
        y = dlat * (math.pi / 180) * R
        
        # X: 1 degree longitude varies with latitude
        x = dlon * (math.pi / 180) * R * math.cos(ref_lat_rad)
        
        return x, y

    @property
    def turbine_count(self) -> int:
        """Get number of turbines."""
        return len(self.turbines)

    @property
    def total_rated_power(self) -> float:
        """Get total rated power in kW."""
        return sum(t.rated_power for t in self.turbines)

    def get_turbine_by_id(self, turbine_id: UUID) -> Turbine | None:
        """Get turbine by ID."""
        for turbine in self.turbines:
            if turbine.id == turbine_id:
                return turbine
        return None

    def get_turbine_by_name(self, name: str) -> Turbine | None:
        """Get turbine by name."""
        for turbine in self.turbines:
            if turbine.name == name:
                return turbine
        return None

    @computed_field
    @property
    def center_lat(self) -> float:
        """Get center latitude of the layout."""
        if self.reference_latitude is not None:
            return self.reference_latitude
        if self.turbines:
            return sum(t.latitude for t in self.turbines) / len(self.turbines)
        return 0.0

    @computed_field
    @property
    def center_lon(self) -> float:
        """Get center longitude of the layout."""
        if self.reference_longitude is not None:
            return self.reference_longitude
        if self.turbines:
            return sum(t.longitude for t in self.turbines) / len(self.turbines)
        return 0.0

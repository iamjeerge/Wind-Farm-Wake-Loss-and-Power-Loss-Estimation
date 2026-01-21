"""Wind condition domain models."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class WindCondition(BaseModel):
    """Single wind condition (direction and speed)."""

    direction: Annotated[
        float, Field(ge=0, lt=360, description="Wind direction in degrees (0=N, 90=E)")
    ]
    speed: Annotated[float, Field(ge=0, le=50, description="Wind speed in m/s")]
    probability: float = Field(default=1.0, ge=0, le=1, description="Probability of this condition")

    @property
    def direction_radians(self) -> float:
        """Get wind direction in radians."""
        import math

        return math.radians(self.direction)

    class Config:
        frozen = True


class WindRoseEntry(BaseModel):
    """Single entry in a wind rose (direction sector probability)."""

    direction: Annotated[
        float, Field(ge=0, lt=360, description="Center direction of sector in degrees")
    ]
    probability: Annotated[float, Field(ge=0, le=1, description="Probability of this sector")]
    sector_width: float = Field(default=10.0, ge=1, le=45, description="Sector width in degrees")

    @property
    def direction_min(self) -> float:
        """Get minimum direction of sector."""
        return (self.direction - self.sector_width / 2) % 360

    @property
    def direction_max(self) -> float:
        """Get maximum direction of sector."""
        return (self.direction + self.sector_width / 2) % 360


class WindRose(BaseModel):
    """Wind rose representing directional wind probability distribution."""

    entries: Annotated[
        list[WindRoseEntry], Field(min_length=4, max_length=72, description="Wind rose entries")
    ]
    name: str = Field(default="Wind Rose", description="Wind rose identifier")

    @field_validator("entries")
    @classmethod
    def validate_probabilities_sum(cls, v: list[WindRoseEntry]) -> list[WindRoseEntry]:
        """Validate that probabilities sum to approximately 1."""
        total = sum(e.probability for e in v)
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Wind rose probabilities must sum to ~1.0, got {total:.3f}")
        return v

    def get_probability(self, direction: float) -> float:
        """Get probability for a given direction."""
        for entry in self.entries:
            if entry.direction_min <= direction < entry.direction_max:
                return entry.probability
            # Handle wrap-around at 360 degrees
            if entry.direction_min > entry.direction_max:
                if direction >= entry.direction_min or direction < entry.direction_max:
                    return entry.probability
        return 0.0


class WeibullParameters(BaseModel):
    """Weibull distribution parameters for wind speed."""

    shape: Annotated[float, Field(gt=0, le=10, description="Shape parameter (k)")]
    scale: Annotated[float, Field(gt=0, le=30, description="Scale parameter (A/λ) in m/s")]
    direction: float | None = Field(
        default=None, ge=0, lt=360, description="Direction this applies to (None = all)"
    )

    @property
    def mean_speed(self) -> float:
        """Calculate mean wind speed from Weibull parameters."""
        import math

        return self.scale * math.gamma(1 + 1 / self.shape)

    def pdf(self, speed: float) -> float:
        """Calculate probability density at given speed."""
        import math

        if speed <= 0:
            return 0.0
        k, a = self.shape, self.scale
        return (k / a) * (speed / a) ** (k - 1) * math.exp(-((speed / a) ** k))

    def cdf(self, speed: float) -> float:
        """Calculate cumulative distribution at given speed."""
        import math

        if speed <= 0:
            return 0.0
        return 1 - math.exp(-((speed / self.scale) ** self.shape))


class WindData(BaseModel):
    """Complete wind data including rose and speed distribution."""

    wind_rose: WindRose = Field(description="Directional probability distribution")
    weibull: WeibullParameters = Field(description="Wind speed distribution parameters")

    # Optional: direction-specific Weibull parameters
    directional_weibull: dict[float, WeibullParameters] | None = Field(
        default=None, description="Direction-specific Weibull parameters"
    )

    @model_validator(mode="after")
    def validate_directional_weibull(self) -> "WindData":
        """Validate directional Weibull parameters match wind rose."""
        if self.directional_weibull is not None:
            rose_directions = {e.direction for e in self.wind_rose.entries}
            weibull_directions = set(self.directional_weibull.keys())
            if not weibull_directions.issubset(rose_directions):
                raise ValueError("Directional Weibull directions must match wind rose")
        return self

    def get_weibull(self, direction: float | None = None) -> WeibullParameters:
        """Get Weibull parameters, optionally for specific direction."""
        if direction is not None and self.directional_weibull:
            # Find closest direction
            closest = min(
                self.directional_weibull.keys(),
                key=lambda d: abs((d - direction + 180) % 360 - 180),
            )
            return self.directional_weibull[closest]
        return self.weibull

    def sample_conditions(self, n_samples: int = 1000) -> list[WindCondition]:
        """Sample wind conditions from distributions."""
        import numpy as np

        conditions = []
        rng = np.random.default_rng()

        for entry in self.wind_rose.entries:
            n_sector = int(entry.probability * n_samples)
            if n_sector == 0:
                continue

            weibull = self.get_weibull(entry.direction)
            speeds = rng.weibull(weibull.shape, n_sector) * weibull.scale

            for speed in speeds:
                # Add some direction variability within sector
                direction = entry.direction + rng.uniform(
                    -entry.sector_width / 2, entry.sector_width / 2
                )
                direction = direction % 360

                conditions.append(
                    WindCondition(
                        direction=direction,
                        speed=float(speed),
                        probability=entry.probability / n_sector,
                    )
                )

        return conditions

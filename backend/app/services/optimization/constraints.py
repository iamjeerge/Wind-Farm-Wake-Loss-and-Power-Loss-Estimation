"""Layout constraints for optimization."""

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
from pydantic import BaseModel, Field


class LayoutConstraints(BaseModel):
    """Container for all layout constraints."""

    min_spacing_diameters: float = Field(
        default=5.0,
        ge=2.0,
        le=15.0,
        description="Minimum spacing between turbines in rotor diameters",
    )
    rotor_diameter: float = Field(
        default=126.0,
        gt=0,
        description="Rotor diameter in meters",
    )
    boundary_buffer: float = Field(
        default=200.0,
        ge=0,
        description="Buffer distance from boundary in meters",
    )
    max_turbines: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of turbines allowed",
    )

    @property
    def min_spacing_meters(self) -> float:
        """Get minimum spacing in meters."""
        return self.min_spacing_diameters * self.rotor_diameter


class Constraint(ABC):
    """Abstract base class for constraints."""

    @abstractmethod
    def is_satisfied(self, positions: np.ndarray) -> bool:
        """Check if constraint is satisfied."""
        pass

    @abstractmethod
    def penalty(self, positions: np.ndarray) -> float:
        """Calculate penalty for constraint violation."""
        pass


class MinSpacingConstraint(Constraint):
    """Minimum spacing constraint between turbines."""

    def __init__(self, min_spacing: float):
        """
        Initialize constraint.

        Args:
            min_spacing: Minimum spacing in meters
        """
        self.min_spacing = min_spacing

    def is_satisfied(self, positions: np.ndarray) -> bool:
        """Check if all turbines meet minimum spacing."""
        n = len(positions)
        for i in range(n):
            for j in range(i + 1, n):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist < self.min_spacing:
                    return False
        return True

    def penalty(self, positions: np.ndarray) -> float:
        """Calculate penalty based on spacing violations."""
        n = len(positions)
        total_penalty = 0.0

        for i in range(n):
            for j in range(i + 1, n):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist < self.min_spacing:
                    # Quadratic penalty for violations
                    violation = (self.min_spacing - dist) / self.min_spacing
                    total_penalty += violation**2

        return total_penalty


class BoundaryConstraint(Constraint):
    """Boundary constraint to keep turbines within a region."""

    def __init__(
        self,
        bounds: Tuple[Tuple[float, float], Tuple[float, float]],
        buffer: float = 0.0,
    ):
        """
        Initialize constraint.

        Args:
            bounds: ((x_min, x_max), (y_min, y_max)) in meters
            buffer: Buffer distance from boundary
        """
        self.x_min = bounds[0][0] + buffer
        self.x_max = bounds[0][1] - buffer
        self.y_min = bounds[1][0] + buffer
        self.y_max = bounds[1][1] - buffer

    def is_satisfied(self, positions: np.ndarray) -> bool:
        """Check if all turbines are within bounds."""
        for pos in positions:
            if not (self.x_min <= pos[0] <= self.x_max):
                return False
            if not (self.y_min <= pos[1] <= self.y_max):
                return False
        return True

    def penalty(self, positions: np.ndarray) -> float:
        """Calculate penalty for boundary violations."""
        total_penalty = 0.0

        for pos in positions:
            # X boundary violations
            if pos[0] < self.x_min:
                total_penalty += ((self.x_min - pos[0]) / 100) ** 2
            elif pos[0] > self.x_max:
                total_penalty += ((pos[0] - self.x_max) / 100) ** 2

            # Y boundary violations
            if pos[1] < self.y_min:
                total_penalty += ((self.y_min - pos[1]) / 100) ** 2
            elif pos[1] > self.y_max:
                total_penalty += ((pos[1] - self.y_max) / 100) ** 2

        return total_penalty


class ExclusionZoneConstraint(Constraint):
    """Constraint to exclude turbines from certain areas."""

    def __init__(self, zones: List[Tuple[float, float, float]]):
        """
        Initialize constraint.

        Args:
            zones: List of (center_x, center_y, radius) exclusion zones
        """
        self.zones = zones

    def is_satisfied(self, positions: np.ndarray) -> bool:
        """Check if all turbines are outside exclusion zones."""
        for pos in positions:
            for cx, cy, radius in self.zones:
                dist = np.sqrt((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2)
                if dist < radius:
                    return False
        return True

    def penalty(self, positions: np.ndarray) -> float:
        """Calculate penalty for exclusion zone violations."""
        total_penalty = 0.0

        for pos in positions:
            for cx, cy, radius in self.zones:
                dist = np.sqrt((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2)
                if dist < radius:
                    violation = (radius - dist) / radius
                    total_penalty += violation**2

        return total_penalty

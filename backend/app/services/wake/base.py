"""Base wake model abstract class."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from app.models.turbine import Turbine
from app.models.wake import WakeParameters, WakeResult


class BaseWakeModel(ABC):
    """Abstract base class for wake models."""

    def __init__(self, params: WakeParameters | None = None) -> None:
        """
        Initialize wake model.

        Args:
            params: Wake calculation parameters
        """
        self.params = params or WakeParameters()

    @abstractmethod
    def calculate_velocity_deficit(
        self,
        upstream: Turbine,
        downstream: Turbine,
        wind_direction: float,
        wind_speed: float,
    ) -> WakeResult:
        """
        Calculate velocity deficit at downstream turbine due to upstream wake.

        Args:
            upstream: Upstream turbine producing wake
            downstream: Downstream turbine affected by wake
            wind_direction: Wind direction in degrees (0=N, 90=E)
            wind_speed: Free-stream wind speed in m/s

        Returns:
            WakeResult with velocity deficit and wake characteristics
        """
        pass

    @abstractmethod
    def calculate_wake_radius(
        self,
        turbine: Turbine,
        distance: float,
    ) -> float:
        """
        Calculate wake radius at given downstream distance.

        Args:
            turbine: Turbine producing wake
            distance: Downstream distance in meters

        Returns:
            Wake radius in meters
        """
        pass

    def get_downstream_position(
        self,
        upstream: Turbine,
        downstream: Turbine,
        wind_direction: float,
    ) -> tuple[float, float]:
        """
        Get position of downstream turbine relative to upstream, in wind-aligned coordinates.

        Returns (downstream_distance, lateral_offset) where:
        - downstream_distance > 0 means downstream is downwind of upstream
        - lateral_offset is perpendicular distance from wake centerline

        Args:
            upstream: Upstream turbine
            downstream: Downstream turbine
            wind_direction: Wind direction in degrees

        Returns:
            (downstream_distance, lateral_offset) in meters
        """
        # Vector from upstream to downstream
        dx = downstream.x - upstream.x
        dy = downstream.y - upstream.y

        # Wind direction vector (wind comes FROM this direction)
        # Convert to direction wind is going TO
        wind_to_rad = math.radians(wind_direction + 180)

        # Unit vector in wind direction
        wind_x = math.sin(wind_to_rad)
        wind_y = math.cos(wind_to_rad)

        # Project onto wind direction (downstream distance)
        downstream_distance = dx * wind_x + dy * wind_y

        # Perpendicular distance (lateral offset)
        lateral_offset = abs(dx * wind_y - dy * wind_x)

        return downstream_distance, lateral_offset

    def is_downstream(
        self,
        upstream: Turbine,
        downstream: Turbine,
        wind_direction: float,
    ) -> bool:
        """
        Check if downstream turbine is actually downstream of upstream.

        Args:
            upstream: Potential upstream turbine
            downstream: Potential downstream turbine
            wind_direction: Wind direction in degrees

        Returns:
            True if downstream is in the downwind direction
        """
        distance, _ = self.get_downstream_position(upstream, downstream, wind_direction)
        return distance > 0

    def calculate_overlap_fraction(
        self,
        downstream: Turbine,
        wake_radius: float,
        lateral_offset: float,
    ) -> float:
        """
        Calculate fraction of downstream rotor area affected by wake.

        Uses geometric overlap of two circles.

        Args:
            downstream: Downstream turbine
            wake_radius: Wake radius at downstream position
            lateral_offset: Lateral distance from wake centerline

        Returns:
            Overlap fraction (0-1)
        """
        rotor_radius = downstream.rotor_radius

        # No overlap if centers are too far apart
        if lateral_offset >= wake_radius + rotor_radius:
            return 0.0

        # Full overlap if wake fully contains rotor
        if lateral_offset + rotor_radius <= wake_radius:
            return 1.0

        # Full overlap if rotor fully contains wake (unusual but possible)
        if lateral_offset + wake_radius <= rotor_radius:
            wake_area = math.pi * wake_radius**2
            rotor_area = math.pi * rotor_radius**2
            return wake_area / rotor_area

        # Partial overlap - calculate intersection area
        # Using formula for intersection of two circles
        d = lateral_offset
        r1, r2 = wake_radius, rotor_radius

        # Check for valid triangle
        if d == 0:
            return min(1.0, (min(r1, r2) / max(r1, r2)) ** 2)

        part1 = r1**2 * math.acos((d**2 + r1**2 - r2**2) / (2 * d * r1))
        part2 = r2**2 * math.acos((d**2 + r2**2 - r1**2) / (2 * d * r2))
        part3 = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))

        intersection_area = part1 + part2 - part3
        rotor_area = math.pi * rotor_radius**2

        return min(1.0, intersection_area / rotor_area)

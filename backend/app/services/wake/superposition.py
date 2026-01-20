"""Wake superposition service."""

from __future__ import annotations

import math
from typing import Literal

from app.models.wake import WakeResult


class WakeSuperposition:
    """
    Service for combining multiple wake deficits.

    When a turbine is affected by multiple upstream wakes,
    the deficits must be combined using a superposition method.
    """

    def __init__(
        self,
        method: Literal["linear", "quadratic", "max"] = "quadratic",
    ) -> None:
        """
        Initialize wake superposition.

        Args:
            method: Superposition method
                - 'linear': Simple sum (overestimates deficit)
                - 'quadratic': Root sum of squares (most common)
                - 'max': Maximum deficit (underestimates)
        """
        self.method = method

    def combine_deficits(self, wake_results: list[WakeResult]) -> float:
        """
        Combine velocity deficits from multiple wakes.

        Args:
            wake_results: List of WakeResult objects affecting the same turbine

        Returns:
            Combined velocity deficit (0-1)
        """
        if not wake_results:
            return 0.0

        # Filter to only wakes that are actually affecting the turbine
        active_wakes = [w for w in wake_results if w.is_in_wake and w.velocity_deficit > 0]

        if not active_wakes:
            return 0.0

        deficits = [w.velocity_deficit for w in active_wakes]

        if self.method == "linear":
            combined = self._linear_superposition(deficits)
        elif self.method == "quadratic":
            combined = self._quadratic_superposition(deficits)
        elif self.method == "max":
            combined = self._max_superposition(deficits)
        else:
            raise ValueError(f"Unknown superposition method: {self.method}")

        # Bound to [0, 1] - deficit cannot exceed 100%
        return min(1.0, max(0.0, combined))

    def _linear_superposition(self, deficits: list[float]) -> float:
        """
        Linear superposition: Δu_total = Σ Δu_i

        Simple but tends to overestimate combined deficit.

        Args:
            deficits: List of individual velocity deficits

        Returns:
            Combined deficit
        """
        return sum(deficits)

    def _quadratic_superposition(self, deficits: list[float]) -> float:
        """
        Quadratic (RSS) superposition: Δu_total = √(Σ Δu_i²)

        Based on energy consideration - most physically reasonable.
        Standard approach in many wind farm codes (e.g., FLORIS).

        Args:
            deficits: List of individual velocity deficits

        Returns:
            Combined deficit
        """
        sum_squares = sum(d**2 for d in deficits)
        return math.sqrt(sum_squares)

    def _max_superposition(self, deficits: list[float]) -> float:
        """
        Maximum superposition: Δu_total = max(Δu_i)

        Takes only the largest deficit. Tends to underestimate
        combined effect but useful for conservative estimates.

        Args:
            deficits: List of individual velocity deficits

        Returns:
            Combined deficit
        """
        return max(deficits)

    def calculate_effective_speed(
        self,
        free_stream_speed: float,
        wake_results: list[WakeResult],
    ) -> float:
        """
        Calculate effective wind speed after wake effects.

        Args:
            free_stream_speed: Free-stream wind speed in m/s
            wake_results: List of wake effects

        Returns:
            Effective wind speed in m/s
        """
        combined_deficit = self.combine_deficits(wake_results)
        return free_stream_speed * (1 - combined_deficit)

    @staticmethod
    def get_upstream_turbines(wake_results: list[WakeResult]) -> list[str]:
        """
        Get list of upstream turbine IDs affecting a location.

        Args:
            wake_results: List of wake results

        Returns:
            List of upstream turbine IDs
        """
        return [
            str(w.upstream_turbine_id)
            for w in wake_results
            if w.is_in_wake and w.velocity_deficit > 0
        ]

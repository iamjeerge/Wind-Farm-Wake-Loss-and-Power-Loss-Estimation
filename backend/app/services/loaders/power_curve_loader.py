"""Power curve loader service."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy import interpolate

from app.models.turbine import PowerCurve, PowerCurvePoint

if TYPE_CHECKING:
    from pandas import DataFrame


class PowerCurveLoader:
    """Service for loading and interpolating turbine power curves."""

    def __init__(self) -> None:
        """Initialize power curve loader."""
        self._interpolators: dict[str, interpolate.interp1d] = {}

    def load_from_csv(self, file_path: str | Path) -> PowerCurve:
        """
        Load power curve from CSV file.

        Expected columns:
        - wind_speed: Wind speed in m/s
        - power: Power output in kW

        Optional columns:
        - cut_in_speed, rated_speed, cut_out_speed (or inferred from data)

        Args:
            file_path: Path to CSV file

        Returns:
            PowerCurve object
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Power curve file not found: {path}")

        df = pd.read_csv(path)
        return self.load_from_dataframe(df)

    def load_from_dataframe(self, df: "DataFrame") -> PowerCurve:
        """
        Load power curve from pandas DataFrame.

        Args:
            df: DataFrame with wind_speed and power columns

        Returns:
            PowerCurve object
        """
        df.columns = df.columns.str.lower().str.strip()

        if "wind_speed" not in df.columns:
            raise ValueError("Missing 'wind_speed' column")
        if "power" not in df.columns:
            raise ValueError("Missing 'power' column")

        # Sort by wind speed
        df = df.sort_values("wind_speed")

        # Create power curve points
        points = [
            PowerCurvePoint(
                wind_speed=float(row["wind_speed"]),
                power=float(row["power"]),
            )
            for _, row in df.iterrows()
        ]

        # Infer cut-in, rated, cut-out speeds
        cut_in_speed = self._find_cut_in_speed(df)
        rated_speed = self._find_rated_speed(df)
        cut_out_speed = self._find_cut_out_speed(df)

        return PowerCurve(
            points=points,
            cut_in_speed=cut_in_speed,
            rated_speed=rated_speed,
            cut_out_speed=cut_out_speed,
        )

    def _find_cut_in_speed(self, df: "DataFrame") -> float:
        """Find cut-in speed from power curve data."""
        # First speed with positive power
        positive_power = df[df["power"] > 0]
        if len(positive_power) > 0:
            return float(positive_power["wind_speed"].iloc[0])
        return 3.0  # Default

    def _find_rated_speed(self, df: "DataFrame") -> float:
        """Find rated speed from power curve data."""
        # Speed where power reaches maximum
        max_power = df["power"].max()
        rated_mask = df["power"] >= max_power * 0.99
        if rated_mask.any():
            return float(df.loc[rated_mask, "wind_speed"].iloc[0])
        return 12.0  # Default

    def _find_cut_out_speed(self, df: "DataFrame") -> float:
        """Find cut-out speed from power curve data."""
        # Last speed with power > 0, or highest speed in data
        max_speed = df["wind_speed"].max()
        if df["power"].iloc[-1] == 0:
            # Power drops to 0 at end
            positive_power = df[df["power"] > 0]
            if len(positive_power) > 0:
                return float(positive_power["wind_speed"].iloc[-1]) + 0.5
        return float(max_speed)

    def create_interpolator(
        self, power_curve: PowerCurve, turbine_id: str = "default"
    ) -> interpolate.interp1d:
        """
        Create cubic interpolation function for power curve.

        Args:
            power_curve: PowerCurve object
            turbine_id: Identifier for caching

        Returns:
            Interpolation function
        """
        speeds = np.array([p.wind_speed for p in power_curve.points])
        powers = np.array([p.power for p in power_curve.points])

        # Use cubic interpolation with bounds handling
        interp_func = interpolate.interp1d(
            speeds,
            powers,
            kind="cubic",
            bounds_error=False,
            fill_value=(0.0, 0.0),  # Zero power outside range
        )

        self._interpolators[turbine_id] = interp_func
        return interp_func

    def get_power(
        self,
        wind_speed: float,
        power_curve: PowerCurve,
        turbine_id: str = "default",
    ) -> float:
        """
        Get interpolated power for given wind speed.

        Respects cut-in, rated, and cut-out speeds.

        Args:
            wind_speed: Wind speed in m/s
            power_curve: PowerCurve object
            turbine_id: Turbine identifier for caching

        Returns:
            Power output in kW
        """
        # Check operating range
        if wind_speed < power_curve.cut_in_speed:
            return 0.0
        if wind_speed > power_curve.cut_out_speed:
            return 0.0

        # Get or create interpolator
        if turbine_id not in self._interpolators:
            self.create_interpolator(power_curve, turbine_id)

        interp = self._interpolators[turbine_id]
        power = float(interp(wind_speed))

        # Clamp to valid range
        return max(0.0, min(power, self._get_rated_power(power_curve)))

    def _get_rated_power(self, power_curve: PowerCurve) -> float:
        """Get rated power from power curve."""
        return max(p.power for p in power_curve.points)

    @staticmethod
    def create_generic_power_curve(
        rated_power: float,
        cut_in_speed: float = 3.0,
        rated_speed: float = 12.0,
        cut_out_speed: float = 25.0,
    ) -> PowerCurve:
        """
        Create a generic power curve based on typical characteristics.

        Uses cubic relationship below rated speed.

        Args:
            rated_power: Rated power in kW
            cut_in_speed: Cut-in wind speed in m/s
            rated_speed: Rated wind speed in m/s
            cut_out_speed: Cut-out wind speed in m/s

        Returns:
            PowerCurve object
        """
        points = []

        # Below cut-in: zero power
        points.append(PowerCurvePoint(wind_speed=0.0, power=0.0))
        points.append(PowerCurvePoint(wind_speed=cut_in_speed - 0.1, power=0.0))

        # Cubic region: cut-in to rated
        n_points = 10
        for i in range(n_points):
            speed = cut_in_speed + (rated_speed - cut_in_speed) * i / (n_points - 1)
            # Cubic relationship: P ∝ v³
            normalized_speed = (speed - cut_in_speed) / (rated_speed - cut_in_speed)
            power = rated_power * normalized_speed**3
            points.append(PowerCurvePoint(wind_speed=speed, power=power))

        # Rated region: constant power
        points.append(PowerCurvePoint(wind_speed=rated_speed + 0.1, power=rated_power))
        points.append(PowerCurvePoint(wind_speed=cut_out_speed - 0.5, power=rated_power))

        # Cut-out
        points.append(PowerCurvePoint(wind_speed=cut_out_speed, power=rated_power * 0.5))
        points.append(PowerCurvePoint(wind_speed=cut_out_speed + 0.5, power=0.0))

        return PowerCurve(
            points=points,
            cut_in_speed=cut_in_speed,
            rated_speed=rated_speed,
            cut_out_speed=cut_out_speed,
        )

    @staticmethod
    def calculate_thrust_coefficient(
        wind_speed: float,
        rated_speed: float = 12.0,
        ct_rated: float = 0.8,
    ) -> float:
        """
        Estimate thrust coefficient based on wind speed.

        Uses simplified model where Ct decreases above rated speed.

        Args:
            wind_speed: Wind speed in m/s
            rated_speed: Rated wind speed
            ct_rated: Ct at rated speed

        Returns:
            Thrust coefficient (0-1)
        """
        if wind_speed <= rated_speed:
            return ct_rated
        else:
            # Ct decreases proportional to 1/v² above rated
            return ct_rated * (rated_speed / wind_speed) ** 2

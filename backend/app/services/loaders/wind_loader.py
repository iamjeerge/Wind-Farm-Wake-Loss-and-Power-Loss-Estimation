"""Wind data loader service."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from app.models.wind import WeibullParameters, WindData, WindRose, WindRoseEntry

if TYPE_CHECKING:
    from pandas import DataFrame


class WindLoader:
    """Service for loading and processing wind data."""

    def __init__(self) -> None:
        """Initialize wind loader."""
        pass

    def load_wind_rose_from_csv(self, file_path: str | Path) -> WindRose:
        """
        Load wind rose from CSV file.

        Expected columns:
        - direction: Direction in degrees (0-360)
        - probability: Probability (0-1) or frequency

        Args:
            file_path: Path to CSV file

        Returns:
            WindRose object
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Wind rose file not found: {path}")

        df = pd.read_csv(path)
        return self.load_wind_rose_from_dataframe(df)

    def load_wind_rose_from_dataframe(self, df: "DataFrame") -> WindRose:
        """
        Load wind rose from pandas DataFrame.

        Args:
            df: DataFrame with direction and probability columns

        Returns:
            WindRose object
        """
        df.columns = df.columns.str.lower().str.strip()

        if "direction" not in df.columns:
            raise ValueError("Missing 'direction' column")

        if "probability" not in df.columns and "frequency" not in df.columns:
            raise ValueError("Missing 'probability' or 'frequency' column")

        prob_col = "probability" if "probability" in df.columns else "frequency"

        # Normalize probabilities to sum to 1
        total = df[prob_col].sum()
        if total <= 0:
            raise ValueError("Probabilities must be positive")

        entries = []
        for _, row in df.iterrows():
            entries.append(
                WindRoseEntry(
                    direction=float(row["direction"]),
                    probability=float(row[prob_col]) / total,
                )
            )

        # Sort by direction
        entries.sort(key=lambda e: e.direction)

        # Calculate sector width
        if len(entries) > 1:
            sector_width = 360.0 / len(entries)
            for entry in entries:
                entry.sector_width = sector_width

        return WindRose(entries=entries)

    def load_weibull_from_csv(self, file_path: str | Path) -> WeibullParameters:
        """
        Load Weibull parameters from CSV.

        Expected columns:
        - shape (or k): Shape parameter
        - scale (or A or lambda): Scale parameter

        Args:
            file_path: Path to CSV file

        Returns:
            WeibullParameters object
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Weibull file not found: {path}")

        df = pd.read_csv(path)
        return self.load_weibull_from_dataframe(df)

    def load_weibull_from_dataframe(self, df: "DataFrame") -> WeibullParameters:
        """
        Load Weibull parameters from DataFrame.

        Args:
            df: DataFrame with shape and scale columns

        Returns:
            WeibullParameters object
        """
        df.columns = df.columns.str.lower().str.strip()

        # Find shape column
        shape_cols = ["shape", "k"]
        shape_col = next((c for c in shape_cols if c in df.columns), None)
        if shape_col is None:
            raise ValueError("Missing 'shape' or 'k' column")

        # Find scale column
        scale_cols = ["scale", "a", "lambda"]
        scale_col = next((c for c in scale_cols if c in df.columns), None)
        if scale_col is None:
            raise ValueError("Missing 'scale', 'A', or 'lambda' column")

        # Use first row (or can be extended for directional)
        return WeibullParameters(
            shape=float(df[shape_col].iloc[0]),
            scale=float(df[scale_col].iloc[0]),
        )

    def load_directional_weibull(self, file_path: str | Path) -> dict[float, WeibullParameters]:
        """
        Load direction-specific Weibull parameters.

        Expected columns:
        - direction: Direction in degrees
        - shape (or k): Shape parameter
        - scale (or A): Scale parameter

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary mapping direction to Weibull parameters
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Directional Weibull file not found: {path}")

        df = pd.read_csv(path)
        df.columns = df.columns.str.lower().str.strip()

        if "direction" not in df.columns:
            raise ValueError("Missing 'direction' column")

        # Find parameter columns
        shape_col = next((c for c in ["shape", "k"] if c in df.columns), None)
        scale_col = next((c for c in ["scale", "a", "lambda"] if c in df.columns), None)

        if shape_col is None or scale_col is None:
            raise ValueError("Missing shape or scale columns")

        result = {}
        for _, row in df.iterrows():
            direction = float(row["direction"])
            result[direction] = WeibullParameters(
                shape=float(row[shape_col]),
                scale=float(row[scale_col]),
                direction=direction,
            )

        return result

    def load_complete_wind_data(
        self,
        wind_rose_path: str | Path,
        weibull_path: str | Path,
        directional_weibull_path: str | Path | None = None,
    ) -> WindData:
        """
        Load complete wind data from multiple files.

        Args:
            wind_rose_path: Path to wind rose CSV
            weibull_path: Path to Weibull parameters CSV
            directional_weibull_path: Optional path to directional Weibull CSV

        Returns:
            Complete WindData object
        """
        wind_rose = self.load_wind_rose_from_csv(wind_rose_path)
        weibull = self.load_weibull_from_csv(weibull_path)

        directional_weibull = None
        if directional_weibull_path:
            directional_weibull = self.load_directional_weibull(directional_weibull_path)

        return WindData(
            wind_rose=wind_rose,
            weibull=weibull,
            directional_weibull=directional_weibull,
        )

    @staticmethod
    def create_uniform_wind_rose(n_sectors: int = 36) -> WindRose:
        """
        Create a uniform wind rose (equal probability all directions).

        Args:
            n_sectors: Number of direction sectors

        Returns:
            Uniform WindRose
        """
        sector_width = 360.0 / n_sectors
        probability = 1.0 / n_sectors

        entries = [
            WindRoseEntry(
                direction=i * sector_width,
                probability=probability,
                sector_width=sector_width,
            )
            for i in range(n_sectors)
        ]

        return WindRose(entries=entries)

    @staticmethod
    def fit_weibull_from_speeds(speeds: list[float] | np.ndarray) -> WeibullParameters:
        """
        Fit Weibull parameters to observed wind speeds.

        Uses maximum likelihood estimation.

        Args:
            speeds: Array of wind speed observations

        Returns:
            Fitted WeibullParameters
        """
        from scipy import stats

        speeds_arr = np.array(speeds)
        speeds_arr = speeds_arr[speeds_arr > 0]  # Filter zero/negative

        if len(speeds_arr) < 10:
            raise ValueError("Need at least 10 speed observations")

        # Fit Weibull distribution
        shape, loc, scale = stats.weibull_min.fit(speeds_arr, floc=0)

        return WeibullParameters(shape=shape, scale=scale)

    @staticmethod
    def generate_speed_bins(
        weibull: WeibullParameters,
        n_bins: int = 25,
        min_speed: float = 0.0,
        max_speed: float = 30.0,
    ) -> list[tuple[float, float]]:
        """
        Generate wind speed bins with their probabilities.

        Args:
            weibull: Weibull parameters
            n_bins: Number of bins
            min_speed: Minimum speed
            max_speed: Maximum speed

        Returns:
            List of (speed, probability) tuples
        """
        bin_edges = np.linspace(min_speed, max_speed, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        result = []
        for i, center in enumerate(bin_centers):
            prob = weibull.cdf(bin_edges[i + 1]) - weibull.cdf(bin_edges[i])
            if prob > 0:
                result.append((center, prob))

        return result

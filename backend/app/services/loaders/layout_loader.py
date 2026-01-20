"""Turbine layout loader service."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from pyproj import Transformer

from app.models.turbine import Turbine, TurbineCreate, TurbineLayout

if TYPE_CHECKING:
    from pandas import DataFrame


class LayoutLoader:
    """Service for loading and processing turbine layout data."""

    # Expected CSV columns
    REQUIRED_COLUMNS = {"name", "latitude", "longitude", "hub_height", "rotor_diameter", "rated_power"}
    OPTIONAL_COLUMNS = {"thrust_coefficient"}

    def __init__(self) -> None:
        """Initialize layout loader."""
        self._transformer: Transformer | None = None
        self._reference_lat: float | None = None
        self._reference_lon: float | None = None

    def load_from_csv(self, file_path: str | Path) -> TurbineLayout:
        """
        Load turbine layout from CSV file.

        Expected columns:
        - name: Turbine identifier
        - latitude: Latitude in degrees
        - longitude: Longitude in degrees
        - hub_height: Hub height in meters
        - rotor_diameter: Rotor diameter in meters
        - rated_power: Rated power in kW
        - thrust_coefficient (optional): Ct value

        Args:
            file_path: Path to CSV file

        Returns:
            TurbineLayout with normalized coordinates
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Layout file not found: {path}")

        df = pd.read_csv(path)
        return self.load_from_dataframe(df, name=path.stem)

    def load_from_dataframe(self, df: "DataFrame", name: str = "Wind Farm") -> TurbineLayout:
        """
        Load turbine layout from pandas DataFrame.

        Args:
            df: DataFrame with turbine data
            name: Layout name

        Returns:
            TurbineLayout with normalized coordinates
        """
        # Validate columns
        df.columns = df.columns.str.lower().str.strip()
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Create turbines
        turbines: list[Turbine] = []
        for _, row in df.iterrows():
            turbine_data = TurbineCreate(
                name=str(row["name"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                hub_height=float(row["hub_height"]),
                rotor_diameter=float(row["rotor_diameter"]),
                rated_power=float(row["rated_power"]),
            )
            turbine = Turbine(**turbine_data.model_dump())

            # Optional thrust coefficient
            if "thrust_coefficient" in df.columns and pd.notna(row.get("thrust_coefficient")):
                turbine.thrust_coefficient = float(row["thrust_coefficient"])

            turbines.append(turbine)

        # Calculate reference point (centroid)
        ref_lat = sum(t.latitude for t in turbines) / len(turbines)
        ref_lon = sum(t.longitude for t in turbines) / len(turbines)

        # Transform to local Cartesian coordinates
        self._setup_transformer(ref_lat, ref_lon)
        turbines = self._transform_coordinates(turbines)

        return TurbineLayout(
            turbines=turbines,
            name=name,
            reference_latitude=ref_lat,
            reference_longitude=ref_lon,
        )

    def _setup_transformer(self, ref_lat: float, ref_lon: float) -> None:
        """
        Set up coordinate transformer for local Cartesian projection.

        Uses a local Transverse Mercator projection centered on the reference point.

        Args:
            ref_lat: Reference latitude
            ref_lon: Reference longitude
        """
        self._reference_lat = ref_lat
        self._reference_lon = ref_lon

        # Create local Transverse Mercator projection
        proj_string = (
            f"+proj=tmerc +lat_0={ref_lat} +lon_0={ref_lon} "
            f"+k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
        )
        self._transformer = Transformer.from_crs("EPSG:4326", proj_string, always_xy=True)

    def _transform_coordinates(self, turbines: list[Turbine]) -> list[Turbine]:
        """
        Transform turbine coordinates to local Cartesian system.

        Args:
            turbines: List of turbines with lat/lon coordinates

        Returns:
            Same turbines with x/y coordinates filled in
        """
        if self._transformer is None:
            raise RuntimeError("Transformer not initialized")

        for turbine in turbines:
            x, y = self._transformer.transform(turbine.longitude, turbine.latitude)
            turbine.x = x
            turbine.y = y

        return turbines

    @staticmethod
    def calculate_distances(layout: TurbineLayout) -> dict[tuple[str, str], float]:
        """
        Calculate distances between all turbine pairs.

        Args:
            layout: Turbine layout

        Returns:
            Dictionary mapping (turbine1_name, turbine2_name) to distance in meters
        """
        distances: dict[tuple[str, str], float] = {}

        for i, t1 in enumerate(layout.turbines):
            for t2 in layout.turbines[i + 1 :]:
                dist = math.sqrt((t2.x - t1.x) ** 2 + (t2.y - t1.y) ** 2)
                distances[(t1.name, t2.name)] = dist
                distances[(t2.name, t1.name)] = dist

        return distances

    @staticmethod
    def get_turbine_positions(layout: TurbineLayout) -> list[tuple[str, float, float]]:
        """
        Get list of turbine positions.

        Args:
            layout: Turbine layout

        Returns:
            List of (name, x, y) tuples
        """
        return [(t.name, t.x, t.y) for t in layout.turbines]

    @staticmethod
    def validate_layout(layout: TurbineLayout) -> list[str]:
        """
        Validate layout for potential issues.

        Args:
            layout: Turbine layout to validate

        Returns:
            List of warning messages
        """
        warnings: list[str] = []

        # Check for duplicate positions
        positions = set()
        for turbine in layout.turbines:
            pos = (round(turbine.x, 1), round(turbine.y, 1))
            if pos in positions:
                warnings.append(f"Turbine {turbine.name} has duplicate position")
            positions.add(pos)

        # Check for turbines too close together
        for i, t1 in enumerate(layout.turbines):
            for t2 in layout.turbines[i + 1 :]:
                dist = math.sqrt((t2.x - t1.x) ** 2 + (t2.y - t1.y) ** 2)
                min_dist = max(t1.rotor_diameter, t2.rotor_diameter) * 2
                if dist < min_dist:
                    warnings.append(
                        f"Turbines {t1.name} and {t2.name} are only {dist:.0f}m apart "
                        f"(recommended minimum: {min_dist:.0f}m)"
                    )

        # Check for inconsistent turbine specs
        hub_heights = set(t.hub_height for t in layout.turbines)
        if len(hub_heights) > 3:
            warnings.append(f"Layout has {len(hub_heights)} different hub heights")

        rotor_diameters = set(t.rotor_diameter for t in layout.turbines)
        if len(rotor_diameters) > 3:
            warnings.append(f"Layout has {len(rotor_diameters)} different rotor diameters")

        return warnings

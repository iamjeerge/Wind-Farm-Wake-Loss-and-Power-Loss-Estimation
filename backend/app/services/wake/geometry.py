"""Wake geometry generator for visualization."""

from __future__ import annotations

import math

from app.models.turbine import Turbine, TurbineLayout
from app.models.wake import WakeGeometry, WakeParameters
from app.services.wake.base import BaseWakeModel
from app.services.wake.jensen import JensenWakeModel
from app.services.wake.bastankhah import BastankhahWakeModel


class WakeGeometryGenerator:
    """Service for generating wake geometries for visualization."""

    def __init__(
        self,
        wake_model: BaseWakeModel | None = None,
        params: WakeParameters | None = None,
    ) -> None:
        """
        Initialize geometry generator.

        Args:
            wake_model: Wake model to use (defaults to Jensen)
            params: Wake parameters
        """
        self.params = params or WakeParameters()
        self.wake_model = wake_model or JensenWakeModel(self.params)

    def generate_wake_cone(
        self,
        turbine: Turbine,
        wind_direction: float,
        length: float = 2000.0,
        n_points: int = 50,
    ) -> WakeGeometry:
        """
        Generate wake cone geometry for a turbine.

        Args:
            turbine: Turbine producing the wake
            wind_direction: Wind direction in degrees
            length: Wake length to generate in meters
            n_points: Number of points for polygon

        Returns:
            WakeGeometry object
        """
        # Wind direction vector (wake extends opposite to wind direction)
        wake_dir_rad = math.radians(wind_direction + 180)  # Direction wake goes
        wake_dx = math.sin(wake_dir_rad)
        wake_dy = math.cos(wake_dir_rad)

        # Perpendicular vector for width
        perp_dx = math.cos(wake_dir_rad)
        perp_dy = -math.sin(wake_dir_rad)

        # Initial and final wake radii
        initial_radius = turbine.rotor_radius
        final_radius = self.wake_model.calculate_wake_radius(turbine, length)

        # Calculate expansion angle
        if length > 0:
            expansion_angle = math.degrees(math.atan((final_radius - initial_radius) / length))
        else:
            expansion_angle = 0.0

        # Generate polygon vertices
        vertices: list[tuple[float, float]] = []

        # Start at turbine position with initial radius (left side)
        vertices.append(
            (
                turbine.x + perp_dx * initial_radius,
                turbine.y + perp_dy * initial_radius,
            )
        )

        # Points along left edge of wake
        for i in range(1, n_points):
            dist = length * i / (n_points - 1)
            radius = self.wake_model.calculate_wake_radius(turbine, dist)
            x = turbine.x + wake_dx * dist + perp_dx * radius
            y = turbine.y + wake_dy * dist + perp_dy * radius
            vertices.append((x, y))

        # Points along right edge (reverse direction)
        for i in range(n_points - 1, -1, -1):
            dist = length * i / (n_points - 1)
            radius = self.wake_model.calculate_wake_radius(turbine, dist)
            x = turbine.x + wake_dx * dist - perp_dx * radius
            y = turbine.y + wake_dy * dist - perp_dy * radius
            vertices.append((x, y))

        # Generate centerline deficit profile
        centerline_deficit: list[tuple[float, float]] = []
        for i in range(n_points):
            dist = length * i / (n_points - 1)
            if isinstance(self.wake_model, JensenWakeModel):
                deficit = self.wake_model.get_deficit_at_distance(turbine, dist)
            elif isinstance(self.wake_model, BastankhahWakeModel):
                deficit = self.wake_model.get_deficit_at_distance(turbine, dist, 0.0)
            else:
                deficit = 0.0
            centerline_deficit.append((dist, deficit))

        return WakeGeometry(
            turbine_id=turbine.id,
            wind_direction=wind_direction,
            origin_x=turbine.x,
            origin_y=turbine.y,
            length=length,
            initial_radius=initial_radius,
            final_radius=final_radius,
            expansion_angle=expansion_angle,
            centerline_deficit=centerline_deficit,
            polygon_vertices=vertices,
        )

    def generate_all_wakes(
        self,
        layout: TurbineLayout,
        wind_direction: float,
        length: float = 2000.0,
    ) -> list[WakeGeometry]:
        """
        Generate wake geometries for all turbines in layout.

        Args:
            layout: Turbine layout
            wind_direction: Wind direction in degrees
            length: Wake length in meters

        Returns:
            List of WakeGeometry objects
        """
        geometries = []
        for turbine in layout.turbines:
            geom = self.generate_wake_cone(turbine, wind_direction, length)
            geometries.append(geom)
        return geometries

    def generate_heatmap_grid(
        self,
        layout: TurbineLayout,
        wind_direction: float,
        wind_speed: float,
        grid_size: int = 100,
        padding: float = 500.0,
    ) -> dict[str, list[list[float]]]:
        """
        Generate velocity deficit heatmap grid.

        Args:
            layout: Turbine layout
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s
            grid_size: Grid resolution (grid_size x grid_size)
            padding: Padding around turbines in meters

        Returns:
            Dictionary with 'x', 'y', 'deficit' arrays
        """
        # Calculate grid bounds
        x_coords = [t.x for t in layout.turbines]
        y_coords = [t.y for t in layout.turbines]

        x_min, x_max = min(x_coords) - padding, max(x_coords) + padding
        y_min, y_max = min(y_coords) - padding, max(y_coords) + padding

        # Add extra space in wake direction
        wake_dir_rad = math.radians(wind_direction + 180)
        x_max += 1500 * math.sin(wake_dir_rad)
        y_max += 1500 * math.cos(wake_dir_rad)

        # Create grid
        x_vals = [x_min + (x_max - x_min) * i / (grid_size - 1) for i in range(grid_size)]
        y_vals = [y_min + (y_max - y_min) * i / (grid_size - 1) for i in range(grid_size)]

        # Calculate deficit at each grid point
        deficit_grid: list[list[float]] = []

        for y in y_vals:
            row: list[float] = []
            for x in x_vals:
                # Sum deficits from all turbines
                total_deficit_sq = 0.0

                for turbine in layout.turbines:
                    # Calculate position relative to turbine
                    dx = x - turbine.x
                    dy = y - turbine.y

                    # Project onto wind direction
                    wake_dx = math.sin(math.radians(wind_direction + 180))
                    wake_dy = math.cos(math.radians(wind_direction + 180))

                    downstream_dist = dx * wake_dx + dy * wake_dy
                    lateral_offset = abs(dx * wake_dy - dy * wake_dx)

                    if downstream_dist > 0:
                        if isinstance(self.wake_model, BastankhahWakeModel):
                            deficit = self.wake_model.get_deficit_at_distance(
                                turbine, downstream_dist, lateral_offset
                            )
                        else:
                            # Jensen with Gaussian profile
                            wake_radius = self.wake_model.calculate_wake_radius(
                                turbine, downstream_dist
                            )
                            if lateral_offset < wake_radius:
                                centerline_deficit = self.wake_model.get_deficit_at_distance(
                                    turbine, downstream_dist
                                )
                                sigma = wake_radius / 2
                                deficit = centerline_deficit * math.exp(
                                    -((lateral_offset / sigma) ** 2)
                                )
                            else:
                                deficit = 0.0

                        total_deficit_sq += deficit**2

                # Quadratic superposition
                combined_deficit = math.sqrt(total_deficit_sq)
                row.append(min(1.0, combined_deficit))

            deficit_grid.append(row)

        return {
            "x": x_vals,
            "y": y_vals,
            "deficit": deficit_grid,
        }

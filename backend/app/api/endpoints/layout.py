"""Layout API endpoints."""

from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
import pandas as pd

from app.models.turbine import TurbineLayout
from app.services.loaders.layout_loader import LayoutLoader

router = APIRouter()


@router.post("/upload", response_model=TurbineLayout)
async def upload_layout(file: UploadFile = File(...)) -> TurbineLayout:
    """
    Upload turbine layout from CSV file.

    Expected columns:
    - name: Turbine identifier
    - latitude: Latitude in degrees
    - longitude: Longitude in degrees
    - hub_height: Hub height in meters
    - rotor_diameter: Rotor diameter in meters
    - rated_power: Rated power in kW
    - thrust_coefficient (optional): Ct value
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        loader = LayoutLoader()
        layout = loader.load_from_dataframe(df, name=file.filename.replace(".csv", ""))

        return layout

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")


@router.post("/validate")
async def validate_layout(layout: TurbineLayout) -> dict[str, Any]:
    """
    Validate a turbine layout and return warnings.

    Checks for:
    - Duplicate positions
    - Turbines too close together
    - Inconsistent specifications
    """
    warnings = LayoutLoader.validate_layout(layout)

    return {
        "valid": len(warnings) == 0,
        "turbine_count": layout.turbine_count,
        "total_rated_power_kw": layout.total_rated_power,
        "warnings": warnings,
    }


@router.post("/distances")
async def calculate_distances(layout: TurbineLayout) -> dict[str, Any]:
    """Calculate distances between all turbine pairs."""
    distances = LayoutLoader.calculate_distances(layout)

    # Convert to serializable format
    distance_list = [
        {"from": pair[0], "to": pair[1], "distance_m": dist} for pair, dist in distances.items()
    ]

    # Calculate statistics
    dist_values = list(set(distances.values()))  # Unique distances
    min_dist = min(dist_values) if dist_values else 0
    max_dist = max(dist_values) if dist_values else 0
    avg_dist = sum(dist_values) / len(dist_values) if dist_values else 0

    return {
        "distances": distance_list,
        "statistics": {
            "min_distance_m": min_dist,
            "max_distance_m": max_dist,
            "avg_distance_m": avg_dist,
            "total_pairs": len(distances) // 2,  # Each pair counted twice
        },
    }


@router.post("/positions")
async def get_positions(layout: TurbineLayout) -> list[dict[str, Any]]:
    """Get turbine positions in local Cartesian coordinates."""
    return [
        {
            "name": t.name,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "x": t.x,
            "y": t.y,
            "hub_height": t.hub_height,
            "rotor_diameter": t.rotor_diameter,
        }
        for t in layout.turbines
    ]


@router.get("/sample")
async def get_sample_layout() -> TurbineLayout:
    """
    Get a sample wind farm layout for testing.

    Returns a simple 3x3 grid of turbines.
    """
    from app.models.turbine import Turbine

    turbines = []
    spacing = 500  # meters

    for i in range(3):
        for j in range(3):
            turbines.append(
                Turbine(
                    name=f"T{i*3 + j + 1}",
                    latitude=55.0 + i * 0.005,
                    longitude=8.0 + j * 0.008,
                    hub_height=90.0,
                    rotor_diameter=126.0,
                    rated_power=3600.0,
                    x=j * spacing,
                    y=i * spacing,
                )
            )

    return TurbineLayout(
        turbines=turbines,
        name="Sample 3x3 Grid",
        reference_latitude=55.005,
        reference_longitude=8.008,
    )

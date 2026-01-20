"""Wind data API endpoints."""

from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
import pandas as pd

from app.models.wind import WeibullParameters, WindData, WindRose
from app.services.loaders.wind_loader import WindLoader

router = APIRouter()


@router.post("/rose/upload", response_model=WindRose)
async def upload_wind_rose(file: UploadFile = File(...)) -> WindRose:
    """
    Upload wind rose from CSV file.

    Expected columns:
    - direction: Direction in degrees (0-360)
    - probability (or frequency): Probability or frequency values
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        loader = WindLoader()
        wind_rose = loader.load_wind_rose_from_dataframe(df)

        return wind_rose

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")


@router.post("/weibull/upload", response_model=WeibullParameters)
async def upload_weibull(file: UploadFile = File(...)) -> WeibullParameters:
    """
    Upload Weibull parameters from CSV file.

    Expected columns:
    - shape (or k): Shape parameter
    - scale (or A or lambda): Scale parameter in m/s
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        loader = WindLoader()
        weibull = loader.load_weibull_from_dataframe(df)

        return weibull

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")


@router.post("/weibull/fit", response_model=WeibullParameters)
async def fit_weibull(speeds: list[float]) -> WeibullParameters:
    """
    Fit Weibull parameters to observed wind speed data.

    Provide a list of wind speed observations.
    """
    if len(speeds) < 10:
        raise HTTPException(
            status_code=400, detail="Need at least 10 speed observations"
        )

    try:
        weibull = WindLoader.fit_weibull_from_speeds(speeds)
        return weibull
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rose/uniform", response_model=WindRose)
async def get_uniform_wind_rose(sectors: int = 36) -> WindRose:
    """
    Generate a uniform wind rose (equal probability all directions).

    Args:
        sectors: Number of direction sectors (default: 36 = 10° steps)
    """
    if sectors < 4 or sectors > 72:
        raise HTTPException(
            status_code=400, detail="Sectors must be between 4 and 72"
        )

    return WindLoader.create_uniform_wind_rose(sectors)


@router.post("/speed-bins")
async def generate_speed_bins(
    weibull: WeibullParameters,
    n_bins: int = 25,
    min_speed: float = 0.0,
    max_speed: float = 30.0,
) -> list[dict[str, float]]:
    """Generate wind speed bins with their probabilities."""
    bins = WindLoader.generate_speed_bins(weibull, n_bins, min_speed, max_speed)

    return [{"speed_ms": speed, "probability": prob} for speed, prob in bins]


@router.get("/sample")
async def get_sample_wind_data() -> WindData:
    """
    Get sample wind data for testing.

    Returns typical North Sea offshore wind conditions.
    """
    from app.models.wind import WindRoseEntry

    # Typical North Sea wind rose (prevailing westerly winds)
    entries = [
        WindRoseEntry(direction=0, probability=0.05),    # N
        WindRoseEntry(direction=30, probability=0.04),   # NNE
        WindRoseEntry(direction=60, probability=0.03),   # ENE
        WindRoseEntry(direction=90, probability=0.04),   # E
        WindRoseEntry(direction=120, probability=0.05),  # ESE
        WindRoseEntry(direction=150, probability=0.06),  # SSE
        WindRoseEntry(direction=180, probability=0.08),  # S
        WindRoseEntry(direction=210, probability=0.12),  # SSW
        WindRoseEntry(direction=240, probability=0.18),  # WSW
        WindRoseEntry(direction=270, probability=0.15),  # W
        WindRoseEntry(direction=300, probability=0.12),  # WNW
        WindRoseEntry(direction=330, probability=0.08),  # NNW
    ]

    wind_rose = WindRose(entries=entries, name="North Sea Sample")

    # Typical offshore Weibull parameters
    weibull = WeibullParameters(shape=2.1, scale=9.5)

    return WindData(wind_rose=wind_rose, weibull=weibull)


@router.post("/statistics")
async def calculate_wind_statistics(wind_data: WindData) -> dict[str, Any]:
    """Calculate wind statistics from wind data."""
    weibull = wind_data.weibull

    # Wind speed statistics
    mean_speed = weibull.mean_speed

    # Probability at different speeds
    prob_above_3 = 1 - weibull.cdf(3.0)  # Above cut-in
    prob_above_12 = 1 - weibull.cdf(12.0)  # Above rated
    prob_below_25 = weibull.cdf(25.0)  # Below cut-out

    # Direction statistics
    dominant_direction = max(
        wind_data.wind_rose.entries, key=lambda e: e.probability
    )

    return {
        "weibull": {
            "shape": weibull.shape,
            "scale": weibull.scale,
            "mean_speed_ms": mean_speed,
        },
        "probabilities": {
            "above_cut_in_3ms": prob_above_3,
            "above_rated_12ms": prob_above_12,
            "below_cut_out_25ms": prob_below_25,
        },
        "direction": {
            "dominant_direction_deg": dominant_direction.direction,
            "dominant_probability": dominant_direction.probability,
            "n_sectors": len(wind_data.wind_rose.entries),
        },
    }

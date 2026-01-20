"""Database fixtures and seed data."""

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, init_db
from app.db.models import WindFarm, Turbine, WindRose, PowerCurve


# Sample North Sea wind farm layout (4x5 grid)
SAMPLE_WIND_FARM = {
    "name": "North Sea Demo Farm",
    "description": "Sample 20-turbine offshore wind farm in the North Sea",
    "center_latitude": 55.5,
    "center_longitude": 3.5,
    "total_capacity_mw": 72.0,
    "turbine_count": 20,
}

# Turbine positions (4x5 grid, 7D spacing = 882m)
SAMPLE_TURBINES = []
SPACING = 882  # 7 rotor diameters (126m * 7)
for row in range(4):
    for col in range(5):
        idx = row * 5 + col + 1
        SAMPLE_TURBINES.append({
            "turbine_id": f"T{idx:02d}",
            "name": f"Turbine {idx}",
            "latitude": 55.5 + (row - 1.5) * 0.008,
            "longitude": 3.5 + (col - 2) * 0.012,
            "x": (col - 2) * SPACING,
            "y": (row - 1.5) * SPACING,
            "hub_height": 90.0,
            "rotor_diameter": 126.0,
            "rated_power_kw": 3600.0,
            "thrust_coefficient": 0.8,
        })

# Prevailing SW wind rose (North Sea typical)
SAMPLE_WIND_ROSE = {
    "name": "North Sea Typical",
    "description": "Typical North Sea wind rose with prevailing SW winds",
    "weibull_shape": 2.1,
    "weibull_scale": 9.5,
    "entries": [
        {"direction": 0, "probability": 0.04, "sector_width": 15},
        {"direction": 15, "probability": 0.03, "sector_width": 15},
        {"direction": 30, "probability": 0.03, "sector_width": 15},
        {"direction": 45, "probability": 0.02, "sector_width": 15},
        {"direction": 60, "probability": 0.02, "sector_width": 15},
        {"direction": 75, "probability": 0.02, "sector_width": 15},
        {"direction": 90, "probability": 0.03, "sector_width": 15},
        {"direction": 105, "probability": 0.03, "sector_width": 15},
        {"direction": 120, "probability": 0.03, "sector_width": 15},
        {"direction": 135, "probability": 0.04, "sector_width": 15},
        {"direction": 150, "probability": 0.04, "sector_width": 15},
        {"direction": 165, "probability": 0.04, "sector_width": 15},
        {"direction": 180, "probability": 0.05, "sector_width": 15},
        {"direction": 195, "probability": 0.06, "sector_width": 15},
        {"direction": 210, "probability": 0.08, "sector_width": 15},
        {"direction": 225, "probability": 0.10, "sector_width": 15},
        {"direction": 240, "probability": 0.10, "sector_width": 15},
        {"direction": 255, "probability": 0.08, "sector_width": 15},
        {"direction": 270, "probability": 0.06, "sector_width": 15},
        {"direction": 285, "probability": 0.04, "sector_width": 15},
        {"direction": 300, "probability": 0.03, "sector_width": 15},
        {"direction": 315, "probability": 0.03, "sector_width": 15},
        {"direction": 330, "probability": 0.03, "sector_width": 15},
        {"direction": 345, "probability": 0.04, "sector_width": 15},
    ],
}

# 3.6 MW power curve
SAMPLE_POWER_CURVE = {
    "name": "Generic 3.6 MW",
    "manufacturer": "Generic",
    "model": "3.6-126",
    "rated_power_kw": 3600.0,
    "rotor_diameter": 126.0,
    "cut_in_speed": 3.0,
    "rated_speed": 12.0,
    "cut_out_speed": 25.0,
    "curve_data": [
        {"wind_speed": 0, "power_kw": 0},
        {"wind_speed": 1, "power_kw": 0},
        {"wind_speed": 2, "power_kw": 0},
        {"wind_speed": 3, "power_kw": 0},
        {"wind_speed": 4, "power_kw": 150},
        {"wind_speed": 5, "power_kw": 350},
        {"wind_speed": 6, "power_kw": 600},
        {"wind_speed": 7, "power_kw": 950},
        {"wind_speed": 8, "power_kw": 1400},
        {"wind_speed": 9, "power_kw": 1950},
        {"wind_speed": 10, "power_kw": 2550},
        {"wind_speed": 11, "power_kw": 3150},
        {"wind_speed": 12, "power_kw": 3600},
        {"wind_speed": 13, "power_kw": 3600},
        {"wind_speed": 14, "power_kw": 3600},
        {"wind_speed": 15, "power_kw": 3600},
        {"wind_speed": 16, "power_kw": 3600},
        {"wind_speed": 17, "power_kw": 3600},
        {"wind_speed": 18, "power_kw": 3600},
        {"wind_speed": 19, "power_kw": 3600},
        {"wind_speed": 20, "power_kw": 3600},
        {"wind_speed": 21, "power_kw": 3600},
        {"wind_speed": 22, "power_kw": 3600},
        {"wind_speed": 23, "power_kw": 3600},
        {"wind_speed": 24, "power_kw": 3600},
        {"wind_speed": 25, "power_kw": 3600},
        {"wind_speed": 26, "power_kw": 0},
    ],
}

# Second sample: Onshore farm
ONSHORE_WIND_FARM = {
    "name": "Onshore Demo Farm",
    "description": "Sample 12-turbine onshore wind farm",
    "center_latitude": 52.0,
    "center_longitude": -1.5,
    "total_capacity_mw": 43.2,
    "turbine_count": 12,
}

ONSHORE_TURBINES = []
ONSHORE_SPACING = 756  # 6 rotor diameters
for row in range(3):
    for col in range(4):
        idx = row * 4 + col + 1
        ONSHORE_TURBINES.append({
            "turbine_id": f"WT{idx:02d}",
            "name": f"Wind Turbine {idx}",
            "latitude": 52.0 + (row - 1) * 0.007,
            "longitude": -1.5 + (col - 1.5) * 0.010,
            "x": (col - 1.5) * ONSHORE_SPACING,
            "y": (row - 1) * ONSHORE_SPACING,
            "hub_height": 80.0,
            "rotor_diameter": 126.0,
            "rated_power_kw": 3600.0,
            "thrust_coefficient": 0.8,
        })


async def seed_database(session: AsyncSession) -> dict:
    """Seed the database with sample data."""
    results = {
        "wind_farms": 0,
        "turbines": 0,
        "wind_roses": 0,
        "power_curves": 0,
    }
    
    # Create North Sea wind farm
    north_sea_farm = WindFarm(
        id=str(uuid4()),
        **SAMPLE_WIND_FARM,
    )
    session.add(north_sea_farm)
    
    # Add turbines
    for turbine_data in SAMPLE_TURBINES:
        turbine = Turbine(
            id=str(uuid4()),
            wind_farm_id=north_sea_farm.id,
            **turbine_data,
        )
        session.add(turbine)
        results["turbines"] += 1
    
    results["wind_farms"] += 1
    
    # Create onshore wind farm
    onshore_farm = WindFarm(
        id=str(uuid4()),
        **ONSHORE_WIND_FARM,
    )
    session.add(onshore_farm)
    
    for turbine_data in ONSHORE_TURBINES:
        turbine = Turbine(
            id=str(uuid4()),
            wind_farm_id=onshore_farm.id,
            **turbine_data,
        )
        session.add(turbine)
        results["turbines"] += 1
    
    results["wind_farms"] += 1
    
    # Create wind rose
    wind_rose = WindRose(
        id=str(uuid4()),
        **SAMPLE_WIND_ROSE,
    )
    session.add(wind_rose)
    results["wind_roses"] += 1
    
    # Create power curve
    power_curve = PowerCurve(
        id=str(uuid4()),
        **SAMPLE_POWER_CURVE,
    )
    session.add(power_curve)
    results["power_curves"] += 1
    
    await session.commit()
    
    return results


async def run_seed():
    """Run the database seeding."""
    print("Initializing database...")
    await init_db()
    
    print("Seeding database with fixtures...")
    async with async_session_maker() as session:
        results = await seed_database(session)
    
    print(f"✅ Seeded database:")
    print(f"   - {results['wind_farms']} wind farms")
    print(f"   - {results['turbines']} turbines")
    print(f"   - {results['wind_roses']} wind roses")
    print(f"   - {results['power_curves']} power curves")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_seed())

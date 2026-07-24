"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.turbine import Turbine, TurbineLayout, PowerCurve, PowerCurvePoint
from app.models.wind import WeibullParameters, WindData, WindRose, WindRoseEntry
from app.models.wake import WakeParameters


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_turbine() -> Turbine:
    """Create a sample turbine for testing."""
    return Turbine(
        name="T1",
        latitude=55.0,
        longitude=8.0,
        hub_height=90.0,
        rotor_diameter=126.0,
        rated_power=3600.0,
        x=0.0,
        y=0.0,
        thrust_coefficient=0.8,
    )


@pytest.fixture
def sample_layout() -> TurbineLayout:
    """Create a sample 3x3 turbine layout."""
    turbines = []
    spacing = 500  # 4D spacing for 126m rotor

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
                    thrust_coefficient=0.8,
                )
            )

    return TurbineLayout(
        turbines=turbines,
        name="Test Layout",
        reference_latitude=55.005,
        reference_longitude=8.008,
    )


@pytest.fixture
def sample_wind_rose() -> WindRose:
    """Create a sample wind rose."""
    entries = [
        WindRoseEntry(direction=i * 30, probability=1 / 12, sector_width=30) for i in range(12)
    ]
    return WindRose(entries=entries, name="Test Wind Rose")


@pytest.fixture
def sample_weibull() -> WeibullParameters:
    """Create sample Weibull parameters."""
    return WeibullParameters(shape=2.0, scale=9.0)


@pytest.fixture
def sample_wind_data(sample_wind_rose: WindRose, sample_weibull: WeibullParameters) -> WindData:
    """Create sample wind data."""
    return WindData(wind_rose=sample_wind_rose, weibull=sample_weibull)


@pytest.fixture
def sample_power_curve() -> PowerCurve:
    """Create a sample power curve."""
    points = [
        PowerCurvePoint(wind_speed=0, power=0),
        PowerCurvePoint(wind_speed=3, power=0),
        PowerCurvePoint(wind_speed=4, power=100),
        PowerCurvePoint(wind_speed=6, power=500),
        PowerCurvePoint(wind_speed=8, power=1200),
        PowerCurvePoint(wind_speed=10, power=2400),
        PowerCurvePoint(wind_speed=12, power=3400),
        PowerCurvePoint(wind_speed=14, power=3600),
        PowerCurvePoint(wind_speed=25, power=3600),
        PowerCurvePoint(wind_speed=25.5, power=0),
    ]
    return PowerCurve(
        points=points,
        cut_in_speed=3.0,
        rated_speed=14.0,
        cut_out_speed=25.0,
    )


@pytest.fixture
def sample_wake_params() -> WakeParameters:
    """Create sample wake parameters."""
    return WakeParameters(
        wake_decay_coefficient=0.04,
        turbulence_intensity=0.06,
    )

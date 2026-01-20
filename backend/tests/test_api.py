"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestLayoutEndpoints:
    """Tests for layout API endpoints."""

    def test_get_sample_layout(self, client: TestClient) -> None:
        """Test getting sample layout."""
        response = client.get("/api/v1/layout/sample")
        assert response.status_code == 200
        data = response.json()
        assert "turbines" in data
        assert len(data["turbines"]) == 9  # 3x3 grid

    def test_validate_layout(self, client: TestClient) -> None:
        """Test layout validation endpoint."""
        # Get sample layout first
        layout_response = client.get("/api/v1/layout/sample")
        layout = layout_response.json()

        # Validate it
        response = client.post("/api/v1/layout/validate", json=layout)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "turbine_count" in data


class TestWindEndpoints:
    """Tests for wind data API endpoints."""

    def test_get_sample_wind_data(self, client: TestClient) -> None:
        """Test getting sample wind data."""
        response = client.get("/api/v1/wind/sample")
        assert response.status_code == 200
        data = response.json()
        assert "wind_rose" in data
        assert "weibull" in data

    def test_get_uniform_wind_rose(self, client: TestClient) -> None:
        """Test generating uniform wind rose."""
        response = client.get("/api/v1/wind/rose/uniform?sectors=36")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) == 36

    def test_wind_statistics(self, client: TestClient) -> None:
        """Test wind statistics calculation."""
        wind_data = {
            "wind_rose": {
                "entries": [
                    {"direction": i * 30, "probability": 1/12, "sector_width": 30}
                    for i in range(12)
                ],
                "name": "Test"
            },
            "weibull": {"shape": 2.0, "scale": 9.0}
        }

        response = client.post("/api/v1/wind/statistics", json=wind_data)
        assert response.status_code == 200
        data = response.json()
        assert "weibull" in data
        assert "probabilities" in data


class TestSimulationEndpoints:
    """Tests for simulation API endpoints."""

    def test_quick_simulation(self, client: TestClient) -> None:
        """Test quick single-condition simulation."""
        # Get sample layout
        layout_response = client.get("/api/v1/layout/sample")
        layout = layout_response.json()

        request = {
            "layout": layout,
            "wind_direction": 270.0,
            "wind_speed": 10.0,
            "wake_model": "jensen",
            "wake_decay_coefficient": 0.04,
        }

        response = client.post("/api/v1/simulation/quick", json=request)
        assert response.status_code == 200
        data = response.json()

        assert "total_power_kw" in data
        assert "wake_loss_percent" in data
        assert "turbine_results" in data
        assert data["wake_loss_percent"] >= 0

    def test_list_simulations(self, client: TestClient) -> None:
        """Test listing simulations."""
        response = client.get("/api/v1/simulation/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

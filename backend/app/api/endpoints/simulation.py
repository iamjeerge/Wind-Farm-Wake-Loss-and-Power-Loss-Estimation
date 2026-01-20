"""Simulation API endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.models.simulation import (
    SimulationConfig,
    SimulationResults,
    SimulationRun,
    SimulationStatus,
)
from app.models.turbine import TurbineLayout
from app.models.wake import WakeModelType, WakeParameters
from app.models.wind import WindData
from app.services.simulation.aep_calculator import AEPCalculator
from app.services.simulation.simulator import Simulator

router = APIRouter()

# In-memory storage for simulation runs (would use database in production)
_simulation_store: dict[UUID, SimulationRun] = {}


class SimulationRequest(BaseModel):
    """Request model for starting a simulation."""

    layout: TurbineLayout = Field(description="Wind farm layout")
    wind_data: WindData = Field(description="Wind data")
    config: SimulationConfig | None = Field(
        default=None, description="Simulation configuration"
    )
    name: str = Field(default="Simulation", description="Simulation name")
    compute_aep: bool = Field(default=True, description="Whether to compute AEP")


class SimulationResponse(BaseModel):
    """Response model for simulation status."""

    id: UUID
    name: str
    status: SimulationStatus
    progress: float
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class QuickSimulationRequest(BaseModel):
    """Request for quick single-condition simulation."""

    layout: TurbineLayout
    wind_direction: float = Field(ge=0, lt=360)
    wind_speed: float = Field(ge=0, le=50)
    wake_model: WakeModelType = WakeModelType.JENSEN
    wake_decay_coefficient: float = Field(default=0.04, ge=0.01, le=0.15)


class FullSimulationRequest(BaseModel):
    """Request for full simulation across all directions."""

    layout: TurbineLayout
    wind_data: WindData | None = None
    wake_model: WakeModelType = WakeModelType.JENSEN
    wake_decay_coefficient: float = Field(default=0.04, ge=0.01, le=0.15)
    turbulence_intensity: float = Field(default=0.06, ge=0.01, le=0.30)
    superposition_method: str = Field(default="quadratic")


@router.post("/", response_model=SimulationResponse)
async def create_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
) -> SimulationResponse:
    """
    Start a new simulation.

    The simulation runs asynchronously. Use GET /simulation/{run_id}
    to check status and retrieve results.
    """
    config = request.config or SimulationConfig()

    # Create simulation run
    run = SimulationRun(
        name=request.name,
        layout=request.layout,
        wind_data=request.wind_data,
        config=config,
        status=SimulationStatus.PENDING,
    )

    _simulation_store[run.id] = run

    # Start background task
    background_tasks.add_task(
        _run_simulation,
        run.id,
        request.compute_aep,
    )

    return SimulationResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        progress=run.progress,
        created_at=run.created_at,
    )


@router.get("/{run_id}", response_model=SimulationRun)
async def get_simulation(run_id: UUID) -> SimulationRun:
    """Get simulation run by ID including results if completed."""
    if run_id not in _simulation_store:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return _simulation_store[run_id]


@router.get("/{run_id}/status", response_model=SimulationResponse)
async def get_simulation_status(run_id: UUID) -> SimulationResponse:
    """Get simulation status without full results."""
    if run_id not in _simulation_store:
        raise HTTPException(status_code=404, detail="Simulation not found")

    run = _simulation_store[run_id]
    return SimulationResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        progress=run.progress,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/{run_id}/results")
async def get_simulation_results(run_id: UUID) -> SimulationResults:
    """Get simulation results."""
    if run_id not in _simulation_store:
        raise HTTPException(status_code=404, detail="Simulation not found")

    run = _simulation_store[run_id]

    if run.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not completed. Status: {run.status}",
        )

    if run.results is None:
        raise HTTPException(status_code=500, detail="Results not available")

    return run.results


@router.post("/quick")
async def quick_simulation(request: QuickSimulationRequest) -> dict[str, Any]:
    """
    Run a quick simulation for a single wind condition.

    Returns immediate results without background processing.
    """
    # Create wake parameters
    wake_params = WakeParameters(
        model_type=request.wake_model,
        wake_decay_coefficient=request.wake_decay_coefficient,
    )

    # Create simulator
    config = SimulationConfig(wake_params=wake_params)
    simulator = Simulator(config)

    # Run single condition
    result = simulator.run_single_condition(
        request.layout,
        request.wind_direction,
        request.wind_speed,
    )

    return {
        "wind_direction": result.wind_direction,
        "wind_speed": result.wind_speed,
        "total_power_kw": result.total_wake_affected_power,
        "total_loss_kw": result.total_power_loss,
        "wake_loss_percent": result.farm_wake_loss_percent,
        "capacity_factor_percent": result.capacity_factor,
        "turbines_in_wake": result.turbines_in_wake,
        "turbine_results": [
            {
                "turbine_id": t.turbine_name,
                "turbine_name": t.turbine_name,
                "name": t.turbine_name,
                "power_kw": t.wake_affected_power,
                "wake_deficit": t.power_loss_percent / 100 if t.power_loss_percent > 0 else 0,
                "loss_percent": t.power_loss_percent,
                "effective_wind_speed": t.effective_speed,
                "effective_speed_ms": t.effective_speed,
            }
            for t in result.turbine_results
        ],
    }


@router.post("/full")
async def full_simulation(request: FullSimulationRequest) -> dict[str, Any]:
    """
    Run a full simulation across all wind directions.

    Returns AEP and directional results.
    """
    # Create wake parameters
    wake_params = WakeParameters(
        model_type=request.wake_model,
        wake_decay_coefficient=request.wake_decay_coefficient,
        turbulence_intensity=request.turbulence_intensity,
    )

    # Create simulator
    config = SimulationConfig(wake_params=wake_params)
    simulator = Simulator(config)

    # Get wind data or create default
    wind_data = request.wind_data
    if wind_data is None:
        from app.models.wind import WindRose, WindRoseEntry, WeibullParameters
        # Create uniform wind rose
        entries = [
            WindRoseEntry(direction=d, probability=1.0/36, sector_width=10.0)
            for d in range(0, 360, 10)
        ]
        wind_data = WindData(
            wind_rose=WindRose(entries=entries),
            weibull=WeibullParameters(shape=2.0, scale=8.0),
        )

    # Run full simulation
    results = simulator.run(request.layout, wind_data)

    # Calculate AEP
    aep_calculator = AEPCalculator()
    aep_result = aep_calculator.calculate_aep(results, request.layout, wind_data)

    # Aggregate turbine results
    turbine_totals: dict[str, dict[str, float]] = {}
    for dir_result in results.directional_results:
        for farm_result in dir_result.farm_results:
            for t in farm_result.turbine_results:
                if t.turbine_name not in turbine_totals:
                    turbine_totals[t.turbine_name] = {
                        "power_sum": 0.0,
                        "loss_sum": 0.0,
                        "count": 0,
                    }
                turbine_totals[t.turbine_name]["power_sum"] += t.wake_affected_power
                turbine_totals[t.turbine_name]["loss_sum"] += t.power_loss_percent
                turbine_totals[t.turbine_name]["count"] += 1

    turbine_results = [
        {
            "turbine_id": name,
            "turbine_name": name,
            "power_kw": totals["power_sum"] / totals["count"] if totals["count"] > 0 else 0,
            "wake_deficit": (totals["loss_sum"] / totals["count"]) / 100 if totals["count"] > 0 else 0,
            "effective_wind_speed": 10.0,  # Average approximation
        }
        for name, totals in turbine_totals.items()
    ]

    # Directional results
    directional_results = [
        {
            "direction": dir_result.direction,
            "power_mw": sum(fr.total_wake_affected_power for fr in dir_result.farm_results) / 1000 / len(dir_result.farm_results) if dir_result.farm_results else 0,
            "wake_loss_percent": dir_result.mean_wake_loss_percent,
        }
        for dir_result in results.directional_results
    ]

    return {
        "aep_gwh": aep_result.net_aep_mwh / 1000,
        "gross_aep_gwh": aep_result.gross_aep_mwh / 1000,
        "wake_loss_percent": aep_result.wake_loss_percent,
        "capacity_factor_percent": aep_result.net_capacity_factor * 100,
        "turbine_results": turbine_results,
        "directional_results": directional_results,
    }


@router.delete("/{run_id}")
async def cancel_simulation(run_id: UUID) -> dict[str, str]:
    """Cancel a running simulation."""
    if run_id not in _simulation_store:
        raise HTTPException(status_code=404, detail="Simulation not found")

    run = _simulation_store[run_id]

    if run.status == SimulationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Simulation already completed")

    run.status = SimulationStatus.CANCELLED
    return {"status": "cancelled", "id": str(run_id)}


@router.get("/")
async def list_simulations() -> list[SimulationResponse]:
    """List all simulation runs."""
    return [
        SimulationResponse(
            id=run.id,
            name=run.name,
            status=run.status,
            progress=run.progress,
            error_message=run.error_message,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in _simulation_store.values()
    ]


async def _run_simulation(run_id: UUID, compute_aep: bool) -> None:
    """Background task to run simulation."""
    run = _simulation_store.get(run_id)
    if run is None:
        return

    try:
        run.status = SimulationStatus.RUNNING
        run.started_at = datetime.utcnow()

        # Create simulator
        simulator = Simulator(run.config)

        # Progress callback
        def update_progress(progress: float) -> None:
            run.progress = progress

        # Run simulation (in executor to not block event loop)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: simulator.run(run.layout, run.wind_data, update_progress),
        )

        # Calculate AEP if requested
        if compute_aep:
            aep_calculator = AEPCalculator()
            results.aep = aep_calculator.calculate_aep(
                results, run.layout, run.wind_data
            )

        run.results = results
        run.status = SimulationStatus.COMPLETED
        run.progress = 100.0
        run.completed_at = datetime.utcnow()

    except Exception as e:
        run.status = SimulationStatus.FAILED
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()

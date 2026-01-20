"""Layout optimization API endpoints."""

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.models.turbine import TurbineLayout
from app.models.wind import WindData
from app.services.optimization import GeneticOptimizer, LayoutConstraints
from app.services.optimization.genetic_optimizer import (
    OptimizationConfig,
    OptimizationResult,
    SelectionMethod,
    CrossoverMethod,
)
from app.services.simulation.simulator import Simulator
from app.services.simulation.aep_calculator import AEPCalculator
from app.services.wake import JensenWakeModel, BastankhahWakeModel
from app.services.power import PowerCalculator


router = APIRouter(prefix="/optimization", tags=["Optimization"])


class OptimizationRequest(BaseModel):
    """Request to optimize a layout."""

    layout: TurbineLayout
    wind_data: WindData
    wake_model: str = Field(default="jensen", pattern="^(jensen|bastankhah)$")
    wake_decay_coefficient: float = Field(default=0.04, ge=0.01, le=0.1)

    # Constraints
    min_spacing_diameters: float = Field(default=5.0, ge=2.0, le=15.0)
    boundary_buffer: float = Field(default=200.0, ge=0)

    # GA parameters
    population_size: int = Field(default=30, ge=10, le=200)
    generations: int = Field(default=50, ge=10, le=500)
    mutation_rate: float = Field(default=0.1, ge=0.01, le=0.5)
    crossover_rate: float = Field(default=0.8, ge=0.5, le=1.0)
    early_stopping: int = Field(default=15, ge=5, le=50)


class OptimizationResponse(BaseModel):
    """Response from optimization."""

    optimized_layout: TurbineLayout
    original_aep_gwh: float
    optimized_aep_gwh: float
    improvement_percent: float
    original_wake_loss_percent: float
    optimized_wake_loss_percent: float
    generations_run: int
    converged_at_generation: Optional[int]
    fitness_history: list[float]


# In-memory storage for background optimization jobs
_optimization_jobs: dict[str, dict] = {}


def create_fitness_function(
    wind_data: WindData,
    wake_model: str,
    wake_decay: float,
):
    """Create fitness function for optimizer."""

    def fitness_fn(layout: TurbineLayout) -> tuple[float, float, float]:
        # Create wake model
        if wake_model == "jensen":
            model = JensenWakeModel(wake_decay_coefficient=wake_decay)
        else:
            model = BastankhahWakeModel(wake_decay_coefficient=wake_decay)

        # Create calculator
        power_calc = PowerCalculator()
        simulator = Simulator(
            wake_model=model,
            power_calculator=power_calc,
        )
        aep_calc = AEPCalculator(simulator)

        # Calculate AEP
        result = aep_calc.calculate_aep(
            layout=layout,
            wind_rose=wind_data.wind_rose,
            weibull=wind_data.weibull,
        )

        return (
            result.net_aep_gwh,
            result.wake_loss_percent,
            result.capacity_factor,
        )

    return fitness_fn


@router.post("/run", response_model=OptimizationResponse)
async def run_optimization(request: OptimizationRequest) -> OptimizationResponse:
    """
    Run layout optimization using genetic algorithm.

    This endpoint runs synchronously and may take a while for large layouts
    or many generations. Consider using /start for background optimization.
    """
    # Create constraints
    constraints = LayoutConstraints(
        min_spacing_diameters=request.min_spacing_diameters,
        rotor_diameter=request.layout.turbines[0].rotor_diameter
        if request.layout.turbines
        else 126.0,
        boundary_buffer=request.boundary_buffer,
        max_turbines=len(request.layout.turbines),
    )

    # Create fitness function
    fitness_fn = create_fitness_function(
        request.wind_data,
        request.wake_model,
        request.wake_decay_coefficient,
    )

    # Calculate original metrics
    original_aep, original_wake_loss, _ = fitness_fn(request.layout)

    # Configure optimizer
    config = OptimizationConfig(
        population_size=request.population_size,
        generations=request.generations,
        mutation_rate=request.mutation_rate,
        crossover_rate=request.crossover_rate,
        early_stopping_generations=request.early_stopping,
    )

    # Create and run optimizer
    optimizer = GeneticOptimizer(
        fitness_function=fitness_fn,
        constraints=constraints,
        config=config,
    )

    result = optimizer.optimize(request.layout)

    return OptimizationResponse(
        optimized_layout=result.best_layout,
        original_aep_gwh=original_aep,
        optimized_aep_gwh=result.best_aep_gwh,
        improvement_percent=result.improvement_percent,
        original_wake_loss_percent=original_wake_loss,
        optimized_wake_loss_percent=result.wake_loss_percent,
        generations_run=result.generations_run,
        converged_at_generation=result.convergence_generation,
        fitness_history=result.fitness_history,
    )


class QuickOptimizeRequest(BaseModel):
    """Quick optimization request with defaults."""

    layout: TurbineLayout
    wind_direction: float = Field(default=270.0, ge=0, lt=360)
    wind_speed: float = Field(default=10.0, ge=3, le=25)
    generations: int = Field(default=20, ge=5, le=100)


class QuickOptimizeResponse(BaseModel):
    """Quick optimization response."""

    optimized_layout: TurbineLayout
    original_power_mw: float
    optimized_power_mw: float
    improvement_percent: float
    generations_run: int


@router.post("/quick", response_model=QuickOptimizeResponse)
async def quick_optimize(request: QuickOptimizeRequest) -> QuickOptimizeResponse:
    """
    Run quick optimization for a single wind direction.

    Faster than full optimization - useful for interactive tuning.
    """
    from app.models.wind import WindRose, WindRoseEntry, WeibullParameters

    # Create simple wind data with single direction
    wind_data = WindData(
        wind_rose=WindRose(
            name="single_direction",
            entries=[
                WindRoseEntry(
                    direction=request.wind_direction,
                    probability=1.0,
                    sector_width=15.0,
                )
            ],
        ),
        weibull=WeibullParameters(
            shape=2.0,
            scale=request.wind_speed,
        ),
    )

    constraints = LayoutConstraints(
        min_spacing_diameters=5.0,
        rotor_diameter=request.layout.turbines[0].rotor_diameter
        if request.layout.turbines
        else 126.0,
    )

    fitness_fn = create_fitness_function(
        wind_data,
        "jensen",
        0.04,
    )

    original_aep, _, _ = fitness_fn(request.layout)

    config = OptimizationConfig(
        population_size=20,
        generations=request.generations,
        mutation_rate=0.15,
        early_stopping_generations=10,
    )

    optimizer = GeneticOptimizer(
        fitness_function=fitness_fn,
        constraints=constraints,
        config=config,
    )

    result = optimizer.optimize(request.layout)

    # Convert AEP to instantaneous power approximation
    # AEP (GWh) / 8760 hours * 1000 = MW average
    original_power = original_aep / 8.76
    optimized_power = result.best_aep_gwh / 8.76

    return QuickOptimizeResponse(
        optimized_layout=result.best_layout,
        original_power_mw=original_power,
        optimized_power_mw=optimized_power,
        improvement_percent=result.improvement_percent,
        generations_run=result.generations_run,
    )

"""Genetic algorithm optimizer for wind farm layout."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
import numpy as np
from enum import Enum

from app.models.turbine import Turbine, TurbineLayout
from app.services.optimization.constraints import (
    LayoutConstraints,
    MinSpacingConstraint,
    BoundaryConstraint,
    Constraint,
)


class SelectionMethod(str, Enum):
    """Selection methods for genetic algorithm."""

    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"


class CrossoverMethod(str, Enum):
    """Crossover methods for genetic algorithm."""

    UNIFORM = "uniform"
    SINGLE_POINT = "single_point"
    BLEND = "blend"


@dataclass
class OptimizationConfig:
    """Configuration for genetic algorithm."""

    population_size: int = 50
    generations: int = 100
    mutation_rate: float = 0.1
    mutation_scale: float = 50.0  # meters
    crossover_rate: float = 0.8
    elitism_count: int = 2
    tournament_size: int = 3
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    crossover_method: CrossoverMethod = CrossoverMethod.BLEND
    constraint_penalty_weight: float = 1000.0
    early_stopping_generations: int = 20
    random_seed: Optional[int] = None


@dataclass
class OptimizationResult:
    """Result of layout optimization."""

    best_layout: TurbineLayout
    best_fitness: float
    best_aep_gwh: float
    wake_loss_percent: float
    improvement_percent: float
    generations_run: int
    fitness_history: List[float] = field(default_factory=list)
    convergence_generation: Optional[int] = None


class GeneticOptimizer:
    """
    Genetic algorithm optimizer for wind farm layout.

    Uses evolutionary strategies to minimize wake losses and maximize AEP
    while respecting spatial constraints.
    """

    def __init__(
        self,
        fitness_function: Callable[[TurbineLayout], Tuple[float, float, float]],
        constraints: LayoutConstraints,
        config: Optional[OptimizationConfig] = None,
    ):
        """
        Initialize optimizer.

        Args:
            fitness_function: Function that takes layout and returns
                              (aep_gwh, wake_loss_percent, capacity_factor)
            constraints: Layout constraints
            config: Optimization configuration
        """
        self.fitness_fn = fitness_function
        self.constraints = constraints
        self.config = config or OptimizationConfig()

        # Set up constraints
        self._constraint_list: List[Constraint] = [
            MinSpacingConstraint(constraints.min_spacing_meters),
        ]

        # Random state
        self.rng = np.random.default_rng(self.config.random_seed)

    def set_boundary(
        self,
        bounds: Tuple[Tuple[float, float], Tuple[float, float]],
    ) -> None:
        """Set boundary constraint."""
        self._constraint_list.append(BoundaryConstraint(bounds, self.constraints.boundary_buffer))
        self._bounds = bounds

    def optimize(
        self,
        initial_layout: TurbineLayout,
        callback: Optional[Callable[[int, float, TurbineLayout], None]] = None,
    ) -> OptimizationResult:
        """
        Run genetic algorithm optimization.

        Args:
            initial_layout: Starting layout
            callback: Optional callback(generation, fitness, best_layout)

        Returns:
            OptimizationResult with optimized layout
        """
        n_turbines = len(initial_layout.turbines)

        # Extract initial positions
        initial_positions = self._layout_to_positions(initial_layout)

        # Calculate initial fitness
        initial_aep, initial_wake_loss, _ = self.fitness_fn(initial_layout)
        initial_fitness = self._evaluate_fitness(initial_positions, initial_layout)

        # Determine bounds from initial layout if not set
        if not hasattr(self, "_bounds"):
            x_coords = initial_positions[:, 0]
            y_coords = initial_positions[:, 1]
            margin = 500  # 500m margin
            self._bounds = (
                (x_coords.min() - margin, x_coords.max() + margin),
                (y_coords.min() - margin, y_coords.max() + margin),
            )
            self.set_boundary(self._bounds)

        # Initialize population
        population = self._initialize_population(initial_positions)

        # Track best solution
        best_positions = initial_positions.copy()
        best_fitness = initial_fitness
        best_generation = 0
        fitness_history: List[float] = [initial_fitness]

        # Early stopping counter
        no_improvement_count = 0

        for gen in range(self.config.generations):
            # Evaluate fitness for all individuals
            fitness_scores = np.array(
                [self._evaluate_fitness(ind, initial_layout) for ind in population]
            )

            # Find best in current generation
            gen_best_idx = np.argmax(fitness_scores)
            gen_best_fitness = fitness_scores[gen_best_idx]

            # Update global best
            if gen_best_fitness > best_fitness:
                best_fitness = gen_best_fitness
                best_positions = population[gen_best_idx].copy()
                best_generation = gen
                no_improvement_count = 0
            else:
                no_improvement_count += 1

            fitness_history.append(best_fitness)

            # Callback
            if callback:
                best_layout = self._positions_to_layout(best_positions, initial_layout)
                callback(gen, best_fitness, best_layout)

            # Early stopping
            if no_improvement_count >= self.config.early_stopping_generations:
                break

            # Selection
            parents = self._select(population, fitness_scores)

            # Create new population
            new_population = []

            # Elitism - keep best individuals
            elite_indices = np.argsort(fitness_scores)[-self.config.elitism_count :]
            for idx in elite_indices:
                new_population.append(population[idx].copy())

            # Crossover and mutation
            while len(new_population) < self.config.population_size:
                # Select parents
                p1_idx = self.rng.integers(len(parents))
                p2_idx = self.rng.integers(len(parents))
                parent1, parent2 = parents[p1_idx], parents[p2_idx]

                # Crossover
                if self.rng.random() < self.config.crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = parent1.copy()

                # Mutation
                if self.rng.random() < self.config.mutation_rate:
                    child = self._mutate(child)

                # Repair if needed (ensure within bounds)
                child = self._repair(child)

                new_population.append(child)

            population = new_population[: self.config.population_size]

        # Create final layout
        best_layout = self._positions_to_layout(best_positions, initial_layout)
        final_aep, final_wake_loss, _ = self.fitness_fn(best_layout)

        improvement = ((final_aep - initial_aep) / initial_aep) * 100

        return OptimizationResult(
            best_layout=best_layout,
            best_fitness=best_fitness,
            best_aep_gwh=final_aep,
            wake_loss_percent=final_wake_loss,
            improvement_percent=improvement,
            generations_run=gen + 1,
            fitness_history=fitness_history,
            convergence_generation=(
                best_generation
                if no_improvement_count >= self.config.early_stopping_generations
                else None
            ),
        )

    def _layout_to_positions(self, layout: TurbineLayout) -> np.ndarray:
        """Convert layout to position array."""
        positions = []
        for t in layout.turbines:
            positions.append([t.x, t.y])
        return np.array(positions)

    def _positions_to_layout(self, positions: np.ndarray, template: TurbineLayout) -> TurbineLayout:
        """Convert positions back to layout."""
        new_turbines = []
        for i, t in enumerate(template.turbines):
            new_turbines.append(
                Turbine(
                    id=t.id,
                    name=t.name,
                    latitude=t.latitude,  # Keep original lat/lon for reference
                    longitude=t.longitude,
                    x=float(positions[i, 0]),
                    y=float(positions[i, 1]),
                    hub_height=t.hub_height,
                    rotor_diameter=t.rotor_diameter,
                    rated_power=t.rated_power,
                    thrust_coefficient=t.thrust_coefficient,
                )
            )

        return TurbineLayout(
            turbines=new_turbines,
            name=f"{template.name}_optimized",
            reference_latitude=template.reference_latitude,
            reference_longitude=template.reference_longitude,
        )

    def _initialize_population(self, initial: np.ndarray) -> List[np.ndarray]:
        """Initialize population with variations of initial layout."""
        population = [initial.copy()]

        for _ in range(self.config.population_size - 1):
            # Add random perturbations to initial layout
            perturbed = initial.copy()
            noise = self.rng.normal(0, self.config.mutation_scale, initial.shape)
            perturbed += noise
            perturbed = self._repair(perturbed)
            population.append(perturbed)

        return population

    def _evaluate_fitness(self, positions: np.ndarray, template: TurbineLayout) -> float:
        """Evaluate fitness of a layout."""
        # Calculate constraint penalty
        total_penalty = 0.0
        for constraint in self._constraint_list:
            total_penalty += constraint.penalty(positions)

        # If heavily constrained, return low fitness
        if total_penalty > 10:
            return -total_penalty * self.config.constraint_penalty_weight

        # Create layout and evaluate
        layout = self._positions_to_layout(positions, template)
        aep, wake_loss, _ = self.fitness_fn(layout)

        # Fitness = AEP - penalty
        fitness = aep - total_penalty * self.config.constraint_penalty_weight

        return fitness

    def _select(self, population: List[np.ndarray], fitness: np.ndarray) -> List[np.ndarray]:
        """Select parents for next generation."""
        if self.config.selection_method == SelectionMethod.TOURNAMENT:
            return self._tournament_selection(population, fitness)
        elif self.config.selection_method == SelectionMethod.ROULETTE:
            return self._roulette_selection(population, fitness)
        else:
            return self._rank_selection(population, fitness)

    def _tournament_selection(
        self, population: List[np.ndarray], fitness: np.ndarray
    ) -> List[np.ndarray]:
        """Tournament selection."""
        selected = []
        for _ in range(len(population)):
            tournament_idx = self.rng.choice(
                len(population), self.config.tournament_size, replace=False
            )
            tournament_fitness = fitness[tournament_idx]
            winner_idx = tournament_idx[np.argmax(tournament_fitness)]
            selected.append(population[winner_idx].copy())
        return selected

    def _roulette_selection(
        self, population: List[np.ndarray], fitness: np.ndarray
    ) -> List[np.ndarray]:
        """Roulette wheel selection."""
        # Shift fitness to be positive
        shifted = fitness - fitness.min() + 1e-6
        probs = shifted / shifted.sum()

        indices = self.rng.choice(len(population), len(population), p=probs)
        return [population[i].copy() for i in indices]

    def _rank_selection(
        self, population: List[np.ndarray], fitness: np.ndarray
    ) -> List[np.ndarray]:
        """Rank-based selection."""
        ranks = np.argsort(np.argsort(fitness)) + 1
        probs = ranks / ranks.sum()

        indices = self.rng.choice(len(population), len(population), p=probs)
        return [population[i].copy() for i in indices]

    def _crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """Perform crossover between two parents."""
        if self.config.crossover_method == CrossoverMethod.UNIFORM:
            return self._uniform_crossover(parent1, parent2)
        elif self.config.crossover_method == CrossoverMethod.SINGLE_POINT:
            return self._single_point_crossover(parent1, parent2)
        else:
            return self._blend_crossover(parent1, parent2)

    def _uniform_crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """Uniform crossover - each gene from random parent."""
        mask = self.rng.random(parent1.shape) < 0.5
        child = np.where(mask, parent1, parent2)
        return child

    def _single_point_crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """Single point crossover."""
        point = self.rng.integers(1, len(parent1))
        child = np.vstack([parent1[:point], parent2[point:]])
        return child

    def _blend_crossover(
        self, parent1: np.ndarray, parent2: np.ndarray, alpha: float = 0.5
    ) -> np.ndarray:
        """BLX-alpha crossover - blend positions."""
        beta = self.rng.uniform(-alpha, 1 + alpha, parent1.shape)
        child = parent1 + beta * (parent2 - parent1)
        return child

    def _mutate(self, individual: np.ndarray) -> np.ndarray:
        """Apply mutation to individual."""
        mutated = individual.copy()

        # Random turbine to mutate
        turbine_idx = self.rng.integers(len(mutated))

        # Gaussian mutation
        noise = self.rng.normal(0, self.config.mutation_scale, 2)
        mutated[turbine_idx] += noise

        return mutated

    def _repair(self, positions: np.ndarray) -> np.ndarray:
        """Repair positions to satisfy boundary constraints."""
        repaired = positions.copy()

        if hasattr(self, "_bounds"):
            x_min, x_max = self._bounds[0]
            y_min, y_max = self._bounds[1]

            buffer = self.constraints.boundary_buffer
            repaired[:, 0] = np.clip(repaired[:, 0], x_min + buffer, x_max - buffer)
            repaired[:, 1] = np.clip(repaired[:, 1], y_min + buffer, y_max - buffer)

        return repaired

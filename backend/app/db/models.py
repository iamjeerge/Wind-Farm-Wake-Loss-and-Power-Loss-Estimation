"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WindFarm(Base):
    """Wind farm layout stored in database."""

    __tablename__ = "wind_farms"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Reference coordinates
    center_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    center_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Metadata
    total_capacity_mw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    turbine_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    turbines: Mapped[list["Turbine"]] = relationship(
        "Turbine",
        back_populates="wind_farm",
        cascade="all, delete-orphan",
    )
    simulations: Mapped[list["SimulationRun"]] = relationship(
        "SimulationRun",
        back_populates="wind_farm",
        cascade="all, delete-orphan",
    )


class Turbine(Base):
    """Individual turbine in a wind farm."""

    __tablename__ = "turbines"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wind_farm_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wind_farms.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Identifier
    turbine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Position
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)  # Local Cartesian
    y: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Specifications
    hub_height: Mapped[float] = mapped_column(Float, default=90.0)
    rotor_diameter: Mapped[float] = mapped_column(Float, default=126.0)
    rated_power_kw: Mapped[float] = mapped_column(Float, default=3600.0)
    thrust_coefficient: Mapped[float] = mapped_column(Float, default=0.8)
    
    # Relationship
    wind_farm: Mapped["WindFarm"] = relationship("WindFarm", back_populates="turbines")


class WindRose(Base):
    """Wind rose data stored in database."""

    __tablename__ = "wind_roses"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Weibull parameters
    weibull_shape: Mapped[float] = mapped_column(Float, default=2.0)
    weibull_scale: Mapped[float] = mapped_column(Float, default=9.0)
    
    # Wind rose entries as JSON array
    entries: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PowerCurve(Base):
    """Power curve data for turbine types."""

    __tablename__ = "power_curves"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Turbine specs
    rated_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    rotor_diameter: Mapped[float] = mapped_column(Float, nullable=False)
    cut_in_speed: Mapped[float] = mapped_column(Float, default=3.0)
    rated_speed: Mapped[float] = mapped_column(Float, default=12.0)
    cut_out_speed: Mapped[float] = mapped_column(Float, default=25.0)
    
    # Power curve data as JSON array of {wind_speed, power_kw}
    curve_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SimulationRun(Base):
    """Simulation run record."""

    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wind_farm_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wind_farms.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Configuration
    wake_model: Mapped[str] = mapped_column(String(50), default="jensen")
    wake_decay_coefficient: Mapped[float] = mapped_column(Float, default=0.04)
    turbulence_intensity: Mapped[float] = mapped_column(Float, default=0.06)
    superposition_method: Mapped[str] = mapped_column(String(50), default="quadratic")
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results
    aep_gwh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wake_loss_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capacity_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Full results as JSON
    results_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationship
    wind_farm: Mapped["WindFarm"] = relationship("WindFarm", back_populates="simulations")


class OptimizationRun(Base):
    """Optimization run record."""

    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wind_farm_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wind_farms.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Configuration
    population_size: Mapped[int] = mapped_column(Integer, default=50)
    generations: Mapped[int] = mapped_column(Integer, default=100)
    mutation_rate: Mapped[float] = mapped_column(Float, default=0.1)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    current_generation: Mapped[int] = mapped_column(Integer, default=0)
    
    # Results
    original_aep_gwh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    optimized_aep_gwh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    improvement_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Optimized layout as JSON
    optimized_layout: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    fitness_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

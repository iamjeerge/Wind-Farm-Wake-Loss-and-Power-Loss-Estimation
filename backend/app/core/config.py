"""Application configuration and settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Wind Wake Loss Estimation Tool"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost"]

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "windwake"
    POSTGRES_PASSWORD: str = "windwake"
    POSTGRES_DB: str = "windwake"

    @property
    def DATABASE_URL(self) -> str:
        """Build async database URL."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync database URL for Alembic."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Physics defaults
    DEFAULT_WAKE_MODEL: Literal["jensen", "bastankhah"] = "jensen"
    DEFAULT_WAKE_DECAY_COEFFICIENT: float = 0.04  # Offshore default
    DEFAULT_TURBULENCE_INTENSITY: float = 0.06
    DEFAULT_AIR_DENSITY: float = 1.225  # kg/m³ at sea level

    # Simulation
    DIRECTION_RESOLUTION: int = 36  # 10-degree steps
    WIND_SPEED_BINS: int = 25  # From cut-in to cut-out
    MAX_SIMULATION_TURBINES: int = 500

    # File paths
    DATA_DIR: str = "../data"
    REPORTS_DIR: str = "../reports"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

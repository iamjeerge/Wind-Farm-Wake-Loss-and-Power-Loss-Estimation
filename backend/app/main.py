"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.db.fixtures import seed_database
from app.core.database import async_session_maker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    # Initialize database
    print("Initializing database...")
    await init_db()

    # Seed if AUTO_SEED is set
    if os.getenv("AUTO_SEED", "false").lower() == "true":
        print("Seeding database with fixtures...")
        async with async_session_maker() as session:
            try:
                results = await seed_database(session)
                print(f"✅ Seeded: {results['wind_farms']} farms, {results['turbines']} turbines")
            except Exception as e:
                print(f"⚠️ Seeding skipped (may already exist): {e}")

    yield

    # Shutdown
    print("Shutting down...")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Wind Farm Wake Loss & Power Loss Estimation API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/api/docs",
    }

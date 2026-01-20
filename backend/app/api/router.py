"""Main API router."""

from fastapi import APIRouter

from app.api.endpoints import simulation, layout, wind, export, optimization

api_router = APIRouter()

api_router.include_router(
    simulation.router,
    prefix="/simulation",
    tags=["simulation"],
)

api_router.include_router(
    layout.router,
    prefix="/layout",
    tags=["layout"],
)

api_router.include_router(
    wind.router,
    prefix="/wind",
    tags=["wind"],
)

api_router.include_router(
    export.router,
    prefix="/export",
    tags=["export"],
)

api_router.include_router(
    optimization.router,
    tags=["optimization"],
)

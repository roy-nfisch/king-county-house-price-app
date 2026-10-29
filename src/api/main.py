"""Create the API without loading the model as an import side effect."""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.auth import AuthenticationMiddleware
from api.errors import invalid_request
from api.houses import router as house_router
from api.routes import router
from api.settings import ApiSettings
from api.traceability import PredictionTraceMiddleware
from king_county.artifacts import ModelArtifact
from king_county.house_records.repository import HouseRepository
from king_county.logging_config import configure_logging
from king_county.prediction import PredictionService


async def database_error(request: Request, error: sqlite3.Error) -> JSONResponse:
    """Return a safe error when storage is unavailable."""
    return JSONResponse(
        status_code=500, content={"detail": "House storage unavailable."}
    )


def configure_http(app: FastAPI) -> None:
    """Register request handlers, middleware, and routes on the app."""
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(sqlite3.Error, database_error)
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(PredictionTraceMiddleware)
    app.include_router(router)
    app.include_router(house_router)


def model_lifespan(settings: ApiSettings):
    """Build a lifespan that verifies the model once before serving requests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Create one service before requests; release its reference on shutdown."""
        configure_logging(settings)
        app.state.prediction_service = PredictionService(
            ModelArtifact(settings.model_path)
        )
        app.state.house_repository = HouseRepository(settings.database_path)
        app.state.house_repository.initialize()
        try:
            yield
        finally:
            del app.state.prediction_service
            del app.state.house_repository

    return lifespan


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Create the API; startup fails if the approved model cannot be loaded."""
    settings = settings or ApiSettings.from_environment()
    app = FastAPI(
        title="King County House Price API",
        version="0.1.0",
        lifespan=model_lifespan(settings),
    )
    app.state.api_token = (
        settings.api_token.get_secret_value() if settings.api_token else None
    )
    app.state.cloud_mode = settings.mode == "cloud"
    configure_http(app)
    return app

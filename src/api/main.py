"""Create the API without loading the model as an import side effect."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.errors import invalid_request
from api.routes import router
from api.settings import ApiSettings
from api.traceability import PredictionTraceMiddleware
from king_county.artifacts import ModelArtifact
from king_county.logging_config import configure_logging
from king_county.prediction import PredictionService


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Return an app that verifies/loads its model once during startup.

    Args:
        settings: Explicit settings for tests/local use, or read the environment.

    Returns:
        FastAPI application with prediction, readiness, and generated docs.
        Startup raises ModelLoadError rather than serving with a missing model.
    """
    settings = settings or ApiSettings.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Create one service before requests; release its reference on shutdown."""
        configure_logging(settings)
        app.state.prediction_service = PredictionService(
            ModelArtifact(settings.model_path)
        )
        try:
            yield
        finally:
            del app.state.prediction_service

    app = FastAPI(
        title="King County House Price API", version="0.1.0", lifespan=lifespan
    )
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_middleware(PredictionTraceMiddleware)
    app.include_router(router)
    # TODO(stage-2): Register separate house CRUD routes if persistence is added.
    return app

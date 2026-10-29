"""Thin HTTP routes; validation and model logic stay outside the router."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.request_validation import validate_unique_json_keys
from king_county.prediction import PredictionError, PredictionService
from king_county.schemas import HouseInput, PredictionResult

router = APIRouter()


class HealthResult(BaseModel):
    """Report readiness of the model loaded during startup, not model quality."""

    status: Literal["ready"] = "ready"
    model_version: str | None = None


def get_prediction_service(request: Request) -> PredictionService:
    """Return the service created once by the application's startup lifespan."""
    return request.app.state.prediction_service


Service = Annotated[PredictionService, Depends(get_prediction_service)]


@router.get("/health", response_model=HealthResult, response_model_exclude_none=True)
def health(request: Request, service: Service) -> HealthResult:
    """Return model readiness and version after successful startup."""
    version = None if request.app.state.cloud_mode else service.model_version
    return HealthResult(model_version=version)


@router.post(
    "/predict",
    response_model=PredictionResult,
    dependencies=[Depends(validate_unique_json_keys)],
)
def predict(house: HouseInput, service: Service) -> PredictionResult:
    """Return a total price, 422 for invalid input, or 500 for model failure."""
    try:
        return service.predict(house)
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

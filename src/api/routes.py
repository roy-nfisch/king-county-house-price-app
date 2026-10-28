"""Thin HTTP routes; validation and model logic stay outside the router."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from king_county.prediction import PredictionError, PredictionService
from king_county.schemas import HouseInput, PredictionResult

router = APIRouter()


class HealthResult(BaseModel):
    """Report readiness of the model loaded during startup, not model quality."""

    status: Literal["ready"] = "ready"
    model_version: str


def get_prediction_service(request: Request) -> PredictionService:
    """Return the service created once by the application's startup lifespan."""
    return request.app.state.prediction_service


Service = Annotated[PredictionService, Depends(get_prediction_service)]


@router.get("/health", response_model=HealthResult)
def health(service: Service) -> HealthResult:
    """Return model readiness and version after successful startup."""
    return HealthResult(model_version=service.model_version)


@router.post("/predict", response_model=PredictionResult)
def predict(house: HouseInput, service: Service) -> PredictionResult:
    """Return a total price, 422 for invalid input, or 500 for model failure."""
    try:
        return service.predict(house)
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

"""HTTP routes for five-field house storage, separate from prediction."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import Path as ApiPath

from api.request_validation import validate_unique_json_keys
from king_county.house_records.repository import HouseRepository
from king_county.house_records.schemas import HouseCreate, HouseOutput, HouseUpdate
from king_county.schemas import MAX_COUNT


def get_repository(request: Request) -> HouseRepository:
    """Return the repository initialized during application startup."""
    return request.app.state.house_repository


Repository = Annotated[HouseRepository, Depends(get_repository)]
HouseId = Annotated[int, ApiPath(gt=0, le=MAX_COUNT)]
router = APIRouter(prefix="/houses", tags=["houses"])


def found(house: HouseOutput | None) -> HouseOutput:
    """Return a house or raise a not-found HTTP response."""
    if house is None:
        raise HTTPException(status_code=404, detail="House not found.")
    return house


@router.post(
    "",
    response_model=HouseOutput,
    status_code=201,
    dependencies=[Depends(validate_unique_json_keys)],
)
def create_house(house: HouseCreate, repository: Repository) -> HouseOutput:
    """Create a house and return its assigned ID and fields."""
    return repository.create(house)


@router.get("", response_model=list[HouseOutput])
def list_houses(
    repository: Repository,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_COUNT)] = 0,
) -> list[HouseOutput]:
    """Return an ID-ordered page, with a maximum of 100 records."""
    return repository.list(limit, offset)


@router.get("/{house_id}", response_model=HouseOutput)
def read_house(house_id: HouseId, repository: Repository) -> HouseOutput:
    """Return a house, or 404 for an unknown ID."""
    return found(repository.get(house_id))


@router.put(
    "/{house_id}",
    response_model=HouseOutput,
    dependencies=[Depends(validate_unique_json_keys)],
)
def update_house(
    house_id: HouseId, house: HouseUpdate, repository: Repository
) -> HouseOutput:
    """Replace all fields, or return 404 for an unknown ID."""
    return found(repository.update(house_id, house))


@router.delete("/{house_id}", status_code=204)
def delete_house(house_id: HouseId, repository: Repository) -> None:
    """Delete a house, or return 404 for an unknown ID."""
    if not repository.delete(house_id):
        raise HTTPException(status_code=404, detail="House not found.")

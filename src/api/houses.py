"""Five-field house storage, independent of prediction inputs."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import Path as ApiPath
from pydantic import BaseModel, ConfigDict, Field

from api.request_validation import validate_unique_json_keys
from king_county.schemas import MAX_COUNT, MAX_MEASUREMENT


class HouseCreate(BaseModel):
    """Require all five stored fields, using the course reference bounds."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    bedrooms: Annotated[int, Field(ge=0, le=20)]
    bathrooms: Annotated[float, Field(ge=0, le=20)]
    sqft_living: Annotated[int, Field(ge=100, le=MAX_MEASUREMENT)]
    grade: Annotated[int, Field(ge=1, le=13)]
    zipcode: Annotated[str, Field(min_length=5, max_length=10)]


class HouseUpdate(HouseCreate):
    """Replace all five fields; null and omitted fields are invalid."""


class HouseOutput(HouseCreate):
    """Return a stored house with its database-assigned identifier."""

    id: int


class HouseRepository:
    """Store and retrieve houses in the configured SQLite database file."""

    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        """Create the table if needed, or propagate a database error."""
        with closing(sqlite3.connect(self.path, timeout=5.0)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS houses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bedrooms INTEGER NOT NULL, bathrooms REAL NOT NULL,
                sqft_living INTEGER NOT NULL, grade INTEGER NOT NULL,
                zipcode TEXT NOT NULL
            )""")

    def _connection(self) -> sqlite3.Connection:
        """Return a connection that maps rows by field name."""
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        return db

    def create(self, house: HouseCreate) -> HouseOutput:
        """Insert a house and return its persisted representation."""
        with closing(self._connection()) as db, db:
            row = db.execute(
                "INSERT INTO houses (bedrooms, bathrooms, sqft_living, grade, zipcode) "
                "VALUES (?, ?, ?, ?, ?) RETURNING *",
                tuple(house.model_dump().values()),
            ).fetchone()
            return HouseOutput.model_validate(dict(row))

    def get(self, house_id: int) -> HouseOutput | None:
        """Return a house by ID, or None when it does not exist."""
        with closing(self._connection()) as db:
            row = db.execute(
                "SELECT * FROM houses WHERE id = ?", (house_id,)
            ).fetchone()
            return HouseOutput.model_validate(dict(row)) if row else None

    def list(self, limit: int, offset: int) -> list[HouseOutput]:
        """Return one ID-ordered page of houses."""
        with closing(self._connection()) as db:
            rows = db.execute(
                "SELECT * FROM houses ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
            return [HouseOutput.model_validate(dict(row)) for row in rows]

    def update(self, house_id: int, house: HouseUpdate) -> HouseOutput | None:
        """Replace a house atomically, or return None when absent."""
        with closing(self._connection()) as db, db:
            row = db.execute(
                "UPDATE houses SET bedrooms=?, bathrooms=?, sqft_living=?, "
                "grade=?, zipcode=? WHERE id=? RETURNING *",
                (*house.model_dump().values(), house_id),
            ).fetchone()
            return HouseOutput.model_validate(dict(row)) if row else None

    def delete(self, house_id: int) -> bool:
        """Delete a house and return whether it existed."""
        with closing(self._connection()) as db, db:
            return (
                db.execute("DELETE FROM houses WHERE id = ?", (house_id,)).rowcount == 1
            )


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

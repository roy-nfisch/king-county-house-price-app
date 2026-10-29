"""SQLite persistence for houses, without an HTTP dependency."""

import sqlite3
from contextlib import closing
from pathlib import Path

from king_county.house_records.schemas import HouseCreate, HouseOutput, HouseUpdate


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

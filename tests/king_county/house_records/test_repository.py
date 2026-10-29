"""Exercise the SQLite repository directly, without API routing."""

import subprocess
import sys

import pytest

from king_county.house_records.repository import HouseRepository
from king_county.house_records.schemas import HouseCreate, HouseUpdate

pytestmark = pytest.mark.integration


@pytest.fixture
def repository(tmp_path):
    """Create an isolated real database and return its repository."""
    repository = HouseRepository(tmp_path / "houses.sqlite3")
    repository.initialize()
    return repository


def test_record_survives_repository_recreation(repository, house_fields):
    """A new repository reads the committed record and preserves its ZIP."""
    record = repository.create(HouseCreate(**house_fields))
    reopened = HouseRepository(repository.path)
    reopened.initialize()
    assert reopened.get(record.id) == record


def test_replace_and_delete(repository, house_fields):
    """Direct callers can replace and remove a record without HTTP objects."""
    record = repository.create(HouseCreate(**house_fields))
    replacement = HouseUpdate(**{**house_fields, "grade": 8})
    assert repository.update(record.id, replacement).grade == 8
    assert repository.delete(record.id) is True
    assert repository.get(record.id) is None


def test_unknown_record_returns_domain_results(repository, house_fields):
    """The repository returns None/False rather than HTTP exceptions."""
    assert repository.get(999) is None
    assert repository.update(999, HouseUpdate(**house_fields)) is None
    assert repository.delete(999) is False


def test_literal_sql_value(repository, house_fields):
    """A SQL-like ZIP remains literal data and leaves the table usable."""
    record = repository.create(HouseCreate(**{**house_fields, "zipcode": "x';--"}))
    assert repository.get(record.id).zipcode == "x';--"
    assert repository.list(20, 0) == [record]


def test_storage_imports_without_fastapi():
    """Another interface can import the domain code without loading FastAPI."""
    script = (
        "import sys; sys.modules['fastapi'] = None; "
        "from king_county.house_records.repository import HouseRepository; "
        "from king_county.house_records.schemas import HouseCreate"
    )
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True)

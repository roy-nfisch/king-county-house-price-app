# House storage API

The optional house resource is separate from `/predict`: its five fields cannot
satisfy the prediction model's 17-field input. The course reference in the
repository's initial commit uses `bedrooms` (integer 0–20), `bathrooms` (number
0–20), `sqft_living` (integer at least 100), `grade` (integer 1–13), and
`zipcode` (string of 5–10 characters). This implementation retains those bounds;
it also caps `sqft_living` at 2**53−1. Unlike prediction's five-digit ZIP rule,
the reference permits arbitrary strings of that length. Fields are required,
null and unknown fields are rejected, and duplicate JSON keys are rejected.

## Responsibilities

- `src/api/houses.py` translates HTTP requests and responses. It contains no SQL.
- `src/king_county/house_records/schemas.py` validates create/update/output records.
- `src/king_county/house_records/repository.py` owns SQLite connections and queries.

The schemas and repository do not import FastAPI. Another interface can reuse
them without importing the API. Routes call the repository and translate a
missing record into HTTP 404; the repository itself returns `None` or `False`.
The database format, field rules, routes and status codes are unchanged.

Tests mirror these responsibilities: unit schema checks and direct SQLite
integration tests live in `tests/king_county/house_records/`; HTTP contracts and app
lifecycle checks stay in `tests/api/test_houses.py`. The field-boundary matrix
moved to schema tests instead of running the same matrix through both layers.

## HTTP endpoints

- `POST /houses`: create, returning 201 and the stored fields plus `id`.
- `GET /houses/{id}`: read; `GET /houses?limit=20&offset=0`: ID-ordered page,
  with limit 1–100 and nonnegative offset.
- `PUT /houses/{id}`: replace all five fields, returning the updated record.
- `DELETE /houses/{id}`: delete and return 204. Unknown IDs return 404;
  invalid inputs and IDs return 422.

The repository uses parameterized SQLite statements and a file configured by
`DATABASE_PATH` (default `houses.sqlite3` in the working directory). Its parent
directory must exist and be writable. Startup creates the table; an unavailable
database prevents startup, and database errors during requests return a generic
500. This is a small single-host alternative to the course reference's Postgres;
it is not a distributed database. Existing databases are not migrated automatically.

Compose stores the file in the named `house-data` volume at
`/var/lib/king-county`. The image prepares that directory for its non-root user;
Docker initializes a new named volume from it. Removing the volume deletes the
stored records. Back up the database and preserve the volume when records matter.
Local and container users should restrict access: this API has no authentication,
and stored data is not encrypted by the application. The model remains a separate
read-only mount; database contents are not baked into the image.

## Review

An independent review by the parent Sol agent identified an oversized app
factory and insufficiently isolated boundary coverage. The HTTP registration
was extracted, and CRUD tests were split and expanded to cover field boundaries,
validation, replacement atomicity, pagination, and database configuration.
The parent reviewed the revised source and documentation, independently reran
59 focused CRUD and settings cases, and approved the implementation. The full
local suite passed 524 tests, including eight Docker integration cases; GitHub
CI passed for the original PR implementation. The original notebook, dataset,
and model are unchanged.

The follow-up separation moves record validation and SQLite storage into
`king_county.house_records`; the API module retains routing only. Its schemas
are unchanged, and the complete generated OpenAPI document matches the previous
implementation. Unit schema tests, direct repository tests, and existing HTTP
and Docker checks verify the same behaviour.
The final `house_records` layout passed all 529 tests, including eight Docker
integration checks. Lint, formatting and wheel/source builds passed too; three
existing pandas warnings from the original notebook remain. This follow-up has
not been committed or pushed, so its GitHub CI has not run yet.

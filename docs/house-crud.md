# House storage API

The optional house resource is separate from `/predict`: its five fields cannot
satisfy the prediction model's 17-field input. The course reference in the
repository's initial commit uses `bedrooms` (integer 0–20), `bathrooms` (number
0–20), `sqft_living` (integer at least 100), `grade` (integer 1–13), and
`zipcode` (string of 5–10 characters). This implementation retains those bounds;
it also caps `sqft_living` at 2**53−1. Unlike prediction's five-digit ZIP rule,
the reference permits arbitrary strings of that length. Fields are required,
null and unknown fields are rejected, and duplicate JSON keys are rejected.

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
CI remains pending. The original notebook, dataset, and model are unchanged.

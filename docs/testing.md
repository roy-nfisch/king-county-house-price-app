# Testing and CI

We test both the individual objects and the path from notebook export to a
working prediction. These checks protect code behaviour—not the model's
accuracy on future house sales.

## Run locally

From the repository root:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui pytest -m "not docker"
```

The `ui` extra includes Streamlit tests; without it, they skip.

## Test categories and CI stages

| Category | Question it answers | Example |
|---|---|---|
| Unit | Does this object follow its rules? | Reject invalid inputs or calculate the expected distance. |
| Integration | Do the parts work together? | Export a fitted model, load it and predict through the API or UI. |
| Contract | Would this change break an API client? | Check required fields, response types and safe error shapes. |

Run one category by adding `-m unit`, `-m integration` or `-m contract` to
pytest. Integration includes Docker cases, which need the setup below.

Tests mirror the source folders. Every test has exactly one category marker;
`docker` is an additional runtime label, not a fourth category. Collection
rejects missing or overlapping categories.

## Checks worth knowing

- **No request-time training:** prediction must work with fitting and CSV reads
  blocked. The saved pipeline is enough.
- **Refactoring safety:** controlled examples compare preprocessing with the
  original notebook. Reordering JSON fields must not change the prediction.
- **Artifact integrity:** altered model bytes fail checksum verification before
  deserialization.
- **Independent contracts:** API expectations are written separately from the
  Pydantic schemas, so changing both accidentally does not hide a breaking change.
- **Real UI behaviour:** form values, session isolation, displayed prices and
  safe errors are exercised through Streamlit's test runner.

Tests reuse the supplied data and temporary models; CI does not need API keys,
a pre-existing model or the full training grid.

## How CI stays fast

Lint, formatting and package build run first. Unit, integration, contract and
Docker jobs then run alongside one another, without repeating test cases.

Only non-Docker integration tests use two `pytest-xdist` workers.
`--dist loadfile` keeps each file together so its shared notebook setup is not
repeated. Unit, contract and Docker cases stay serial within their jobs.
Use `-n 0` when debugging.

CI limits numerical-library threads to one per worker to avoid competing thread
pools. Streamlit test runs allow 30 seconds per render; package-import subprocesses
allow 60 seconds for cold startup. These are failure limits, not added waits.

Pushes and pull requests run checks; they do not publish images or deploy apps.

## Container integration checks

With Docker running:

```bash
docker build -t king-county-api:test .
DOCKER_TEST_IMAGE=king-county-api:test uv run --locked pytest -m "integration and docker"
```

These checks cover readiness, HTTP prediction, rejected artifacts, persistent
house storage and Compose's localhost/read-only mounts. A small
`DockerContainer` helper cleans up even after failures or timeouts.

The healthy test container approves a temporary model's checksum only in its
test process. Production constants and the normal entrypoint stay unchanged;
a separate check confirms the normal startup rejects that unapproved model.

# Repository layout

Source code and tests mirror each other. This is the detailed file reference;
see the [README](../README.md#repository-layout) for the main entry points.

```text
mle-refactoring-project/
├── .github/workflows/ci.yml       # Automated development checks
├── .github/workflows/publish-image.yml # Manual GHCR publishing after image tests
├── .github/scripts/check_image_version.py # Reject reused tags and registry errors
├── Dockerfile                    # Locked installation and non-root API runtime
├── .dockerignore                 # Exclude models, data, notebooks and secrets
├── compose.yaml                  # Local API and read-only model mount
├── src/api/
│   ├── __init__.py
│   ├── errors.py                 # Safe 422 errors without raw input values
│   ├── houses.py                 # HTTP routes for house CRUD
│   ├── main.py                   # App factory and one-time startup loading
│   ├── request_validation.py     # Reject duplicate JSON keys before prediction
│   ├── routes.py                 # Predict, readiness and error responses
│   ├── auth.py                   # Optional bearer authentication
│   ├── settings.py               # Model, logging and authentication configuration
│   └── traceability.py           # Request identity, timing and metadata logging
├── src/king_county/
│   ├── __init__.py
│   ├── artifacts.py              # Code-pinned checksum and verified loader
│   ├── cleaning.py               # Copy-first cleaning rules
│   ├── features.py               # Fitted distances and ordered features
│   ├── house_records/
│   │   ├── __init__.py
│   │   ├── schemas.py            # Five-field create, update and output models
│   │   └── repository.py         # SQLite house storage without HTTP dependencies
│   ├── prediction.py             # Shared prediction service; no training
│   ├── schemas.py                # Pydantic house and price contracts
│   ├── streamlit/
│   │   ├── __init__.py           # Optional UI package
│   │   ├── app.py                # Streamlit entry point
│   │   ├── form.py               # Grouped inputs and raw field collection
│   │   └── page.py               # Validation, session service and price card
│   ├── validation.py             # Cleaning and feature input checks
│   ├── settings.py               # Pydantic logging settings
│   └── logging_config.py         # Console logging setup
├── tests/
│   ├── conftest.py               # Shared fixtures from the existing CSV
│   ├── king_county/              # Tests matching the Python package
│   │   ├── streamlit/
│   │   │   ├── test_form.py      # Layout, field keys and coordinate precision
│   │   │   └── test_page.py      # Prediction, session and safe-error integration
│   │   └── house_records/
│   │       ├── conftest.py       # Shared sample house fields
│   │       ├── test_schemas.py   # Unit checks for house validation
│   │       └── test_repository.py # Direct SQLite persistence checks
│   ├── api/                      # Shared client, API contracts, HTTP and settings
│   │   ├── conftest.py           # Shared API client with a temporary approved model
│   │   ├── test_auth.py          # Bearer and cloud configuration checks
│   │   ├── test_contract.py      # Public request, response and error contracts
│   │   ├── test_houses.py        # House HTTP contracts, errors and app lifecycle
│   │   ├── test_main.py          # Local/cloud application factory integration
│   │   ├── test_routes.py        # Startup, prediction and HTTP failure handling
│   │   ├── test_settings.py      # API configuration and environment checks
│   │   └── test_traceability.py  # Request IDs, trace metadata and privacy
│   ├── notebooks/                # Regression, training boundaries and export/reload
│   ├── docker/test_container.py   # Container lifecycle, health, HTTP and Compose checks
│   ├── workflows/                # Offline registry checks and smoke-check failures
│   └── fixtures/                 # Fixed expectations, not a duplicate CSV
├── docs/
│   ├── codespaces.md             # Private cloud development, diagram and checks
│   ├── project-overview.pdf       # Five-slide project, learning and challenges summary
│   ├── house-crud.md              # House storage contract and persistence
│   ├── final-review.md            # Project review, checks and limitations
│   ├── notebook-to-app.md         # Project journey, decisions, checks and limitations
│   ├── design.md                 # Class responsibilities and application design
│   ├── notebook-baseline.md      # Original rules and comparison details
│   ├── streamlit-ui.md           # Local form, model requirements and private access
│   ├── testing.md                # Test categories, CI and container checks
│   ├── api-and-model.md          # HTTP contracts, artifact approval and tracing
│   ├── containers.md             # Docker runtime and manual image releases
│   ├── repository-layout.md      # Detailed file reference
│   └── images/streamlit-app.jpg  # Actual local UI screenshot
├── data/King_County_House_prices_dataset.csv
├── model/versions/king-county-20261028T153712021211Z/
│   └── pipeline.skops            # Single checksum-approved inference pipeline
├── assets/                       # Notebook images
├── examples/house.json           # Feature-only record from the supplied CSV
├── .devcontainer/                # Private Codespaces development environment
├── King-County.ipynb              # Original EDA and modelling reference
├── King-County-refactored.ipynb    # Preprocessing, training, evaluation and export
├── pyproject.toml                # Dependencies and development configuration
├── uv.lock                       # Locked dependencies
├── .python-version
├── .gitignore
├── project-description.md        # Course assignment for context
├── tasks.md                      # Progress and next steps
├── README.md
└── LICENSE
```

Only the versioned `pipeline.skops` shown above is allowed by `.gitignore`; the original `model.bin`, other exports, metadata, and reload examples stay ignored. Generated files, virtual environments, and local course references are also excluded.

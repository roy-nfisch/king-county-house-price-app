# Refactoring Project

We are turning the King County house-price notebook into a simple, object-oriented Python application. The course's core task is to extract data cleaning and feature engineering into a reusable pipeline. Training, evaluation, and model saving stay in the notebook. Our portfolio extension adds a prediction API, tests, and a local Docker run.

**Status: foundation in progress (T04).** The design is approved. The installable Python package, validated logging settings, foundation tests, and CI workflow are in place; the first GitHub CI run is still pending. Cleaning/feature classes, the prediction API, model verification, and the app's Docker setup are not implemented yet. The existing `bonus_solution/` is a separate course CRUD example, not the prediction application.

## Our project at a glance

| Stage | What we build |
|---|---|
| Course core | Small Python objects for cleaning and feature engineering, with reusable pipeline steps. |
| Notebook | Import our preprocessing classes, train and evaluate the complete pipeline, and save it for the app. No training service or endpoint. |
| Our first application | Load the saved pipeline; accept house details through FastAPI; return a predicted total sale price in US dollars. Add Pydantic validation, logging, unit/integration tests, PR checks, and Docker. |
| Optional result saving | Save a prediction result before returning it. Off by default; separate from saving the trained model. |
| Later | House CRUD with a database; optional cloud deployment. |

See [the design and flow diagrams](docs/design.md) for class responsibilities, exact notebook cell references, and the proposed request example. [tasks.md](tasks.md) tracks what is done and what we will build next. We use small branches and PRs to review each piece.

### What information does prediction need?

The saved notebook model expects **19 prepared features**. Our proposed API accepts **17 raw fields** and calculates basement area, the construction/renovation field, and distance features. It needs location and neighbouring-house measurements, not just the five CRUD fields.

For the first demo, we can supply feature-only records from the bundled dataset. For a new house, missing required details mean a validation error. Supporting fewer fields requires training and evaluating a separate model—not inventing values. The full input contract and example are in [the design](docs/design.md#what-if-we-do-not-have-all-the-inputs).

### Quality and traceability

The executed notebook records test **R² = 0.844** for its final model. This is not 84.4% accuracy, a rerun by the agent, or a verified score for the proposed app. The data covers 2014–2015; this is an educational project, not a current valuation service.

We propose minimal request/model/outcome logging and optional result saving, not a separate audit platform. The [design](docs/design.md#a-lightweight-audit-not-another-platform) explains what would be recorded and the privacy limits.

Before loading the model, the app will check its SHA-256 against an approved checksum pinned in code and stop on mismatch. This checks file integrity, not prediction quality or the safety of an untrusted model. See [the model integrity design](docs/design.md#model-integrity-before-loading).

The course setup and reference material follow below. They do not yet provide a command to start our planned prediction app.

## Learning Objectives

By the end of this repository, you should be able to:

- Read and understand an existing Data Science notebook well enough to refactor it.
- Refactor data cleaning and feature engineering code into reusable Python functions.
- Build a pipeline that reproduces a notebook's preprocessing steps end to end.
- Apply the same refactoring approach to a modeling workflow (stretch goal).
- Build and containerize a FastAPI CRUD service backed by a database (stretch goal).

## Learning Path

| File / Folder | Description |
|---|---|
| [**Project Description**](project-description.md) | The assignment tasks and stretch goals. |
| [**King County Notebook**](King-County.ipynb) | The original notebook: EDA, cleaning, feature engineering, and modeling for King County house prices. |

## Repository layout

Main files and folders at T04; folder contents are collapsed where not relevant to the foundation:

```text
mle-refactoring-project/
├── .github/
│   └── workflows/
│       └── ci.yml                # Automated lint, format, tests and package build
├── src/
│   └── king_county/
│       ├── __init__.py            # Makes king_county an importable package
│       ├── settings.py            # Pydantic validation for LOG_LEVEL
│       └── logging_config.py      # Standard Python console logging setup
├── tests/
│   ├── test_settings.py           # Defaults, allowed levels and invalid settings
│   ├── test_logging_config.py     # Logging configuration unit test
│   └── test_package.py            # Installed imports and real console logging
├── docs/
│   └── design.md                 # Agreed design, notebook mapping and diagrams
├── data/
│   └── King_County_House_prices_dataset.csv
├── assets/                       # Original notebook images
├── bonus_solution/               # Separate course CRUD reference, unchanged
├── model/                        # Local saved model; ignored by Git
├── King-County.ipynb              # Training, evaluation and model saving
├── .gitignore                    # Excludes local/generated files
├── .python-version               # Existing Python 3.13 version rule
├── pyproject.toml                # Dependencies, packaging, pytest and Ruff
├── uv.lock                       # Exact resolved dependency versions
├── project-description.md        # Original course assignment
├── tasks.md                      # Task progress and completion checks
├── README.md                     # Project overview and development commands
└── LICENSE
```

`model/` is local and will not appear in a fresh clone. `.venv/`, caches, and `dist/` build outputs are omitted from this tree and ignored by Git. The planned cleaning, feature-engineering, and prediction modules are not created yet.

## Setup

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.5 or newer
and Python 3.13.17 or a newer 3.13 patch release, as defined in
[`.python-version`](.python-version).

Rebuild existing Docker images with `--pull --no-cache` after this update
to refresh their system certificates and dependencies.

> [!NOTE]
> Throughout these steps, text in angle brackets like `<repo-name>` is a **placeholder**. Replace it, including the `< >` brackets, with your own value. For example, `cd <repo-name>` becomes `cd mle-refactoring-project`.

### 1. Create the Repository from the Template

Click **Use this template** on GitHub.

When creating the repository:

- Set yourself as the **Owner**
- Choose a repository name
- Disable **Include all branches**
- Click **Create repository**

> [!IMPORTANT]
> If you are working in pairs or groups, only **one person** should complete this step.

---

### 2. Add Collaborators (Pairs/Groups Only)

If working with teammates:

1. Open the repository on GitHub
2. Go to **Settings → Collaborators**
3. Add your teammates as collaborators
4. Share the repository link with your team

Teammates should accept the invitation before continuing.

---

### 3. Clone the Repository

Copy the SSH URL from the **Code** button on GitHub, then run:

```bash
git clone <copied-ssh-url>
```

The copied SSH URL will look like `git@github.com:<your-username>/<repo-name>.git`.

---

### 4. Move into the Project Folder and Install Dependencies

This installs all dependencies and creates a virtual environment in `.venv/`.

```bash
cd <repo-name>
uv sync
```

---

### 5. Open the Repository in VS Code

> [!NOTE]
> Make sure you open VS Code from the project root so it automatically detects the environment created by `uv sync`.

Launch VS Code in the project root folder:

```bash
code .
```

Then open [King-County.ipynb](King-County.ipynb) and select the Python environment created by `uv sync` as the kernel.

## Development checks (T04)

Run these from the project root. `uv sync --locked` installs the package and development dependencies using `uv.lock`; do not add `src/` to `PYTHONPATH`.

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
```

Ruff currently checks the new package, tests, and `pyproject.toml`, not the original notebook or the separate bonus solution. CI runs the checks and Python package build on `ubuntu-slim` for pushes, pull requests, or a manual run. It uses the existing Python 3.13 version rule and a locked dependency install; no API keys or model files are needed, and it does not train or deploy a model. The slim runner has a 15-minute job limit. Future Docker build/container checks will use a separate `ubuntu-latest` job; registry publishing is tracked separately in [T11a](tasks.md#to-do) and is not implemented yet.

`AppSettings` reads `LOG_LEVEL` from the environment; the default is `INFO`. Allowed values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. An invalid value raises a Pydantic validation error. Use logging explicitly at startup; importing the package does not configure global logging:

```python
import logging

from king_county.logging_config import configure_logging
from king_county.settings import AppSettings

settings = AppSettings.from_environment()
configure_logging(settings)
logging.getLogger("king_county").info("Foundation ready")
```

## How to Use This Repo

1. Read the assignment brief in [project-description.md](project-description.md).
2. Work through the notebook in [King-County.ipynb](King-County.ipynb).
3. Refactor the cleaning and feature engineering logic into Python files.
4. Build a reusable pipeline.
5. If you want an extra challenge, extend your refactor to cover the modeling step as well.
6. If you want to go even further, use [bonus_solution/](bonus_solution/) as a reference for the optional FastAPI + Docker stretch goal.

## Bonus Solution

The [bonus_solution/](bonus_solution/) folder contains a minimal working example of:

- a FastAPI CRUD API
- Postgres persistence
- a `Dockerfile` for the API
- a `docker-compose.yaml` file to run the API and database together

It is included as a reference implementation for the optional stretch task, not as a required project structure.

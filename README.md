# King County: From Notebook to Python

We are refactoring a house-price notebook into a small, object-oriented Python project. The goal is to make its preprocessing reusable, testable, and eventually usable by a prediction application—not to build another training service.

This is a portfolio project developed during the neue fische MLE course. It builds on the supplied King County notebook and dataset, with our own Python package, validation, tests, and CI.

## What works today

- **Reusable preprocessing:** `HouseCleaner` and `HouseFeatureEngineer` run together in a scikit-learn pipeline.
- **Clear responsibilities:** validation checks inputs; the cleaner transforms them; the feature object calculates distances and returns 19 ordered model inputs.
- **Stored reference data:** fitting remembers training waterfront coordinates. Transforming new houses reuses those coordinates without fitting again.
- **Regression tests:** controlled examples check that the refactor preserves the original preprocessing results.
- **Development checks:** pytest, Ruff, and a package build run in GitHub Actions.

**Still planned:** connecting preprocessing to notebook model training/export, then adding a prediction API and Docker. There is no prediction server to start yet. See [tasks.md](tasks.md) for progress.

## The flow

```mermaid
flowchart LR
    A[House data] --> B[HouseCleaner]
    B --> C[HouseFeatureEngineer]
    C --> D[19 ordered features]
    D -. Next: notebook training and export .-> E[Saved prediction pipeline]
```

Training, evaluation, and model saving stay in the notebook. The future application will load the saved pipeline and predict; it will not run the notebook or retrain during requests.

The working notebook currently fits all retained rows **only to compare with the original baseline**. For model evaluation, we must split first and fit preprocessing on training rows only. That integration is the next step.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.5 or newer. The project uses Python 3.13.17 or a newer 3.13 patch release.

```bash
git clone https://github.com/roy-nfisch/mle-refactoring-project.git
cd mle-refactoring-project
uv sync --locked
```

Open [King-County-refactored.ipynb](King-County-refactored.ipynb) in your notebook editor, select the project's `.venv` kernel, and run it from the project root. It reads the bundled CSV and prepares features; it does not train or overwrite a model.

For the original EDA and modelling workflow, see [King-County.ipynb](King-County.ipynb).

### Use the preprocessing package

```python
import pandas as pd
from sklearn.pipeline import Pipeline

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer

training_houses = pd.read_csv("data/King_County_House_prices_dataset.csv")
preprocessor = Pipeline([
    ("cleaning", HouseCleaner()),
    ("features", HouseFeatureEngineer()),
])
# In model evaluation, pass only the training split here.
prepared = preprocessor.fit_transform(training_houses)
print(prepared.shape)
```

Use `preprocessor.transform(new_houses)` afterwards to reuse the fitted references. The training input must contain at least one waterfront house. Invalid or missing required inputs raise an error rather than receiving guessed values.

## Run the checks

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest tests/
uv build
```

Tests mirror the source packages: `src/king_county/` → `tests/king_county/`. Notebook regression tests live in `tests/notebooks/`; shared fixtures stay at the test root. Future `src/api/` code will have its tests in `tests/api/`, discovered by the same CI command.

CI runs lint, formatting, tests, and the package build on pushes and pull requests. It does not train or deploy a model and needs no API keys or model artifact.

## Repository layout

```text
mle-refactoring-project/
├── .github/workflows/ci.yml       # Automated development checks
├── src/king_county/
│   ├── __init__.py
│   ├── cleaning.py               # Copy-first cleaning rules
│   ├── features.py               # Fitted distances and ordered features
│   ├── validation.py             # Cleaning and feature input checks
│   ├── settings.py               # Pydantic logging settings
│   └── logging_config.py         # Console logging setup
├── tests/
│   ├── conftest.py               # Shared fixtures from the existing CSV
│   ├── king_county/              # Tests matching the Python package
│   ├── notebooks/                # Original/refactored regression comparison
│   └── fixtures/                 # Fixed expectations, not a duplicate CSV
├── docs/
│   ├── design.md                 # Class responsibilities and planned app
│   └── notebook-baseline.md      # Original rules and comparison details
├── data/King_County_House_prices_dataset.csv
├── assets/                       # Notebook images
├── King-County.ipynb              # Original EDA and modelling reference
├── King-County-refactored.ipynb    # Reusable preprocessing working copy
├── pyproject.toml                # Dependencies and development configuration
├── uv.lock                       # Locked dependencies
├── .python-version
├── .gitignore
├── project-description.md        # Course assignment for context
├── tasks.md                      # Progress and next steps
├── README.md
└── LICENSE
```

The local `model/` folder is ignored and is not included in a fresh clone. Generated files, virtual environments, and local course references are also excluded.

## Prediction inputs and limitations

The original notebook model uses **19 prepared features**. Our planned API will accept **17 raw fields** and derive basement area, the construction/renovation field, and distances. Missing information must produce a validation error; supporting fewer fields would require a separately trained and evaluated model. See [the input design](docs/design.md#what-if-we-do-not-have-all-the-inputs).

The data covers **2014–2015**. This is an educational project, not a current property valuation service. No model-quality result is claimed for the refactored pipeline yet. Regression tests establish compatibility with the original preprocessing—not prediction accuracy.

The planned model loader will verify an approved SHA-256 before loading. This checks artifact integrity, not model quality or the safety of an untrusted file.

## Project notes

- [Design and diagrams](docs/design.md): responsibilities, notebook mapping, and planned prediction flow.
- [Baseline reference](docs/notebook-baseline.md): preserved rules and regression checks.
- [Task list](tasks.md): completed work and next steps.
- [Original assignment](project-description.md): the course requirements behind this project.

The course's optional CRUD/database example is not part of this project's current implementation. Its local reference copy is excluded from Git. We are focusing on preprocessing first, followed by our prediction application.

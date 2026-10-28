# Refactoring Project

We are turning the King County house-price notebook into a simple, object-oriented Python application. The course's core task is to extract data cleaning and feature engineering into a reusable pipeline. Training, evaluation, and model saving stay in the notebook. Our portfolio extension adds a prediction API, tests, and a local Docker run.

**Status: design review.** We have run the notebook and saved its model. The refactored prediction application, its tests, and its Docker setup have not been implemented yet. The existing `bonus_solution/` is a separate course CRUD example, not the prediction application.

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

### Additional Folders and Files

| File / Folder | Description |
|---|---|
| [**data**](data/) | The King County house price dataset used by the notebook. |
| [**assets**](assets/) | Visual aids referenced in the repository. |
| [**bonus_solution**](bonus_solution/) | A FastAPI + Postgres + Docker reference implementation for the optional CRUD stretch goal. |
| [**pyproject.toml**](pyproject.toml) | Project configuration and dependencies. |
| [**uv.lock**](uv.lock) | Dependency lock file. |

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

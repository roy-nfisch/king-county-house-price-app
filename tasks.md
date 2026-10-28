# Project tasks

Goal: turn the King County notebook into a simple, object-oriented Python application that predicts total house prices and runs in Docker.

Keep model training, evaluation, and saving in the notebook. Python modules provide reusable preprocessing and application prediction; there is no training service or training endpoint.

Status rules: **To do** = not started; **In progress** = active or waiting for review; **Done** = the stated completion checks passed. No Jira board is needed.

## Done

- [x] **T01 — Understand the executed notebook.** Identify the cleaning, feature creation, training, evaluation, and save steps. Done: all 79 code cells have execution counts and no saved error outputs; the recorded final test R² is 0.844. This is a review of saved outputs, not an independent rerun.
- [x] **T02 — Inspect the saved model safely.** Inspect `model/model.bin` without loading Python objects. Done: its skops archive describes a fitted pipeline with 19 prepared input features. Polynomial expansion and scaling are included; the earlier cleaning and geographic feature creation are not.
- [x] **T03 — Agree on the design.** Done: we reviewed and approved the notebook/application responsibilities, prediction inputs, and documented differences. Training, evaluation, and model saving stay in the notebook.

- [x] **T04 — Create the project foundation and CI.** Done: the package, validated settings, logging, tests, Ruff, and locked CI are in place. Local and isolated-source checks passed on Python 3.13.17, and the [GitHub PR checks passed on ubuntu-slim](https://github.com/roy-nfisch/mle-refactoring-project/actions/runs/40689614650). No automatic cloud deployment is configured.
    - [x] Add the installable `king_county` package, Pydantic settings, and standard logging setup.
    - [x] Add pytest, Ruff, and a locked GitHub Actions workflow on `ubuntu-slim` for pushes and PRs.
    - [x] Run the local tests, lint, and formatting checks on Python 3.13.17.
    - [x] Verify a non-editable installation, tests, lint, formatting, and package build from an isolated source copy.
    - [x] Confirm GitHub Actions passed for [PR #2](https://github.com/roy-nfisch/mle-refactoring-project/pull/2).

- [x] **T05 — Capture a repeatable notebook baseline.** Done: the working preprocessing notebook, fixed expected outputs, rules, settings, and metric provenance are recorded. Controlled comparisons pass for both notebooks and detect a deliberate output change. Intentional later changes are documented separately.
    - [x] Create the working copy without modifying the original notebook or saved model.
    - [x] Record rules, settings, metric provenance, and intended differences in [the baseline reference](docs/notebook-baseline.md).
    - [x] Verify controlled snapshots, feature order, and row alignment for both notebooks; a deliberate output change was detected.
    - [x] Run every working-copy code cell on the full CSV: 21,596 rows, 19 features, 146 waterfront references, no missing prepared values. All 16 tests, Ruff checks, and the package build passed.

The original notebook, saved model, and CSV checksums are unchanged. T05 is locally complete; its changes are not committed or pushed, and remote CI has not run for this branch yet.

## In progress

No task currently in progress. T06 is next, after reviewing the T05 baseline.

## To do

- [ ] **T06 — Extract cleaning into a small class.** Rebuild basement area, fill the specified missing values, and derive the construction/renovation year field. Make the training-row exclusion explicit; do not silently drop prediction requests. Done when unit tests check values, row alignment, missing values, and input immutability.
- [ ] **T07 — Extract feature creation into a fitted class.** Calculate the two distance features and return model columns in a fixed order. Learn waterfront reference locations from training data only for the app version. Done when the formula matches controlled notebook examples and new requests reuse stored references without fitting again.
- [ ] **T08 — Connect the notebook to the reusable pipeline and export the model.** In the working notebook, import our preprocessing classes and join them with the existing sklearn steps. Keep splitting, training/tuning, evaluation, and saving there; do not create a training service. Split before fitting dataset-dependent features, then save the complete fitted pipeline plus metadata to a new location and calculate its SHA-256 checksum for review. Done when a fresh process can reload it and reproduce predictions without notebook variables or reading the training CSV during a request. Do not overwrite our existing model.
- [ ] **T09 — Build the prediction API.** Use Pydantic request/response models and a prediction service. Pin the approved artifact's SHA-256 in code; verify it before loading the same bytes once, and fail startup on mismatch. Validate the 17 raw input fields, predict, and return a finite price with its currency and model version. Provide a feature-only dataset example; missing required information must cause a clear validation error, not guessed values. Done when `/predict`, `/health`, and `/docs` work; invalid requests and missing-model startup fail clearly. Add a code TODO for Stage 2 CRUD at the application boundary, without implementing unused database scaffolding.
- [ ] **T09a — Add minimal prediction traceability.** Log request ID, UTC timestamp, model version, outcome, and duration without full request data. Keep saving prediction results optional and off by default; agree on the proposed JSON Lines format and failure policy in the design before implementing it. Done when logs identify a prediction's model and outcome, and optional saving is either explicitly deferred or has enabled, disabled, and write-failure tests. No audit database or dashboard is required.
- [ ] **T10 — Add integration tests.** Check preprocessing → saved artifact → checksum verification → reload → prediction and request → API → response. Done when tests cover valid/invalid data, feature order, no fitting during prediction, and clear failures. Verify that approved bytes load and altered/truncated/wrong files are rejected before deserialisation. Add tests alongside T06–T09 rather than leaving all testing until the end.
- [ ] **T11 — Run the app in Docker.** Package the app and define how its model artifact is supplied. Choose a free host port without changing internal addresses. Use `ubuntu-latest`, not `ubuntu-slim`, for the Docker build and container integration CI job; the lightweight Python checks can stay on slim. Done when a documented command starts the container, health is checked, and an example prediction succeeds. No database is required for Stage 1.
- [ ] **T11a — Publish the Docker image to a registry.** Choose the registry (GitHub Container Registry is the proposed default) and its visibility. Build and test the image before publishing, using version/commit tags. Publish only through an approved release or manual workflow, not untrusted PRs; give registry-write permission only to the publishing job and keep credentials out of the image and logs. Done when we can pull the published image by digest and run the health and example prediction checks using documented commands. Publishing an image does not deploy the application.
- [ ] **T12 — Prepare the portfolio explanation.** Update the README and a short notebook-to-app walkthrough. Explain the original workflow, classes, input/output example, tests, Docker commands, observed metrics, and limitations. Answer the course reflection questions: what steps we took, what challenges we faced, and what we would change with more time. Done when another person can follow the steps from a clean checkout. Do not describe R² as percentage accuracy.
- [ ] **T13 — Final review and public repository check.** Use small feature branches and PRs. Check the public repository for secrets, generated files, misleading claims, and reproducibility gaps. Done when CI passes and we approve the working application and documentation.

## Stage 2 — Deferred

- [ ] **T14 — Add house CRUD.** Add Pydantic models, a persistence component, database tests, and database/Compose configuration for the course's five-field house resource. Keep storage separate from prediction; five stored fields alone do not satisfy the current model's full input contract. Done when create/read/update/delete work without changing prediction behaviour.
- [ ] **T15 — Optional cloud deployment.** Choose a host only after local Docker works. Review costs, secrets, model storage, and access before deploying. Done when the deployed health and prediction checks pass and operating instructions are documented.

## Working agreement

- Python and OOP first: small classes with one clear responsibility; use composition rather than a large inheritance hierarchy.
- Keep training and model evaluation in the notebook; do not create a class for every notebook activity. The app loads the saved pipeline and predicts.
- Methods/functions and displayed code blocks stay within 50 lines. Do not hide complexity in oversized expressions to meet the limit.
- Use Pydantic at boundaries, useful logging, and explicit runtime errors. Use readable assertions and appropriate comparison helpers in tests.
- Keep changes small and reviewable. Do not commit, push, open PRs, or deploy without the relevant approval.
- Before a PR, update the relevant task checkboxes and status sections. Only mark a task done when its completion checks have passed; state any checks still awaiting GitHub CI.
- This task file tracks progress; the design document explains decisions. Avoid repeating the course instructions in both.

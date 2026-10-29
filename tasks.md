# Project tasks

Goal: turn the King County notebook into a simple, object-oriented Python application that predicts total house prices and runs in Docker.

Keep model training, evaluation, and saving in the notebook. Python modules provide reusable preprocessing and application prediction; there is no training service or training endpoint.

Status rules: **To do** = not started; **In progress** = active or waiting for review; **Done** = the stated completion checks passed. No Jira board is needed.

## Done

- [x] **T01 — Understand the executed notebook.** Identify the cleaning, feature creation, training, evaluation, and save steps. Done: the earlier review found execution counts on all 79 code cells, no saved error outputs, and final test R² 0.844. The notebook's outputs and execution counts are now cleared. This records the earlier review, not an independent model rerun.
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

Keep the original notebook, saved model, and CSV unchanged as reference material. Use the fixed baseline outputs to check that refactoring preserves preprocessing behaviour.

- [x] **T06 — Extract cleaning into a small class.** Rebuild basement area, fill the specified missing values, and derive the construction/renovation year field. Done: implementation and tests reviewed and merged in [PR #3](https://github.com/roy-nfisch/mle-refactoring-project/pull/3); the training-row exclusion remains outside prediction preprocessing.
    - [x] Add `HouseCleaner` and replace inline cleaning in the working notebook.
    - [x] Keep training-row exclusion outside the cleaner; preserve the original notebook and model.
    - [x] Verify cleaning unit tests, notebook parity, input immutability, and clear validation failures.
    - [x] Verify explicit area, nullable-value, renovation-zero, non-finite, batch-size, and row-label boundaries. The cases exposed and fixed handling of pandas `pd.NA` values.
    - [x] Separate input checks into `HouseDataValidator(data).validate()`, with direct tests; keep transformations in `HouseCleaner`.
    - [x] Reject non-real measurements and years outside integer storage limits; preserve exact integer years. All 118 tests pass, including regression and boundary checks.
    - [x] Run all working-copy code cells on the full CSV: 21,596 rows, 19 features, 146 waterfront references, no missing prepared values. Extracted cleaning matches the original on all 21,597 input rows. All 118 tests, Ruff, formatting, and the package build pass; original notebook/data/model checksums are unchanged.
    - [x] Review and merge PR #3. Push and PR CI passed, including 118 tests, Ruff, formatting, and package build.

- [x] **T07 — Extract feature creation into a fitted class.** Done: the fitted feature object, baseline parity, and reference isolation checks were reviewed and merged in [PR #4](https://github.com/roy-nfisch/mle-refactoring-project/pull/4). Push and PR CI passed.
    - [x] Add `HouseFeatureEngineer` and `HouseFeatureValidator`; return only the canonical 19 features.
    - [x] Share the distance calculation in one method; preserve the notebook's distinct latitude corrections and formulas.
    - [x] Store only training waterfront coordinates; verify that new batches never refit or add references.
    - [x] Replace inline feature engineering with a reusable cleaning/feature pipeline in the working notebook. Clearly label its full-data fit as baseline comparison only.
    - [x] Match all 19 columns against original preprocessing on the full 21,596 retained rows; preserve the original notebook, CSV, and saved model.
    - [x] Pass 187 tests, including held-out-reference isolation, cloning, output order, geographic boundaries, invalid inputs, and empty prediction batches.
    - [x] Pass local lint, formatting, package build, notebook-format validation, and 50-line function/code-block checks.
    - [x] Review and merge PR #4. Push and PR CI passed. Preprocessing parity is separate from model-quality evaluation.

- [x] **T08 — Connect preprocessing to notebook modelling and export the model.** Done: the complete pipeline, notebook training/evaluation, new local export, and fresh-process verification were reviewed and merged in [PR #5](https://github.com/roy-nfisch/mle-refactoring-project/pull/5). Push and PR CI passed. The original model was not overwritten.
    - [x] Build a separate complete pipeline and split the 17 raw inputs before fitting. Keep full-data preprocessing only for the labelled original-baseline comparison.
    - [x] Run the original 9-candidate / 5-fold training search, preserving ElasticNet and scaling settings while isolating waterfront references inside each fold.
    - [x] Evaluate on 6,479 held-out rows: R² 0.8447, MAE $94,808, RMSE $143,443. Record limitations, measured scores, and a training-mean baseline separately from regression checks.
    - [x] Export a new ignored timestamped skops bundle with metadata, checksum, versions, input contract, and held-out reload example; do not overwrite the original artifact.
    - [x] Verify fresh-process reload and prediction without the CSV; add small integration tests for fold isolation, metadata, explicit trusted types, checksum rejection, no refit, and overwrite prevention.
    - [x] Pass 195 local tests, Ruff, formatting, package build, notebook validation, local documentation links, original-artifact checksums, and 50-line checks. Only the unchanged original notebook emits pandas deprecation warnings.
    - [x] Review the implementation and scope before opening a PR. Training stays in the notebook; API work is not included. The implementation is committed and pushed.
    - [x] Confirm PR CI passes, review the changes, and merge before marking T08 done.

- [x] **T09 — Build the prediction API.** Done: reviewed and merged in [PR #6](https://github.com/roy-nfisch/mle-refactoring-project/pull/6), with 355 tests and passing push/PR CI. Pydantic validates raw house inputs; a shared service loads the checksum-approved model once and predicts. Readiness/docs work and missing/changed artifacts fail startup. Stage 2 CRUD remains a boundary TODO, not unused database scaffolding.
    - [x] Add `HouseInput`, `PredictionResult`, `ModelArtifact`, and `PredictionService` with separate validation, verified loading, and prediction responsibilities.
    - [x] Pin the reviewed export's SHA-256 and model version in code; verify and load the same bytes. Ignore sidecar checksums and reject unapproved custom types.
    - [x] Add `src/api/` and matching `tests/api/`, an application factory, one-time lifespan loading, and predict/readiness/docs endpoints. No model loading during imports.
    - [x] Require all 17 raw keys, implement explicit numeric/coordinate/area/null rules, convert ZIP strings to the numeric model feature, and reject unusable price outputs.
    - [x] Provide `examples/house.json`, startup configuration, and instructions for supplying or deliberately approving a replacement model. Package both `king_county` and `api`.
    - [x] Smoke-test the real reviewed artifact through TestClient and live Uvicorn on localhost:7002; readiness/docs/prediction succeeded, missing ZIP returned 422, and the temporary server was stopped.
    - [x] Pass 329 tests, Ruff, formatting, package build, installed-package imports, wheel contents, documentation links, protected checksums, and 50-line checks. Fix the non-finite HTTP-input error boundary so invalid numbers return 422 without echoing raw inputs.
    - [x] Reject duplicate raw JSON keys before prediction, including identical/conflicting values and escaped names; cover malformed/empty/non-object bodies and verify prediction is not called.
    - [x] Address review findings: add schema-owned technical numeric bounds with endpoint/just-outside and HTTP regression tests, correct the strict-integer design example and validate it in tests, and compare the API price against the loaded pipeline's direct prediction. All 355 tests, Ruff, formatting, package build, and diff checks passed locally and in PR CI.
    - [x] Review and merge PR #6 after passing GitHub CI. Request traceability, result saving, Docker, and deployment were outside that change.

- [x] **T09a — Add minimal prediction traceability.** Done: reviewed and merged in [PR #7](https://github.com/roy-nfisch/mle-refactoring-project/pull/7), with passing push/PR CI. Per-request objects log request ID, UTC timestamp, model version, outcome, status, and duration without house inputs or prices. Result saving remains explicitly deferred.
    - [x] Add per-request `PredictionTrace` and HTTP middleware, keeping logging separate from prediction/model loading.
    - [x] Include a server-owned correlation header on handled responses; log success, input rejection, and failure without inputs, prices, or exception details.
    - [x] Explicitly defer result persistence; no file writer, database, or unused feature flag.
    - [x] Pass 379 local tests, Ruff, formatting, package build, diff checks, and the 50-line function limit. Tests cover UTC/monotonic timing, independent metadata fields, handled/unexpected failures, validation rejection, privacy, correlation, and concurrent requests.
    - [x] Fix review findings: account for URL prefixes and distinguish completion from HTTP status. Regression tests cover cancellation/errors before and after headers, preserving observed status and propagating exceptions.
    - [x] Review, pass CI, and merge PR #7.

- [x] **T10 — Add integration tests.** Done: integration and public API contract coverage reviewed and merged in [PR #8](https://github.com/roy-nfisch/mle-refactoring-project/pull/8).
    - [x] Review existing coverage: preprocessing parity, fold isolation, fresh-process export/reload, checksum/type validation, API startup/validation, and traceability already have tests.
    - [x] Connect the existing notebook-export fixture to the actual verified loader and API; compare three held-out predictions with normal/reversed JSON key order and block fitting or CSV reads during startup/requests.
    - [x] Check preserved feature order/reference locations, real truncated/altered archives and replacement models, representative invalid HTTP values, and invalid pipeline-output translation through the real service.
    - [x] Pass 395 local tests, Ruff, formatting, package build, diff checks, and the 50-line function limit. Only the three existing original-notebook pandas warnings remain. No application-code changes, duplicated dataset, or CI job were needed.
    - [x] Add independent public API contract expectations for request fields/types/nullability, live prediction responses, and safe validation errors. Reuse API/model fixtures and move overlapping checks instead of copying them. All 423 tests, Ruff, formatting, and diff checks pass; the three original-notebook warnings remain.
    - [x] Review and merge the integration and contract changes in PR #8.

- [x] **T11 — Run the app in Docker.** Done: local Docker setup merged in PR #9, test categories and parallel execution merged in PR #10, with passing PR #10 CI including Docker on Ubuntu 26.04. The API runs with its approved model mounted read-only; no database is required.
    - [x] Add a multi-stage image with locked runtime dependencies, non-root user, and readiness health check. Exclude model/data/notebooks/secrets from the build context.
    - [x] Add Compose with localhost port 7003 → container 8000 and a read-only approved-model mount. Preserve code-pinned checksum verification and fail on a missing host artifact.
    - [x] Build and start locally; verify readiness and a prediction using the approved model.
    - [x] Add opt-in container smoke tests reusing the temporary model fixture, plus a separate `ubuntu-26.04` CI job. Select Ubuntu 26.04 explicitly instead of following the moving `ubuntu-latest` label. No publishing, deployment, or database.
    - [x] Map each test to one registered unit/integration/contract marker, with an additional Docker runtime marker where needed. Split CI into lint/format/build, three Python test-category jobs, and a Docker integration job without repeating test cases. Preserve source-mirroring test folders.
    - [x] Verify all 436 cases map to exactly one CI selection: 302 unit, 96 non-Docker integration, 32 contract, and six Docker integration. All pass locally and in merged PR #10 CI; collection rejects missing/overlapping categories and incorrect Docker categorisation.
    - [x] Add development-only pytest-xdist for two-worker, file-grouped non-Docker integration tests. Keep unit/contract/Docker cases serial within their jobs; run Docker alongside the category jobs after lint/build. A local comparison reduced integration wall time from 8.32s to 6.68s; unit workers were slower, so no unit-worker default was added. These timings are indicative, not a CI speed guarantee.
    - [x] Verify the package build, Compose validation, and 50-line function limit. Verify the image runs non-root and excludes project data/model/tests/.env.
    - [x] Fix review findings with a test-only container lifecycle object: clean up after timeouts/startup failures, retain both log streams, and require Docker health. Add helper regressions, a real timeout-cleanup test, and Compose port/mount/missing-file checks. Remove the duplicated invalid-input container test; validation remains covered by API tests. All 436 tests pass with Docker enabled; the Docker file contains 13 cases (seven helper, three real-container, three Compose). Without Docker enabled, its seven helper cases pass and six cases skip. Lint, formatting, and diff checks pass; only the three existing original-notebook warnings remain. No application-code changes.
    - [x] Inspect the approved artifact (about 72 KB): its SHA-256 matches the code pin, the verified loader accepts only the expected custom types, and fitted state includes 105 waterfront coordinate pairs. Keep versioned exports under `model/versions/`; allow only the approved version's `pipeline.skops` in `.gitignore`. Keep legacy/experimental models and sidecars ignored. Document why one model belongs with the runnable demo; keep it outside the image.
    - [x] Review, pass CI, and merge PRs #9 and #10. The dataset/model redistribution check remains open under T13, not silently approved by this technical completion.

- [x] **T11a — Publish the Docker image to a registry.** First approved publication passed from `main` (`f213617`), tag `2026.10.29`, with commit and `latest` tags. Both workflow jobs passed. The package was initially kept private; T13 records its corrected public release. No API was deployed.
    - [x] Prepare a main-only manual workflow with `YYYY.MM.DD[.N]` version tags, commit tags, and `latest` updated only after post-publish health/prediction checks. Validate real calendar dates, transfer the tested image, pin actions, and limit package-write permission to the publishing job. Use `GITHUB_TOKEN`; keep the model out of the image. Do not change registry visibility automatically.
    - [x] Document manual execution, default private package visibility, digest-based pulling, model mounting, amd64 architecture, and failure/cleanup behavior.
    - [x] Reject existing version tags before any push; fail closed on registry/authentication/network errors. Bound smoke-check HTTP requests and add offline regression tests for registry responses, workflow ordering, and timeout failures. Only `latest` intentionally moves between releases; commit tags identify the source revision.
    - [x] Pass all 463 tests, including 27 offline publishing regressions and the local Docker tests. Lint, formatting, package build, Compose validation, and Bash syntax checks pass. Earlier preparation also verified ten version-input cases, non-main rejection, and image save/load identity. Workflow lint passes with only its outdated Ubuntu 26.04 label inventory excluded; that runner already passed PR #10 CI. No registry login, push, or workflow dispatch was performed.
    - [x] Review and merge PR #11 and the README badges in PR #12.
    - [x] With explicit approval, run [publication 40786740479](https://github.com/roy-nfisch/mle-refactoring-project/actions/runs/40786740479). Hosted artifact transfer, GHCR authentication, digest pull, approved-model health/prediction, and latest promotion passed. Digest: `sha256:dd2e189dd437878d3a09f7a18e89cd0b063126a0721f97b3641894c444327311`.
    - [x] Verify visibility in GitHub settings. The package initially displayed Public despite the documented private default; change it to Private and confirm the resulting setting. No model is included in the image. Local CLI package metadata remains unavailable without `read:packages`; the signed-in browser supplied the visibility check.

- [x] **T12 — Prepare the portfolio explanation.** Merged in PR #13 with passing CI. The walkthrough and README explain the original workflow, class responsibilities, input/output example, test categories, measured results, challenges, and limitations. R² is not described as percentage accuracy.
    - [x] Draft `docs/notebook-to-app.md`, link it from the README and file tree, and distinguish the course core from our prediction extension. Correct stale artifact/app status in the design document.
    - [x] Add private registry login, exact digest pull, read-only model mount, localhost port, example prediction, troubleshooting, and stop instructions.
    - [x] Review the walkthrough from an isolated checkout: locked installation, package build, and 457 tests passed; six Docker checks skipped without a selected image. The first publishing workflow verified its image; local private pulling still needs authorised package credentials. Public-image readiness is tracked separately below.

- [x] **T13 — Final review and public runtime release.** Review and license fix merged in PR #14. Corrected image `2026.10.29.1` is public and anonymous pulls passed. Release documentation is on `docs/public-image-release`, uncommitted for review. Engineering review and runtime delivery are complete; dataset/model redistribution remains a separate unresolved follow-up below. Evidence is in `docs/final-review.md`.
    - [x] Run an independent read-only audit with GPT-6 Astra (high), different from implementer GPT-6.1 Sol. No application correctness/OOD redesign needed; record concrete packaging and documentation findings.
    - [x] Check an isolated clone, merged-main CI, tracked/generated files, and common credential signatures across the tracked tree and 43 locally reachable commits. Targeted checks found no matches; do not claim a comprehensive security scan.
    - [x] Fix missing MIT notice in package/image inputs, add metadata/runtime regressions, and correct stale Docker/app wording. Preserve original notebook, CSV, and approved model.
    - [x] Verify local fixes: all 466 tests pass with the corrected local image, including seven Docker integration cases; three existing notebook warnings remain. Lint, formatting, package build, Compose, documentation links/shell syntax, and diff checks pass. Independent reviewer rechecked the delta and four package tests; no remaining defect found in those changes.
    - [x] Merge the reviewed fixes and PDF in PR #14. Merged-main CI passed at `563785d`; follow-up Terra audit found only stale status wording, corrected in the release documentation.
    - [x] Publish corrected `2026.10.29.1` in run 40792312600. All 466 tests and post-publish verification passed. Remove old version `2026.10.29` and its two associated manifests with explicit approval; preserve the corrected version and its manifests. No old tag was overwritten; `latest` was intentionally promoted.
    - [x] Confirm public visibility, pull version/latest/digest with an empty Docker credential folder, check the installed MIT notice, and verify all old references are unavailable. Update README/badge/no-login instructions. No API was deployed; only a temporary Python-only container checked the license locally.

## Open provenance follow-up

- [ ] Confirm redistribution permission for the course dataset and the model's retained waterfront coordinates. The MIT software license alone does not establish the dataset's licensing; no separate dataset source/license notice was found. These files already exist in the repository but stay outside the public image. Do not treat technical checksum approval or completion of the engineering work as redistribution clearance.

## Stage 2 — Deferred

- [x] **T14 — Add house CRUD.** Independently reviewed: Pydantic models, SQLite persistence, database tests, and a Compose volume for the course's five-field house resource. Storage remains separate from prediction; five fields do not satisfy its full input contract. Local verification passed 524 tests, including eight Docker integration cases; GitHub CI is pending. See [house CRUD](docs/house-crud.md).
- [ ] **T15 — Optional cloud deployment.** Choose a host only after local Docker works. Review costs, secrets, model storage, and access before deploying. Done when the deployed health and prediction checks pass and operating instructions are documented.
- [ ] **T15a — Optional Streamlit prediction UI.** Build a small house-input form that passes data through Pydantic validation to the shared `PredictionService` and displays the predicted price. Call the Python service directly; FastAPI is not required between Streamlit and the service. Both interfaces must reuse the same prediction code and verified saved pipeline, without training during requests. Done when valid and invalid inputs are tested, local run instructions work, and model availability and compatible dependencies are documented before any Streamlit Community Cloud deployment.

## Working agreement

- Python and OOP first: small classes with one clear responsibility; use composition rather than a large inheritance hierarchy.
- Keep training and model evaluation in the notebook; do not create a class for every notebook activity. The app loads the saved pipeline and predicts.
- Methods/functions and displayed code blocks stay within 50 lines. Do not hide complexity in oversized expressions to meet the limit.
- Use Pydantic at boundaries, useful logging, and explicit runtime errors. Use readable assertions and appropriate comparison helpers in tests.
- Keep changes small and reviewable. Do not commit, push, open PRs, or deploy without the relevant approval.
- After each task, run an independent audit with a different model from the implementer. Check task scope, correctness, security, tests, and simple OOD; record the reviewer/model and findings, address them, and rerun relevant checks before marking the task complete. If a different model is unavailable, report that limitation rather than claiming an independent audit.
- Challenge assumptions and generated output throughout the task. Use plan reviews, evidence, and feedback on small changes to steer the implementation while it is in progress, not only at the final review.
- Before a PR, update the relevant task checkboxes and status sections. Only mark a task done when its completion checks have passed; state any checks still awaiting GitHub CI.
- This task file tracks progress; the design document explains decisions. Avoid repeating the course instructions in both.

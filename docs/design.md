# King County: notebook to application

**Status: prediction app implemented.** This document records the agreed design and its notebook mapping. Training, evaluation, and model saving stay in the notebook. For the shorter project story, read the [notebook-to-app walkthrough](notebook-to-app.md); track remaining work in [tasks](../tasks.md).

The [baseline reference](notebook-baseline.md) records exact preprocessing rules, controlled outputs, and differences between the working copy and the original.

## 1. What the notebook currently does

The notebook loads 21,597 house-sale records, cleans them, creates features, trains several regressions, evaluates them, and saves the final sklearn pipeline. Its prediction target is **total sale price in US dollars**, not the exploratory `sqft_price` ratio.

| Step | Confirmed behaviour |
|---|---|
| Clean | Remove row label 15856; rebuild basement area as living area minus above-ground area; fill missing `view` and `waterfront` with zero. |
| Construction/renovation | Use the renovation year unless it is zero or missing; otherwise use the construction year. |
| Create features | Calculate distance to a fixed reference location and to the nearest waterfront reference house. `sqft_price` is for exploration and is excluded from model inputs. |
| Split | Reserve 30% for testing using `random_state=42`. |
| Train | Compare linear and polynomial regressions, then tune a pipeline containing polynomial features, scaling, and ElasticNet with target scaling. |
| Save | Write the selected pipeline to `model/model.bin` using skops. |

An earlier review recorded adjusted R² values of **0.43**, **0.48**, and **0.75** for the earlier models, and ordinary test R² **0.844** for the final model. The notebook's saved outputs are now cleared; these results have not been newly reproduced. Adjusted and ordinary R² are different measures; neither means "84.4% of predictions are correct."

### What we inspected in the legacy artifact

The local artifact exists and is 69,583 bytes. Its JSON schema was read without deserialising Python objects. It describes polynomial expansion, input scaling, and an ElasticNet regressor with target scaling. The stored sklearn version is 1.9.0.

It expects these **19 prepared features in this order**:

```text
bedrooms, bathrooms, sqft_living, sqft_lot, floors,
waterfront, view, condition, grade, sqft_above,
sqft_basement, zipcode, lat, long, sqft_living15,
sqft_lot15, last_known_change, center_distance, water_distance
```

It does not contain the earlier cleaning or waterfront reference-building steps. Loading this legacy file alone will not turn raw house details into a prediction. It remains a reference; the API uses the complete refactored pipeline exported by the working notebook instead.

The repository includes one approved versioned `pipeline.skops` (about 72 KB), containing the complete refactored pipeline. Other exports and the legacy `model.bin` stay ignored. A fresh clone can use that approved file without retraining. Loading a different export requires deliberate code approval; a missing or changed model stops API startup. The Docker image excludes the model and loads it from a read-only mount. See the [artifact reference](api-and-model.md#exported-files) for artifact and redistribution limitations.

## 2. The proposed pattern: small objects working together

Use **composition**: each class owns one job and receives the components it needs. Do not add a generic framework, a base class for every service, or a database before it is needed.

| Component | Its job | What it must not do |
|---|---|---|
| `HouseDataValidator` | Hold the input table and run its named checks through `validate()`. Return numeric cleaning columns or raise a clear error. | Fill missing values, remove rows, or apply cleaning rules. |
| `HouseFeatureValidator` | Check cleaned feature inputs, finite numeric values, and latitude/longitude limits. | Calculate features, learn references, or replace the future API contract. |
| `HouseCleaner` | Apply the stated cleaning rules to a copy of the input table. Use sklearn's transformer interface. | Train a model or silently remove prediction rows. |
| `HouseFeatureEngineer` | Learn and retain waterfront reference locations in `fit`; create distances and ordered features in `transform`. | Learn new references from prediction requests or use sale price as an input. |
| `ModelArtifact` | Read the configured model once, check its code-pinned SHA-256 and custom-type allowlist, and return the fitted complete pipeline. | Trust a supplied metadata checksum or uploaded model. |
| `PredictionService` | Load through `ModelArtifact` at construction and reuse the pipeline for validated house inputs. Return a validated finite positive price. | Refit preprocessing, retrain, or save house records. |
| Pydantic models | Define house inputs, application settings, and prediction responses with explicit validation. | Learn data patterns or establish that a prediction is accurate. |
| FastAPI routes | Pass requests to the service and return responses/errors; optionally save a validated prediction result before returning it. | Duplicate cleaning or model logic. |

### Where these jobs come from in the notebook

Cell numbers below count **all cells, including Markdown**, starting at 1. `In[...]` refers to the earlier reviewed run; execution counts are now cleared and can change after rerunning. Search for the shown heading or code to find the same step.

| Proposed component | Notebook heading and cells | Recognisable code / move |
|---|---|---|
| `HouseDataValidator` | No separate validator in the original notebook. | New safeguards around the extracted cleaning inputs, separate from the future API's Pydantic contract. |
| `HouseCleaner` | **Data Preparation**, code cells 31, 36, 39, 42–44 (`In[10]`, `In[13]`, `In[15]`, `In[17]`–`In[19]`). | Rebuild `sqft_basement`; fill `view` / `waterfront`; create `last_known_change`. Cell 29's fixed-row exclusion belongs to training-row rules, not request cleaning. |
| `HouseFeatureEngineer` | **Feature Engineering**, cell 61 (`In[28]`); **Distance to the waterfront**, cells 68–71 (`In[32]`–`In[35]`); **Modeling**, cells 79–81, 93, 102. | Create `center_distance` / `water_distance`, then select and order inputs. `X_train.columns` shows 20 columns; dropping `id` leaves 19. Do not include the exploratory `sqft_price`. |
| Notebook training — stays in the notebook | **Data Preparation**, cell 29; **Modeling**, cells 79–83; **Regularization and Hyperparameter Tuning**, cells 118–121; **Save the Model**, cell 132. | Import our preprocessing classes, then apply training-row rules, split, fit/tune, evaluate, and save the complete pipeline. Do not turn these steps into an application service. |
| `PredictionService` | **Regularization and Hyperparameter Tuning**, cell 124 (`In[73]`) calls `elastic.predict(X_test_poly)`. | Reuse that prediction operation with the complete saved preprocessing pipeline. Startup loading and HTTP requests are new application code, not existing notebook steps. |
| Pydantic models | No corresponding notebook implementation. **Business Understanding**, cell 5, describes dataset fields. | New validation around incoming house JSON, settings, and outgoing results. |
| FastAPI routes | No corresponding notebook implementation. | Prediction and five-field house CRUD boundaries. Storage and validation live outside the HTTP route module. |

The notebook creates waterfront references before splitting. Moving reference fitting inside the training pipeline is a deliberate change, explained in section 3; the table maps responsibilities, not an identical execution order.

This is the familiar application shape: **validated request → service → validated response**. The sklearn pipeline remains the mechanism that runs preprocessing and prediction in order; our small classes supply the project-specific behaviour.

### Training in the notebook: build and save what prediction will reuse

The working copy imports `HouseCleaner` and `HouseFeatureEngineer` and first compares their preprocessing with the original full-data baseline. A separate complete model pipeline then splits raw inputs before fitting; grid search clones cleaning, features, polynomial expansion, scaling, and the estimator for every training fold. Data splitting, training, tuning, evaluation, and export stay in the notebook. Each export creates a new ignored bundle with the fitted pipeline, metadata, and a held-out reload example. A fresh process verifies the checksum, applies an explicit custom-type allowlist, and reproduces predictions without reading the CSV. The application loads an approved artifact; it will not run or serve the notebook. No training service, training endpoint, or scheduled retraining is needed.

```mermaid
flowchart LR
    A[Training CSV] --> B[Training-row rules]
    B --> C[Split into train and test]
    C --> D[Fit complete pipeline on training data]
    D --> E[Evaluate on held-out test data]
    E --> F[Save fitted pipeline and metadata]
```

### Prediction: use the saved pipeline, without fitting again

```mermaid
flowchart TD
    A[House JSON] --> B[Pydantic input validation]
    B --> C[PredictionService]
    C --> D[Saved pipeline: clean, create features, predict]
    D --> E[Validate price response]
    E --> F{Save prediction enabled?}
    F -->|No: default| H[Return price response]
    F -->|Yes: optional| G[Save prediction result]
    G --> H
```

**These are two different saves.** The notebook saves the fitted model for reuse. The optional prediction step saves a result before returning it; it does not retrain or modify the model. Keep result saving outside `PredictionService` and use a small helper first, not a database framework. This remains optional, off by default, and separate from Stage 2 house CRUD. If enabled saving fails, return a clear error rather than claiming the result was saved.

### Initial app scope

- Use FastAPI with `/predict`, `/health`, and interactive `/docs` as the first usable interface. A separate frontend is not required for this first stage.
- Accept the raw inputs described below, not `price`, `sqft_price`, an ID, or manually computed distance features. Reject missing required inputs rather than inventing values.
- Rebuild basement area and the last-known-change field using the notebook rules. Preserve the distance formulas in the first implementation.
- In the notebook, save the complete fitted pipeline, including geographic reference state, rather than only the final estimator steps. Record feature order, dependencies, data/model version, split settings, and measured metrics alongside it. The app only loads this artifact.
- Load only the project's own trusted artifact, after verifying the checksum described below. Do not accept uploaded model files or blindly trust all types reported by a loader.
- Keep our notebook and existing model unchanged as reference material. Write refactored artifacts to a separate location.

### What if we do not have all the inputs?

**We cannot use the existing model with only five fields.** A working endpoint does not remove the model's information requirements. For the first local demonstration, we can use feature-only examples from the supplied CSV. For a genuinely new house, we need the same information from a user or a verified data source.

| Source | Fields / behaviour |
|---|---|
| Required house details | `bedrooms`, `bathrooms`, `sqft_living`, `sqft_lot`, `floors`, `condition`, `grade`, `sqft_above`, `yr_built`. |
| Location | `zipcode`, `lat`, `long`. The app has no address lookup yet. |
| Dataset-specific details | `sqft_living15`, `sqft_lot15`: the supplied neighbouring-house measurements. These are not the current house's areas. Their exact aggregation is not established by the notebook, so do not invent a calculation for new houses. |
| Explicit notebook missing-value rules | Require the keys `view`, `waterfront`, and `yr_renovated`, but allow `null`. Fill null `view` / `waterfront` with 0; use `yr_built` when `yr_renovated` is null or 0. These are documented transformations, not guessed defaults for unrelated fields. |
| Computed by our pipeline | `sqft_basement = sqft_living - sqft_above`; derive `last_known_change`; calculate both distances from coordinates and stored reference locations. |

That is **17 raw input fields → 19 prepared model features**. Basement area and three derived features are calculated; the two raw year fields are replaced by one. Input validation must reject inconsistent areas, such as above-ground area exceeding total living area.

This request example comes from the first CSV record, with the empty `waterfront` value represented as `null`. No sale price, ID, date, or precomputed features are sent:

```json
{
  "bedrooms": 3,
  "bathrooms": 1.0,
  "sqft_living": 1180,
  "sqft_lot": 5650,
  "floors": 1.0,
  "waterfront": null,
  "view": 0.0,
  "condition": 3,
  "grade": 7,
  "sqft_above": 1180,
  "yr_built": 1955,
  "yr_renovated": 0,
  "zipcode": "98178",
  "lat": 47.5112,
  "long": -122.257,
  "sqft_living15": 1340,
  "sqft_lot15": 5650
}
```

This is an input example, not evidence of performance on an unseen house. Use held-out records for evaluation. A reference house ID may select an example locally, but it is not a feature sent to the model.

If the intended interface must work with fewer details, the alternative is to **train and evaluate a separate model using only those available fields**. It will have a different input contract and may have different quality. Do not silently fill unknown neighbouring measurements with zeros or reuse the current 19-feature artifact with a shorter request. Automatic property-data lookup is outside the initial scope.

## 3. Decisions that must stay visible

**HTTP boundary:** `src/api/main.py` creates the app without model-loading import side effects. Its startup lifespan creates one service per worker; routes in `src/api/routes.py` reuse it. `HouseInput` requires all 17 keys, rejects extra/coerced/non-finite values, validates physical coordinate limits, nonnegative counts/areas, binary waterfront flags, int64-safe nonnegative years, five-digit ZIP strings, and area consistency. The ZIP string is converted to the notebook's numeric feature by the service. These technical checks do not guarantee that an unfamiliar house is within the model's learned domain.

**Failure policy:** invalid request data returns 422 before prediction. A dedicated handler returns error types, field locations, and messages without raw input/context objects; this also prevents non-finite inputs from breaking error-response serialization. The model must return one finite positive total price; zero/negative/non-finite or malformed output raises `PredictionError` and returns a controlled 500 response, without clamping or exposing internal pipeline details. `/health` reports that startup loaded the reviewed model, not that its predictions are accurate. Requests and results are not persisted. Request-level metadata logging is described below; authentication, result saving, and deployment remain deferred. Bind the current server to localhost.

**Numeric limits:** `HouseInput` owns the technical bounds. Counts and years are limited to nonnegative int64 storage; measurements are capped at `2**53 - 1`, float64's consecutive-integer precision limit. This conservative application policy prevents oversized requests from reaching pandas as object-valued counts or overflowing degree-two products. It does not establish realistic property limits, learned-domain membership, or guaranteed prediction success. Boundary tests cover each capped field; HTTP regression tests check that the two reported oversized inputs return 422 without calling prediction.

**Notebook parity versus app behaviour:** first compare extracted transformations with fixed notebook examples. The original notebook builds its waterfront reference list before splitting the dataset. In the working notebook, fit the reusable pipeline on training rows only, so its reference locations can be saved and reused at inference. This is an intentional training-boundary change, not a claim of identical predictions or the same 0.844 score. Evaluate and document it separately.

**Row removal:** the notebook drops a fixed row label. That is tied to this CSV, not a general validation rule. Record the known exclusion for the training baseline, then agree on an explicit rule. Prediction requests must produce a result or a clear validation error, not silently disappear.

**Current limitations:** the source sales are from 2014–2015, so this is an educational demonstration, not a current property valuation service. The notebook uses a shuffled row split and contains repeated house IDs. We have not established performance on future sales or entirely unseen properties.

**Stale narrative:** the final notebook paragraph says roughly 83%, while the earlier reviewed run reported R² 0.844. Some later outlier lookups also use fixed house IDs rather than the IDs produced by that run. Keep these as historical observations; the cleared outputs no longer show that run. Do not silently change the notebook or turn these into current portfolio claims.

## 4. Tests, logging, and failure behaviour

### Model integrity before loading

`src/king_county/artifacts.py` pins `MODEL_VERSION` and `EXPECTED_MODEL_SHA256` in code. At startup, `PredictionService` delegates to `ModelArtifact`, which reads model bytes once, verifies their SHA-256 **before deserialising anything**, rejects unapproved custom types, and loads those same bytes. A mismatch or incompatible pipeline stops startup. `MODEL_PATH` may relocate the artifact but cannot change its approved identity; the loader never reads a sidecar checksum.

The original reference artifact, `model/model.bin`, has this checksum (not the API's approved model):

```text
2ba5c24e79ec5563ef40420870a22ae2c8d6300a2afa097c05ea7bf3493359de
```

This value identifies the legacy artifact, not the API's complete pipeline. When we deliberately export a replacement from the notebook, calculate its checksum, review the model and its evaluation, and update the pinned constant in the same release. Do not automatically replace the expected checksum at startup or accept one supplied with an uploaded file.

This is an **integrity check**: it detects a changed, corrupted, or wrong artifact relative to the approved code. It is not a digital signature, a model-quality check, or permission to load an untrusted model. Anyone able to change both the artifact and the trusted code can replace both; code review and deployment access still matter. Keep skops' type checks; do not automatically trust every reported type. No model-upload endpoint is planned.

### Behaviour checks

- Unit tests cover cleaning values, missing values, distance examples, feature order, and preservation of row labels and input data.
- Integration tests cover artifact round-trip prediction and the API using a small controlled fitted model. Test startup failure for a missing/incompatible artifact and rejection of invalid requests.
- The approved artifact loads, while altered/truncated/wrong bytes are rejected before skops inspects or deserialises them. Tests also check missing-model startup failure, one-time loading, no CSV/refit during prediction, and controlled HTTP errors.
- Compare tables with pandas testing helpers and floats with a justified tolerance. Full model quality belongs in a repeatable evaluation, not an assertion that every prediction equals its true sale price.
- Keep small deterministic checks in PR CI. Do not run expensive grid searches or depend on cloud credentials for ordinary unit tests.
- Use standard Python logging for startup, training stages, and failures. Do not log complete requests or secrets. A healthcheck passing is not evidence of prediction quality.
- Use explicit exceptions/validation errors at runtime, not Python assertions. Do not hide failures or silently clamp an implausible model output; agree on the API's failure policy and test it.

### A lightweight audit, not another platform

**Implemented:** `PredictionTrace` owns one server-generated UUID, UTC start timestamp, model version, and monotonic timer. `PredictionTraceMiddleware` wraps only `POST /predict` and emits one JSON message through standard INFO logging, with outcome, HTTP status, and elapsed milliseconds. Instances are per request, not shared mutable state. The model version comes from the loaded service; neither house inputs nor prices are logged. The console formatter can add a prefix around the JSON message. This is operational evidence, not a tamper-proof compliance audit or proof that a price is correct.

The middleware returns `X-Request-ID` on handled responses, including input rejection and controlled model failures; incoming IDs are replaced. Unexpected exceptions still propagate after a failed trace is logged. FastAPI's outer generic-500 response may lack the ID header. Readiness/docs are not prediction events. INFO logging must be enabled to emit these records; external log retention is an operator responsibility.

Route matching uses Starlette's application-relative path so configured proxy prefixes do not bypass tracing. Completion is tracked separately from the observed HTTP status: errors and cancellations propagate and produce a failed outcome, even after 200 headers started. Before any headers, the recorded status is `null`; it does not guess what an outer handler or proxy might send. Regression tests cover interruption before/after headers and prefixed/unprefixed routing.

**Result saving is explicitly deferred.** There is no result writer, database, file handler, or `SAVE_PREDICTIONS` setting in this implementation. Do not enable persistence without first agreeing on its format and failure policy. The paragraphs below describe a future option, not existing behaviour.

The optional **save prediction result** step in the diagram can write a JSON Lines file: one record per validated result, containing the same request ID, timestamp, model version, predicted price, and currency. Propose `SAVE_PREDICTIONS=false` as the default. Do not store raw house inputs, exact locations, personal information, or secrets by default. Minimal result records are not enough for exact input replay; if we later need that, agree on consent, access, retention, and storage first.

For the local prototype, use a configured writable file location and test the enabled, disabled, and write-failure paths. Container-local files are temporary unless persisted with a volume; do not claim otherwise. A database, audit dashboard, checksum chain, and permanent request storage are unnecessary for Stage 1. Before exposing this publicly, agree on access and retention rather than turning optional saving on automatically.

### Container boundary

Docker packages the existing app; it adds no new service class or training path. The builder installs locked runtime dependencies and the package; the final image runs Uvicorn as a non-root user. A narrow build-context allowlist excludes datasets, notebooks, models, and secrets. We retain the existing dependency list rather than refactoring packaging during this task.

Compose publishes only `127.0.0.1:7003` → container port `8000`, with the approved model mounted read-only. The normal startup path still verifies the code-pinned digest before loading. An HTTP health check reports readiness after startup. No database or custom network is needed for a single service; Compose manages its own default network.

Container smoke tests use the existing temporary model fixture and a test-only startup command that approves its digest in memory. The normal image command is also tested to reject that unapproved fixture. This lets CI check packaging without distributing the production artifact or adding a production checksum override. Image publishing remains a separate task.

The test-only `DockerContainer` object owns a named container's lifetime. A context manager removes it after success, startup failure, or a client timeout. Readiness inspects Docker health rather than bypassing the image health check, and diagnostics retain both output streams. Compose configuration checks cover the localhost port and read-only model mount without requiring a production artifact in CI.

Keep invalid-request validation in the API tests. Container tests focus on packaging, startup, prediction wiring, checksum rejection, and resource cleanup rather than repeating application-level cases.

Build reference: [uv's Docker integration guide](https://docs.astral.sh/uv/guides/integration/docker/).

## 5. House storage boundary

House CRUD is a separate feature: API routes → a house storage component → database. It should not be added inside `PredictionService`.

`src/api/houses.py` contains HTTP routing only. The Pydantic records in
`king_county/house_records/schemas.py` and SQLite repository in
`king_county/house_records/repository.py` do not depend on FastAPI. The app initializes
the repository during startup and injects it into the routes. Tests mirror the
same split. See [house storage](house-crud.md) for the unchanged five-field
contract and persistence behaviour.

## 6. Review and delivery

Review this design before implementation. Then use small feature branches and PRs for foundations, preprocessing, notebook integration/model export, API, Docker, and documentation. Add tests with each behaviour. CI/CD starts with automated checks; automatic deployment is a later decision.

Keep [tasks.md](../tasks.md) current. The final README and walkthrough will explain how each notebook step became a class or pipeline step and how another person can run the app locally. A PDF/presentation or cloud deployment can follow once the local application works.

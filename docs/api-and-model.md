# API, model and preprocessing reference

Run commands from the repository root. For the shortest startup path, see the
[README](../README.md#run-the-prediction-api).

## Preprocessing and notebook training

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

Training and evaluation stay in `King-County-refactored.ipynb`. Select the project's `.venv` kernel and run from the repository root. Review results before export; new bundles are ignored and do not overwrite the original model.

The notebook first fits preprocessing on all retained rows only for original-baseline comparison. Its separate modelling section splits raw inputs first and fits a fresh complete pipeline in each training fold. Evaluation never reuses the full-data baseline object. See [the baseline and export reference](notebook-baseline.md#model-training-and-export).

## Prediction inputs and limitations

The model uses **19 prepared features**. The API accepts **17 raw fields** and derives basement area, the construction/renovation field, and distances. Missing information produces a validation error; supporting fewer fields would require a separately trained and evaluated model. See [the input design](design.md#what-if-we-do-not-have-all-the-inputs).

The model uses historical data, not current property valuations. See the
[evaluation record](notebook-baseline.md#model-training-and-export) for measured
results and split limitations. Regression tests establish preprocessing
compatibility, not prediction quality.

### Exported files

The notebook saves `pipeline.skops`, `metadata.json`, and `reload-example.json` under a new timestamped `model/versions/king-county-…/` directory. Metadata records the input contract, metrics, data checksum, versions, and model SHA-256. The reload example contains three held-out feature-only records and their expected predictions. New exports remain local and ignored unless deliberately approved; rerunning export with the same directory fails rather than overwriting it.

**Why include one trained model?** The `pipeline.skops` file (about 72 KB) lets a fresh clone run the API and Docker demo without retraining or requesting a separate model download. It contains preprocessing and the fitted estimator, not just prediction weights. The original `model.bin` is a reference artifact and is not used by the API. Keeping one approved version also makes the demo reproducible; an arbitrary new export is not automatically trusted.

**Artifact review:** the approved file matches the SHA-256 pinned in `src/king_county/artifacts.py` and loads with only the two expected custom transformer types. It retains 105 training waterfront coordinate pairs, scaling statistics, and fitted model parameters; it is not anonymised or free of training-derived data. No credential-like fields were found in the archive schema, but that inspection is not a comprehensive security certification. Before public release, confirm permission to redistribute the course dataset and its retained coordinates: the repository has an MIT software license, but no separate dataset source/license notice was found. This remains an open release check in `tasks.md`.

The notebook's fresh-process check verifies the bytes and permits only the two named custom transformer types. It checks serialization, not model quality or release approval. See [the export reference](notebook-baseline.md#model-training-and-export) for details.

The model loader verifies the code-pinned SHA-256 before loading the same bytes and permits only the two named custom transformer types. This checks artifact integrity, not model quality or the safety of an untrusted file. It does not trust a colocated metadata checksum.

## HTTP behaviour

The response contains `predicted_price`, `currency` (`USD`), and `model_version`. `/health` reports readiness after model loading, not prediction quality. Missing/invalid fields return **422**; model/output failures return **500**. Non-finite or non-positive prices fail explicitly rather than being clamped.

ZIP codes must be five-digit strings; the service converts them to the model's numeric feature. Numeric fields reject strings and booleans. Years/counts are whole numbers, areas and coordinates are finite, and above-ground area cannot exceed living area. The keys `view`, `waterfront`, and `yr_renovated` are required but may be `null`, following the notebook's cleaning rules. There is no address lookup or guarantee that any in-range location is suitable for this historical model.

Duplicate JSON keys return **422**, even when their values are identical or their names use equivalent Unicode escapes. Raw-body validation checks this before prediction, since normal dictionary parsing would silently keep only the last occurrence.

Technical input limits also reject oversized numbers with **422** before prediction: counts and years must fit nonnegative int64 (`2**63 - 1` maximum), and measurements are capped at `2**53 - 1`, float64's consecutive-integer precision limit. The measurement cap is a conservative application policy that also keeps degree-two products finite—not a realistic house-size limit or a guarantee of accurate predictions. A model may still reject an otherwise valid request or produce an unusable price.

### Supply or deliberately replace the model

`src/king_county/artifacts.py` pins the reviewed model version, SHA-256, and default export path. `MODEL_PATH` can point to another location containing **the same approved bytes**; `LOG_LEVEL` controls logging. No `.env` file is loaded automatically, and no environment setting overrides the approved checksum.

The approved artifact is intended to be versioned alongside the code so a fresh clone can start without training. To create a replacement, run the notebook, review its evaluation/export and redistribution suitability, then deliberately update `MODEL_VERSION`, `EXPECTED_MODEL_SHA256`, the exact `.gitignore` exception, and Compose's default model path together. A re-export may have a different checksum even with identical predictions. Never calculate and accept a new expected checksum automatically at startup. The model stays outside the Docker image and is mounted read-only at runtime.

### Prediction traceability

Traceability helps us answer: **“What happened to this prediction request?”** Each call to `/predict` gets a unique ID and a short record in the server terminal—even when the input is rejected.

| Recorded field | What it tells us |
|---|---|
| `request_id` | Which request we are looking at. |
| `timestamp` | When it started, in UTC. |
| `model_version` | Which loaded model handled the request. |
| `outcome` | Did it succeed, reject invalid input, or fail? |
| `status_code` | Which HTTP status started the response, such as 200 or 422. |
| `duration_ms` | How long the request took, in milliseconds. |

**Example:** someone reports a failed prediction. We take the `X-Request-ID` from their response headers and search the server logs for the same ID. This tells us which model was used, what happened, and how long it took. It does **not** tell us whether the predicted price was accurate.

To see the response headers, add `-i` to the example request:

```bash
curl -i -X POST http://127.0.0.1:7002/predict \
  -H 'Content-Type: application/json' \
  --data-binary @examples/house.json
```

We log **no house details, predicted prices, or exception text** in these trace records. The app writes them to standard logging, not a dedicated file or database; your terminal or hosting platform may retain them. Keep `LOG_LEVEL=INFO` to see them. Health checks and documentation visits do not create prediction records.

If processing is interrupted, the outcome is `failed` even if a 200 response had already started. No started response means `status_code` is `null`. Unexpected server errors may return a generic 500 without the request-ID header. See [the design notes](design.md#a-lightweight-audit-not-another-platform) for technical details.

The source supports optional bearer authentication for HTTP routes except `/health`;
cloud mode requires a token. See [private Codespaces development](codespaces.md)
for prerequisites and operating instructions. A private Codespace passed direct
health and prediction checks both directly and through a private browser port,
and was then stopped. This is a development workspace, not production hosting. Saving prediction
results remains deferred. Keep the local prototype bound to `127.0.0.1`.

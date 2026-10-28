# Notebook baseline (T05)

Before changing the code's structure, we need a reference for its behaviour. This baseline answers: **did our refactor change the prepared data?** It does not prove that every original rule is a good production rule.

## Files and how to run

| File | Purpose |
|---|---|
| `King-County.ipynb` | Original course notebook; not edited by T05. Its committed execution outputs are currently cleared. |
| `King-County-refactored.ipynb` | A 10-cell working copy using the cleaner and feature object in a preprocessing pipeline. No EDA or model training. |
| `src/king_county/cleaning.py` | Reusable sklearn-compatible cleaner; fixed rules, no row removal or learned values. |
| `src/king_county/features.py` | Fitted waterfront locations, shared distance calculation, and ordered model features. |
| `src/king_county/validation.py` | Separate input validators for cleaning and feature creation; neither changes supplied data. |
| `tests/fixtures/notebook_baseline.json` | Fixed expected outputs and feature order; no duplicate raw dataset. |
| `tests/notebooks/test_notebook_baseline.py` | Runs selected trusted preprocessing cells against controlled CSV rows. No training or model loading. |

From the project root:

```bash
uv run --locked pytest tests/notebooks/test_notebook_baseline.py
```

Open the working notebook with the project's `.venv` kernel and run it from the repository root. It processes the full CSV through the reusable preprocessing pipeline. Waterfront distances use array operations per reference rather than the original nested per-house loop. It does not write any model file.

Verification: all working-copy code cells ran against the full CSV in Python and produced **21,596 rows, 19 features, 146 waterfront reference houses, and no missing prepared values**. All 19 prepared columns also match the original preprocessing on the full retained dataset within the comparison tolerances below. Both controlled notebook snapshots match. No model was trained or loaded.

## The reference rules

Cell numbers below refer to the original notebook and include Markdown. The working copy records its remaining copied cells and shared pipeline steps in metadata for the comparison tests.

| Step | Original cells | Behaviour to preserve before intentional changes |
|---|---|---|
| Load | 8 | Read the bundled CSV: 21,597 rows and 21 columns. |
| Training-row exclusion | 29 | Drop row label `15856` (house ID `2402100895`, 33 bedrooms). This is CSV-specific, not a request-validation rule. |
| Basement | 31 | `sqft_living - sqft_above`. |
| Missing values | 36, 39 | Replace missing `view` and `waterfront` with 0. |
| Construction/renovation | 42–44 | Use `yr_built` when renovation is 0 or missing; otherwise use renovation year. Drop the two raw year columns. |
| Centre distance | 61 | Latitude `47.62774`, longitude `-122.24194`; preserve the separate cosine latitude `47.6219` and Earth radius `6378` km. Do not silently unify the latitudes. |
| Waterfront distance | 68–71 | Minimum distance to houses with `waterfront == 1`; preserve the formula and full-data reference selection for parity. The full CSV has 146 reference houses. |
| Input selection | 79–81, 102 | Exclude `price`, `sqft_price`, `date`, helper deltas, and `id`. Return the 19 features in the snapshot's order. |

The original `sqft_price` calculation is exploration-only and is not copied. It is never a model input. EDA charts, training experiments, evaluation, and saving stay in notebooks, not services.

## A small controlled comparison

The tests read CSV row labels **0, 1, 2, 7, 49, 230, and 15856**. The exclusion leaves six rows, covering missing waterfront/view values, missing or zero renovation years, actual renovations, and non-zero basement areas.

Only rows **49 and 230** are waterfront references in this comparison. Its frozen distances belong to this controlled two-reference example, **not** the full 146-reference dataset. Their self-distances are zero.

Tests compare six transformed columns, retained row labels, waterfront reference rows, and all 19 feature names in order. Float comparisons use `rtol=1e-10` and `atol=1e-8`, allowing rounding noise rather than a changed formula. A dataset SHA-256 detects source-data changes. Tests must never regenerate expected values automatically.

These tests temporarily execute selected cells from our own trusted notebooks. The working copy uses the cleaning/feature pipeline, while the original still runs inline preprocessing. The runner returns the same pair of results for both: prepared features and waterfront coordinates. Both are compared with the same frozen expectations. This is a baseline bridge, not the application's loading mechanism.

Pandas warnings about `DataFrame.drop(..., inplace=True)` remain visible in the unchanged original. The working copy and our transformers do not use `inplace`.

## Extracted cleaning

`HouseCleaner` applies the notebook's fixed cleaning rules and returns a new DataFrame. It preserves row labels and unrelated columns, including a training target if present. `fit` validates input but learns no means, medians, or references; `transform` applies the rules. Training-row filtering stays in the notebook and must never silently discard a prediction request.

Missing required columns, non-real cleaning values (including booleans and complex numbers), missing living/above-ground/build-year values, infinities, and inconsistent areas now raise clear errors. Years must also fit the output's signed 64-bit integer storage, rather than silently overflow or lose precision. This is a technical storage limit, not an invented range of plausible construction dates. Explicit null view/waterfront/renovation values follow the original fill/fallback rules. These checks are input safeguards, not new imputation rules or a replacement for the future API's Pydantic contract.

The checks live in `HouseDataValidator`, not in the cleaner. `HouseDataValidator(raw_data).validate()` runs the named checks in order and returns the numeric cleaning columns. Direct validator tests check failures and input preservation; cleaner tests check transformations and pipeline behaviour.

Boundary tests explicitly cover zero and just-negative areas, equality and values just above/below the living-area limit, finite floating-point extremes, and both infinities. They also cover year-storage boundaries, each nullable field, zero renovation, empty/single-house batches, and nonsequential/duplicate row labels. They do not invent maximum house sizes, plausible construction-year ranges, or API business rules that the cleaner does not implement.

## Extracted feature engineering

`HouseFeatureEngineer.fit()` stores a copy of waterfront longitude/latitude pairs from its supplied rows, not complete records or prices. `transform()` never refits or adds incoming waterfront houses to those references. It returns a new table with the canonical 19 feature names and preserves row labels. Extra columns and supplied distances are excluded or recalculated.

The centre and waterfront paths share `_distance_km()`. Their latitude corrections remain different, exactly as in the notebook. Each reference is compared with all query rows using NumPy, keeping temporary memory linear in the query count rather than allocating a full query-by-reference matrix.

`HouseFeatureValidator` requires the cleaned numeric inputs, finite values, and physical coordinate ranges (latitude +/-90, longitude +/-180). Missing columns and fitting without any waterfront house fail clearly; an empty transform batch is allowed after a successful fit. Tests cover those boundaries, input/reference preservation, feature order, pipeline cloning, and a held-out waterfront house whose distance must not become zero through self-reference.

For baseline parity, this notebook deliberately fits on all retained rows. For actual model evaluation, fit after the train/test split and inside each cross-validation fold. The feature object already supports that boundary; wiring it to model training and exporting its learned state belongs to T08. Do not claim the original R² for this changed training setup without evaluating it.

## Training settings recorded for T08

These remain notebook responsibilities; T05 regression tests do not run them:

| Setting | Original notebook |
|---|---|
| Target | Total sale `price`, in US dollars. |
| Split | `test_size=0.3`, `random_state=42`; 15,117 training and 6,479 test rows after exclusion. |
| Final pipeline | Degree-2 polynomial features (`include_bias=False`), `StandardScaler`, then target-scaled `ElasticNet`. |
| Tuning | Five-fold `GridSearchCV`, scoring `r2`; alpha `[0.01, 0.1, 1]`, L1 ratio `[0.2, 0.5, 0.8]`. |
| ElasticNet | `max_iter=5000`, `tol=1e-4`, `precompute=True`. |
| Earlier saved run | Adjusted R² `0.43`, `0.48`, `0.75`; final ordinary test R² `0.844`, winning alpha `0.01` / L1 ratio `0.2`. These were recorded during an earlier review, not reproduced by T05 or currently visible in the cleared outputs. |
| Existing artifact | Local `model/model.bin`, SHA-256 `2ba5c24e79ec5563ef40420870a22ae2c8d6300a2afa097c05ea7bf3493359de`; do not overwrite it. |

## Intentional changes stay separate

- Later, fit waterfront references inside training, including within validation folds. Evaluate this change separately rather than promise the original score.
- Replacing the fixed row exclusion needs an agreed rule and separate tests. Never silently remove prediction rows.
- Faster distance calculations must match controlled outputs before replacing the loop.
- T08 will connect notebook modelling to our reusable classes. The app loads the exported pipeline, not a training service.

See [the design](design.md) and [tasks](../tasks.md).

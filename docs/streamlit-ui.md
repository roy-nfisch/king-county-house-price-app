# Streamlit prediction UI

From a checkout with Python 3.13.17 or a newer 3.13 patch and uv 0.13.5 or
newer, run:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui streamlit run src/king_county/streamlit/app.py --server.address 127.0.0.1
```

The form uses the checked-in `examples/house.json` as its starting point. ZIP
is a five-digit string, including leading zeroes; waterfront, view and year
renovated can be unknown. Numeric widgets cap non-coordinate values at one
billion for practical browser input, a narrower range than the API schema.
The shared Pydantic contract also checks relationships such as above-ground
area not exceeding living area. A result shows USD and the model version.

The UI reads the approved artifact at the repository's fixed
`model/versions/king-county-20261028T153712021211Z/pipeline.skops` path. It
verifies the code-pinned checksum before loading and reuses the service within
the user's session. A missing, altered or incompatible artifact produces an
error; there is no upload, automatic download, retraining, or approval by the
UI. Restart the session after replacing the model with an approved version.
The artifact and example are checkout assets, not included in the wheel.

Run UI checks with `uv run --locked --extra ui pytest tests/king_county/streamlit/`. Other tests
can run without this extra; UI tests then explicitly skip. The API Docker image
does not install the optional UI dependency.

The merged [Codespaces setup](codespaces.md) has been verified for the API.
The Streamlit UI has only been verified locally, not hosted. To try it in the
existing Codespace, first review access and remaining included allowance, then
install the UI extra and run:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui streamlit run src/king_county/streamlit/app.py --server.address 0.0.0.0
```

Keep forwarded port 8501 **private** and check its visibility before opening
the app. The all-interface bind is for the Codespace, not a public deployment.
Port 8501 is separate from the API's port 8000 and must be forwarded manually.
`API_MODE` and `API_TOKEN` protect FastAPI only: this UI calls the Python service
directly and has no application login. Keep local access on `127.0.0.1` and
Codespaces access behind its private GitHub tunnel. Do not expose the UI publicly.
Before activation, confirm costs, access, secrets, compatible Python and the
availability of the exact approved model and example at the checkout paths.
Check Streamlit's [supported Python versions](https://docs.streamlit.io/knowledge-base/using-streamlit/sanity-checks)
again at deployment time. Confirm redistribution permission for the dataset
and retained model coordinates before publishing them; the software license
and checksum do not establish those rights. Do not publish or deploy until
those choices and permissions are resolved. Community Cloud has not been used.

## Independent audit

The Streamlit implementation was independently audited by GPT-6.1 Sol. The audit
found the verified loading and validation boundary sound, and requested clearer
page ownership and tests for nullable fields, leading-zero ZIP codes, altered
model bytes, and invalid bundled examples. The page now owns its fixed paths
and session service wiring, and those cases have regression coverage. The final
local checks passed 467 non-Docker tests and 7 Docker integration tests across
runs; lint, formatting and package build also passed. The reviewer reran the
eight UI tests and lint independently. These counts describe the original
implementation, before rebasing; the current local review is recorded below.

## Review with house records and Codespaces support

Rebased onto `main` at `03bf21d`, preserving the separate house-record package,
API authentication, date-based API version and verified Codespaces instructions.
The shared prediction service remains unchanged; the UI does not use the CRUD
database or API routes. The UI lives under `src/king_county/streamlit/`:
`app.py` starts the page and `page.py` owns its form and service wiring.
Tests mirror that layout under `tests/king_county/streamlit/` and reuse the
existing root fixtures. CI selects these tests by their integration marker,
so no workflow-path change is needed.

The review tightened form-to-service value checks, compares the displayed price
with the shared service, and covers missing/malformed bundled example files.
No UI deployment or new model approval was performed. The rewritten branch must
be pushed with a lease and pass CI again before merge.

Local verification passed 555 non-Docker tests, eight Docker integration checks,
Ruff, formatting and the package build. Three existing pandas warnings come from
the unchanged original notebook. The real browser form returned **$323,409.49
USD** for the bundled example using the approved model. The runtime image still
installs only base dependencies, without Streamlit. Original notebook, dataset
and approved model files are unchanged.

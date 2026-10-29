# Streamlit prediction UI

From a checkout with Python 3.13.17 or a newer 3.13 patch and uv 0.13.5 or
newer, run:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui streamlit run src/streamlit_app.py --server.address 127.0.0.1
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

Run UI checks with `uv run --locked --extra ui pytest tests/king_county/test_ui.py`. Other tests
can run without this extra; UI tests then explicitly skip. The API Docker image
does not install the optional UI dependency.

GitHub Codespaces is the selected hosting direction; no hosted environment has
been activated for this UI. Once the separately developed T15 Codespaces
configuration is merged and its access is reviewed, install the UI extra in
that checkout and run:

```bash
uv run --locked --extra ui streamlit run src/streamlit_app.py --server.address 0.0.0.0
```

Keep forwarded port 8501 **private** and check its visibility before opening
the app. The all-interface bind is for the Codespace, not a public deployment.
Before activation, confirm costs, access, secrets, compatible Python and the
availability of the exact approved model and example at the checkout paths.
Check Streamlit's [supported Python versions](https://docs.streamlit.io/knowledge-base/using-streamlit/sanity-checks)
again at deployment time. Confirm redistribution permission for the dataset
and retained model coordinates before publishing them; the software license
and checksum do not establish those rights. Do not publish or deploy until
those choices and permissions are resolved. Community Cloud has not been used.

## Independent audit

The T15a implementation was independently audited by GPT-6.1 Sol. The audit
found the verified loading and validation boundary sound, and requested clearer
page ownership and tests for nullable fields, leading-zero ZIP codes, altered
model bytes, and invalid bundled examples. The page now owns its fixed paths
and session service wiring, and those cases have regression coverage. The final
local checks passed 467 non-Docker tests and 7 Docker integration tests across
runs; lint, formatting and package build also passed. The reviewer reran the
eight UI tests and lint independently. GitHub CI remains pending.

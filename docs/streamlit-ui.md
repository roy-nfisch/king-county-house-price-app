# Streamlit house-price app

A local form for estimating a King County house price with the saved model.
It calls the shared Python prediction service directly—no API server or
training is needed. This historical educational model is not a professional
valuation tool.

## Run locally

From the repository root, with Python 3.13.17 or a newer 3.13 patch and uv
0.13.5 or newer:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui streamlit run src/king_county/streamlit/app.py --server.address 127.0.0.1
```

Open [localhost:8501](http://127.0.0.1:8501). Stop the server with Ctrl+C.
The API Docker image does not include Streamlit; run this interface from a
checkout with the `ui` extra installed.

## Use the form

The form starts with `examples/house.json`. Adjust House details, Property
size, Location and Optional information, then select **Estimate price**.
The result shows the estimated total price in USD and the model version.
The unchanged example returns approximately **$323,409.49**.

- All 17 raw fields are supplied; select **Unknown** for unavailable waterfront,
  view or renovation-year values. These become `None`, following the model's rules.
- ZIP codes contain five digits and retain leading zeroes.
- Areas are in square feet; above-ground area cannot exceed living area.
- Non-coordinate numeric inputs range from zero to one billion for browser
  usability. This is an input limit, not a claim that such values are realistic.
- Invalid inputs show an error before prediction. In-range inputs do not
  guarantee the model is suitable for a particular house or location.

## Model and files

The checkout must include `examples/house.json` and the approved artifact:

```text
model/versions/king-county-20261028T153712021211Z/pipeline.skops
```

The service checks the code-pinned checksum before loading and reuses the
verified model within each browser session. Missing or altered files produce
an error; the UI cannot upload, download, train or approve a replacement.
Restart the server after deliberately approving and installing a new version.
These files are checkout assets, not included in the Python wheel.

`app.py` starts the interface, `HouseForm` collects inputs in `form.py`, and
`HousePricePage` in `page.py` handles validation, session reuse and results.
Tests mirror this layout under `tests/king_county/streamlit/`.

## Run the UI tests

```bash
uv run --locked --extra ui pytest tests/king_county/streamlit/ -q
```

The integration tests cover field forwarding, layout, predictions, session
isolation, checksum failures and safe errors. Without the `ui` extra, these
tests skip; CI installs the extra so they run.

## Private Codespaces access

The UI is verified locally, not hosted. For a private demo, follow the
[Codespaces guide](codespaces.md), install the `ui` extra, and start:

```bash
uv run --locked --extra ui streamlit run src/king_county/streamlit/app.py --server.address 0.0.0.0
```

Manually forward port **8501** and confirm its visibility is **Private** before
opening it. Stop the Codespace afterwards to conserve allowance.

The UI has **no login**. `API_MODE` and `API_TOKEN` protect FastAPI, not this
interface. Keep local access on `127.0.0.1` or use the private GitHub tunnel;
do not expose the UI publicly. Dataset/model redistribution permission must be
resolved before broader publication. No Streamlit Community Cloud deployment
is configured.

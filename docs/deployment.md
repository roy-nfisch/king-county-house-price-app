# Private GitHub Codespaces deployment

This is a private, manually started development environment, not an always-on
production service. No Codespace has been created or verified by this change.
The repository's dev container installs the locked dependencies with uv 0.13.5;
it does not start the server automatically. The existing tracked model is loaded
from the checkout and verified against the checksum and trusted types in code.
No model is baked into a public image or downloaded from an unverified source.
House CRUD records use SQLite in the Codespace checkout by default; they are
separate from predictions and persist with the Codespace until removed. Treat
them as private data, review retention, and do not commit the database. Stopping
the Codespace retains them; deleting it can permanently remove them. Back up
needed records securely before deletion.

## Before creating a Codespace

- [ ] Approve the candidate two-core machine in Europe West, private port, and
  30-minute idle timeout. The creation screen identifies `roy-nfisch` as payer;
  confirm a budget and available included usage before creation. Running compute
  and stored work can incur charges;
  [GitHub explains usage and billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces).
- [ ] Confirm permission to host the tracked model, including its retained
  training coordinates, in the chosen GitHub account and region. The model's
  data provenance remains unresolved; the software license does not settle it.
- [ ] Decide who may access the service. A private forwarded port is only for
  the Codespace creator, not a shared production endpoint. Do not change it to
  organization or public visibility without a separate security review.

## Start and verify

After the prerequisites are approved, create a Codespace for the reviewed branch
using this repository's dev container. Wait for `postCreateCommand` to complete.
In its terminal, run:

```bash
uv run --locked uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8000
```

The dev container forwards port 8000. GitHub makes forwarded ports **private by
default**, but explicitly inspect the Ports tab and confirm visibility is Private
before accessing it. From a trusted local terminal with GitHub CLI authenticated
as the Codespace creator, the visibility can also be set and inspected with:

```bash
gh codespace ports visibility 8000:private -c CODESPACE_NAME
gh codespace ports -c CODESPACE_NAME
```

Replace `CODESPACE_NAME` with the actual name. Private forwarded ports require
GitHub authentication; see [GitHub's security documentation](https://docs.github.com/en/codespaces/reference/security-in-github-codespaces).
The server binds inside the container; do not use a public port. The default
local API has no application-level authentication and relies here on the private
Codespaces tunnel. Treat access to the Codespace itself as privileged.

In a second Codespace terminal, check the server directly without forwarding:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' --data-binary @examples/house.json
```

The first response reports ready and the loaded model version; the second has a
predicted price, currency, and model version. The model must pass startup checks;
do not bypass them. Confirm both results through the private forwarded port too,
using a GitHub-authenticated browser or a locally forwarded port. Avoid placing
credentials or sensitive input in URLs, shell history, or logs.

Stop the server with Ctrl+C and explicitly stop the Codespace when finished;
closing the browser does not stop it. Stopped Codespaces can still incur storage
charges. See [stopping a Codespace](https://docs.github.com/en/codespaces/developing-in-a-codespace/stopping-and-starting-a-codespace)
and review the configured idle timeout and storage retention.

## Optional application token

For an additional API layer, set `API_MODE=cloud` and `API_TOKEN` in the server
process environment before starting it. Generate a high-entropy URL-safe token
using a secure secret manager or `secrets.token_urlsafe(32)` in a private
context, without printing or saving it to shell history. Cloud mode rejects a
missing, malformed, or shorter-than-32-character token. Length is not proof of
entropy. Never commit or place it in URLs, logs, or tickets. `/health` remains
public and reports only `{"status":"ready"}`; all other HTTP routes, including
docs and prediction, require `Authorization: Bearer <token>`. The server does
not automatically load `.env`. A shared token is not per-user authorization,
rate limiting, or a substitute for keeping the port private. Restart the server
with a new secret and update clients to rotate it.

## Completion checklist

- [ ] Verify actual Codespace creation, cost controls, private port visibility,
  approved model access, startup, health and prediction.
- [ ] Record the owner, stop/cleanup procedure and any intended access policy.

T15 remains open until those live checks pass. The existing public GHCR image
predates authentication and is not a substitute for this private environment.

## Preparation review

The implementation was independently reviewed by GPT-6.1 Sol. The review found
that cloud mode accepted a weak short token and that the application factory had
grown too long. Cloud mode now requires at least 32 token characters, and the
model lifespan was extracted from the factory. Length alone does not guarantee
entropy. The reviewer independently built the development image and verified
Python 3.13.18 and uv 0.13.5 in it, and ran the focused authentication and
dev-container checks. This does not establish a successful Codespace deployment.

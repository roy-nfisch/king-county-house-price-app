# Containers and image releases

Run commands from the repository root with Docker running. For a short local
startup, see the [README](../README.md#run-with-docker-compose).

## Run with Docker Compose

From the project root, with Docker running and the approved local model available:

```bash
docker compose up --build --wait
curl http://127.0.0.1:7003/health
curl -X POST http://127.0.0.1:7003/predict \
  -H 'Content-Type: application/json' --data-binary @examples/house.json
docker compose logs api
# Stop this project's container when finished:
docker compose down
```

Open [Docker API docs](http://127.0.0.1:7003/docs). Host port **7003** forwards to **8000 inside the container**; the API listens on all container interfaces, but Compose publishes it only on localhost. If 7003 is busy, use `API_PORT=7004 docker compose up --build --wait` and change the curl/browser port accordingly.

The non-root runtime contains the installed package and locked runtime dependencies, not the CSV, notebooks, tests, model, or stored records. Compose mounts the approved artifact read-only at `/models/pipeline.skops` and keeps SQLite records in a named volume. No external database, training service, or API key is needed. The health check succeeds only after startup loads the model and initializes storage. A missing host file fails the mount; changed/unapproved bytes fail application startup. Check `docker compose logs api` if startup fails.

To relocate the same approved model, set `MODEL_FILE=/absolute/path/pipeline.skops` before the Compose command. This changes only the host file location, **not** its trusted checksum. The default image command performs the usual code-pinned verification; no new checksum environment override is provided.

For test commands and container-test design, see [testing and CI](testing.md#container-integration-checks).

## Run the published image

The corrected `2026.10.29.1` image includes the project's MIT notice and is
publicly downloadable. The old `2026.10.29` version and its associated manifests
were removed rather than overwritten. No GitHub account, token, or Docker login
is needed to pull the public image.

You need Docker running and a checkout of this repository with the approved model. No local Python install
or model retraining is needed. Run these commands from the project root.

**1. Pull and start the verified image.** This digest pins the exact corrected image;
the `2026.10.29.1` and `latest` tags currently point to it. The image is Linux amd64,
so an ARM Mac uses Docker's amd64 emulation. The model stays outside the image.

```bash
KING_COUNTY_IMAGE=ghcr.io/roy-nfisch/mle-refactoring-project@sha256:95bf5253cc3a7288651876e7abbcb70df933b7c3d16ce100d3421a9726ad672f
docker pull --platform linux/amd64 "$KING_COUNTY_IMAGE"
docker run --rm --platform linux/amd64 -p 127.0.0.1:7003:8000 \
  --mount "type=bind,source=$(pwd)/model/versions/king-county-20261028T153712021211Z/pipeline.skops,target=/models/pipeline.skops,readonly" \
  "$KING_COUNTY_IMAGE"
```

**2. Check it in another terminal**, also from the project root, once startup
finishes. Keep the first terminal running. Open <http://127.0.0.1:7003/docs> or:

```bash
curl --fail http://127.0.0.1:7003/health
curl --fail http://127.0.0.1:7003/predict \
  -H 'Content-Type: application/json' --data-binary @examples/house.json
```

Prediction returns `predicted_price`, `currency`, and `model_version`. Press
Ctrl+C in the first terminal to stop; `--rm` removes that container. If port 7003
is occupied, change only the host port (for example, `7004:8000`) and use that
port in the URLs. A missing model or checksum mismatch stops startup; do not
bypass the approval check. If stale saved GHCR credentials cause an authentication
error, try pulling with an empty temporary Docker configuration instead of
creating a token. Keep the repository/model files separate from that configuration.

The image contains no model or dataset. Their redistribution permissions remain
an open provenance review item; public runtime publication does not establish
permission to redistribute the data or the model's retained training coordinates.

## Publish to GitHub Container Registry

The corrected [publication run](https://github.com/roy-nfisch/mle-refactoring-project/actions/runs/40792312600) passed from `main` at commit `563785d`. It published `2026.10.29.1`, `sha-563785d9d511184024db99b9490bdd05896c4711`, and `latest`. All 466 tests passed, including the complete MIT notice check in the container. Post-publish health, prediction, digest pull, and image identity checks also passed; no API was deployed. See the [image page](https://github.com/roy-nfisch/mle-refactoring-project/pkgs/container/mle-refactoring-project).

For a future release, open **Actions → Publish API image → Run workflow**, select `main`, and enter a new version using `YYYY.MM.DD`. For another release on the same date, append `.1`, `.2`, etc. Dates must be real calendar dates with two-digit months/days, and an optional suffix must be a positive integer without leading zeros. Pushes and pull requests do not publish images, and a manual run from another branch is rejected.

The workflow builds and tests the image, transfers that exact image between jobs, and checks its image ID before publishing. Only the publishing job has `packages: write`; authentication uses GitHub's short-lived `GITHUB_TOKEN`, not a personal token stored in this repository. The version is the image tag: `ghcr.io/roy-nfisch/mle-refactoring-project:2026.10.28` (or the selected date/suffix). It also publishes a `sha-<full-commit>` tag and updates `latest` only after post-publish health and prediction checks pass. `latest` means the last successfully verified manual publication, not necessarily the highest date tag. The workflow does not change package visibility. New GHCR packages default to private; review package access settings before sharing, even when the repository is public. See [GitHub's registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

Before pushing, an authenticated registry check rejects an existing version tag. Only an explicit missing-manifest/name response permits publication; authentication, network, malformed-response, and other registry errors stop the job. Workflow runs are serialized, but this is not registry-enforced immutability: someone publishing outside this workflow could still change a tag.

After pushing, it pulls by registry digest and checks health and prediction with the approved model mounted read-only. HTTP checks have a five-second connection timeout and a 15-second total timeout per request. The run summary records the digest reference. Publishing creates a downloadable image, not a hosted API. If post-push verification fails, the workflow fails but does not automatically delete already-pushed tags. Choose a new version for the next attempt rather than overwriting an existing tag.

# Final review

Review date: 29 October 2026. Base: merged `main` at `ccf0f90`.
The review and license fix merged in PR #14 at `563785d`. Release documentation
continues on `docs/public-image-release`; those documentation changes remain uncommitted.

## Independent audit

- Implementer: GPT-6.1 Sol.
- Independent reviewer: GPT-6 Astra, high effort, read-only audit.
- Follow-up reviewer: GPT-6.1 Terra, high effort, read-only audit. Four package
  tests passed; the only finding was stale uncommitted-state wording, corrected here.
- Scope: course task, simple OOD, code correctness, input contracts, model
  loading, packaging, tests, documentation, and public-image readiness.
- Assessment: small focused objects, composition, thin API routes, and no
  request-time training are appropriate. No application redesign was needed.

## Findings and changes

| Finding | Action | Status |
|---|---|---|
| The first image lacks the project's MIT notice. | Declare `license`/`license-files`, allow `LICENSE` into the build context, and include it in builder inputs. The built wheel carries the original notice into the installed runtime package. | Merged in PR #14 and verified in release `2026.10.29.1`. |
| License-file layout differs for editable development installs. | Check metadata in development; check full license text in the actual non-editable Docker runtime. | Regression checks added. |
| Docker/future-app wording was stale. | Correct the README and existing Stage 2 TODO description. | Updated. |
| Making a GHCR package public exposes old versions too. | Remove the old deficient version and its platform/attestation manifests with explicit approval before changing visibility. | Corrected package is public; anonymous pulls pass and old references are unavailable. |
| Dataset/model redistribution permission is not established by the software license. | Keep the caveat visible. The model retains 105 training coordinate pairs and stays outside the image. | Requires provenance/permission evidence; no clearance claimed. |

The audit caught the editable-install test assumption; we adjusted that test
instead of changing development installation behaviour. A second model can
find mistakes, but is not a replacement for executing checks.

## Verification evidence

- Isolated clone of merged `main`: locked install and package build succeeded;
  457 tests passed and six Docker cases skipped without a selected image.
- The new Docker license regression intentionally fails against the old local
  image, confirming it detects the missing notice.
- The built wheel contains the original `LICENSE` text and MIT license metadata.
- Corrected local image: all **466 tests passed**, including seven Docker
  integration cases; three existing original-notebook warnings remain. Lint,
  formatting, package build, Compose validation, local documentation links,
  README shell syntax, and diff checks passed.
- The independent reviewer checked the adjusted delta and reran four package
  tests successfully; no remaining defect was found in those changes.
- Independent audit: 139 schema/contract tests passed; the unchanged approved
  artifact loaded and the example returned a positive USD price.
- Targeted secret-pattern checks found no common GitHub/AWS credential or private
  key signatures in the tracked tree or 43 commits reachable from local refs.
  No tracked environment files, caches, or generated model sidecars were found.
- [Merged-main CI](https://github.com/roy-nfisch/mle-refactoring-project/actions/runs/40792031928)
  passed with the license fix and PDF at `563785d`. The release-documentation
  branch has not been committed or pushed.

These are targeted checks, not a comprehensive secret scan, vulnerability scan,
legal review, or proof that the model is accurate on future house sales. The
model, original notebook, and CSV must stay unchanged during this review.
Git diff confirms all three remain unchanged.

## Public image hand-off

Release `2026.10.29.1` passed [publication 40792312600](https://github.com/roy-nfisch/mle-refactoring-project/actions/runs/40792312600)
from `563785d`: all 466 tests, license notice, image identity, digest pulling,
health, and prediction checks passed. `latest` points to the corrected digest
`sha256:95bf5253cc3a7288651876e7abbcb70df933b7c3d16ce100d3421a9726ad672f`.
The workflow removed its temporary verification container; no API was deployed.

With explicit approval, the old release `2026.10.29` and its two associated
manifests were removed before the package became public. Anonymous checks used
an empty temporary Docker credential folder, without changing the user's saved
login: version tag, `latest`, and corrected digest all pulled successfully.
The downloaded image contains the complete original MIT notice. The old tag,
index digest, platform digest, and attestation digest all return missing-manifest
errors. The corrected version and its two associated manifests remain intact.

The engineering review and runtime release are complete. The separate
dataset/model provenance question remains unresolved in `tasks.md`; no legal
redistribution clearance is claimed. Local release checks ran only a temporary
Python process to inspect the installed license, not an API server.

Public download does not deploy the API. Users still need the approved model
mounted read-only; no model, data, or credentials should be baked into the image.

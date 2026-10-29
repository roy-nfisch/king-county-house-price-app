# Final review

Review date: 29 October 2026. Base: merged `main` at `ccf0f90`.
Working branch: `feature/final-review`. Changes are not committed or published.

## Independent audit

- Implementer: GPT-6.1 Sol.
- Independent reviewer: GPT-6 Astra, high effort, read-only audit.
- Scope: course task, simple OOD, code correctness, input contracts, model
  loading, packaging, tests, documentation, and public-image readiness.
- Assessment: small focused objects, composition, thin API routes, and no
  request-time training are appropriate. No application redesign was needed.

## Findings and changes

| Finding | Action | Status |
|---|---|---|
| The first image lacks the project's MIT notice. | Declare `license`/`license-files`, allow `LICENSE` into the build context, and include it in builder inputs. The built wheel carries the original notice into the installed runtime package. | Fixed locally; needs review, CI, and a new image release. |
| License-file layout differs for editable development installs. | Check metadata in development; check full license text in the actual non-editable Docker runtime. | Regression checks added. |
| Docker/future-app wording was stale. | Correct the README and existing Stage 2 TODO description. | Updated. |
| Making a GHCR package public exposes old versions too. | Keep the current package private. Before public access, approve removal of the old deficient version, or use a separate public package containing only corrected images. | Release decision pending; no version deleted. |
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
- Merged-main CI passed before these local fixes. New branch CI still requires
  a commit/push, which has not been authorised.

These are targeted checks, not a comprehensive secret scan, vulnerability scan,
legal review, or proof that the model is accurate on future house sales. The
model, original notebook, and CSV must stay unchanged during this review.
Git diff confirms all three remain unchanged.

## Public image hand-off

Do not overwrite `2026.10.29` or pretend source changes repair its digest.
After review and merge, publish a corrected version such as `2026.10.29.1` and
verify its license notice, digest, health, and prediction. Resolve the old-version
visibility decision before exposing the package. Then verify anonymous pulling
and update the README to the new digest and no-login instructions.

Public download does not deploy the API. Users still need the approved model
mounted read-only; no model, data, or credentials should be baked into the image.

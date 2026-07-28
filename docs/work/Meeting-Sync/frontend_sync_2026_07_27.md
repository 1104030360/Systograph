# Systograph Frontend Sync - v2 integration, rename, and issue triage

Status: ready for PR and merge; automated validation and browser QA complete

Branch: `feature/v2-frontend-integration`

## Scope

- Integrate the current `ai-system-map/v2` project/build-scoped frontend flows.
- Keep Profile and Readiness facts backend-owned and build-scoped.
- Integrate Detail Scan child builds, Mapping Proposal/Apply, Query Trace, and build history.
- Use **Systograph** consistently as the user-facing product name.
- Finalize the DeepResearch-style three-column workspace:
  - remove the redundant normalized-map title block and move Reset View to the top toolbar;
  - keep the 10-plane architecture map as the central, backend-driven surface;
  - place Query Trace behind a `Details / Query Trace` switch in the right panel;
  - replace compressed CSS-drawn Filter marks with bounded, scalable semantic SVG glyphs;
  - let Mapping Profile and Readiness callouts scroll normally instead of obscuring content;
  - dismiss toolbar menus when focus moves to another surface.
- This integration PR changed product-facing branding only. The later hard-cutover
  migration owns package, CLI, state, schema-ID, and repository identifiers.

The primary CLI command is `systograph`. Query Trace reads
`[tool.systograph.trace]`.

## Checkout and external reference submodule

`ref-opensource/Understand-Anything` is an external reference project tracked as a Git submodule. The
current checkout is populated and pinned at `73559a160645359c57be44c174935899dec9f9f2`.

After cloning or pulling this repository, initialize or refresh it with:

```powershell
git submodule update --init --recursive
```

Alternatively, pull the repository and submodules together:

```powershell
git pull --recurse-submodules
```

The Systograph application can update without the submodule, but the reference directory may otherwise
be empty or remain on an older pinned revision.

## Timmy backend changes already consumed

- `0e48727`: shared index and rich graph projection.
- `70e7f89`: TOML-backed profile catalog and deterministic profile projection.
- `0a68ccd`: active v2 cutover, immutable build lineage, and atomic 10-artifact publication.
- Current project/build APIs for Viewer, Apply, Detail Scan, Mapping, Trace, Profile, and Readiness.

The remaining newly available frontend feature is Inventory Preflight / one-run inventory selection from
`e10f737`. It will be implemented after this integration branch merges.

## Artifact API boundary

Atomic publication of 7 JSON + 3 render artifacts is a backend storage guarantee, not a browser fetch
contract. Current `GET /api/map-builds/{build_id}` does not return safe `artifact_refs`, and no controlled
build-scoped artifact fetch route exists. `GET /api/map/report` is session-latest only.

The Readiness dialog therefore generates a clearly labelled Markdown view from the inline
`readiness_report` payload. It must not claim to preview or download the persisted `.md` artifact.

## Old PR disposition

| PR | Current state | Disposition |
| --- | --- | --- |
| #198 Detail Scan | closed, unmerged | Superseded by the current build-scoped Detail Scan implementation. |
| #199 Mapping Proposal | closed, unmerged | Superseded by the current v2 proposal/decision/Apply implementation. |
| #218 Query Trace | closed, unmerged | Superseded by the current build-bound Query Trace implementation. |
| #227 Artifact Actions | closed, unmerged | Keep closed; server-local path loading is not part of the safe project flow. |
| #252 10-plane Viewer | open draft | Close as superseded only after the new integration PR is opened. |

## Old issue triage

Close as completed/superseded after the integration PR merges:

- #53 Viewer backend integration
- #54 and #78-#80 Query Trace frontend
- #55 and #81-#83 Detail Scan frontend
- #56 and #84-#86 Mapping Proposal frontend
- #74 Viewer API contract alignment

Keep open:

- #123 Project Mapping Profile Page: broader product page for persisted mappings and decision history;
  the current read-only Profile dialog does not complete it.
- #179 Typed interactive lifecycle schemas: Detail/Proposal are typed, but Inventory Preflight and the
  final scan-selection lifecycle remain.
- #185 Evidence code preview drawer: blocked on a bounded, masked evidence-snippet API.
- #219 Artifact actions: rewrite around a future safe build-scoped artifact API; do not restore the old
  server-local path acceptance criteria.
- #231 API test/fixture realignment: substantially covered by this branch, but keep open through live
  backend E2E and Inventory Preflight.
- #241 Static execution map and #242 typed runtime component trace: backend work remains open.
- #243 AssessmentOrchestrator candidate flow: explicitly deferred.

No GitHub issues were closed or edited during this triage.

## Validation

- Frontend tests: 35 files / 160 tests passed.
- Frontend lint: 0 errors; one pre-existing `BoundaryDecisionModal` Fast Refresh warning.
- Frontend build: passed (`tsc -b && vite build`); existing `web-worker` external warning remains.
- Rename-specific backend tests: 64 passed.
- Python lint/format: passed for the modified runtime and test files.
- `git diff --check`: passed.
- Full pre-commit hooks on Windows/Python 3.14:
  - `ruff check --fix` and `ruff format`: passed;
  - `mypy`: blocked by three existing non-Windows attributes (`os.O_NOFOLLOW`, `os.O_DIRECTORY`,
    and `os.mkfifo`) in Inventory Preflight code/tests;
  - full `pytest`: 977 passed, 51 failed, 8 skipped. Failures are the existing Windows
    Inventory Preflight safe-open/fixture baseline and downstream build-binding fixtures, outside this
    frontend/rename diff. Scoped modified-runtime tests remain green.
- Browser QA at 1280x720:
  - central title block absent and Reset View restores Overview, clears search and clears selection;
  - `Details / Query Trace` tabs are keyboard-accessible and Query Trace remains within the right column;
  - all 16 Filter icons stay inside their 23x23 tile with a 14x14 SVG glyph;
  - right panel has no horizontal overflow;
  - Mapping Profile `Validated sidecar` and the Readiness Markdown notice scroll out normally.

## Known limitations and post-merge QA

- A successful live Query Trace still needs a scanned project whose build publishes a callable endpoint
  accepted by the backend egress policy. The repository's current safe sample does not provide that
  happy-path endpoint.
- Live backend exercises for Detail Scan, Mapping Apply, Query Trace, and historical/stale build conflict
  handling remain useful post-merge smoke QA. Contract, controller, component, stale-response, partial,
  timeout, and preservation behavior are covered by the frontend/backend scoped suites in this branch.
- A reusable Playwright/API harness should be implemented separately on `test/v2-backend-e2e`; it should
  not be mixed into the Inventory Preflight feature.

## Handoff

- Implement Inventory Preflight UI after this branch merges, on `feature/inventory-preflight-ui`.
- Ask the backend owner to freeze `ArtifactRef`, scope checks, and controlled fetch routes before adding
  build-scoped report or artifact download actions.
- Run live backend smoke QA when a safe callable Query Trace fixture is available.
- Do not rename `systograph`, existing schema IDs, persisted state paths, or the GitHub repository with a
  blind text replacement; each requires an explicit compatibility/migration plan.

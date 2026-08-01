# Systograph Frontend Sync - product identity hard cutover

Status: ready for PR review; scoped validation complete

Branch: `feature/systograph-hard-cutover`

## Scope

- Make **Systograph** the only active product and technical identity.
- Rename the Python package from `kai_mind` to `systograph`.
- Keep only the `systograph` CLI entry point; no legacy CLI or import alias remains.
- Move runtime configuration to the Systograph namespace:
  - `SYSTOGRAPH_STATE_DIR`
  - `~/.systograph`
  - `[tool.systograph.trace]`
  - Systograph-prefixed NVIDIA NIM proposal settings
- Move JSON Schema IDs to `https://systograph.local/schemas/`.
- Rename active scripts, examples, tests, documentation, reference files, and repository links.
- Add an identity contract test and a hard-cutover migration guide.
- Update the 23 open GitHub issues that still referenced the previous product identity,
  package paths, or CLI commands.
- Fix the three Windows mypy baseline errors without weakening Inventory
  Preflight filesystem safety:
  - carry validated POSIX file and directory flags through a typed immutable
    bundle instead of accessing POSIX-only `os` attributes after the runtime
    guard;
  - fail closed with `safe_open_unavailable` when either required primitive is
    absent;
  - narrow `os.mkfifo` to a local callable inside the FIFO test and skip at
    runtime when unavailable.

This is an intentional breaking cutover. It does not provide compatibility
aliases or automatically discover state stored under the previous default
directory.

## Canonical identifiers

| Surface | Identifier |
| --- | --- |
| GitHub repository | `1104030360/Systograph` |
| Python distribution | `systograph` |
| Python import | `systograph` |
| CLI | `systograph` |
| State environment variable | `SYSTOGRAPH_STATE_DIR` |
| Default state directory | `~/.systograph` |
| Trace configuration | `[tool.systograph.trace]` |
| Schema authority | `https://systograph.local/schemas/` |

The artifact contract names `ai-system-map/v1` and `ai-system-map/v2` remain
unchanged because they are schema-version identifiers rather than product
names.

## Repository and submodule

The GitHub repository has been renamed to `1104030360/Systograph`, and the
local `origin` now uses:

```text
https://github.com/1104030360/Systograph.git
```

`ref-opensource/Understand-Anything` remains an external Git submodule pinned
at `73559a160645359c57be44c174935899dec9f9f2`.

After cloning or pulling, initialize or refresh it with:

```powershell
git submodule update --init --recursive
```

## Validation

- `uv sync`: passed; the editable installation uses the `systograph`
  distribution.
- Python import and CLI smoke checks: passed.
- Python package build: passed; produced the Systograph wheel and source
  distribution.
- Ruff format/check: passed.
- Windows `uv run mypy src tests`: passed with no issues in 312 source files.
- Required POSIX primitive fail-closed tests: 2 passed.
- Secret masking regression check: passed after correcting the hard-cutover
  test expectation to the existing four-character prefix contract.
- Rename and contract-focused backend suites: 94 passed in the final scoped
  run.
- Frontend tests: 35 files / 160 tests passed.
- Frontend lint: 0 errors; one pre-existing `BoundaryDecisionModal` Fast
  Refresh warning remains.
- Frontend build: passed; the existing `web-worker` external warning remains.
- `git diff --check`: passed.
- Active tracked text and path scan: no previous product identifier remains.
- Open GitHub issue scan: no previous product identifier remains.

Full Windows/Python 3.14 baseline:

- normal `pre-commit run --all-files`:
  - Ruff check: passed;
  - Ruff format: passed;
  - mypy: passed;
  - pytest: 980 passed, 51 failed, 8 skipped.
- `tests/unit/core/test_inventory_candidate_service.py`: 15 passed, 3 failed,
  1 skipped. The FIFO hard-blocked case is the expected Windows skip; the
  failures are two unavailable symlink-privilege cases and one existing cp950
  Git subprocess decoding case.
- `tests/unit/core/test_inventory_selection_safety.py`: 12 passed, 9 failed.
  Both required-primitive fail-closed cases pass; the remaining failures are
  existing Windows positive-path and symlink-privilege baseline cases.

The 51 pytest failures are the existing Windows Inventory Preflight
safe-open/fixture baseline and its downstream build-binding fixtures. They are
outside this identity migration and mypy correction; the modified runtime and
contract checks are green. A normal commit was attempted and confirmed that
Ruff, formatting, and mypy pass before the existing pytest baseline blocks the
hook. The follow-up commit therefore records that verified baseline and skips
the repeated failing hook; no test or safety check was silently omitted from
this handoff.

## Migration and developer impact

- Run `uv sync` after pulling so the editable package and console script are
  rebuilt.
- Replace previous Python imports with `systograph`.
- Replace previous CLI invocations with `systograph`.
- Update environment files and CI secrets to the Systograph-prefixed variable
  names.
- Update scanned-project trace configuration to `[tool.systograph.trace]`.
- Set `SYSTOGRAPH_STATE_DIR` explicitly when existing durable state must remain
  at a non-default path.
- Re-import or re-scan projects whose state only exists under the previous
  default directory; there is no implicit fallback.

The detailed migration contract is recorded in
`docs/SYSTOGRAPH-HARD-CUTOVER.md`.

## Known limitations and handoff

- Historical Git commits, closed issue discussions, and comments are not
  rewritten. Rewriting Git history is outside the active product cutover.
- The local checkout directory may still use its previous folder name while
  Codex or another process has the workspace open. This does not affect the
  package, CLI, Git remote, or runtime identity.
- After merge, other active branches must rebase or merge `main` and resolve
  imports against `src/systograph`; the previous package path no longer
  exists.

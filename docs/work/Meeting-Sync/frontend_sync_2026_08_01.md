# Systograph Frontend Sync - Windows pytest baseline recovery

Status: ready for draft PR review; required backend validation passed

Branch: `fix/windows-pytest-baseline`

## PR scope

- Restore the complete Windows pre-commit and pytest baseline after the
  Systograph identity cutover.
- Add a Windows-only post-decision safe-open adapter that opens the validated
  project-relative path and compares the resulting handle identity and
  metadata before reading or hashing content.
- Preserve the existing POSIX `openat` traversal, `O_NOFOLLOW`, `O_DIRECTORY`,
  `dir_fd`, and fail-closed behavior used by Timmy's macOS development
  environment.
- Decode Git subprocess input and output explicitly as UTF-8 with
  `surrogateescape`, avoiding CP950 failures when the Windows user or temporary
  path contains non-ASCII characters.
- Make filesystem tests capability-aware when a normal Windows account cannot
  create symbolic links.
- Validate migration backup permissions according to host semantics: exact
  `0600` on POSIX, and file creation/presence on Windows where `os.chmod`
  cannot represent owner/group/other permission bits.

No CLI command, JSON report schema, API response contract, or frontend payload
shape changes in this PR.

## Root cause

The post-decision safety service treated POSIX-only safe-open primitives as
the sole supported implementation. Windows therefore returned
`safe_open_unavailable` for ordinary regular files. That emptied final scan
inventories and caused 51 downstream snapshot, build-binding, mapping,
detail-scan, trace, web, and end-to-end failures.

Three additional failures came from tests assuming symbolic-link privilege or
exact POSIX mode reporting on Windows. Git helpers and runtime Git calls also
relied on the host CP950 default even though Git for Windows emits UTF-8 path
data, producing unhandled decode warnings and one `stdout is None` failure.

## Validation results

Windows host: Python 3.14.5, pytest 8.4.2.

- Baseline before the fix: 54 failed, 1067 passed, 8 skipped.
- Root-cause focused suite: 53 passed, 6 capability skips.
- Full pytest after the runtime and test fixes: 1117 passed, 13 skipped,
  0 failed.
- Final `pre-commit run --all-files`:
  - Ruff check with fixes: passed.
  - Ruff format: passed.
  - strict mypy across `src` and `tests`: passed, 328 source files.
  - complete pytest hook: passed.
- `git diff --check`: passed.

The five additional Windows skips are three symbolic-link cases that require
Developer Mode or elevated privilege and two POSIX primitive removal cases.
The Windows adapter has its own positive regression test. On macOS, the
symbolic-link and POSIX primitive tests continue to run; only the Windows-only
adapter test is skipped.

## Known limitations

- macOS was not available for a live host run in this task. Compatibility is
  maintained structurally by leaving the existing POSIX branch unchanged and
  by keeping its tests active on POSIX.
- Windows `os.chmod(0o600)` only maps the read-only attribute; it cannot prove
  a POSIX owner-only ACL. This PR aligns the test with the already documented
  platform behavior and does not claim Windows ACL hardening.
- Symbolic-link safety remains implemented and tested where the host permits
  link creation. A Windows account without that privilege reports an explicit
  capability skip instead of a false product failure.

## Frontend and handoff notes

- No frontend code or API contract regeneration is required.
- Successful Windows scans now retain normal inventory files, so existing
  inventory-selection, mapping, detail-scan, build, and trace UI flows receive
  their expected payloads again.
- Error codes and fail-closed behavior remain unchanged for actual target
  changes, unsupported file types, binary content, unreadable paths, and
  unavailable POSIX primitives.
- Review should focus on the Windows handle-identity check, explicit Git
  encoding, and the platform-specific test guards. The user-owned untracked
  Hardy review document is intentionally excluded from this PR.

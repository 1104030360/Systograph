# Phase 138 Secret Masking TODO

**Date:** 2026-06-22  
**Issue:** GitHub #138  
**Branch:** `fix/138-secret-masking`

## Decision

- [x] Trace the credential data flow from scanner input to canonical map,
      Markdown, Viewer, trace, proposal, logs, and snapshots.
- [x] Compare the plan with OWASP, pip, detect-secrets, and Gitleaks.
- [x] Keep a mandatory Python masking baseline; do not move the security
      invariant to user-overridable TOML in this issue.
- [x] Refine the implementation plan before changing production code.

## TDD execution

- [x] RED: add secret-key normalization regression tests.
- [x] RED: add structured URL userinfo masking tests.
- [x] RED: add independent canonical validation tests.
- [x] RED: add QueryTrace error masking test.
- [x] RED: add proposal, structured logging, snapshot, JSON, API, Viewer, and
      Markdown consumer-path tests.
- [x] Confirm the focused tests fail for the expected leak paths.
- [x] GREEN: extend `SecretMaskingService` without changing its public API.
- [x] GREEN: add an independent URL credential validator and wire it into
      `SystemMapValidationService`.
- [x] GREEN: mask QueryTrace error fields before building events/results.
- [x] Run focused tests until green.

## Verification

- [x] Run the complete pytest suite.
- [x] Run Ruff checks.
- [x] Run mypy.
- [x] Re-run the synthetic leak reproduction and record boolean-only output.
- [x] Review the final diff for raw synthetic credential values in generated
      artifacts or diagnostics.
- [x] Write the phase report.
- [x] Move the completed plan from `plan/unfinish` to `plan/finish`.

## External references

- OWASP Logging Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- pip URL authentication redaction:
  https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/misc.py
- Yelp detect-secrets keyword and basic-auth detectors:
  https://github.com/Yelp/detect-secrets
- Gitleaks configuration behavior:
  https://github.com/gitleaks/gitleaks#configuration

## Baseline

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
438 passed in 6.88s
```

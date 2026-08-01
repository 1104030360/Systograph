# GitHub #175 Redacted Local Paths In API Responses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/175

**Goal:** 成功回應中的 `MapBuildResult` / `PreconditionError.project_path` 支援 redacted local path 模式，降低本機絕對路徑外洩。

**Architecture:** API compatibility must be explicit. If default behavior changes, update docs and frontend contract; otherwise provide opt-in redaction via request flag or serializer while keeping canonical artifact path fields project-relative.

**Tech Stack:** Pydantic serialization, FastAPI response models, path redaction service, route tests.

---

## Source

- GitHub issue #175, assignee Timmy.
- Origin: Backend findings L-7.
- Primary files: `src/systograph/core/models/map_build.py`, `src/systograph/core/models/errors.py`, `src/systograph/web/schemas.py`, `docs/API-GUIDE.md`.
- Related plans: #149 local path redaction, #158 MapBuildResult docs, #168 path-independent tests.

### Task 1: Define compatibility policy

**Files:**
- Inspect/Modify: `src/systograph/core/models/map_build.py`
- Inspect/Modify: `src/systograph/core/models/errors.py`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Decide default vs opt-in redacted mode**
- [ ] **Step 2: Document which fields may contain local absolute paths today**
- [ ] **Step 3: Preserve machine-readable status/error semantics**

### Task 2: Add serialization tests

**Files:**
- Modify: `tests/web/test_map_routes.py`
- Modify: `tests/web/test_project_scan_routes.py`
- Modify: `tests/unit/core/test_precondition_output_policy.py` if model-level redaction is added

- [ ] **Step 1: Successful build response redacts local project path when requested**
- [ ] **Step 2: Precondition error response redacts `project_path` when requested**
- [ ] **Step 3: Canonical `ai_system_map.json` still uses project-relative evidence paths**
- [ ] **Step 4: Response contains no `/Users/...`, `/home/...`, or Windows local path in redacted mode**

### Task 3: Implement response redaction

**Files:**
- Modify: `src/systograph/web/routes/map_routes.py`
- Modify: `src/systograph/web/routes/scan_routes.py`
- Modify: `src/systograph/core/services/path_safety_service.py` if shared redaction helper needs extension

- [ ] **Step 1: Use existing `redact_local_paths` behavior where possible**
- [ ] **Step 2: Keep redaction after map build validation, before API serialization**
- [ ] **Step 3: Avoid mutating stored canonical build result unless policy says so**

## Verification

```bash
.venv/bin/pytest tests/web/test_map_routes.py tests/web/test_project_scan_routes.py tests/unit/core/test_precondition_output_policy.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- API can return successful build/precondition payloads without exposing local absolute paths.
- Contract docs clearly state default and opt-in behavior.
- Canonical map evidence remains project-relative and validated.

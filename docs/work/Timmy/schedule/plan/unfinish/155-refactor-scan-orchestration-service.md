# GitHub #155 Scan Orchestration Service Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/155

**Goal:** 恢復 thin-adapter 邊界，把 inventory、boundary preflight 與 build 編排從 `scan_routes.py` 下沉到 core service。

**Architecture:** Web route handles DTO and HTTP mapping only. Core orchestration owns inventory, boundary preflight, and map build coordination so CLI/web can share behavior.

**Tech Stack:** FastAPI, core service layer, pytest source guard.

---

## Source

- GitHub issue #155, assignee Timmy.
- Origin: Backend findings M-9.
- Primary file: `src/kai_mind/web/routes/scan_routes.py`.

### Task 1: Lock route thin-adapter regression

**Files:**
- Modify: `tests/web/test_project_scan_routes.py`

- [ ] **Step 1: Add source guard that `scan_routes.py` does not instantiate `FilesystemProvider`**
- [ ] **Step 2: Add behavior tests proving scan response unchanged**

### Task 2: Create orchestration service

**Files:**
- Create: `src/kai_mind/core/services/scan_orchestration_service.py`
- Test: `tests/unit/core/test_scan_orchestration_service.py`

- [ ] **Step 1: Move inventory creation into service**
- [ ] **Step 2: Move boundary preflight into service**
- [ ] **Step 3: Move build handoff into service**
- [ ] **Step 4: Return domain result that route can map to response schema**

### Task 3: Wire route and dependencies

**Files:**
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/dependencies.py`
- Modify: `src/kai_mind/web/app.py`

- [ ] **Step 1: Route depends on orchestration service**
- [ ] **Step 2: Preserve `requires_boundary_decision` behavior**
- [ ] **Step 3: Preserve latest map update behavior**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_scan_orchestration_service.py tests/web/test_project_scan_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- `scan_routes.py` no longer directly orchestrates filesystem inventory.
- API behavior remains backward-compatible.
- Core orchestration has unit tests.


# GitHub #140 Viewer Map Loading Path Oracle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/140

**Goal:** 限制 `POST /api/viewer/load` 只能讀取受控 map，並避免回應洩漏 exception、errno 或本機絕對路徑。

**Architecture:** Viewer route 是 thin adapter，只能載入 session allowlist 或受控 output root 內的 map artifact。錯誤對外使用穩定 code，細節只進 masked log。

**Tech Stack:** FastAPI, Pydantic schemas, path safety helpers, pytest.

---

## Source

- GitHub issue #140, assignee Timmy.
- Origin: Backend findings H-2.
- Primary files: `src/kai_mind/web/routes/viewer_routes.py`, `src/kai_mind/core/services/viewer_session_service.py`, `src/kai_mind/web/session_store.py`.

### Task 1: Add path oracle regression tests

**Files:**
- Modify: `tests/web/test_viewer_routes.py`
- Modify: `tests/unit/core/test_viewer_session_service.py`

- [ ] **Step 1: Test absolute path rejection**
- [ ] **Step 2: Test `..` traversal rejection**
- [ ] **Step 3: Test nonexistent path, directory path, and non-JSON path**
- [ ] **Step 4: Assert responses do not contain `/Users`, `/home`, `Errno`, traceback, or quoted absolute paths**

### Task 2: Restrict load source

**Files:**
- Modify: `src/kai_mind/web/session_store.py`
- Modify: `src/kai_mind/web/routes/viewer_routes.py`
- Modify: `src/kai_mind/core/services/viewer_session_service.py`

- [ ] **Step 1: Store allowlisted map artifact paths after successful build/load**
- [ ] **Step 2: Require `project_id` or allowlisted artifact reference where possible**
- [ ] **Step 3: Reject arbitrary absolute paths and traversal before file read**
- [ ] **Step 4: Keep viewer projection pure and scanner-free**

### Task 3: Stabilize error contract

**Files:**
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Use stable codes such as `map_load_not_allowed`, `map_read_failed`, `invalid_json`, `invalid_map`**
- [ ] **Step 2: Mask log details through existing logging/path safety service**

## Verification

```bash
.venv/bin/pytest tests/web/test_viewer_routes.py tests/unit/core/test_viewer_session_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- `/api/viewer/load` cannot probe arbitrary local paths.
- Error responses do not reveal errno, tracebacks, or local absolute paths.
- Valid allowlisted map artifacts still load successfully.


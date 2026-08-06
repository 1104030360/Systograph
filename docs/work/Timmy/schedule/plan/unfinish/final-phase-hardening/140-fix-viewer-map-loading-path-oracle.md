# GitHub #140 Viewer Map Loading Path Oracle Implementation Plan

Status: **superseded**（由 `plan/unfinish/refactor/05-retire-api-viewer-load.md`
＋ umbrella issue #277 取代，2026-08-07）

> **2026-08-07 — 本計畫不再執行。**
> `POST /api/viewer/load` 已於 refactor Plan 05 整支退役（route 檔、
> `ViewerLoadMapRequest` schema、trace script、API-GUIDE 章節一併移除；
> `tests/web/test_retired_endpoints.py` 以 404 regression 鎖住）。本計畫的
> Goal 是「**限制**該端點只能讀受控 map」，端點不存在後已無標的：H-2 的
> path oracle 風險改以**移除**方式消解，而非加固。載入既有
> `ai_system_map.json` 的能力保留在 CLI `systograph validate-map`
> （`cli/viewer_command.py` → `ViewerSessionService.load_map`），該路徑是
> operator 在本機自行指定檔案，不是遠端可觸發的 oracle。
> issue #140 依此結論關閉並於 issue 上註明。
> **本檔保留作為決策軌跡，不得刪除。**若日後需要 HTTP 版載圖能力，應以
> build-scoped artifact API ＋ 白名單重新設計，不要恢復本端點、也不要沿用
> 以下 Task。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/140

**Goal:** 限制 `POST /api/viewer/load` 只能讀取受控 map，並避免回應洩漏 exception、errno 或本機絕對路徑。

**Architecture:** Viewer route 是 thin adapter，只能載入 session allowlist 或受控 output root 內的 map artifact。錯誤對外使用穩定 code，細節只進 masked log。

**Tech Stack:** FastAPI, Pydantic schemas, path safety helpers, pytest.

---

## Source

- GitHub issue #140, assignee Timmy.
- Origin: Backend findings H-2.
- Primary files: `src/systograph/web/routes/viewer_routes.py`, `src/systograph/core/services/viewer_session_service.py`, `src/systograph/web/session_store.py`.

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
- Modify: `src/systograph/web/session_store.py`
- Modify: `src/systograph/web/routes/viewer_routes.py`
- Modify: `src/systograph/core/services/viewer_session_service.py`

- [ ] **Step 1: Store allowlisted map artifact paths after successful build/load**
- [ ] **Step 2: Require `project_id` or allowlisted artifact reference where possible**
- [ ] **Step 3: Reject arbitrary absolute paths and traversal before file read**
- [ ] **Step 4: Keep viewer projection pure and scanner-free**

### Task 3: Stabilize error contract

**Files:**
- Modify: `src/systograph/web/schemas.py`
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


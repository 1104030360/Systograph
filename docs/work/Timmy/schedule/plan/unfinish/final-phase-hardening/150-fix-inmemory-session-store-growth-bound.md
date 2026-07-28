# GitHub #150 In-Memory Session Store Growth Bound Implementation Plan

> **2026-07-28 更新（phase2.5 Plan 2 Task 5）：** 本計畫原針對 `InMemorySessionStore`，
> 但該類別在 production 不會被實例化（`create_app()` 只建 `PersistentSessionStore`）。
> `PersistentSessionStore` 只保留 `_latest_build_result` / `_latest_viewer_payload`
> 兩個單槽快取，不會隨 project 數量無上限累積，所以這裡沒有等價的成長邊界問題；
> 其 thread safety 已在
> `docs/work/Timmy/schedule/plan/unfinish/phase2.5/2.md` Task 5 實作完成（見 #174）。
> 本計畫剩餘範圍：確認 `InMemorySessionStore` 是否遷移到 `tests/helpers/`（見 Plan 3 A-13）。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/150

**Goal:** 避免 project 與完整 `MapBuildResult` 在 `InMemorySessionStore` 無上限累積造成記憶體 DoS。

**Architecture:** In-memory mode remains local/dev friendly but bounded. Eviction policy must be deterministic and later compatible with Task 26 session history domain.

**Tech Stack:** Python collections, threading-safe store later with #174, pytest.

---

## Source

- GitHub issue #150, assignee Timmy.
- Origin: Backend findings M-5.
- Primary file: `src/kai_mind/web/session_store.py`.

### Task 1: Add growth regression tests

**Files:**
- Create/Modify: `tests/unit/web/test_session_store.py`

- [ ] **Step 1: Test max projects cap**
- [ ] **Step 2: Test max build results cap**
- [ ] **Step 3: Test oldest project/build eviction is deterministic**
- [ ] **Step 4: Test latest viewer payload behavior remains unchanged**

### Task 2: Implement bounded store

**Files:**
- Modify: `src/kai_mind/web/session_store.py`

- [ ] **Step 1: Add configurable `max_projects` and `max_build_results`**
- [ ] **Step 2: Use deterministic insertion/LRU order**
- [ ] **Step 3: Evict associated build result when project is evicted**
- [ ] **Step 4: Keep defaults conservative and documented**

### Task 3: Document relationship to Task 26

**Files:**
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase3-platform-foundation/26-implement-persistent-session-store-and-scan-history.md`

- [ ] **Step 1: Note bounded in-memory behavior as pre-DB safety baseline**

## Verification

```bash
.venv/bin/pytest tests/unit/web/test_session_store.py tests/web/test_project_scan_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- In-memory store cannot grow without bound.
- Eviction behavior is deterministic and tested.
- Existing project scan/map behavior remains compatible.

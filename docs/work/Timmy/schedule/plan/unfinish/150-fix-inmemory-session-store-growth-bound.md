# GitHub #150 In-Memory Session Store Growth Bound Implementation Plan

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
- Modify: `docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`

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


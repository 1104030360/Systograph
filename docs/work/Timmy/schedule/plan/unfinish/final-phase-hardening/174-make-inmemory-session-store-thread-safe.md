# GitHub #174 In-Memory Session Store Thread Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/174

**Goal:** 避免 FastAPI threadpool 中 `InMemorySessionStore` 多步讀寫 race。

**Architecture:** In-memory store 仍只是 local/dev adapter，但需要基本 atomicity。Thread safety 應與 #150 容量上限一起考慮，避免 eviction 與 latest pointer 不一致。

**Tech Stack:** Python `RLock`, pytest concurrency tests, FastAPI route tests.

---

## Source

- GitHub issue #174, assignee Timmy.
- Origin: Backend findings L-6.
- Primary file: `src/kai_mind/web/session_store.py`.
- Related plans: #150 store growth bound, #164 proposal create dedup, Task 26 persistent session store.

### Task 1: Add concurrent store tests

**Files:**
- Create/Modify: `tests/unit/web/test_session_store.py`
- Modify: `tests/web/test_project_scan_routes.py` if route-level coverage is needed

- [ ] **Step 1: Concurrent project save/read does not raise**
- [ ] **Step 2: Concurrent build result save/read keeps latest pointer valid**
- [ ] **Step 3: If #150 eviction exists, concurrent eviction remains consistent**

### Task 2: Add minimal locking

**Files:**
- Modify: `src/kai_mind/web/session_store.py`

- [ ] **Step 1: Add private `RLock`**
- [ ] **Step 2: Lock multi-step writes and dependent reads**
- [ ] **Step 3: Return immutable snapshots where callers iterate store state**
- [ ] **Step 4: Avoid holding lock across expensive map build work**

### Task 3: Document adapter boundary

**Files:**
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase3-platform-foundation/26-implement-persistent-session-store-and-scan-history.md`

- [ ] **Step 1: Note thread-safe in-memory behavior as temporary local adapter baseline**
- [ ] **Step 2: Keep DB repository as production-capable path**

## Verification

```bash
.venv/bin/pytest tests/unit/web/test_session_store.py tests/web/test_project_scan_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Concurrent route/store access does not corrupt project/build-result state.
- Latest build result and project-specific build result remain internally consistent.
- Locking remains scoped to store state, not long-running scan execution.

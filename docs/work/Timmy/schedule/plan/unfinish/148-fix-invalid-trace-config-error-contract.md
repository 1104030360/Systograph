# GitHub #148 Invalid Trace Config Error Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/148

**Goal:** `POST /api/trace` 不得把 config parser exception、errno 或本機絕對路徑放進 HTTP detail。

**Architecture:** External API gets stable error code only. Internal parse details go to masked logs and never echo user filesystem or parser messages.

**Tech Stack:** FastAPI, TOML config loader, pytest.

---

## Source

- GitHub issue #148, assignee Timmy.
- Origin: Backend findings M-3.
- Primary files: `src/kai_mind/web/routes/trace_routes.py`, `src/kai_mind/core/services/query_trace_config_loader.py`, `docs/API-GUIDE.md`.

### Task 1: Add regression tests

**Files:**
- Modify: `tests/web/test_trace_routes.py`
- Modify: `tests/unit/core/test_query_trace_config_loader.py`

- [ ] **Step 1: Test malformed `pyproject.toml`**
- [ ] **Step 2: Test unreadable config where supported by platform**
- [ ] **Step 3: Assert HTTP detail equals `invalid_trace_config`**
- [ ] **Step 4: Assert response does not contain `/Users`, `Errno`, parser text, or traceback**

### Task 2: Stabilize route error mapping

**Files:**
- Modify: `src/kai_mind/web/routes/trace_routes.py`
- Modify: `src/kai_mind/core/services/query_trace_config_loader.py`

- [ ] **Step 1: Convert loader exceptions to safe domain error**
- [ ] **Step 2: Route maps domain error to stable HTTP detail**
- [ ] **Step 3: Mask details before logging**

### Task 3: Update API contract

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Replace prose exception examples with stable error code**
- [ ] **Step 2: Add migration note for frontend error mapping**

## Verification

```bash
.venv/bin/pytest tests/web/test_trace_routes.py tests/unit/core/test_query_trace_config_loader.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Invalid trace config response is stable and path-safe.
- Parser/OS details are masked and log-only.
- API guide matches runtime behavior.


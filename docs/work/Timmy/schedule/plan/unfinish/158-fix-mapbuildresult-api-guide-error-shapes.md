# GitHub #158 MapBuildResult API Guide Error Shape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/158

**Goal:** 修正 `docs/API-GUIDE.md` 與實作對 `MapBuildResult.error`、`output_run_dir` 的型別 drift。

**Architecture:** API docs must be traced from actual Pydantic models and route behavior. No prose-only contract should contradict runtime schemas.

**Tech Stack:** FastAPI route tests, Pydantic models, API docs.

---

## Source

- GitHub issue #158, assignee Timmy.
- Origin: Backend findings M-12.
- Primary files: `docs/API-GUIDE.md`, `src/kai_mind/core/models/map_build.py`, `src/kai_mind/core/models/errors.py`.

### Task 1: Trace runtime error shape

**Files:**
- Modify: `tests/web/test_map_routes.py`

- [ ] **Step 1: Add map error-path route test**
- [ ] **Step 2: Assert `error` is structured `PreconditionError`**
- [ ] **Step 3: Assert nullable fields are actually nullable on failure**

### Task 2: Update API guide

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Replace `error: string | null` with structured shape**
- [ ] **Step 2: Mark `output_run_dir` and related payload fields nullable where runtime says so**
- [ ] **Step 3: Add one JSON example copied from traced test output with secrets/paths redacted**

### Task 3: Add drift guard

**Files:**
- Modify: `tests/web/test_map_routes.py`

- [ ] **Step 1: Assert documented keys remain present**
- [ ] **Step 2: Keep test resilient to timestamp/run-dir variability**

## Verification

```bash
.venv/bin/pytest tests/web/test_map_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- API-GUIDE matches actual `MapBuildResult` failure shape.
- Frontend can rely on structured `error.failure_reason`.
- Docs do not imply non-null paths where runtime returns null.


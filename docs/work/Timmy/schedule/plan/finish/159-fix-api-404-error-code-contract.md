# GitHub #159 API 404 Error Code Contract Implementation Plan

> **Current verified state（2026-07-05）：部分完成。** 多數 routes 已使用
> `project_not_found`，但 `src/systograph/web/routes/scan_routes.py` 仍回傳字串
> `Project not found`。本 plan 保留在 unfinish，剩餘工作必須聚焦此 route 與一致性測試。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/159

**Goal:** 統一 API 404 detail 格式，避免 `Project not found` 與 `project_not_found` 混用破壞前端 mapping。

**Architecture:** API errors should use stable machine-readable codes. Any wording migration must be documented before OpenAPI generated SDK work.

**Tech Stack:** FastAPI HTTPException mapping, route tests, API docs.

---

## Source

- GitHub issue #159, assignee Timmy.
- Origin: Backend findings M-13.
- Primary files: `src/systograph/web/routes/scan_routes.py`, trace/detail/mapping routes, `docs/API-GUIDE.md`.

### Task 1: Choose canonical error codes

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Define `project_not_found` as canonical 404 detail**
- [ ] **Step 2: List affected routes**
- [ ] **Step 3: Add migration note from `Project not found`**

### Task 2: Lock route tests

**Files:**
- Modify: `tests/web/test_project_scan_routes.py`
- Modify: `tests/web/test_trace_routes.py`
- Modify: `tests/web/test_detail_scan_routes.py`
- Modify: `tests/web/test_mapping_routes.py`
- Modify: `tests/web/test_mapping_proposal_routes.py`

- [ ] **Step 1: Assert exact `detail` for project 404**
- [ ] **Step 2: Assert related resource 404 codes remain stable**

### Task 3: Update route details

**Files:**
- Modify: `src/systograph/web/routes/scan_routes.py`
- Modify: related route modules if inconsistent

- [ ] **Step 1: Replace human sentence with stable code**
- [ ] **Step 2: Keep status codes unchanged**

## Verification

```bash
.venv/bin/pytest tests/web/test_project_scan_routes.py tests/web/test_trace_routes.py tests/web/test_detail_scan_routes.py tests/web/test_mapping_routes.py tests/web/test_mapping_proposal_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Project 404 details are stable machine-readable codes.
- API guide documents exact error codes.
- Frontend no longer needs to handle mixed project 404 wording.

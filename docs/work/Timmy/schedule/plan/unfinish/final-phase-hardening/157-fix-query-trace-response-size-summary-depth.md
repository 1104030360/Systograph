# GitHub #157 Query Trace Response Bounds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/157

**Goal:** 避免 endpoint 回傳超大或深層 JSON 導致記憶體耗盡或 `_summary` recursion failure。

**Architecture:** Query trace is opt-in but still bounded. Response body read, JSON summary depth, dict keys, and list items must have deterministic caps and truncation markers.

**Tech Stack:** httpx, QueryTraceService, pytest mocks.

---

## Source

- GitHub issue #157, assignee Timmy.
- Origin: Backend findings M-11.
- Primary files: `src/systograph/core/providers/endpoint_call_provider.py`, `src/systograph/core/services/query_trace_service.py`.

### Task 1: Add oversized response tests

**Files:**
- Modify: `tests/unit/core/test_endpoint_call_provider.py`
- Modify: `tests/unit/core/test_query_trace_service.py`

- [ ] **Step 1: Mock response larger than max bytes**
- [ ] **Step 2: Mock deeply nested JSON**
- [ ] **Step 3: Mock dict with many keys and list with many items**
- [ ] **Step 4: Assert truncation markers are returned safely**

### Task 2: Implement bounds

**Files:**
- Modify: `src/systograph/core/providers/endpoint_call_provider.py`
- Modify: `src/systograph/core/services/query_trace_service.py`

- [ ] **Step 1: Limit response bytes before JSON parsing**
- [ ] **Step 2: Add summary max depth**
- [ ] **Step 3: Add dict key and list item caps**
- [ ] **Step 4: Preserve masking before response is exposed**

### Task 3: Document trace limits

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Document truncation and uncertainty semantics**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_endpoint_call_provider.py tests/unit/core/test_query_trace_service.py tests/web/test_trace_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Oversized/deep responses do not OOM or recurse indefinitely.
- Truncated trace events remain useful and marked as truncated.
- Raw response content remains masked.


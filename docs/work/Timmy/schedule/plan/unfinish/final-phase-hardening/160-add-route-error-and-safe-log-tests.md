# GitHub #160 Route Error and Safe Log Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/160

**Goal:** 補齊報告列出的 route error paths、CLI map error path、`safe_log_event` 與 config loader 測試。

**Architecture:** This is test coverage only unless tests expose a real bug. Error-path tests must assert both behavior and non-leakage of API keys/local paths.

**Tech Stack:** pytest, FastAPI TestClient, Typer CliRunner, caplog.

---

## Source

- GitHub issue #160, assignee Timmy.
- Origin: Backend findings M-14.
- Primary files: route tests, CLI tests, `src/systograph/core/services/logging_service.py`.

### Task 1: Add route error tests

**Files:**
- Modify: `tests/web/test_trace_routes.py`
- Modify: `tests/web/test_detail_scan_routes.py`
- Modify: `tests/web/test_mapping_routes.py`
- Modify: `tests/web/test_project_scan_routes.py`

- [ ] **Step 1: Cover invalid trace config**
- [ ] **Step 2: Cover detail scan 404**
- [ ] **Step 3: Cover mapping update 404 and 422**
- [ ] **Step 4: Cover scan boundary invalid decision 422**

### Task 2: Add CLI map error test

**Files:**
- Modify: `tests/cli/test_map_command.py`

- [ ] **Step 1: Invoke CLI with invalid project path**
- [ ] **Step 2: Assert non-zero exit and safe error summary**

### Task 3: Add safe log tests

**Files:**
- Create/Modify: `tests/unit/core/test_logging_service.py`

- [ ] **Step 1: Log field containing fake API key and local absolute path**
- [ ] **Step 2: Assert caplog contains masked values only**
- [ ] **Step 3: Add config loader error log regression if applicable**

## Verification

```bash
.venv/bin/pytest tests/web tests/cli/test_map_command.py tests/unit/core/test_logging_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Listed route/CLI error paths have tests.
- Safe log behavior is directly tested.
- Tests verify no full secret or local absolute path leaks.


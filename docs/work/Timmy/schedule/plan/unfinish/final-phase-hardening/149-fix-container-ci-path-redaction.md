# GitHub #149 Container and CI Path Redaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/149

**Goal:** 補齊 `/app`、`/workspace`、`/srv`、`/data`、`/mnt`、`/root` 等容器/CI 常見絕對路徑的 redaction。

**Architecture:** Path redaction should be conservative for absolute local paths. Prefer a general absolute-path redaction policy over brittle prefix-only coverage if it does not over-redact URLs or project-relative paths.

**Tech Stack:** Regex/path utilities, pytest.

---

## Source

- GitHub issue #149, assignee Timmy.
- Origin: Backend findings M-4.
- Primary file: `src/systograph/core/services/path_safety_service.py`.

### Task 1: Add path redaction tests

**Files:**
- Modify: `tests/unit/core/test_cross_platform_paths.py`

- [ ] **Step 1: Add parametrized tests for `/app`, `/workspace`, `/srv`, `/data`, `/mnt`, `/root`**
- [ ] **Step 2: Assert URLs and project-relative POSIX paths are not incorrectly redacted**
- [ ] **Step 3: Assert Windows path behavior remains covered**

### Task 2: Implement safer path redaction

**Files:**
- Modify: `src/systograph/core/services/path_safety_service.py`

- [ ] **Step 1: Expand POSIX absolute path coverage or adopt general absolute-path detector**
- [ ] **Step 2: Preserve safe placeholders such as `<project_root>`**
- [ ] **Step 3: Ensure redaction output is deterministic**

### Task 3: Run affected output tests

**Files:**
- Test only unless regressions require code changes

- [ ] **Step 1: Run tests covering logs/errors/evidence path safety**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_cross_platform_paths.py tests/unit/core/test_system_map_validation.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Common container/CI absolute paths are redacted.
- Project-relative POSIX paths remain intact.
- URLs are not mangled by path redaction.


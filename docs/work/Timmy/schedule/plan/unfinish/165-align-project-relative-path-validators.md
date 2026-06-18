# GitHub #165 Project-Relative Path Validator Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/165

**Goal:** 讓 `is_project_relative_posix_path` 與 `normalize_project_relative_path` 對含冒號 segment、Windows drive-like path、UNC-like path 等非法路徑採一致規則。

**Architecture:** Path safety 是 shared boundary。所有 scanner evidence、viewer path、trace config 與 API path validation 應使用同一個 project-relative POSIX policy，不可各自放寬。

**Tech Stack:** Python pathlib, pytest, cross-platform path tests.

---

## Source

- GitHub issue #165, assignee Timmy.
- Origin: Backend findings L-8.
- Primary file: `src/kai_mind/core/services/path_safety_service.py`.
- Related plans: #140 viewer path oracle, #146 scan root boundary policy, #147 output artifact confinement.

### Task 1: Add path policy regression tests

**Files:**
- Modify: `tests/unit/core/test_cross_platform_paths.py`
- Modify: `tests/unit/core/test_system_map_validation.py`

- [ ] **Step 1: Reject colon segments**

Cover `foo/a:b`, `config:prod.yaml`, `C:relative/path`, and `C:/absolute/path`.

- [ ] **Step 2: Reject UNC-like and backslash paths**
- [ ] **Step 3: Preserve valid POSIX project-relative paths**
- [ ] **Step 4: Assert validation service delegates to shared policy**

### Task 2: Centralize validation rules

**Files:**
- Modify: `src/kai_mind/core/services/path_safety_service.py`

- [ ] **Step 1: Add helper for invalid path segments**
- [ ] **Step 2: Make normalize and predicate share the same checks**
- [ ] **Step 3: Keep error messages stable and non-leaky**

### Task 3: Sweep call sites

**Files:**
- Inspect/Modify: `src/kai_mind/core/services/system_map_validation_service.py`
- Inspect/Modify: `src/kai_mind/core/services/scan_boundary_review_service.py`
- Inspect/Modify: `src/kai_mind/core/services/code_path_scan_service.py`

- [ ] **Step 1: Remove duplicate or weaker path predicates if present**
- [ ] **Step 2: Confirm all public path fields remain project-relative POSIX**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_cross_platform_paths.py tests/unit/core/test_system_map_validation.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Colon-containing path segments are rejected consistently.
- Windows drive/UNC/backslash paths cannot enter canonical map path fields.
- Existing valid project-relative POSIX paths remain valid.

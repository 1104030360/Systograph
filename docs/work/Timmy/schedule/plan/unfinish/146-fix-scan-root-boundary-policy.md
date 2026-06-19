# GitHub #146 Scan Root Boundary Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/146

**Goal:** 限制 project import、map build 與 CLI scan 的可掃路徑與 boundary 行為，避免任意本機目錄掃描、snippet 外洩及大型目錄 DoS。

**Architecture:** Scan root validation belongs in core boundary policy and is reused by web/CLI. Project-scoped scans must honor boundary gate consistently; unsafe arbitrary roots should fail closed or default to no snippets.

**Tech Stack:** Path safety service, FastAPI routes, Typer CLI, pytest.

---

## Source

- GitHub issue #146, assignee Timmy.
- Origin: Backend findings M-1.
- Primary files: `src/kai_mind/web/routes/project_routes.py`, `src/kai_mind/web/routes/map_routes.py`, `src/kai_mind/core/services/project_scan_service.py`, `src/kai_mind/cli/map_command.py`.

### Task 1: Add scan-root regression tests

**Files:**
- Modify: `tests/web/test_project_scan_routes.py`
- Modify: `tests/web/test_map_routes.py`
- Modify: `tests/cli/test_map_command.py`

- [ ] **Step 1: Test nonexistent path rejection**
- [ ] **Step 2: Test file path rejection**
- [ ] **Step 3: Test out-of-scope absolute path rejection**
- [ ] **Step 4: Test boundary gate is not bypassed by map/build or CLI**

### Task 2: Implement shared scan-root policy

**Files:**
- Create: `src/kai_mind/core/services/scan_root_policy_service.py`
- Modify: `src/kai_mind/web/routes/project_routes.py`
- Modify: `src/kai_mind/web/routes/map_routes.py`
- Modify: `src/kai_mind/cli/map_command.py`

- [ ] **Step 1: Validate path exists and is directory**
- [ ] **Step 2: Enforce allowed-root policy**
- [ ] **Step 3: Return stable safe error codes**
- [ ] **Step 4: Make CLI/web use the same policy object**

### Task 3: Update documentation

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Document local-only scan root expectations**
- [ ] **Step 2: Document map/build boundary behavior**

## Verification

```bash
.venv/bin/pytest tests/web/test_project_scan_routes.py tests/web/test_map_routes.py tests/cli/test_map_command.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Import/build/CLI reject invalid or out-of-scope scan roots.
- Project-scoped scans enforce boundary gate consistently.
- Unsafe failure responses do not leak local paths or snippets.


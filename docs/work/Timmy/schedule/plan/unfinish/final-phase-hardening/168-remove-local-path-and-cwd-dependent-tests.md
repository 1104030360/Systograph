# GitHub #168 Test Path Independence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/168

**Goal:** 測試不得依賴開發者本機絕對路徑或 process CWD 才能找到 fixtures。

**Architecture:** Tests 應從 repo root helper 或 pytest tmp_path 建立輸入，不可硬編 `/Users/linjunting` 或隱含目前執行目錄。這是 CI portability 與 privacy baseline。

**Tech Stack:** pytest fixtures, pathlib, CLI runner, repo-root helper.

---

## Source

- GitHub issue #168, assignee Timmy.
- Origin: Backend findings L-11/L-12.
- Primary areas: contract tests, CLI tests, web tests, README examples.
- Related plans: #144 cross-platform quality gate, #149 local path redaction, #175 redacted local paths.

### Task 1: Locate path/CWD dependencies

**Files:**
- Inspect/Modify: `tests/contracts/test_secret_snapshot_safety.py`
- Inspect/Modify: `tests/unit/core/test_cross_platform_paths.py`
- Inspect/Modify: `tests/web/test_local_api_hardening.py`
- Inspect/Modify: `tests/cli/*.py`
- Inspect/Modify: `tests/helpers/fixtures.py`

- [ ] **Step 1: Search for user-home absolute paths**
- [ ] **Step 2: Search for direct relative fixture access without helper**
- [ ] **Step 3: Search docs examples that imply a developer-specific path**

### Task 2: Add repo-root fixture helpers

**Files:**
- Modify: `tests/helpers/fixtures.py`
- Modify: `tests/conftest.py` if shared fixture is needed

- [ ] **Step 1: Provide a stable repo root helper**
- [ ] **Step 2: Provide fixture path helper independent of CWD**
- [ ] **Step 3: Keep helpers small and explicit**

### Task 3: Rewrite dependent tests

**Files:**
- Modify: affected tests from Task 1
- Modify: `README.md` only if examples are misleading

- [ ] **Step 1: Replace local absolute paths with synthetic paths**
- [ ] **Step 2: Replace CWD assumptions with helper paths**
- [ ] **Step 3: Add a subprocess or monkeypatch CWD regression for representative tests**

## Verification

```bash
.venv/bin/pytest tests/contracts/test_secret_snapshot_safety.py tests/unit/core/test_cross_platform_paths.py tests/web/test_local_api_hardening.py tests/cli -v
(cd /tmp && /Users/linjunting/Systograph/.venv/bin/pytest /Users/linjunting/Systograph/tests/cli/test_viewer_command.py -v)
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Tests do not require `/Users/linjunting` or any developer-specific absolute path.
- Representative CLI/fixture tests pass when invoked from a different CWD.
- README examples avoid leaking local machine assumptions.

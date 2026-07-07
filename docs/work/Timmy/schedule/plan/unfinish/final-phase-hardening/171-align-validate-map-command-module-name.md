# GitHub #171 Validate-Map Command Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/171

**Goal:** 消除 `viewer_command.py` 檔名與實際註冊命令 `validate-map` 的命名歧義。

**Architecture:** CLI module naming should reflect the user-facing command or contain an explicit docstring explaining why viewer projection powers validation. Any rename must be safe for package import and tests.

**Tech Stack:** Typer CLI, Python imports, pytest CLI tests.

---

## Source

- GitHub issue #171, assignee Timmy.
- Origin: Backend findings L-15.
- Primary files: `src/kai_mind/cli/viewer_command.py`, `src/kai_mind/cli/main.py`.
- Related tests: `tests/cli/test_viewer_command.py`.

### Task 1: Choose rename or docstring-only strategy

**Files:**
- Inspect: `src/kai_mind/cli/viewer_command.py`
- Inspect: `src/kai_mind/cli/main.py`
- Inspect: `tests/cli/test_viewer_command.py`

- [ ] **Step 1: Check whether external imports rely on `viewer_command`**
- [ ] **Step 2: Prefer rename to `validate_map_command.py` if no compatibility issue**
- [ ] **Step 3: Use module docstring if rename creates unnecessary churn**

### Task 2A: If renaming module

**Files:**
- Move: `src/kai_mind/cli/viewer_command.py` to `src/kai_mind/cli/validate_map_command.py`
- Modify: `src/kai_mind/cli/main.py`
- Modify: `tests/cli/test_viewer_command.py` name if useful

- [ ] **Step 1: Update imports**
- [ ] **Step 2: Keep user-facing command `validate-map` unchanged**
- [ ] **Step 3: Run CLI tests**

### Task 2B: If keeping module name

**Files:**
- Modify: `src/kai_mind/cli/viewer_command.py`

- [ ] **Step 1: Add precise module docstring explaining viewer projection validation**
- [ ] **Step 2: Avoid touching user-facing command behavior**

## Verification

```bash
.venv/bin/pytest tests/cli/test_viewer_command.py -v
.venv/bin/kai-mind validate-map --help
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- File/module naming no longer confuses maintainers about the `validate-map` command.
- The CLI command name and behavior remain backward compatible.
- Tests and imports pass after rename or documentation update.

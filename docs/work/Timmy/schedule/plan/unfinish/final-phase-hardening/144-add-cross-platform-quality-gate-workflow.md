# GitHub #144 Cross-Platform Quality Gate Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/144

**Goal:** 為 release-readiness gate 本身建立不可只靠本機 hook 的 GitHub Actions 品質閘門。

**Architecture:** CI must run the same core gates as local development, with least-privilege permissions and a minimal OS matrix. Windows job focuses on CLI and path-sensitive tests.

**Tech Stack:** GitHub Actions, uv, pytest, Ruff, mypy.

---

## Source

- GitHub issue #144, assignee Timmy.
- Origin: Backend findings H-6.
- Primary files: `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`.

### Task 1: Add baseline CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Add least-privilege permissions**
- [ ] **Step 2: Install uv and Python**
- [ ] **Step 3: Run `uv sync --all-groups`**
- [ ] **Step 4: Run `.venv/bin/ruff check .`, `.venv/bin/mypy`, `.venv/bin/pytest` on Ubuntu**

### Task 2: Add Windows path-sensitive job

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add `windows-latest` matrix entry**
- [ ] **Step 2: Run CLI tests and `tests/unit/core/test_cross_platform_paths.py`**
- [ ] **Step 3: Document any skipped tests with exact reason**

### Task 3: Verify workflow locally as far as possible

**Files:**
- Modify: `README.md` if CI badge or gate docs are added

- [ ] **Step 1: Run local full gate**
- [ ] **Step 2: Push PR branch and inspect Actions result**
- [ ] **Step 3: Fix workflow-only path/shell differences**

## Verification

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- PRs run automated quality gates.
- Ubuntu full backend gate passes.
- Windows validates CLI/path-sensitive behavior.
- Workflow permissions are least privilege.


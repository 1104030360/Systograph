# GitHub #172 Mypy Compatibility Range Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/172

**Goal:** 避免 `mypy>=2.1.0` 無上限造成未來 dev environment 非預期 breaking change。

**Architecture:** Dev tooling should be reproducible. `uv.lock` 是主要 pinning source，但 `pyproject.toml` 也應表達相容範圍，避免 fresh resolution 拉到未驗證 major version。

**Tech Stack:** uv dependency management, mypy strict mode, pyproject.

---

## Source

- GitHub issue #172, assignee Timmy.
- Origin: Backend findings L-16.
- Primary files: `pyproject.toml`, `uv.lock`.
- Related plan: #144 cross-platform quality gate workflow.

### Task 1: Decide dependency policy

**Files:**
- Inspect: `pyproject.toml`
- Inspect: `uv.lock`

- [ ] **Step 1: Check current locked mypy version**
- [ ] **Step 2: Decide whether policy is `<3` or narrower**
- [ ] **Step 3: Record why the upper bound is chosen**

### Task 2: Update dependency declaration

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Add compatible upper bound to dev dependency**
- [ ] **Step 2: Refresh lock with `uv lock`**
- [ ] **Step 3: Avoid unrelated dependency churn**

### Task 3: Run quality gate

**Files:**
- No source changes expected unless mypy exposes real errors

- [ ] **Step 1: Run mypy with locked environment**
- [ ] **Step 2: Run full pytest if lock refresh changes dependency graph**
- [ ] **Step 3: Document lock refresh result in implementation report**

## Verification

```bash
uv lock
.venv/bin/mypy
.venv/bin/pytest
.venv/bin/ruff check .
git diff --check
git diff -- pyproject.toml uv.lock
```

## Acceptance Criteria

- `pyproject.toml` expresses a bounded mypy compatibility range.
- `uv.lock` is refreshed without unrelated surprises.
- Strict mypy still passes.

# GitHub #143 Web Test Dotenv Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/143

**Goal:** 避免 `tests/web` 自動載入開發者真實 `.env`、API key 或 process environment，確保測試可重現且不會意外 wire 真實 AI provider。

**Architecture:** Tests must be hermetic by default. Web tests should construct deterministic app state and isolate dotenv/process env unless a test explicitly opts in.

**Tech Stack:** pytest fixtures, FastAPI app factory, monkeypatch.

---

## Source

- GitHub issue #143, assignee Timmy.
- Origin: Backend findings H-5.
- Primary files: `tests/conftest.py`, `src/kai_mind/web/app.py`, `src/kai_mind/core/providers/llm_proposal_provider.py`.

### Task 1: Add failing isolation test

**Files:**
- Modify: `tests/web/test_nvidia_provider_app_wiring.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Create fake `.env` with NVIDIA proposal flags and fake key**
- [ ] **Step 2: Set process env with conflicting NVIDIA values**
- [ ] **Step 3: Assert default web tests do not wire real provider**

### Task 2: Add hermetic pytest fixture

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Clear provider-related environment variables by default**
- [ ] **Step 2: Point app factory env file to nonexistent temp path in tests**
- [ ] **Step 3: Provide explicit opt-in fixture for provider wiring tests**

### Task 3: Keep production behavior explicit

**Files:**
- Modify: `src/kai_mind/web/app.py`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Ensure app factory accepts explicit `env_file`**
- [ ] **Step 2: Document test isolation and production config source**

## Verification

```bash
.venv/bin/pytest tests/web -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Web tests do not depend on developer `.env` or process environment.
- Provider wiring tests must opt in explicitly.
- CI/pre-commit/local test behavior is consistent.


# GitHub #154 Independent Secret Validation Defense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/154

**Goal:** 讓 canonical validation gate 不再與 masking 完全共用同一套偵測規則，降低共同盲點。

**Architecture:** Validation defense should use independent heuristics from output masking. It must reject unsafe canonical values without echoing them.

**Tech Stack:** Validation service, Pydantic models, pytest.

---

## Source

- GitHub issue #154, assignee Timmy.
- Origin: Backend findings M-8 and C-1.
- Primary files: `src/systograph/core/services/system_map_validation_service.py`, `src/systograph/core/services/secret_masking_service.py`.

### Task 1: Add validation blind-spot tests

**Files:**
- Modify: `tests/unit/core/test_system_map_validation.py`

- [ ] **Step 1: Add DSN userinfo raw secret case**
- [ ] **Step 2: Add key/value credential-like case**
- [ ] **Step 3: Add non-secret control cases to avoid overblocking**

### Task 2: Implement independent validator

**Files:**
- Create: `src/systograph/core/services/secret_validation_service.py`
- Modify: `src/systograph/core/services/system_map_validation_service.py`

- [ ] **Step 1: Add URL userinfo detector**
- [ ] **Step 2: Add high-risk credential shape detector**
- [ ] **Step 3: Keep error messages redacted**
- [ ] **Step 4: Do not call masking service as the only decision path**

### Task 3: Verify full serialization boundary

**Files:**
- Modify: `tests/contracts/test_secret_snapshot_safety.py`

- [ ] **Step 1: Add fixture serialization regression**
- [ ] **Step 2: Assert unsafe maps fail before JSON artifact is trusted**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_system_map_validation.py tests/contracts/test_secret_snapshot_safety.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Validation blocks at least one secret-like case independent of masking rules.
- Validation errors do not leak raw secret values.
- Existing valid maps continue to pass.


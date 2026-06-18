# GitHub #153 Short Secret Masking Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/153

**Goal:** 避免 9-16 字元 secret 因固定露出前後四字元而幾乎完整洩漏。

**Architecture:** Short secret values should be full masked. Longer values may retain bounded prefix/suffix only if the visible ratio is safe.

**Tech Stack:** `SecretMaskingService`, pytest.

---

## Source

- GitHub issue #153, assignee Timmy.
- Origin: Backend findings M-7.
- Primary file: `src/kai_mind/core/services/secret_masking_service.py`.

### Task 1: Add short-secret regression tests

**Files:**
- Modify: `tests/unit/core/test_secret_masking_service.py`

- [ ] **Step 1: Add 9, 12, and 16 character secret cases**
- [ ] **Step 2: Assert full raw secret does not appear**
- [ ] **Step 3: Assert visible characters are zero or within strict policy**

### Task 2: Update masking policy

**Files:**
- Modify: `src/kai_mind/core/services/secret_masking_service.py`

- [ ] **Step 1: Full mask values with length <= 16**
- [ ] **Step 2: Keep long secret prefix/suffix visibility capped**
- [ ] **Step 3: Preserve existing non-secret localhost/model/route behavior**

### Task 3: Run shared output regressions

**Files:**
- Test only unless failures appear

- [ ] **Step 1: Run Phase 5 integration tests**
- [ ] **Step 2: Run map build tests that serialize evidence**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/integration/test_phase5_secret_masking_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- 9-16 character secret-like values are not partially revealed.
- Existing long-secret masking remains deterministic.
- False positives are not increased for known non-secret examples.


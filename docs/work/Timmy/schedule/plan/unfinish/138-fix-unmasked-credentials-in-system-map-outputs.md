# GitHub #138 Unmasked Credentials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/138

**Goal:** 補齊 secret masking，避免 DSN URL userinfo、`PASSWD` / `PWD`、無底線 `APIKEY` 等機密以明文進入 `ai_system_map.json`、Markdown、Viewer、trace 或 proposal evidence。

**Architecture:** 修補 shared `SecretMaskingService`，並讓 canonical validation 阻止明文落盤。此 issue 可和 #153、#154 同 branch 實作，但仍需保留本 issue 的 regression tests。

**Tech Stack:** Python regex, pytest, Pydantic validation, existing scanner providers.

---

## Source

- GitHub issue #138, assignee Timmy.
- Origin: `docs/work/Timmy/schedule/fable-5/find-error/report/2026-06-12-backend-security-ai-findings.md` C-1.
- Primary files: `src/kai_mind/core/services/secret_masking_service.py`, `src/kai_mind/core/services/system_map_validation_service.py`.

### Task 1: Reproduce the leaked secret cases

**Files:**
- Modify: `tests/unit/core/test_secret_masking_service.py`
- Modify: `tests/integration/test_phase5_secret_masking_behaviors.py`

- [ ] **Step 1: Add failing tests for key marker variants**

Cases: `DB_PASSWD`, `DB_PWD`, `MYAPIKEY`, `ACCESSKEY`, `SESSION_COOKIE`.

- [ ] **Step 2: Add failing tests for URL userinfo**

Cases: PostgreSQL, Redis, MongoDB, and HTTP service URLs with `user:password@host`.

- [ ] **Step 3: Add map-build regression fixture**

Create synthetic fixture values only; never use real credentials.

### Task 2: Fix shared masking behavior

**Files:**
- Modify: `src/kai_mind/core/services/secret_masking_service.py`

- [ ] **Step 1: Normalize key markers before matching**

Normalize by uppercasing and removing separators so `API_KEY` and `APIKEY` are both secret-like.

- [ ] **Step 2: Mask URL userinfo password segments**

Preserve scheme/host where useful, but never preserve the full password.

- [ ] **Step 3: Ensure recursive JSON-like masking uses the same path**

`mask_value`, `mask_text`, and `mask_json_like` must share the fixed behavior.

### Task 3: Block unsafe canonical output

**Files:**
- Modify: `src/kai_mind/core/services/system_map_validation_service.py`
- Test: `tests/unit/core/test_system_map_validation.py`

- [ ] **Step 1: Add validation tests for raw DSN credentials**
- [ ] **Step 2: Reject unmasked URL userinfo in evidence values/snippets**
- [ ] **Step 3: Verify validation error messages do not echo the raw secret**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/unit/core/test_system_map_validation.py tests/integration/test_phase5_secret_masking_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Raw DSN passwords, `DB_PASSWD`, `DB_PWD`, and `MYAPIKEY` values do not appear in JSON, Markdown, viewer payload, trace, proposal evidence, logs, or snapshots.
- Existing `CLIENT_SECRET` behavior remains protected.
- Canonical validation catches unsafe output before artifact write.


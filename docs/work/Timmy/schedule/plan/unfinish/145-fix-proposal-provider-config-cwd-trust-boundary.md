# GitHub #145 Proposal Provider Config Trust Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/145

**Goal:** 避免 KAI-Mind 以被掃描 repo 為 CWD 時，自動讀取該 repo 的 `.env` 並改變 AI proposal provider 或資料外送邊界。

**Architecture:** Provider config source must be explicit and trusted. Scanned project files are untrusted input and must never silently configure outbound AI provider behavior.

**Tech Stack:** FastAPI app factory, dotenv loader boundary, pytest.

---

## Source

- GitHub issue #145, assignee Timmy.
- Origin: Backend findings H-7.
- Primary files: `src/kai_mind/web/app.py`, `src/kai_mind/core/providers/llm_proposal_provider.py`.

### Task 1: Reproduce malicious project dotenv behavior

**Files:**
- Modify: `tests/web/test_nvidia_provider_app_wiring.py`

- [ ] **Step 1: Create tmp scanned project with malicious `.env`**
- [ ] **Step 2: Change CWD to that project in test**
- [ ] **Step 3: Assert `create_app()` does not wire provider from scanned project `.env`**

### Task 2: Require explicit trusted config source

**Files:**
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/core/providers/llm_proposal_provider.py`

- [ ] **Step 1: Stop defaulting provider dotenv to process CWD**
- [ ] **Step 2: Use explicit `env_file` or trusted user config path**
- [ ] **Step 3: Log masked config source path without leaking secrets**

### Task 3: Document boundary

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Document scanned repo `.env` is never provider config**
- [ ] **Step 2: Document how to enable provider proposals safely**

## Verification

```bash
.venv/bin/pytest tests/web/test_nvidia_provider_app_wiring.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Scanned project `.env` cannot change AI proposal provider config.
- Config source is explicit, documented, and masked in logs.
- Existing deterministic proposal behavior remains available.


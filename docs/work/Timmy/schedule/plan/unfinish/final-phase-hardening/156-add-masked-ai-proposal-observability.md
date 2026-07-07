# GitHub #156 Masked AI Proposal Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/156

**Goal:** 為 mapping proposal AI 呼叫增加可除錯且不洩漏機密的結構化 observability。

**Architecture:** Observability records masked summaries, model/provider metadata, latency, token/cost when available, fallback and error classification. It must never log raw prompt, raw evidence, full secret, or local absolute path.

**Tech Stack:** Existing logging service, AI proposal provider, pytest caplog.

---

## Source

- GitHub issue #156, assignee Timmy.
- Origin: Backend findings M-10.
- Primary files: `src/kai_mind/core/providers/llm_proposal_provider.py`, `src/kai_mind/core/services/mapping_proposal_service.py`.

### Task 1: Add observability tests

**Files:**
- Modify: `tests/unit/core/test_nvidia_nim_proposal_provider.py`
- Modify: `tests/unit/core/test_mapping_proposal_service.py`

- [ ] **Step 1: Assert provider/model/latency event is logged**
- [ ] **Step 2: Assert fallback/error classification is logged**
- [ ] **Step 3: Assert logs do not contain fake secret or local absolute path**

### Task 2: Implement masked log events

**Files:**
- Modify: `src/kai_mind/core/providers/llm_proposal_provider.py`
- Modify: `src/kai_mind/core/services/mapping_proposal_service.py`
- Modify: `src/kai_mind/core/services/logging_service.py` if needed

- [ ] **Step 1: Emit start/finish/failure events**
- [ ] **Step 2: Include masked prompt/evidence summary only**
- [ ] **Step 3: Include token/cost only when provider returns it safely**

### Task 3: Document diagnostics

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Document observability fields and redaction guarantees**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_nvidia_nim_proposal_provider.py tests/unit/core/test_mapping_proposal_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- AI proposal calls emit useful masked diagnostics.
- Logs contain no raw prompt, secret, or absolute local path.
- Provider unavailable behavior remains safe.


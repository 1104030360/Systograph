# GitHub #161 Proposal Prompt Untrusted Evidence Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/161

**Goal:** 降低掃描 repo 內容對 mapping proposal prompt 的間接 prompt injection 與 social-engineering 風險。

**Architecture:** Evidence packet is untrusted data. Prompt construction must spotlight/delimit untrusted evidence, mask source fields, and preserve deterministic candidate validation/pending-only workflow.

**Tech Stack:** Prompt builder, LLM proposal provider, mapping proposal service tests.

---

## Source

- GitHub issue #161, assignee Timmy.
- Origin: Backend findings M-15.
- Primary files: `src/systograph/core/providers/llm_proposal_provider.py`, `src/systograph/core/services/mapping_proposal_service.py`.

### Task 1: Add prompt injection regression tests

**Files:**
- Modify: `tests/unit/core/test_nvidia_nim_proposal_provider.py`
- Modify: `tests/unit/core/test_mapping_proposal_service.py`

- [ ] **Step 1: Create evidence packet with injection-like filename/reason/snippet**
- [ ] **Step 2: Assert prompt delimits untrusted evidence**
- [ ] **Step 3: Assert output validation still restricts evidence ids and target slots**

### Task 2: Harden prompt construction

**Files:**
- Modify: `src/systograph/core/providers/llm_proposal_provider.py`

- [ ] **Step 1: Add explicit untrusted-data delimiter**
- [ ] **Step 2: Mask/redact `source_file`, `reason`, and snippets before prompt**
- [ ] **Step 3: Keep schema instructions outside untrusted block**

### Task 3: Preserve deterministic validation and UI warning

**Files:**
- Modify: `src/systograph/core/services/mapping_proposal_service.py`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Ensure candidate validation remains allowlist-based**
- [ ] **Step 2: Document proposal rationale as AI-generated and pending confirmation**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_nvidia_nim_proposal_provider.py tests/unit/core/test_mapping_proposal_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Prompt clearly isolates untrusted evidence.
- Injection-like evidence cannot bypass evidence/slot allowlists.
- Proposal remains pending-only and user-confirmed.


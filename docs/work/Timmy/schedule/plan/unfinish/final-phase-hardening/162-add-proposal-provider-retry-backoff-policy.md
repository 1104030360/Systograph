# GitHub #162 Proposal Provider Retry Backoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/162

**Goal:** 對 AI proposal provider transient failure 與 429 quota/rate-limit failure 加入 bounded retry/backoff，並清楚定義 deterministic fallback 順序。

**Architecture:** Retry policy 屬於 provider boundary，不可讓 route 或 proposal service 無限等待。所有 retry 記錄都必須遮罩 prompt/evidence，且 provider 最終不可用時仍回到 deterministic proposal。

**Tech Stack:** Python, httpx exception classification, pytest fake client, existing `MappingProposalService`.

---

## Source

- GitHub issue #162, assignee Timmy.
- Origin: Backend findings L-1.
- Primary files: `src/systograph/core/providers/llm_proposal_provider.py`, `src/systograph/core/services/mapping_proposal_service.py`.
- Related plans: #145 provider config trust boundary, #156 masked observability, #161 prompt evidence isolation.

### Task 1: Add transient failure tests

**Files:**
- Modify: `tests/unit/core/test_nvidia_nim_proposal_provider.py`
- Modify: `tests/unit/core/test_mapping_proposal_service.py`

- [ ] **Step 1: Test retryable HTTP statuses**

Cover 429, 500, 502, 503, and 504 with a fake http client.

- [ ] **Step 2: Test retryable transport failures**

Cover timeout/connection errors without making real network calls.

- [ ] **Step 3: Test non-retryable errors fail fast**

Validation errors, malformed provider JSON, 400, and 401 must not loop.

### Task 2: Implement bounded retry policy

**Files:**
- Modify: `src/systograph/core/providers/llm_proposal_provider.py`
- Modify: `src/systograph/core/services/llm_proposal_config_loader.py` if config is needed

- [ ] **Step 1: Add explicit max attempts and backoff bounds**
- [ ] **Step 2: Classify retryable status/exception types**
- [ ] **Step 3: Keep total wait under a small configured ceiling**
- [ ] **Step 4: Do not retry after schema validation failure**

### Task 3: Preserve deterministic fallback

**Files:**
- Modify: `src/systograph/core/services/mapping_proposal_service.py`

- [ ] **Step 1: Surface provider unavailable reason without raw exception data**
- [ ] **Step 2: Ensure deterministic candidates are still returned after exhausted retry**
- [ ] **Step 3: Keep provider failure from changing route status to 500**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_nvidia_nim_proposal_provider.py tests/unit/core/test_mapping_proposal_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Retry/backoff is finite, deterministic in tests, and configurable within strict bounds.
- 429/transient failures are retried; auth/schema failures are not retried.
- No log, exception, or test output contains raw prompt, raw evidence, API key, or local absolute path.
- Proposal endpoint still falls back to deterministic output when provider is unavailable.

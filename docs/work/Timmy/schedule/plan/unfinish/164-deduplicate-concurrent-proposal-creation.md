# GitHub #164 Concurrent Proposal Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/164

**Goal:** 避免同一 `source_unmapped_id` 並發 create proposal 時同時 miss pending proposal，造成重複呼叫 AI provider 與重複 pending proposal。

**Architecture:** Dedup 應以 project/source key 為粒度做 single-flight 或 repository atomic operation。不得用全域粗鎖長時間包住 provider network call，避免阻塞不同 source 的 proposal。

**Tech Stack:** Python threading, repository protocol, pytest concurrency tests.

---

## Source

- GitHub issue #164, assignee Timmy.
- Origin: Backend findings L-3.
- Primary file: `src/kai_mind/core/services/mapping_proposal_service.py`.
- Related plans: #162 retry/backoff, #174 in-memory store thread safety.

### Task 1: Add concurrency regression tests

**Files:**
- Modify: `tests/unit/core/test_mapping_proposal_service.py`

- [ ] **Step 1: Create fake slow provider**

Use an event/barrier so two threads enter create concurrently.

- [ ] **Step 2: Assert same source calls provider once**
- [ ] **Step 3: Assert different sources can still proceed independently**
- [ ] **Step 4: Assert returned proposal id is stable for duplicate pending request**

### Task 2: Implement single-flight policy

**Files:**
- Modify: `src/kai_mind/core/services/mapping_proposal_service.py`

- [ ] **Step 1: Define key as `(project_id, source_unmapped_id)`**
- [ ] **Step 2: Re-check repository after acquiring per-key coordination**
- [ ] **Step 3: Avoid holding decision lock around provider network I/O unless scoped per key**
- [ ] **Step 4: Clean up per-key state after success or failure**

### Task 3: Keep repository contract clear

**Files:**
- Modify: `src/kai_mind/core/services/mapping_proposal_service.py`
- Modify: `src/kai_mind/storage/repositories.py` if repository behavior needs support

- [ ] **Step 1: Document whether dedup lives in service or repository**
- [ ] **Step 2: Preserve future DB unique constraint path for Task 27**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_mapping_proposal_service.py tests/web/test_mapping_proposal_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Concurrent create for the same source results in one pending proposal and one provider call.
- Concurrent create for different sources does not serialize unnecessarily.
- Provider failures still fall back safely and do not leave stale in-flight locks.

# GitHub #163 Query Trace Timeout Exposure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/163

**Goal:** 配合 SSRF egress 修補，降低 web query trace `timeout_seconds` 最高 120 秒造成的慢速探測與資源占用風險。

**Architecture:** Timeout policy 應集中在 shared trace policy，web schema、CLI option、service 呼叫都使用同一組上下限。此 issue 需等 #139 的 SSRF egress policy 決定後再定稿。

**Tech Stack:** FastAPI/Pydantic v2 validation, Typer CLI, pytest.

---

## Source

- GitHub issue #163, assignee Timmy.
- Origin: Backend findings L-2.
- Primary files: `src/kai_mind/web/schemas.py`, `src/kai_mind/core/services/query_trace_service.py`.
- Related plans: #139 SSRF egress policy, #167 CLI trace timeout bound.

### Task 1: Define shared timeout policy

**Files:**
- Create/Modify: `src/kai_mind/core/services/query_trace_policy.py`
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/cli/trace_command.py`

- [ ] **Step 1: Pick safe default and maximum**

Use the smallest practical max for local release-readiness checks; do not keep 120 seconds unless #139 documents why.

- [ ] **Step 2: Expose constants for web and CLI**
- [ ] **Step 3: Document timeout uncertainty and why long probes are rejected**

### Task 2: Add boundary tests

**Files:**
- Modify: `tests/web/test_trace_routes.py`
- Modify: `tests/cli/test_trace_command.py`
- Modify: `tests/unit/core/test_query_trace_service.py` if service-level validation is added

- [ ] **Step 1: Assert max+epsilon request is rejected**
- [ ] **Step 2: Assert default timeout still works**
- [ ] **Step 3: Assert rejected errors do not echo endpoint internals**

### Task 3: Wire policy into runtime

**Files:**
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/cli/trace_command.py`
- Modify: `src/kai_mind/core/services/query_trace_service.py`

- [ ] **Step 1: Use shared max in `TraceCreateRequest`**
- [ ] **Step 2: Use shared max in Typer option callback or service validation**
- [ ] **Step 3: Keep endpoint-specific timeout lower than the total route budget**

## Verification

```bash
.venv/bin/pytest tests/web/test_trace_routes.py tests/cli/test_trace_command.py tests/unit/core/test_query_trace_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Web and CLI use one timeout policy.
- Query trace no longer accepts long timeout values that enable slow probing.
- Existing valid trace flows remain compatible.
- This plan does not weaken #139 SSRF allowlist/egress protections.

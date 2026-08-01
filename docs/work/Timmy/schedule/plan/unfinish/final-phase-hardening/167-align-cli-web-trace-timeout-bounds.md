# GitHub #167 CLI/Web Trace Timeout Bounds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/167

**Goal:** 讓 CLI `trace --timeout-seconds` 與 web trace timeout 契約一致，避免 CLI 接受無界或過長 timeout。

**Architecture:** CLI 是同一個 query trace capability 的 thin adapter。Timeout bounds 應下沉到 shared policy 或 service validation，避免 web 與 CLI 分叉。

**Tech Stack:** Typer, Pydantic, pytest CLI runner.

---

## Source

- GitHub issue #167, assignee Timmy.
- Origin: Backend findings L-10.
- Primary file: `src/systograph/cli/trace_command.py`.
- Related plans: #139 SSRF egress policy, #163 query trace timeout exposure.

### Task 1: Add CLI timeout tests

**Files:**
- Modify: `tests/cli/test_trace_command.py`

- [ ] **Step 1: Assert valid timeout succeeds**
- [ ] **Step 2: Assert zero/negative timeout is rejected**
- [ ] **Step 3: Assert above-max timeout is rejected**
- [ ] **Step 4: Assert error message is stable and does not include endpoint detail**

### Task 2: Share validation policy

**Files:**
- Modify: `src/systograph/cli/trace_command.py`
- Modify: `src/systograph/web/schemas.py`
- Create/Modify: `src/systograph/core/services/query_trace_policy.py`

- [ ] **Step 1: Move min/max/default constants to shared module**
- [ ] **Step 2: Use Typer callback or explicit pre-service validation**
- [ ] **Step 3: Keep Pydantic `TraceCreateRequest` aligned with the same constants**

### Task 3: Confirm route/CLI parity

**Files:**
- Modify: `tests/web/test_trace_routes.py`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Add one web boundary test mirroring CLI**
- [ ] **Step 2: Document the same allowed timeout range for API and CLI**

## Verification

```bash
.venv/bin/pytest tests/cli/test_trace_command.py tests/web/test_trace_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- CLI and web reject the same invalid timeout range.
- The configured maximum matches #163's reduced exposure policy.
- Trace service cannot be reached with unbounded timeout through supported entry points.

# GitHub #139 Query Trace SSRF Egress Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/139

**Goal:** 防止 query trace 對 metadata、loopback、private/link-local network 或未授權 endpoint 發送請求。

**Architecture:** `EndpointCallProvider` 必須在送出 HTTP request 前做 egress preflight。預設拒絕高風險位址；localhost trace 若要保留，必須是明確 opt-in。

**Tech Stack:** Python `ipaddress`, DNS resolution guard, httpx tests/mocks, pytest.

---

## Source

- GitHub issue #139, assignee Timmy.
- Origin: Backend findings H-1.
- Primary files: `src/kai_mind/core/providers/endpoint_call_provider.py`, `src/kai_mind/core/services/query_trace_service.py`, `src/kai_mind/web/routes/trace_routes.py`.

### Task 1: Lock SSRF regression tests

**Files:**
- Modify: `tests/unit/core/test_endpoint_call_provider.py`
- Modify: `tests/unit/core/test_query_trace_service.py`
- Modify: `tests/web/test_trace_routes.py`

- [ ] **Step 1: Add blocked endpoint cases**

Cases: `169.254.169.254`, `127.0.0.1`, `0.0.0.0`, `::1`, RFC1918 private ranges, link-local, and metadata hostnames.

- [ ] **Step 2: Assert `query_sent=false` for blocked cases**

The provider must not call httpx for blocked targets.

- [ ] **Step 3: Add IPv6 and DNS-rebinding-oriented tests**

Resolve hostname then validate every resolved IP.

### Task 2: Implement egress policy

**Files:**
- Modify: `src/kai_mind/core/providers/endpoint_call_provider.py`
- Create: `src/kai_mind/core/services/egress_policy_service.py`

- [ ] **Step 1: Implement URL host extraction and DNS resolution**
- [ ] **Step 2: Reject metadata, loopback, private, link-local, multicast, unspecified, and reserved ranges by default**
- [ ] **Step 3: Add explicit local opt-in config if localhost trace must remain supported**
- [ ] **Step 4: Return stable blocked reason without leaking raw endpoint internals**

### Task 3: Document boundary

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/work/Timmy/schedule/plan/finish/22-implement-query-trace-mvp.md`

- [ ] **Step 1: Document default-deny egress policy**
- [ ] **Step 2: Document localhost opt-in and uncertainty**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_endpoint_call_provider.py tests/unit/core/test_query_trace_service.py tests/web/test_trace_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Blocked targets never send a network request.
- Metadata/private/link-local/loopback/unspecified endpoints are denied by default.
- Trace responses expose stable error codes and `query_sent=false`.


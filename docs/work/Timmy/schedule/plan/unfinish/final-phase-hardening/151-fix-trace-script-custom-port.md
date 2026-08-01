# GitHub #151 Trace Script Custom Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/151

**Goal:** 修正 trace script 使用 `--start-server` 搭配自訂 `--api-base-url` 時，uvicorn 仍硬編碼 port 8000 而 timeout。

**Architecture:** Trace script server startup must derive host/port from `API_BASE_URL`, or fail immediately with a clear mismatch error. Shell behavior must remain portable for macOS/Linux dev use.

**Tech Stack:** POSIX shell, curl, existing trace scripts.

---

## Source

- GitHub issue #151, assignee Timmy.
- Origin: Backend findings M-5b.
- Primary file: `scripts/lib/api_trace_common.sh`.

### Task 1: Add shell parsing tests or smoke script

**Files:**
- Modify/Create: `tests/cli/test_trace_scripts.py` or shell smoke under `scripts/`

- [ ] **Step 1: Test parsing `http://127.0.0.1:9000`**
- [ ] **Step 2: Test default port remains 8000**
- [ ] **Step 3: Test invalid API URL fails fast**

### Task 2: Fix startup host/port

**Files:**
- Modify: `scripts/lib/api_trace_common.sh`

- [ ] **Step 1: Parse host and port from `API_BASE_URL`**
- [ ] **Step 2: Pass parsed values to uvicorn**
- [ ] **Step 3: Keep `wait_for_api` polling the same URL**
- [ ] **Step 4: Add clear error if scheme/host/port is unsupported**

### Task 3: Verify real smoke path

**Files:**
- No code change unless smoke reveals follow-up

- [ ] **Step 1: Run a trace script with `--api-base-url http://127.0.0.1:9000 --start-server`**
- [ ] **Step 2: Ensure no orphan uvicorn process remains**

## Verification

```bash
.venv/bin/pytest tests/cli -v
scripts/trace_all.sh --api-base-url http://127.0.0.1:9000 --start-server
git diff --check
```

## Acceptance Criteria

- Custom API port works with `--start-server`.
- Invalid URL fails quickly with clear message.
- Existing default port behavior remains intact.


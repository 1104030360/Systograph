# GitHub #151 Trace Script Custom Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/151

**Goal:** 修正 trace script 使用 `--start-server` 搭配自訂 `--api-base-url` 時，uvicorn 仍硬編碼 port 8000 而 timeout。

**Architecture:** Trace script server startup must derive host/port from `API_BASE_URL`, or fail immediately with a clear mismatch error. Shell behavior must remain portable for macOS/Linux dev use.

**Tech Stack:** POSIX shell, curl, existing trace scripts.

> **進度（2026-08-07）：部分完成，本檔仍在 `unfinish/`。**
> Task 2（修正 startup host/port）與 Task 3（實機 smoke）已由 **#277 Stage 4** 順帶完成：
> Steps 1–3 於 commit `5871be8`，Step 4（fail-fast 明確錯誤）於 commit `9b9b996`。
> **剩餘範圍：Task 1（`API_BASE_URL` 解析的自動化測試）尚未實作** —— 目前 fail-fast 只有手動負向
> 案例佐證，沒有回歸測試綁住行為；補完 Task 1 後本檔才可移入 `finish/`。

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

- [x] **Step 1: Parse host and port from `API_BASE_URL`**（`systograph_resolve_server_bind`）
- [x] **Step 2: Pass parsed values to uvicorn**（`--host "$SERVER_BIND_HOST" --port "$SERVER_BIND_PORT"`）
- [x] **Step 3: Keep `wait_for_api` polling the same URL**（`wait_for_api` 未動，仍打 `$API_BASE_URL/openapi.json`）
- [x] **Step 4: Add clear error if scheme/host/port is unsupported**（非 `http://`、無 host、無明確數字 port 皆立即 `systograph_die`）

### Task 3: Verify real smoke path

**Files:**
- No code change unless smoke reveals follow-up

- [x] **Step 1: Run a trace script with `--api-base-url http://127.0.0.1:9000 --start-server`**
- [x] **Step 2: Ensure no orphan uvicorn process remains**（跑完 `pgrep -f "uvicorn systograph.web.app"` 無殘留）

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


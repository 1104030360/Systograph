# GitHub #173 Loopback Server Binding Implementation Plan

> **Current verified state（2026-07-05）：部分完成。** `scripts/dev.py` 已提供 `--host`
> 並預設 loopback；剩餘工作是 non-loopback explicit opt-in、CORS/安全 guard 與 regression
> tests。本 plan 不再重做已存在的 host/default 行為。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/173

**Goal:** 官方啟動入口預設綁定 `127.0.0.1`，並對非 loopback bind 提示或要求明確 opt-in。

**Architecture:** Systograph local API 預設是本機 release-readiness tool，不應意外暴露到 LAN。Non-loopback binding 可存在，但必須由使用者明確選擇並理解 network exposure 風險。

**Tech Stack:** uvicorn startup docs/scripts, FastAPI docs, pytest where startup wrapper exists.

---

## Source

- GitHub issue #173, assignee Timmy.
- Origin: Backend findings L-5.
- Primary areas: `src/systograph/web/app.py`, uvicorn startup path, README/API docs.
- Related plans: #139 SSRF egress policy, #144 cross-platform CI, #170 README drift.

### Task 1: Trace official startup paths

**Files:**
- Inspect: `README.md`
- Inspect: `docs/API-GUIDE.md`
- Inspect: scripts that start uvicorn
- Inspect: package scripts if any

- [ ] **Step 1: List every documented API startup command**
- [ ] **Step 2: Confirm default host in docs is `127.0.0.1`**
- [ ] **Step 3: Identify any script that defaults to `0.0.0.0`**

### Task 2: Add explicit non-loopback policy

**Files:**
- Modify: startup script/module if one exists
- Modify: `docs/API-GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Keep documented default as loopback**
- [ ] **Step 2: Add warning or explicit opt-in for non-loopback host**
- [ ] **Step 3: Document CORS is not a security boundary**

### Task 3: Add tests where executable policy exists

**Files:**
- Modify: CLI/startup tests if a managed server command exists
- Otherwise add docs verification notes in the implementation report

- [ ] **Step 1: Test default host value if startup wrapper is implemented**
- [ ] **Step 2: Test non-loopback requires opt-in if wrapper enforces it**

## Verification

```bash
rg -n "0\\.0\\.0\\.0|127\\.0\\.0\\.1|uvicorn|--host" README.md docs scripts src tests
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Official startup documentation defaults to `127.0.0.1`.
- Non-loopback exposure is either rejected by a wrapper or clearly requires explicit user choice.
- No docs imply CORS alone makes the local API safe on a network.

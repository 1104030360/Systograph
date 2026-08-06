# GitHub #170 README Command And Verdict Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/170

**Goal:** 修正 README 對 READY/RISKY/NOT READY verdict 的實作狀態宣稱，並補上正式 API-GUIDE / CLI entry point 連結。

**Architecture:** README 必須分清楚 implemented capability 與 roadmap。Release-readiness 目前以 evidence-based map/report/trace 為核心，不可宣稱尚未實作的單一 verdict engine 已完成。

**Tech Stack:** Markdown docs, CLI command verification.

---

## Source

- GitHub issue #170, assignee Timmy.
- Origin: Backend findings L-14.
- Primary file: `README.md`.
- Related docs: `docs/API-GUIDE.md`, CLI entry point `systograph`.

### Task 1: Trace implemented command surface

**Files:**
- Inspect: `src/systograph/cli/main.py`
- Inspect: `src/systograph/cli/map_command.py`
- Inspect: `src/systograph/cli/trace_command.py`
- Inspect: `src/systograph/cli/viewer_command.py`
- Inspect: `docs/API-GUIDE.md`

- [ ] **Step 1: List actual CLI commands**
- [ ] **Step 2: List actual local API entry points**
- [ ] **Step 3: Confirm verdict-like behavior is not implemented as final READY/RISKY/NOT READY**

### Task 2: Update README claims

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Move unimplemented verdict language into roadmap**
- [ ] **Step 2: Describe current output as evidence-based readiness artifacts**
- [ ] **Step 3: Link to API-GUIDE and command examples**
- [ ] **Step 4: Keep product boundary clear: not chatbot, not RAG builder, not enterprise security scanner**

### Task 3: Add doc drift checks

**Files:**
- Modify: docs tests if there is an existing docs test location
- Otherwise document manual verification in this plan's implementation report

- [ ] **Step 1: Verify CLI examples run or print help**
- [ ] **Step 2: Verify README command names match Typer registration**

## Verification

```bash
.venv/bin/systograph --help
.venv/bin/systograph map --help
.venv/bin/systograph trace --help
.venv/bin/systograph validate-map --help
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- README no longer implies READY/RISKY/NOT READY verdict is already implemented if it is roadmap-only.
- README links to actual API and CLI entry points.
- Command examples match currently registered Typer commands.

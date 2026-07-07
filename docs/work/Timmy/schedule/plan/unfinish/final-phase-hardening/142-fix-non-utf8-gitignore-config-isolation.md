# GitHub #142 Non-UTF-8 File Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/142

**Goal:** 非 UTF-8 `.gitignore` 或 `.env` 不得讓 inventory 或整個 config provider 崩潰。

**Architecture:** Decode failure 是 per-file parse issue/warning，不是 whole-scan crash。Inventory failure 要安全降級並保留診斷資訊；config parsing 應 per-file isolation。

**Tech Stack:** Python filesystem IO, pytest fixtures, existing providers.

---

## Source

- GitHub issue #142, assignee Timmy.
- Origin: Backend findings H-4.
- Primary files: `src/kai_mind/core/providers/filesystem_provider.py`, `src/kai_mind/core/providers/config_parse_provider.py`.

### Task 1: Add non-UTF-8 fixtures and tests

**Files:**
- Modify: `tests/unit/core/test_filesystem_provider.py`
- Modify: `tests/unit/core/test_config_parse_provider.py`
- Modify: `tests/integration/test_phase8_config_parse_provider_behaviors.py`

- [ ] **Step 1: Add `.gitignore` fixture bytes with invalid UTF-8**
- [ ] **Step 2: Add `.env` fixture bytes with invalid UTF-8**
- [ ] **Step 3: Assert scan continues and other eligible files are scanned**

### Task 2: Implement decode policy

**Files:**
- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Modify: `src/kai_mind/core/providers/config_parse_provider.py`

- [ ] **Step 1: Convert decode errors to warning/parse issue**
- [ ] **Step 2: Use `errors=\"replace\"` only where preserving partial parse is safe**
- [ ] **Step 3: Avoid echoing raw undecodable content in messages**
- [ ] **Step 4: Ensure per-file failures do not abort provider collection**

### Task 3: Document behavior

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Document non-UTF-8 files as warning/partial scan**
- [ ] **Step 2: Clarify scanner does not transcode or repair user files**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_filesystem_provider.py tests/unit/core/test_config_parse_provider.py tests/integration/test_phase8_config_parse_provider_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Non-UTF-8 `.gitignore` and `.env` do not crash scan.
- Other files remain scanned.
- Warnings are safe and do not contain raw bytes or secrets.


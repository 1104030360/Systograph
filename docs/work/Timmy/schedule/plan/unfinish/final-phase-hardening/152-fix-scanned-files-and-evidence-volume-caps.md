# GitHub #152 Scan Size and Evidence Volume Caps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/152

**Goal:** 對掃描總檔案數與總 evidence 量設上限，避免大量小檔案 repo 導致 CPU/記憶體耗盡。

**Architecture:** Resource limits are deterministic truncation boundaries, not silent data loss. The scan should emit warning/summary evidence when limits are hit.

**Tech Stack:** FilesystemProvider, ProjectScanService, pytest synthetic fixtures.

---

## Source

- GitHub issue #152, assignee Timmy.
- Origin: Backend findings M-6.
- Primary files: `src/systograph/core/providers/filesystem_provider.py`, `src/systograph/core/services/project_scan_service.py`.

### Task 1: Add large-repo synthetic tests

**Files:**
- Modify: `tests/unit/core/test_filesystem_provider.py`
- Modify: `tests/unit/core/test_project_scan_service.py`

- [ ] **Step 1: Generate many small synthetic files in tmp path**
- [ ] **Step 2: Assert `max_total_files` caps inventory deterministically**
- [ ] **Step 3: Assert `max_total_evidence` caps facts/evidence deterministically**
- [ ] **Step 4: Assert warnings are present and safe**

### Task 2: Implement caps

**Files:**
- Modify: `src/systograph/core/providers/filesystem_provider.py`
- Modify: `src/systograph/core/services/project_scan_service.py`

- [ ] **Step 1: Add configurable defaults**
- [ ] **Step 2: Sort before truncation for deterministic output**
- [ ] **Step 3: Record limit-hit warnings**
- [ ] **Step 4: Ensure caps apply before expensive provider work where possible**

### Task 3: Reflect limits in API/docs

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Document resource limits and uncertainty**
- [ ] **Step 2: Document how truncation appears in scan summary**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_filesystem_provider.py tests/unit/core/test_project_scan_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Large small-file repos cannot create unbounded inventory/evidence growth.
- Limit-hit behavior is deterministic and visible to users.
- Warnings do not leak local paths or secrets.


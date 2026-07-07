# GitHub #147 Output Artifact Path Confinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/147

**Goal:** 避免 API caller 透過 `output` 指定任意絕對或 traversal 路徑建立報告檔。

**Architecture:** Output artifacts must be confined to a KAI-Mind controlled output root. User-provided output is treated as project-relative or app-output-relative, never arbitrary filesystem authority.

**Tech Stack:** Path safety service, OutputArtifactProvider, FastAPI schemas, pytest.

---

## Source

- GitHub issue #147, assignee Timmy.
- Origin: Backend findings M-2.
- Primary files: `src/kai_mind/web/schemas.py`, `src/kai_mind/core/providers/output_artifact_provider.py`, `src/kai_mind/web/routes/scan_routes.py`.

### Task 1: Add path confinement tests

**Files:**
- Modify: `tests/unit/core/test_output_artifact_provider.py`
- Modify: `tests/web/test_map_routes.py`
- Modify: `tests/web/test_project_scan_routes.py`

- [ ] **Step 1: Reject absolute output path**
- [ ] **Step 2: Reject `..` traversal output path**
- [ ] **Step 3: Allow safe relative output path under controlled root**

### Task 2: Implement output policy

**Files:**
- Create: `src/kai_mind/core/services/output_path_policy_service.py`
- Modify: `src/kai_mind/core/providers/output_artifact_provider.py`
- Modify: `src/kai_mind/web/schemas.py`

- [ ] **Step 1: Normalize output path through shared policy**
- [ ] **Step 2: Confine run directories to configured output root**
- [ ] **Step 3: Return stable error code for rejected output path**

### Task 3: Sync docs

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Document `output` as controlled relative path**
- [ ] **Step 2: Document rejection of absolute and traversal paths**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_output_artifact_provider.py tests/web/test_map_routes.py tests/web/test_project_scan_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- API cannot create artifacts outside controlled output root.
- Existing safe output behavior remains compatible.
- Error response does not expose local filesystem details.


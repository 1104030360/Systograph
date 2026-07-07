# GitHub #166 Evidence-Based Scan Summary Implementation Plan

> **Current verified state（2026-07-05）：部分完成。** 多數 summary 欄位已有 evidence
> source，但 `secret_masking_applied` 仍含 heuristic 判定。本 plan 保留在 unfinish，
> 驗收必須證明該欄位可回查實際 masking/validation event。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/166

**Goal:** 修正 `not_configured_slots` 恆為 0 與 `secret_masking_applied` 以字串啟發式推論造成的 scan summary 語意失真。

**Architecture:** Summary 欄位必須能回溯到 deterministic evidence 或明確文件化為 best-effort。不能用看起來像 masked string 的啟發式去宣稱 masking 已套用。

**Tech Stack:** Pydantic system map models, normalize service, contract tests.

---

## Source

- GitHub issue #166, assignee Timmy.
- Origin: Backend findings L-9.
- Primary file: `src/kai_mind/core/services/system_map_normalize_service.py`.
- Related plans: #138 secret masking, #154 independent secret validation, #158 API error shape docs.

### Task 1: Add summary contract tests

**Files:**
- Modify: `tests/unit/core/test_system_map_normalize_service.py`
- Modify: `tests/contracts/test_ai_system_map_schema.py` if schema examples need updates

- [ ] **Step 1: Capture current incorrect `not_configured_slots` behavior**
- [ ] **Step 2: Capture current heuristic `secret_masking_applied` behavior**
- [ ] **Step 3: Add fixture with no secret processing and no false positive**

### Task 2: Define evidence-based semantics

**Files:**
- Modify: `src/kai_mind/core/models/system_map.py` if field semantics need doc updates
- Modify: `src/kai_mind/core/services/system_map_normalize_service.py`
- Modify: `schemas/ai-system-map.v1.schema.json` only if schema contract changes

- [ ] **Step 1: Decide whether `not_configured_slots` is computed or removed/deprecated**
- [ ] **Step 2: Make `secret_masking_applied` come from actual masking workflow metadata**
- [ ] **Step 3: Avoid schema breaking change unless migration note exists**

### Task 3: Update docs and samples

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/work/Timmy/design/frontend-json-sample.json` if sample is still canonical for handoff
- Modify: `tests/fixtures/ai_system_map/*.json` as needed

- [ ] **Step 1: Document exact field meaning**
- [ ] **Step 2: Update sample values to match real calculation**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_system_map_normalize_service.py tests/contracts/test_ai_system_map_schema.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Summary fields are either evidence-based or clearly deprecated/documented.
- `secret_masking_applied` is not inferred solely from masked-looking strings.
- No incompatible JSON schema change ships without migration notes and tests.

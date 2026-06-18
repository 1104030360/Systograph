# Scan Profile Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 local data-only scan profile catalog，讓 KAI-Mind 可追蹤 profile/template metadata、compatibility 與 scan result lineage。

**Architecture:** Profile catalog 是本機 metadata registry，不是 remote marketplace。Profile/template 不可執行 code，不可下載 dependency，不可取代 canonical `ai_system_map.json`。

**Tech Stack:** Pydantic v2, bundled JSON/TOML metadata, FastAPI read-only routes, pytest.

---

## 最新狀態（2026-06-18）

- `rag-core-v1.json` 是目前唯一 reference template。
- Task 24 已明確移除 remote template import；profile/catalog 不屬 Epic 1 blocker。
- Task 28 OpenAPI/generated SDK 先完成後，再新增 profile route 可避免前端 contract drift。

## Scope

- 建立 local scan profile metadata：id、name、version、description、schema_version、template_id、digest、supported_system_type。
- Read-only API：list/get profiles。
- Scan result metadata 可記錄 profile id/version/digest；若改 `ai-system-map/v1`，需 migration note 與 backward-compatible tests。
- 與 project mapping profile page 可整合，但不取代 manual mapping overlay。

## Out of scope

- 不做 remote import。
- 不做 marketplace。
- 不執行 template scripts/hooks。
- 不讓 profile 改 scanner filesystem boundary。

### Task 1: Define profile models and registry

**Files:**
- Create: `src/kai_mind/core/models/scan_profile.py`
- Create: `src/kai_mind/core/services/scan_profile_registry_service.py`
- Create: `src/kai_mind/core/profiles/rag-core-v1.toml`
- Test: `tests/unit/core/test_scan_profile_registry_service.py`

- [ ] **Step 1: Write model validation tests**
- [ ] **Step 2: Compute digest from bundled template content**
- [ ] **Step 3: Reject profile metadata with unknown schema version or executable fields**

### Task 2: Add read-only profile API

**Files:**
- Create: `src/kai_mind/web/routes/scan_profile_routes.py`
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/web/schemas.py`
- Test: `tests/web/test_scan_profile_routes.py`

- [ ] **Step 1: Add `GET /api/scan-profiles`**
- [ ] **Step 2: Add `GET /api/scan-profiles/{profile_id}`**
- [ ] **Step 3: Ensure responses include digest and compatibility but no local absolute paths**
- [ ] **Step 4: Ensure routes are read-only and do not instantiate scanner providers**

### Task 3: Record profile lineage in scan artifacts

**Files:**
- Modify: `src/kai_mind/core/models/system_map.py`
- Modify: `src/kai_mind/core/services/system_map_normalize_service.py`
- Modify: `schemas/ai-system-map.v1.schema.json`
- Test: `tests/contracts/test_ai_system_map_schema.py`

- [ ] **Step 1: Decide if lineage can fit existing metadata without schema break**
- [ ] **Step 2: If schema changes, add migration note before code change**
- [ ] **Step 3: Add contract tests for profile id/version/digest**

### Task 4: Document frontend handoff

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1: Document catalog routes**
- [ ] **Step 2: Document profile selection is local-only and data-only**
- [ ] **Step 3: Document that remote template import remains Task 38**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_scan_profile_registry_service.py tests/web/test_scan_profile_routes.py tests/contracts/test_ai_system_map_schema.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Profile catalog lists bundled profiles with stable digest.
- Routes are read-only and safe for frontend usage.
- Profile/template metadata cannot contain executable hooks.
- Scan artifacts can trace profile lineage without replacing canonical map truth.


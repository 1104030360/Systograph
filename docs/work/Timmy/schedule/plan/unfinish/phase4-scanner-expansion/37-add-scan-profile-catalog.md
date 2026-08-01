# Scan Configuration Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 local data-only **scan configuration** catalog，追蹤 scanner preset、
compatibility與 build lineage；不得與 Phase2 capability profile registry或 AI System Capability
Map reference catalog混為同一個 `profile` truth。

**Architecture:** Scan configuration catalog是本機 metadata registry，不是 remote
marketplace。它只描述「用哪個 scanner preset / boundary / template version執行 build」，不
定義 capability detection。Phase2 `profile_registry.toml`擁有 capability display metadata；
`capability_reference_map.toml`擁有 fixed planes/nodes reference metadata；三者不得互相複製。

**Tech Stack:** Pydantic v2, bundled JSON/TOML metadata, FastAPI read-only routes, pytest.

---

## 最新狀態（2026-06-18）

- `rag-core-v1.json` 是 legacy v1 compatibility template；active新 catalog不得把它包裝成
  generic v2 capability truth。
- Task 24 已明確移除 remote template import；profile/catalog 不屬 Epic 1 blocker。
- Task 28 OpenAPI/generated SDK 先完成後，再新增 profile route 可避免前端 contract drift。

## Scope

- 建立 local scan configuration metadata：id、name、version、description、compatible
  canonical schema、optional legacy template id、digest、supported scan mode。
- Read-only API：list/get scan configurations。
- Plan 03A build lineage記錄 scan configuration id/version/digest；不修改或延伸
  `ai-system-map/v1` 作 active product contract。
- 與 project mapping profile page 可整合，但不取代 manual mapping overlay。

## Out of scope

- 不做 remote import。
- 不做 marketplace。
- 不執行 template scripts/hooks。
- 不讓 profile 改 scanner filesystem boundary。
- 不定義 planes/nodes、capability labels、detector rules、thresholds或 profile status。

### Task 1: Define scan configuration models and registry

**Files:**
- Create: `src/systograph/core/models/scan_configuration.py`
- Create: `src/systograph/core/services/scan_configuration_registry_service.py`
- Create: `src/systograph/core/scan_configurations/default-static-readiness.toml`
- Test: `tests/unit/core/test_scan_configuration_registry_service.py`

- [ ] **Step 1: Write model validation tests**
- [ ] **Step 2: Compute digest from bundled scan configuration content and referenced legacy template only when explicitly used**
- [ ] **Step 3: Reject profile metadata with unknown schema version or executable fields**
- [ ] **Step 4: Reject capability/profile/reference-map fields to prevent duplicate metadata ownership**

### Task 2: Add read-only scan configuration API

**Files:**
- Create: `src/systograph/web/routes/scan_configuration_routes.py`
- Modify: `src/systograph/web/app.py`
- Modify: `src/systograph/web/schemas.py`
- Test: `tests/web/test_scan_configuration_routes.py`

- [ ] **Step 1: Add `GET /api/scan-configurations`**
- [ ] **Step 2: Add `GET /api/scan-configurations/{configuration_id}`**
- [ ] **Step 3: Ensure responses include digest and compatibility but no local absolute paths**
- [ ] **Step 4: Ensure routes are read-only and do not instantiate scanner providers**

### Task 3: Record configuration lineage in Plan 03A build metadata

**Files:**
- Modify: Plan 03A build lineage / artifact manifest models
- Test: build repository and artifact manifest contract tests

- [ ] **Step 1: Add `scan_configuration_id/version/digest` to build lineage or artifact manifest, not canonical component truth**
- [ ] **Step 2: Keep v1 reader compatibility without adding new active v1 writer fields**
- [ ] **Step 3: Add contract tests for configuration id/version/digest and B1→B2 Apply reuse**

### Task 4: Document frontend handoff

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1: Document catalog routes**
- [ ] **Step 2: Document scan configuration selection is local-only and data-only**
- [ ] **Step 3: Document that any future remote import requires separate approval/validation and is not enabled by this catalog**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_scan_configuration_registry_service.py tests/web/test_scan_configuration_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Scan configuration catalog lists bundled presets with stable digest.
- Routes are read-only and safe for frontend usage.
- Configuration metadata cannot contain executable hooks、capability rules或 reference-map nodes。
- Plan 03A build metadata can trace configuration lineage without replacing canonical map truth。

## Dependencies and Follow-ups

- 依賴 Phase2 Plan 03A build lineage與 active v2 compatibility boundary。
- 必須與 Phase2 Plan 01A `capability_reference_map.toml`及 Plan 11
  `profile_registry.toml`維持不同 loader/model/ownership。
- Phase5 Task 42消費 backend capability projection，不消費 scan configuration catalog來
  推論 graph state。

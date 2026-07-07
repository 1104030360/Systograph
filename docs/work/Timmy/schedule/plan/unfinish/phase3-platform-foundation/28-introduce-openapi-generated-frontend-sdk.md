# OpenAPI Contract and Generated Frontend Types Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 FastAPI OpenAPI 變成 versioned machine-readable contract，產生 TypeScript 型別並加入 drift gate，逐步取代前端重複手寫的 response schemas。

**Architecture:** FastAPI/Pydantic 是 API schema source of truth；repo 匯出固定 OpenAPI artifact，前端先用 `openapi-typescript` 產生 types，再保留薄 fetch wrapper。第一階段不導入大型 full-client runtime，避免 codegen churn 與隱藏 transport policy。

**Tech Stack:** FastAPI OpenAPI, Pydantic v2, openapi-typescript, TypeScript, pnpm, CI.

---

## 最新狀態（2026-06-18）

- FastAPI runtime 已能產生 OpenAPI，但 repo 無 export script、versioned artifact 或 drift test。
- routes 尚未設定 stable `operation_id`。
- frontend 仍手寫 `fetch` 與 Zod schemas。
- GitHub issues：[#124](https://github.com/1104030360/Local-AI-Health-Doctor/issues/124)、[#158](https://github.com/1104030360/Local-AI-Health-Doctor/issues/158)、[#159](https://github.com/1104030360/Local-AI-Health-Doctor/issues/159)、[#179](https://github.com/1104030360/Local-AI-Health-Doctor/issues/179)。
- 本計畫在 #159 完成後執行；Task 25–27 未完成 endpoints 不得提前塞進 Epic 1 contract。
- 官方文件查證（2026-06-18）：FastAPI generated clients 依賴 OpenAPI `operationId`；若自訂 `operation_id` 或 `generate_unique_id_function`，必須保證每個 operation id 全域唯一。

### Task 1: Stabilize route operation IDs and response schemas

**Files:**
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/web/routes/*.py`
- Modify: `src/kai_mind/web/schemas.py`
- Test: `tests/contracts/test_openapi_schema.py`

- [ ] **Step 1: Write red test asserting unique stable operation IDs**
- [ ] **Step 2: Use explicit `operation_id` or one centralized unique-id function**
- [ ] **Step 3: Document 400/404/422 error models instead of relying on prose-only details**
- [ ] **Step 4: Assert no duplicate operation IDs**

### Task 2: Export a deterministic OpenAPI artifact

**Files:**
- Create: `scripts/export_openapi_schema.py`
- Create: `schemas/openapi.local-api.json`
- Test: `tests/contracts/test_openapi_schema.py`

- [ ] **Step 1: Export through `create_app().openapi()` without starting a server**
- [ ] **Step 2: Serialize with sorted keys and a trailing newline**
- [ ] **Step 3: Assert required current endpoints exist and deferred endpoints do not**

Required current endpoints:

```text
/api/projects/import
/api/scans
/api/map
/api/map/build
/api/viewer/load
/api/mappings
/api/mapping-proposals
/api/detail-scans
/api/trace
```

### Task 3: Generate frontend types

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/api/generated/schema.d.ts`
- Create: `frontend/src/api/client.ts`
- Modify: `frontend/src/services/viewerApi.ts`

- [ ] **Step 1: Add pinned `openapi-typescript` dev dependency and `api:generate` script**
- [ ] **Step 2: Generate types; generated file is never hand-edited**
- [ ] **Step 3: Migrate one stable flow (`GET /api/map`) to generated response types**
- [ ] **Step 4: Keep timeout, AbortController, error normalization, and validation in the thin wrapper**

### Task 4: Add drift detection

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: CI exports schema and regenerates types**
- [ ] **Step 2: CI fails when `git diff --exit-code` detects drift**
- [ ] **Step 3: Document human-readable vs machine-readable contract ownership**

## Verification

```bash
.venv/bin/pytest tests/contracts/test_openapi_schema.py -v
pnpm --dir frontend run api:generate
pnpm --dir frontend run build
git diff --exit-code -- schemas/openapi.local-api.json frontend/src/api/generated/schema.d.ts
```

## Acceptance Criteria

- Operation IDs are stable and unique.
- OpenAPI export does not require a running server or developer `.env`.
- Generated types cover current APIs without `any` fallback for core responses.
- Transport/safety behavior remains in reviewed frontend wrapper code.
- CI catches backend schema or generated-type drift.

## Official references

- FastAPI generated clients and operation IDs: https://fastapi.tiangolo.com/advanced/generate-clients/
- FastAPI path operation `operation_id`: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
- FastAPI OpenAPI extension: https://fastapi.tiangolo.com/how-to/extending-openapi/

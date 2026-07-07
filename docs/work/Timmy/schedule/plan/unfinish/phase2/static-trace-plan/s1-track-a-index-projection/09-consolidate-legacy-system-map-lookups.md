# 整合 Legacy System Map Lookups 實作計畫

> **2026-07-05 boundary sync：** Cleanup 後 reference catalog lookup 由 Plan 01A loader、
> repo fact lookup 由 `SystemMapIndex`、assessment/projection 由 Plan 02/06 各自擁有；
> 不得建立新的混合 lookup helper。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。本 cleanup 只收斂 canonical map lookup 與 v1/v2 branching；
`ua-analysis-result` 是 snapshot internal sidecar，不應成為新的 lookup helper 或 active
consumer dependency。Phase2 UA semantic 訊號**無消費者**（Plan 17 deferred）；未來重啟
時才經 Plan 17 candidate flow。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 在 00A/07/08 通過後，移除已被 normalized v2 `SystemMapIndex` 取代的
duplicated v1/local lookup helpers，保留有明確 ownership 的特殊 lookup。

**Architecture:** `CanonicalMapLoader` 是唯一 v1/v2 branching owner；
`SystemMapIndex` 是 normalized v2 canonical facts 的 shared lookup owner。Validation、
pre-map manual replay、projection-specific ids 與 runtime endpoint execution仍留在原 service。

**Tech Stack:** Python 3.11、pytest、`rg`、既有 service/route regression tests。

---

## 執行摘要

### 目標

刪除 08 已替換的 duplicate helpers與 inline dicts，讓後續工程師不會在 v1/v2
兩套 lookup 中選錯 source of truth。

### 背景

Migration 後若舊 loops 仍存在，新功能可能繞過 adapter/index，造成 evidence order、
unknown refs與 legacy extension behavior 漂移。

### 目前 code 狀態

候選主要在 `DetailScanService` 與 mapping proposal routes。Viewer risk membership、
validator invariant sets、manual live-evidence 與 query trace endpoint lookup不是 duplicate。

### 相關檔案

- Modify: `src/kai_mind/core/services/detail_scan_service.py`
- Modify: `src/kai_mind/web/routes/mapping_proposal_routes.py`
- Modify: `tests/unit/core/test_system_map_index.py`
- Modify: `tests/unit/core/test_detail_scan_service.py`
- Modify: `tests/web/test_mapping_proposal_routes.py`

### 實作步驟

先以 `rg` 建 inventory並分類 ownership；只刪除 08 已由 tests 證明等價的 helpers；
補 source-level guardrails，最後跑完整相關 regression。

### 驗收標準

Selected consumers 無 duplicate canonical lookup或 schema-version branching；剩餘 local
lookup 都有 validation、pre-map、projection或 runtime ownership 理由。

### 風險與注意事項

Cleanup 不得改 public schema、error text、graph fallback、candidate lifecycle或 trace
behavior。沒有 characterization test 的 helper 不刪。

## Consolidation Rule

```text
Normalized AiSystemMapV2 read-only fact lookup -> SystemMapIndex
Schema branching / v1 migration                 -> CanonicalMapLoader
Schema invariant enforcement                    -> SystemMapValidationService
Graph/view ids and risk membership              -> GraphProjectionService
Pre-map decision replay                         -> ManualMappingService
Runtime endpoint execution                      -> QueryTraceService
```

## Task 1：Inventory

- [ ] 搜尋 `_find_*`、inline `*_by_id` dict、`components_by_slot`、`extensions`、
  `schema_version` branches。
- [ ] 將每個 hit 標記為 remove/keep，並附 owning reason。
- [ ] 確認 v1 branching 只應存在 loader/adapter/legacy tests。

## Task 2：Delete Replaced Helpers

- [ ] 刪除 08 已替換的 detail scan component/edge/evidence/location helpers。
- [ ] 刪除 route-local target lookup與 id-list assembly。
- [ ] 移除 active consumer 對 `RagSystemMap.extensions` 的直接讀取。
- [ ] 每刪一組 helper立即執行對應 focused tests。

## Task 3：Preserve Explicit Exceptions

- [ ] 保留 validator cross-reference sets。
- [ ] 保留 manual mapping對 `ComponentDetectionResult` 的 live-evidence lookup。
- [ ] 保留 GraphProjectionService 的 render id/anchor/risk membership maps。
- [ ] 保留 QueryTraceService endpoint-not-found lookup，但 Plan 12 typed internal trace
  仍 deferred。

## Task 4：Guardrails

- [ ] Test 確認 detail scan/routes 不直接 import legacy v1 model。
- [ ] Test 確認 active consumers不出現 `schema_version == "ai-system-map/v1"`。
- [ ] Test 確認 loader/adapter之外無 `RagSystemMap.extensions` active access。
- [ ] Test 確認 `SystemMapIndex` 沒有 validate/save/infer/project methods。

## 驗收標準

- [ ] `CanonicalMapLoader` 是唯一 schema branching owner。
- [ ] `SystemMapIndex` 是 normalized v2 facts 的唯一 shared lookup owner。
- [ ] Detail scan與 proposal routes無 duplicate canonical lookup。
- [ ] 特殊 lookups 保留在正確 service並有 regression tests。
- [ ] 無 public contract或 behavior change。
- [ ] 本 cleanup 不阻擋 Plan 14；非必要 deletion 可在不保留雙重 truth下延後。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py \
  tests/unit/core/test_detail_scan_service.py \
  tests/web/test_mapping_proposal_routes.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py -q
rg -n "RagSystemMap|\.extensions|schema_version" \
  src/kai_mind/core/services src/kai_mind/web/routes
```

Expected：v1/extension hits 只在 loader、adapter、legacy migration或明確 compatibility tests。

## 不在範圍內

- 不移除 v1 schema/reader/adapter。
- 不改 validation、manual mapping、projection或 runtime ownership。
- 不新增 repository/cache/persistence。
- 不執行 Plan 12 runtime trace implementation。

## P0 Execution Mapping 補充（2026-07-03）

Legacy lookup cleanup 完成後，execution mapping 不應留下 parallel lookup stack：

- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 的 ref validation 共用
  normalized v2 loader/index。
- 舊 `FlowDerivationService` slot-order lookup 可保留作 baseline hint，但不得成為唯一 execution
  path source。
- `rg` cleanup gate 應檢查 routes/renderers 沒有直接 parse v1 slots 或 extensions 來畫 execution
  path。
- 本 cleanup 不刪 dynamic `00` artifacts；只刪 duplicate schema/version branching。

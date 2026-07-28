# 整合 Legacy System Map Lookups 實作計畫

> **狀態：已完成（2026-07-12）。** Backend implementation與驗證全部通過。

> **2026-07-05 boundary sync：** Cleanup 後 reference catalog lookup 由 Plan 01A loader、
> repo fact lookup 由 `SystemMapIndex`、assessment/projection 由 Plan 02/06 各自擁有；
> 不得建立新的混合 lookup helper。

> **2026-07-11 live-state sync：** Active persisted/viewer/detail/proposal contract在 Plan 13
> 前仍包含 v1 compatibility。Plan 08只遷移 canonical read-only resolution/packet assembly，
> 並刻意保留 detail child-map mutation與 slot/extension alias seam。因此本 cleanup使用
> owner allowlist，不要求 repo-wide `RagSystemMap`/`.extensions`/`schema_version` grep歸零。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。本 cleanup 只收斂 canonical map lookup 與 v1/v2 branching；
`ua-analysis-result` 是 snapshot internal sidecar，不應成為新的 lookup helper 或 active
consumer dependency。Phase2 UA semantic 訊號**無消費者**（Plan 17 deferred）；未來重啟
時才經 Plan 17 candidate flow。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 在 00A/05/06/07/08通過後，移除已被 normalized v2 `SystemMapIndex`與
Plan 08 resolvers/builders取代的 duplicated canonical read-only helpers，保留有明確
compatibility/domain ownership的特殊 lookup。

**Architecture:** 新 normalized consumer的 v1/v2 branching只經 `CanonicalMapLoader`；
`SystemMapIndex`是 normalized v2 canonical facts的 shared lookup owner。V2 validation、v1
detail mutation、legacy alias、adapter migration index、profile semantic maps、pre-map manual
replay、projection-specific ids與 runtime endpoint execution仍留在原 owner。

**Tech Stack:** Python 3.11、pytest、`rg`、既有 service/route regression tests。

---

## 執行摘要

### 目標

刪除 Plan 08已替換的 canonical read-only helpers與 inline dicts，並用 allowlist註明每個
剩餘 local lookup的 owner，讓後續工程師不會把必要 compatibility seam誤當 shared truth。

### 背景

Migration後若 selected consumer舊 loops仍存在，新功能可能繞過 adapter/index，造成
evidence order與 unknown refs漂移；反之若無差別刪除 v1 mutation/alias lookup，則會破壞
detail child build與已發布 extension/slot behavior。

### 目前 code 狀態

候選主要是 mapping proposal route的 `_find_unmapped`/local id assembly，以及 detail scan
read-only target/evidence resolution。Viewer risk/filter maps、v1 detail mutation、adapter
`_ComponentIndex`、v1/v2 validator sets、profile semantic maps、manual live-evidence與 query
trace endpoint lookup都不是 duplicate。

### 相關檔案

- Modify: `src/systograph/core/services/detail_scan_service.py`
- Modify: `src/systograph/core/services/detail_scan_target_resolver.py`
- Modify: `src/systograph/core/services/mapping_evidence_packet_builder.py`
- Modify: `src/systograph/web/routes/mapping_proposal_routes.py`
- Modify: `tests/unit/core/test_system_map_index.py`
- Modify: `tests/unit/core/test_detail_scan_service.py`
- Modify: `tests/web/test_mapping_proposal_routes.py`

### 實作步驟

先以 `rg` 建 inventory並分類 ownership/allowlist；只刪除 Plan 08已由 equivalence tests證明
取代的 helpers；補 source-level guardrails，最後跑完整相關 regression與 live API。

### 驗收標準

Selected normalized consumers無 duplicate canonical lookup或 schema-version branching；
剩餘 local lookup都有 adapter、validation、v1 mutation/alias、profile、pre-map、projection或
runtime ownership理由。

### 風險與注意事項

Cleanup 不得改 public schema、error text、graph fallback、candidate lifecycle或 trace
behavior。沒有 characterization test 的 helper 不刪。

## Consolidation Rule

```text
Normalized AiSystemMapV2 read-only fact lookup -> SystemMapIndex
Schema branching / v1 migration                 -> CanonicalMapLoader
V2 schema invariant enforcement                 -> SystemMapV2ValidationService
V1 child-map validation / mutation              -> SystemMapValidationService / DetailScanService
V1 slot / extension target aliases              -> Detail compatibility resolver
Adapter migration working index                 -> SystemMapV1ToV2Adapter._ComponentIndex
Graph/view ids and risk membership              -> GraphProjectionService
Profile related-ref / semantic maps             -> Profile inference / validation services
Pre-map decision replay                         -> ManualMappingService
Runtime endpoint execution                      -> QueryTraceService
```

## Task 1：Inventory

- [x] 搜尋 `_find_*`、inline `*_by_id` dict、`components_by_slot`、`.extensions`、
  `RagSystemMap`與 `schema_version` branches。
- [x] 將每個 hit標記為 remove/keep，keep必須對應 Consolidation Rule owner並記入本階段 REP。
- [x] 確認新 `SystemMapIndex`、`GraphProjectionService`、detail target resolver、mapping packet
  builder/route不自行 branch schema version；repo其他 v1 compatibility hits不要求歸零。

## Task 2：Delete Replaced Helpers

- [x] 刪除 Plan 08已替換的 detail scan canonical read-only target/evidence/location helpers；
  將仍需修改 deep-copied v1 map的 lookup明確命名為 compatibility mutation helper。
- [x] 刪除 mapping proposal route-local `_find_unmapped`與 id-list assembly，改由 normalized
  index + canonical packet builder提供。
- [x] 移除 selected normalized consumers對 `RagSystemMap.extensions` 的直接讀取；adapter、
  packet compatibility projection與 detail slot/extension alias owner可保留。
- [x] 每刪一組 helper立即執行對應 focused tests。

## Task 3：Preserve Explicit Exceptions

- [x] 保留 validator cross-reference sets。
- [x] 保留 manual mapping對 `ComponentDetectionResult` 的 live-evidence lookup。
- [x] 保留 GraphProjectionService 的 render id/anchor/risk membership maps。
- [x] 保留 QueryTraceService endpoint-not-found lookup，但 Plan 12 typed internal trace
  仍 deferred。
- [x] 保留 adapter `_ComponentIndex`、profile inference/validation semantic maps，以及 v1
  detail child-map mutation與 slot/extension aliases。

## Task 4：Guardrails

- [x] Test確認 `detail_scan_target_resolver.py`與 mapping proposal route/builder不直接 import
  legacy v1 models；`DetailScanService` compatibility mutation import列入 allowlist。
- [x] Test確認新 normalized consumers不出現 `schema_version ==` branch。
- [x] Test確認 `.extensions` access只出現在 adapter、detail compatibility或 mapping packet
  compatibility projection allowlist；不得出現在 generic index/projection。
- [x] Test 確認 `SystemMapIndex` 沒有 validate/save/infer/project methods。

## 驗收標準

- [x] `CanonicalMapLoader` 是新 normalized consumer的唯一 schema branching owner。
- [x] `SystemMapIndex` 是 normalized v2 facts 的唯一 shared lookup owner。
- [x] Detail target resolver與 proposal route/builder無 duplicate canonical lookup。
- [x] 特殊 lookups 保留在正確 service並有 regression tests。
- [x] 無 public contract或 behavior change。
- [x] Cleanup inventory/allowlist逐 hit有 owner evidence；`rg`有輸出不等於失敗，未分類 hit
  才是失敗。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py \
  tests/unit/core/test_detail_scan_target_resolver.py \
  tests/unit/core/test_detail_scan_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/web/test_mapping_proposal_routes.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py -q
.venv/bin/ruff check src tests
.venv/bin/mypy src tests
rg -n "RagSystemMap|\.extensions|schema_version" \
  src/systograph/core/services src/systograph/web/routes
git diff --check -- \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-a-index-projection/09-consolidate-legacy-system-map-lookups.md
```

Expected：每個 v1/extension/schema hit都能對應 Consolidation Rule owner；selected normalized
resolver/builder/route沒有未分類 hit。完整 pytest、Ruff與 scoped Mypy另依 Plan 08/phase4 gate
執行。

## 不在範圍內

- 不移除 v1 schema/reader/adapter。
- 不改 validation、detail child-map mutation/alias、manual mapping、profile、projection或
  runtime ownership。
- 不新增 repository/cache/persistence。
- 不執行 Plan 12 runtime trace implementation。

## P0 Execution Mapping 補充（2026-07-03）

Legacy lookup cleanup 完成後，execution mapping 不應留下 parallel lookup stack：

- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 的 ref integrity由
  normalized v2 validation/artifact load boundary負責；需要顯示 canonical refs時才共用 index。
- 舊 `FlowDerivationService` slot-order lookup 可保留作 baseline hint，但不得成為唯一 execution
  path source。
- `rg` cleanup gate應檢查 selected normalized routes/renderers沒有直接 parse v1 slots或
  extensions來畫 execution path；compatibility owner hits須逐一列入 allowlist。
- 本 cleanup不刪 dynamic `00` artifacts；只刪 test-proven duplicate canonical lookup與
  selected consumer schema/version branching。

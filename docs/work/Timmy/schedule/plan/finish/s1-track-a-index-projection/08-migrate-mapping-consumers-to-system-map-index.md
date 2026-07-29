# 將 Selected Consumers 遷移至 Generic SystemMapIndex 實作計畫

> **狀態：已完成（2026-07-12）。** Backend implementation與驗證全部通過。

> **2026-07-05 boundary sync：** Consumer migration 只讀 normalized repo facts；固定
> reference catalog、五態與 activation 由 Plan 01A/02/06 擁有。本計畫不得重新建立
> capability mapping 或把 legacy extension 轉成 active product node。

> **2026-07-11 live-state sync：** `MapBuildResult` 已同時保留 v1
> `ai_system_map` 與 normalized v2 map，但 active persisted/viewer/detail/proposal contract仍是
> v1。`DetailScanService` 會 deep-copy v1 map、append evidence/detail scans並產生 immutable
> child build；`AiSystemMapV2` 尚無 detail-scan write model。故本計畫遷移 read-only
> resolution/packet assembly，保留 versioned v1 mutation與 response compatibility owner。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。Detail scan 與 mapping proposal consumers 仍只讀
`CanonicalMapLoader` + `SystemMapIndex` 的 normalized repo facts；不得直接讀取
`ua-analysis-result` internal sidecar 或 UA 原生 semantic graph 來建立 proposal。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 在 00A/05/06/07穩定後，把 mapping proposal packet assembly與 detail scan的
canonical read-only target/evidence resolution遷移到 normalized v2 `SystemMapIndex`，
保持 public behavior等價。

**Architecture:** Route/service boundary先用現有 normalized build result，或以
`CanonicalMapLoader` 將 compatibility v1 map轉成 `AiSystemMapV2`，再建立
`SystemMapIndex`。Consumers不自行判斷 schema version、不持有 profile/readiness logic。
Legacy slot/extension alias resolution與 v1 child-map mutation保留在命名清楚的 compatibility
seam，不能偽裝成 generic canonical lookup。

**Tech Stack:** Python 3.11、FastAPI、pytest、SystemMapIndex、既有 route/service tests。

---

## 執行摘要

### 目標

遷移已有 characterization tests保護的 read-only resolution/packet assembly，不動 mapping
lifecycle、candidate ranking、manual decisions、detail child-build semantics、runtime trace或
viewer layout。

### 背景

Detail scan與 proposal route目前各自遍歷 v1 slots/extensions/unmapped/evidence。
Canonical target/evidence若繼續保留兩套 lookup，會形成 split-brain behavior；但在 Plan 13
提供 versioned v2 detail persistence前，直接刪除所有 v1 mutation lookup同樣會破壞行為。

### 目前 code 狀態

- `DetailScanService` 有多組 `_find_*` 與 evidence-file helpers。
- `mapping_proposal_routes.py` 自行 resolve unmapped targets與 available ids。
- Error codes、detail strings、evidence ordering 與 no-mutation behavior 已有 tests。
- `MappingEvidencePacket` / `MappingCandidateType` 仍公開
  `existing_slot_mapping` / `new_extension_component` compatibility fields；本計畫不可未經
  versioned migration移除。
- `DetailScanService.scan()` 會 deep-copy v1 map、append evidence/detail scans、attach ids並
  重新執行 v1 validation；這是 mutation owner，不是 duplicate read-only lookup。

### 相關檔案

- Modify: `src/kai_mind/core/services/detail_scan_service.py`
- Create: `src/kai_mind/core/services/detail_scan_target_resolver.py`
- Modify: `src/kai_mind/web/routes/mapping_proposal_routes.py`
- Modify: `src/kai_mind/core/services/mapping_evidence_packet_builder.py`
- Read: `src/kai_mind/core/services/canonical_map_loader.py`
- Modify: `tests/unit/core/test_detail_scan_service.py`
- Create: `tests/unit/core/test_detail_scan_target_resolver.py`
- Modify: `tests/unit/core/test_mapping_evidence_packet_builder.py`
- Modify: `tests/web/test_mapping_proposal_routes.py`
- Modify: `tests/unit/core/test_system_map_index.py`

### 實作步驟

先補 v1-adapted/v2-native read-only resolution/packet equivalence matrix，再逐一替換 lookup。
每個 consumer完成後先跑 focused tests，最後用 source checks確認新 consumer沒有 schema
branching外洩，並以 live API確認 compatibility response/child build不變。

### 驗收標準

V1-adapted與語意等價 v2 input對 canonical detail target resolution與 proposal packet產生
相同 status、error、evidence order與 masked evidence。Legacy slot/extension target與 response
仍由明確 compatibility seam讀取，直到 versioned replacement存在。

### 風險與注意事項

不得用 index隱藏 behavior change。V1 extension target/`new_extension_component` response是
已發布 compatibility contract；本計畫只阻止新 canonical logic依賴 extension-first model，
不做未版本化刪除。

## Task 1：Characterize Both Input Paths

- [x] 為 canonical detail target resolver與 mapping evidence packet建立 v1-adapted/v2-native
  pair fixtures；重用現有 v2 samples，不複製完整 project fixtures。
- [x] 鎖定 component、unmapped、edge、evidence、unknown target、related location/order與
  no-mutation；component slot/extension另鎖定 compatibility behavior。
- [x] 為 proposal route 鎖定 missing project/map/target status與 detail strings。
- [x] 鎖定 proposal packet的 evidence ids/rule ids/masked values/available slots/extensions/
  confirmed component ids，以及 public candidate response shape。
- [x] 鎖定 detail scan parent immutability、child build lineage、snapshot stale、evidence append、
  `detail_scans` append與 v1 validation。
- [x] 執行：

```bash
.venv/bin/pytest tests/unit/core/test_detail_scan_service.py \
  tests/web/test_mapping_proposal_routes.py -q
```

Expected：遷移前 characterization 全部 PASS。

## Task 2：Migrate Mapping Proposal Packet Assembly

- [x] Route優先使用 build result既有 normalized map；只有 compatibility-only in-memory result
  才呼叫 `CanonicalMapLoader`，不得自行 inspect `schema_version`。
- [x] 使用 `SystemMapIndex.unmapped_by_id()` resolve target，並讓
  `MappingEvidencePacketBuilder` 接 canonical unmapped/evidence/component facts。
- [x] Available slots/extensions只從 adapter metadata做 compatibility projection；confirmed
  ids只取 repo components。Index不新增 slot/extension-specific public methods。
- [x] `unmapped_not_found`、evidence ordering、masked snippets/values、provider fallback、
  project scope與 map no-mutation保持不變。
- [x] 保留 `new_extension_component`與現有 response fields；移除它屬未來 versioned contract
  migration，不是本計畫 lookup refactor。

## Task 3：Migrate Detail Read-only Resolution

- [x] 抽出 pure `DetailScanTargetResolver`，以 `SystemMapIndex` resolve canonical
  component/unmapped/edge/evidence與 `related_locations_for_evidence_ids()`；不讀 filesystem、
  不執行 scan、不 mutate map。
- [x] `component_slot`與 `extension`是 v1 alias targets，留在命名清楚的 compatibility
  resolver；不得加入 generic index API。Resolver output統一成 target type/id/related files。
- [x] `DetailScanService`在 scan前使用 read-only resolver；deep-copy後的 target mutation、
  evidence append、`detail_scans` append與 v1 validation仍由 service/compatibility materializer
  負責，不放入 index。
- [x] Workflow JSON evidence locations保留 JSON pointer/config key；只有 project-relative
  path可進 related files。Unknown target維持 `DetailScanTargetError("target_not_found")`。
- [x] Parent build immutability、child lineage、snapshot fingerprint與 profile-sidecar fail-closed
  behavior保持不變。

## Task 4：Boundary Tests

- [x] 不遷移 `ManualMappingService._has_live_evidence()`，它操作 pre-map detection result。
- [x] 不遷移 `MappingProposalService` heuristics/provider lifecycle。
- [x] 不遷移 runtime trace endpoint execution或 viewer-specific graph lookup。
- [x] Normalized v2 validation仍由 `CanonicalMapLoader` /
  `SystemMapV2ValidationService` 擁有；v1 detail child-map mutation仍由
  `SystemMapValidationService` fail closed。
- [x] 保留 v1 detail child-map mutation與 legacy slot/extension alias resolution；這些不是
  generic canonical duplicate。
- [x] Source check確認新 resolver/builder/routes無 `schema_version ==` branch，且 index未新增
  slot/extension/profile/readiness methods。

## 驗收標準

- [x] Selected read-only resolution/packet paths只讀 normalized v2 index；v1 mutation與
  response compatibility seam有明確命名與 tests。
- [x] V1-adapted/v2-native resolver/packet semantic equivalence tests通過。
- [x] Public HTTP/error/evidence ordering behavior 不變。
- [x] 本計畫不新增 extension-first contract，也不未版本化移除既有 extension response。
- [x] Index、read-only resolver與 packet builder不 mutate map/profile/readiness artifacts。
- [x] Detail scan mutation只發生於 deep-copied child v1 map；parent/canonical index/profile/
  readiness保持 immutable。
- [x] 本計畫是 post-06B refactor，不阻擋已完成的 profile/readiness/projection outputs。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py \
  tests/unit/core/test_detail_scan_target_resolver.py \
  tests/unit/core/test_detail_scan_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/web/test_mapping_proposal_routes.py \
  tests/web/test_detail_scan_routes.py \
  tests/web/test_detail_scan_build_binding.py \
  tests/unit/core/test_mapping_proposal_service.py -q
.venv/bin/ruff check src/kai_mind/core/services/detail_scan_service.py \
  src/kai_mind/core/services/detail_scan_target_resolver.py \
  src/kai_mind/core/services/mapping_evidence_packet_builder.py \
  src/kai_mind/web/routes/mapping_proposal_routes.py
.venv/bin/mypy src tests
git diff --check -- \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-a-index-projection/08-migrate-mapping-consumers-to-system-map-index.md
```

## 不在範圍內

- 不改 candidate ranking、LLM proposal config或 manual storage。
- 不新增 mapping API actions。
- 不改 runtime trace與 frontend projection。
- 不對外暴露 `SystemMapIndex`。
- 不在缺少 v2 detail persistence model時把 v1 child-map mutation改成 partial v2 write。

## P0 Execution Mapping 補充（2026-07-03）

Consumer migration 也要避免 execution artifacts 重新發明 lookup：

- Detail scan、mapping proposal若未來需要顯示 execution path related refs，必須透過
  validated artifact load boundary與 `SystemMapIndex` resolve canonical ids，而不是各自直接
  parse `call_graph.json`。
- Mapping consumers 不得根據 execution path 自動建立 manual mapping decisions。
- API response 可以提供 execution artifact paths 或 ids，但不能暴露 absolute local paths。
- 本計畫不遷移 dynamic `01` runtime trace；runtime refs 後續也應使用同一 lookup contract。

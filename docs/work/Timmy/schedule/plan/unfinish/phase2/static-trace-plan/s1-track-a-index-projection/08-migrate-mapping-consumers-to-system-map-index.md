# 將 Selected Consumers 遷移至 Generic SystemMapIndex 實作計畫

> **2026-07-05 boundary sync：** Consumer migration 只讀 normalized repo facts；固定
> reference catalog、五態與 activation 由 Plan 01A/02/06 擁有。本計畫不得重新建立
> capability mapping 或把 legacy extension 轉成 active product node。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。Detail scan 與 mapping proposal consumers 仍只讀
`CanonicalMapLoader` + `SystemMapIndex` 的 normalized repo facts；不得直接讀取
`ua-analysis-result` internal sidecar 或 UA 原生 semantic graph 來建立 proposal。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 在 00A/05/07 穩定後，把 detail scan 與 mapping proposal packet assembly
遷移到 normalized v2 `SystemMapIndex`，保持 public behavior 等價。

**Architecture:** Route/service boundary 先用 `CanonicalMapLoader` 取得
`AiSystemMapV2`，再建立 `SystemMapIndex`。Consumers 不自行判斷 v1/v2、不讀 legacy
extensions、不持有 profile/readiness logic。

**Tech Stack:** Python 3.11、FastAPI、pytest、SystemMapIndex、既有 route/service tests。

---

## 執行摘要

### 目標

只遷移已有 characterization tests 保護的低風險 read-only consumers，不動 mapping
lifecycle、candidate ranking、manual decisions、runtime trace 或 viewer layout。

### 背景

Detail scan 與 proposal routes 目前各自遍歷 v1 slots/extensions/unmapped/evidence。
Plan 13 切換 v2 後，若保留兩套 lookup，會形成 split-brain schema behavior。

### 目前 code 狀態

- `DetailScanService` 有多組 `_find_*` 與 evidence-file helpers。
- `mapping_proposal_routes.py` 自行 resolve unmapped targets與 available ids。
- Error codes、detail strings、evidence ordering 與 no-mutation behavior 已有 tests。

### 相關檔案

- Modify: `src/kai_mind/core/services/detail_scan_service.py`
- Modify: `src/kai_mind/web/routes/mapping_proposal_routes.py`
- Modify: `tests/unit/core/test_detail_scan_service.py`
- Modify: `tests/web/test_mapping_proposal_routes.py`
- Modify: `tests/unit/core/test_system_map_index.py`

### 實作步驟

先補 v1-adapted/v2-native characterization matrix，再逐一替換 lookup。每個 consumer
完成後先跑 focused tests，最後用 source checks 確認沒有 schema branching 外洩。

### 驗收標準

V1 legacy input 與語意等價的 v2 input，對 detail scan/proposal routes 產生相同
status、error、evidence order 與 candidate packet；active flow 不讀 extensions。

### 風險與注意事項

不得用 index 隱藏 behavior change。V1 extension target 由 adapter 轉成 generic
legacy component/capability candidate ref；new API 不再暴露 extension product concept。

## Task 1：Characterize Both Input Paths

- [ ] 為 detail scan 建立 v1-adapted與 v2-native pair fixtures。
- [ ] 鎖定 component、edge、evidence、unknown target、related location 與 no-mutation。
- [ ] 為 proposal route 鎖定 missing project/map/target status與 detail strings。
- [ ] 鎖定 generic component taxonomy targets與 non-baseline capability candidates。
- [ ] 執行：

```bash
.venv/bin/pytest tests/unit/core/test_detail_scan_service.py \
  tests/web/test_mapping_proposal_routes.py -q
```

Expected：遷移前 characterization 全部 PASS。

## Task 2：Migrate DetailScanService

- [ ] Constructor/method 接收 normalized v2 map 或 prebuilt `SystemMapIndex`。
- [ ] 使用 `component_by_id`、`edge_by_id`、`evidence_for_ids`、
  `related_locations_for_evidence_ids`。
- [ ] Workflow component detail 保留 JSON pointer/config key evidence locations。
- [ ] Unknown target 維持 `DetailScanTargetError("target_not_found")`。
- [ ] 不把 detail scan staging/mutations 放入 index。

## Task 3：Migrate Mapping Proposal Route

- [ ] Route 使用 `CanonicalMapLoader`，不直接 parse schema version。
- [ ] Packet 使用 generic component ids/types/layers、grounding dimensions 與
  capability candidate ids。
- [ ] Legacy extension aliases 只由 adapter 解析；new response 不含
  `new_extension_component`。
- [ ] Proposal create/decide 仍 project-scoped，且不 mutate canonical map。

## Task 4：Boundary Tests

- [ ] 不遷移 `ManualMappingService._has_live_evidence()`，它操作 pre-map detection result。
- [ ] 不遷移 `MappingProposalService` heuristics/provider lifecycle。
- [ ] 不遷移 runtime trace endpoint execution或 viewer-specific graph lookup。
- [ ] 不把 canonical validation 移出 `SystemMapValidationService`。
- [ ] Source check 確認 detail scan/routes 無 `schema_version ==` 分支。

## 驗收標準

- [ ] Selected consumers 只讀 normalized v2 index。
- [ ] V1-adapted/v2-native semantic equivalence tests 通過。
- [ ] Public HTTP/error/evidence ordering behavior 不變。
- [ ] New API 不 expose extension-first contract。
- [ ] Consumer 不 mutate map/profile/readiness artifacts。
- [ ] 本計畫是 post-vertical-slice refactor，不阻擋 02/03/06 outputs。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py \
  tests/unit/core/test_detail_scan_service.py \
  tests/web/test_mapping_proposal_routes.py \
  tests/unit/core/test_mapping_proposal_service.py -q
.venv/bin/ruff check src/kai_mind/core/services/detail_scan_service.py \
  src/kai_mind/web/routes/mapping_proposal_routes.py
.venv/bin/mypy
```

## 不在範圍內

- 不改 candidate ranking、LLM proposal config或 manual storage。
- 不新增 mapping API actions。
- 不改 runtime trace與 frontend projection。
- 不對外暴露 `SystemMapIndex`。

## P0 Execution Mapping 補充（2026-07-03）

Consumer migration 也要避免 execution artifacts 重新發明 lookup：

- Detail scan、mapping proposal、viewer routes 若需要顯示 execution path related refs，必須透過
  `SystemMapIndex` / shared lookup，而不是各自讀 `call_graph.json`。
- Mapping consumers 不得根據 execution path 自動建立 manual mapping decisions。
- API response 可以提供 execution artifact paths 或 ids，但不能暴露 absolute local paths。
- 本計畫不遷移 dynamic `01` runtime trace；runtime refs 後續也應使用同一 lookup contract。

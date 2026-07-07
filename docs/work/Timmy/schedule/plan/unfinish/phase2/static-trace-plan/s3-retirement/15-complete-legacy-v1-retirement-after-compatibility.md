# 完全遷移：Legacy v1 / Extension 相容層退役計劃

> **執行者注意：** 本計畫只能在 **Gate-4** 通過後執行：`00A` compatibility gate、
> `13` active v2 cutover、`14` final validation 與 `18` provider retirement 都已通過，且
> Plan 14 report 可回溯。逐 task、逐 test file 做，不得跳過相容遷移或提前移除 v1。
>
> REQUIRED SUB-SKILL: `superpowers:test-driven-development`（characterization ->
> migration guard -> removal -> regression）。

**Goal:** 在已證明 v1 artifacts 可相容遷移、active output 已切到
`ai-system-map/v2`、且 Plan 14 已驗證真實 import / workflow fixtures 後，移除不再需要的
v1 write path、legacy extension product surface 與 dual-read 長期維護負擔。

**Architecture:** 本計畫是 expand-and-contract 的 **contract phase**，不是 hard cut。
`00A` 先建立 v1/v2 dual-read 與 v1-to-v2 adapter；`13` 切換 active v2；`14` 驗證
active v2 與 legacy import；本計畫再把 legacy compatibility 降為 migration-only 或刪除。
`rag-core-v1@1.1.0` 可保留為 scanner 內部 grounding template，但不得作為 active
canonical schema 或 top-level `extensions[]` 產品 surface。

**Tech Stack:** Python 3.11、Pydantic v2、JSON Schema、pytest、Ruff、mypy、frontend
pnpm build/lint。

---

## 2026-07-05 Active Contract and Execution Gate

Plan 15 是 active plan，但只能在 Gate-4 通過後開始：Plan 14 必須完成並留下通過、可回溯
的 validation report，且 Plan 18 已完成 KAI TOML provider retirement。若 `00A`、`13`、
`14`、`18` 任一 gate 未通過，Plan 15 必須維持 pending，不得提前清除 compatibility code。

退役後的 active v2 contract 必須保留：

- 固定 10-plane / 52-node reference map + repo overlay；Governance / observability 是
  canonical plane，cross-plane governance lens 只作 derived view。
- Reference capability node 與 repo component 是不同 semantic kind。
- 五態 `detected` / `partial` / `undetermined` / `not_detected` / `conflicted`。
- 六種 `activation`、direct / indirect / explicit-negative evidence、field-specific
  conflicts 與 `not_detected` coverage gate。
- `build_id`、`scan_id`、`environment_id` assessment scope；`scan_id` 識別 immutable
  scan snapshot，不另設 `snapshot_id`。
- 可重算 Mapping Completeness：detected 1、not_detected 1、partial 0.5、其餘 0；
  denominator 是全部固定 reference nodes，activation/not_applicable 不排除 node；它不是
  confidence。

Legacy 三態資料只允許由 migration adapter 讀取並轉成 active 五態 contract；不得保留
三態 active writer、API 或 viewer 分支。

## 2026-07-07 UA 整合對齊

Plan 15 的 legacy v1 / extension 退役不包含 UA sidecar 退役。UA 已成為 Step 3 primary
scanner 後，Plan 15 只確認 active v2 / static execution artifacts 不依賴 legacy v1 或
extension surface；KAI TOML scan providers 的主掃描路徑退役由 Plan 18 在 Plan 14 parity
gate 通過後處理。

## 執行摘要

### 目標

把 Phase2 從「v1/v2 相容過渡」收斂到「v2-only active product contract」，並確保所有
legacy v1 / extension 移除都有 migration report、fixtures 與 regression tests 保護。

### 背景

使用者已確認遷移策略：**先相容遷移確認沒問題，再完全遷移**。因此本計畫不可再主張
跳過 `00A`、不做 adapter 或直接刪除 legacy surface。若尚未完成 00A/13/14，本計畫只能保持 pending。

### 目前 code 狀態

執行本計畫前必須重新 audit `src/`、`tests/`、`schemas/`、`frontend/src/`：

- `ai-system-map/v2` model/schema 是否已是 active output。
- v1 fixtures 是否已能透過 adapter 匯入並產生等價 v2 facts。
- `ExtensionComponent` / `new_extension_component` 是否只剩 legacy reader 或測試資料。
- P0 execution artifacts 是否已能與 v2 build 同 run directory 產出。

### 相關檔案

- `src/kai_mind/core/models/ai_system_map_v2.py`
- `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`
- `src/kai_mind/core/services/canonical_map_loader.py`
- `src/kai_mind/core/services/system_map_normalize_service.py`
- `src/kai_mind/core/services/system_map_validation_service.py`
- `src/kai_mind/core/providers/output_artifact_provider.py`
- `schemas/ai-system-map.v2.schema.json`
- `tests/fixtures/ai_system_map/`
- `tests/contracts/test_ai_system_map_v2_schema.py`
- `frontend/src/types.ts`
- `docs/MODEL-CONTRACT.md`
- `docs/API-GUIDE.md`
- `frontend/API_CONTRACT.md`

### 實作步驟

先鎖定 00A/13/14 報告與 fixtures，再新增 legacy-surface absence tests；接著移除 v1 write
path、extension product surface 與長期 dual-read 分支，最後跑 v2-only artifact / frontend /
CLI / API regression gate。

### 驗收標準

- [ ] `00A` compatibility report、`13` cutover report、`14`
  final validation report 都存在且通過。
- [ ] 新 build 只輸出 `schema_version="ai-system-map/v2"` 的 `ai_system_map.json`。
- [ ] `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、`evidence_table.json`
  與 `execution_map.mmd` 若已由 dynamic `00` 納入 P0，仍由同一 validated v2 build result
  產生，不依賴 v1 slots。
- [ ] active `src/`、`tests/`、`frontend/src/` 不再有 `NEW_EXTENSION` /
  `ExtensionComponent` product path；legacy 字串只允許出現在 migration fixtures、明確
  deprecated tests 或 docs。
- [ ] v1 artifacts 的保留策略明確：刪除、移入 migration-only helper，或以 explicit error
  指示使用 migration tool；不得留下 silent dual-read。
- [ ] `uv run pytest`、`ruff check`、`mypy src`、`cd frontend && pnpm build && pnpm lint`
  全部通過。

### 風險與注意事項

這是 breaking cleanup，只能在相容路徑已驗證後做。若發現仍有外部 consumer、未遷移 fixture
或 Plan 14 真實 repo 仍依賴 v1 shape，必須停止本計畫並回到 00A/13 修相容層。

## P0 Execution Mapping 補充（2026-07-03）

完全遷移後，P0 的 static inferred execution mapping 不能被退役流程誤刪：

- `ai_system_map.json` 保留 canonical components/edges/evidence。
- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 是 derived static trace
  artifacts；不得寫回 canonical map。
- `execution_map.mmd` 是 renderer output；不得被 viewer runtime trace overlay 取代。
- 所有 execution steps 必須保留 `runtime_verified=false` 或等效 limitations，直到
  dynamic `01` runtime trace 明確觀測到 target app 回傳 envelope。

## Migration Readiness Gate

執行本計畫前先新增或確認以下測試：

- [ ] v1 fixture 經 00A adapter 後的 v2 components、edges、evidence ids 完整保留。
- [ ] v2-native fixture 與 v1-adapted fixture 產生相同 readiness/profile/report 結論。
- [ ] Plan 14 的四象限 fixture、workflow JSON fixture 與至少兩個 direct import target 通過。
- [ ] Plan 14 已驗證固定 reference map + repo overlay、五態、activation、evidence kind、
  conflict、coverage gate、assessment scope 與 Mapping Completeness。
- [ ] `rg -n "ai-system-map/v1|RagSystemMap|ExtensionComponent|NEW_EXTENSION|new_extension_component" src tests frontend/src`
  的 hit 全部有分類：remove、migration-only、deprecated-test 或 docs。

## Implementation Tasks

### Task 1：凍結相容遷移報告

- [ ] 將 00A compatibility report、13 cutover report、14 validation report 路徑寫入本計畫的
  implementation issue 或 migration checklist。
- [ ] 新增 regression test，若缺少 v1-to-v2 adapter coverage 或 active v2 output test，本計畫
  fail closed。

### Task 2：移除 v1 write path

- [ ] 找出 `MapBuildService`、CLI、web routes、artifact provider 中仍能寫出
  `ai-system-map/v1` 的 code path。
- [ ] 先新增 failing tests，要求新 build 一律輸出 v2。
- [ ] 移除或封存 v1 write branch；保留 migration-only reader 時必須命名清楚，不可與 active
  loader 混用。

### Task 3：退役 Extension product surface

- [ ] 將 `ExtensionComponent`、`NEW_EXTENSION`、`new_extension_component` 的 active product
  usage 改成 generic components、unmapped components 或 non-baseline capability candidates。
- [ ] 保留 legacy fixture 時，加上 migration-only naming 與 test comments，避免新流程誤用。
- [ ] Frontend/API 不再顯示「新增 extension」作為使用者 action。

### Task 4：收斂 loaders 與 consumers

- [ ] `CanonicalMapLoader` 移除 silent dual-read default；若仍支援 v1，必須只作 explicit
  migration command 或 explicit compatibility test helper。
- [ ] `SystemMapIndex`、profile inference、readiness、graph projection、detail scan、mapping
  consumers 全部讀 normalized v2 facts。
- [ ] 移除 active 三態 writer/API/viewer 分支；若讀入 legacy 三態 fixture，必須透過
  explicit migration adapter 產生五態 assessment。
- [ ] 確認 graph projection 保留 fixed reference nodes 與 repo overlay semantic kinds，
  並由同一 build/snapshot/environment scope 產生。
- [ ] `schema_version` 分支不得散落在 routes、viewer 或 renderers。

### Task 5：同步 artifacts 與文件

- [ ] `OutputArtifactProvider` 的 artifact filename set 包含 P0 static execution outputs。
- [ ] `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`、`frontend/API_CONTRACT.md` 移除 v1 active
  output 語意，保留 migration note。
- [ ] `static-trace-plan/README.md` 與 `dynamic-trace-plan/README.md` 更新為 00A -> 13 -> 14
  -> 15 的順序。

### Task 6：完整 regression gate

```bash
uv run pytest
uv run ruff check
uv run mypy src
cd frontend && pnpm build && pnpm lint
```

Expected：tests、lint、typecheck 全部通過；若 frontend tooling 尚未安裝，記錄缺少的安裝步驟與
未驗證項目，不得假裝通過。

## 不在範圍內

- 不跳過 00A adapter / compatibility gate。
- 不把 static execution map 宣稱為 runtime trace。
- 不實作 Langflow/Dify/Flowise 完整 importer、round-trip 或 runtime semantics。
- 不新增 OpenTelemetry、trace persistence、RAG eval framework 或自動修 code。
- 不改 profile inference trigger logic；只移除 legacy surface。

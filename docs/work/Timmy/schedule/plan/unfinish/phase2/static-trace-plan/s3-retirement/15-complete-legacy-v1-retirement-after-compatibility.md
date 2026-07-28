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
`rag-core-v1@1.0.0`（**凍結內容**）可保留為 scanner 內部 grounding / migration-only
template，但不得 bump version、改 slots/flows，或作為 active canonical schema 或 top-level
`extensions[]` 產品 surface。

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

### Plan 13 Task 4 handoff（persisted mapping migration 暫時寫法）

Plan 13 Task 4 會先建立**過渡用** persisted mapping migration surface，讓舊
`mapping_type="new_extension_component"` JSON 能在刪除 active
`ManualMappingType.NEW_EXTENSION` 前安全搬家。這些寫法**不是**長期產品路徑：

| Plan 13 建立（暫時） | Plan 15 必須處理 |
| --- | --- |
| `LegacyManualMappingDTO`（migration-only 讀舊 shape） | 刪除或確認已無 active import |
| `LegacyManualMappingMigrationService` | 刪除；不得被 normal repository／API 再呼叫 |
| `migrate-legacy-mappings` CLI（`--dry-run` / `--apply`） | 刪除 command 註冊與實作 |
| state 目錄 backup／quarantine／migration report 產物與 helper | 清掉不再需要的 code；文件記載保留／清除策略 |
| active enum 已移除後仍殘留的 legacy 字串讀取分支 | 只允許 migration fixtures／deprecated tests／docs |

原則（2026-07-15 記錄）：

- Plan 13：**先搬家，再拆舊門**（migration 完成後 active path 停寫／停讀 legacy mapping type）。
- Plan 15：**搬家結束後丟掉紙箱**——移除上述暫時 migration 寫法，避免 dual-read／DTO／CLI
  變成永久維護負擔。
- normal API／`ManualMapping` repository **不得**在 Plan 15 後仍長期接受 legacy shape。

### 目前 code 狀態

執行本計畫前必須重新 audit `src/`、`tests/`、`schemas/`、`frontend/src/`：

- `ai-system-map/v2` model/schema 是否已是 active output。
- v1 fixtures 是否已能透過 adapter 匯入並產生等價 v2 facts。
- `ExtensionComponent` / `new_extension_component` 是否只剩 legacy reader 或測試資料。
- Plan 13 Task 4 的 `LegacyManualMappingDTO`、migration service、`migrate-legacy-mappings`
  CLI、quarantine／backup helpers 是否仍存在且僅 migration-only（或可安全刪除）。
- P0 execution artifacts 是否已能與 v2 build 同 run directory 產出。

### 相關檔案

- `src/kai_mind/core/models/ai_system_map_v2.py`
- `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`
- `src/kai_mind/core/services/canonical_map_loader.py`
- `src/kai_mind/core/services/system_map_normalize_service.py`
- `src/kai_mind/core/services/system_map_materialization_service.py`
  （operator-rollback-only v1 materializer。module docstring 已於 Plan 13.5 Stage D 明寫
  「Plan 15 removes it」——本清單補列，讓該承諾在計畫端有對應項目。）
- `src/kai_mind/core/services/system_map_validation_service.py`
- `src/kai_mind/core/services/legacy_slot_layer_map.py`
  （Plan 13.5 Task C5 抽出的 `SLOT_LAYER_BY_ID` 單一來源。**不可**隨 v1 adapter 一起刪：
  它同時被 `system_map_v1_to_v2_adapter.py`（Plan 15 刪）與 **active** 的
  `system_map_v2_normalize_service.py`（`layer=SLOT_LAYER_BY_ID.get(slot.slot, ...)`）
  import；刪 adapter 時必須明確裁定此 module 去留——v2 側仍需要它，最小處置是保留並
  改名／搬到中立位置，不是刪除。）
- `src/kai_mind/core/providers/output_artifact_provider.py`
- `src/kai_mind/core/models/mapping_base.py`（確認 active enum 已無 `NEW_EXTENSION`）
- `src/kai_mind/core/services/legacy_manual_mapping_migration_service.py`（Plan 13 建、本計畫刪）
- Legacy DTO／`migrate-legacy-mappings` CLI 註冊處（Plan 13 建、本計畫刪）
- `schemas/ai-system-map.v2.schema.json`
- `tests/fixtures/ai_system_map/`
- `tests/contracts/test_ai_system_map_v2_schema.py`
- `frontend/src/types.ts`
- `docs/MODEL-CONTRACT.md`
- `docs/API-GUIDE.md`
- `frontend/API_CONTRACT.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md`（Task 4 來源）

### 實作步驟

先鎖定 00A/13/14 報告與 fixtures，再新增 legacy-surface absence tests；接著移除 v1 write
path、extension product surface、**Plan 13 Task 4 暫時 mapping migration DTO／CLI／quarantine**
與長期 dual-read 分支，最後跑 v2-only artifact / frontend / CLI / API regression gate。

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
- [ ] Plan 13 Task 4 暫時 migration surface 已退役：`LegacyManualMappingDTO`、
  `LegacyManualMappingMigrationService`、`migrate-legacy-mappings` CLI、quarantine／backup
  helpers 已刪除或只剩文件化的 historical note；normal repository／API 不接受 legacy
  mapping shape。
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

### Task 3b：移除 Plan 13 Task 4 暫時 persisted mapping migration 寫法

> 來源：`13-retire-legacy-extension-contract.md` Task 4。Plan 13 只負責搬家與 active 停寫；
> **本 task 負責刪掉暫時 migration 工具**，避免 DTO／CLI／quarantine 變成永久維護面。

前置：Plan 13 cutover report 證明所有 legacy extension mappings 已 migrate（**任何**
unresolved `requires_manual_review` row 都阻擋，不只 `CONFIRMED`——見 Plan 13 Task 4），
reload gate 通過，且 active `ManualMappingType` 已無 `NEW_EXTENSION`。

Plan 13.5 交接的兩個前置事實（先確認再動手，可省一輪撞牆）：

- **`src/kai_mind/web/legacy_mapping_guards.py` 已與 migration module 解耦。** Plan 13.5
  Task B1 把 `new_extension_component` 內聯成字面值、移除對
  `legacy_manual_mapping_migration_service` 的 import。刪 module 前確認
  `rg legacy_manual_mapping_migration src/kai_mind/web/` 零命中即可，不需要再拆 web 層。
  **guard 本體不隨 module 刪除**——它的去留由下方 bullet 5（normal API 仍須 fail-closed）
  決定，兩者生命週期不同。
- **census 已看得見 enum 名稱，因此刪除是 census-guarded 的。** Plan 13.5 Task B2 把
  `LegacyManualMappingType` / `NEW_EXTENSION` 加進
  `tests/contracts/test_v2_cutover_consumer_allowlist.py` 的 `LEGACY_NAMES`。allowlist 是
  雙向 fail-closed：刪掉 module 卻沒同步移除對應 allowlist 記錄，會以 stale record 讓
  census contract test 失敗。這是設計行為，不是意外——**同一個 change 內必須一併移除記錄**。

- [ ] 刪除 `LegacyManualMappingDTO` 與任何仍能 parse `new_extension_component` 的
  migration-only model（若仍需歷史測試，改為明確 deprecated fixture + comment，不得掛在
  active import graph）。
- [ ] 刪除 `LegacyManualMappingMigrationService` 及對應 unit／integration tests 的 active
  production import；必要 characterization 改寫為「此 surface 已不存在」absence test。
- [ ] 移除 `migrate-legacy-mappings` CLI command 註冊、help 文案與 scripts 引用。
- [ ] 清除 quarantine／backup index helpers（**沒有** state-side migration report writer 這種
  東西——report 只是 CLI 回傳的 `LegacyMappingMigrationReport`，不落地成檔案，別去找不存在
  的 writer）。兩個 state 目錄的保留／刪除決策點必須明確裁定並寫進文件，不得靜默留 code
  path：
  - `<KAI_MIND_STATE_DIR>/migration-backups/<project>/` —— `<mapping>.<token>.legacy.json`
    （原 payload 的 **re-serialization**）+ `index.json`。
  - `<KAI_MIND_STATE_DIR>/migration-quarantine/<project>/` —— 兩種檔案：
    `<mapping>.<token>.legacy.json`（payload re-serialization，包 migration version 與
    input digest）與 `<mapping>.<token>.original.json`（**byte-exact** 原檔，Plan 13.5
    Task C6 新增，由 `_retire_original` move 進來）。
  - 檔案為 owner-only `0600`；**目錄維持 `0755`**（權限只做在檔案層）。
  - **清空 quarantine 袋 = 放行 cutover gate 的操作行為**：`cutover_blocked` 只要袋內還有
    `*.original.json` 就維持 `True`。同一個動作也會銷毀唯一的 byte-exact 遷移前證據
    （兩份 `*.legacy.json` 都是 re-serialization）。裁定保留策略時，這兩件事必須同時被
    看見——它不是單純的「清暫存檔」。
  - 語意詳述見 `docs/MODEL-CONTRACT.md` §7.0.1；`ManualMapping.audit_metadata` 的三個永久
    key 保留為 audit provenance，不在本 task 刪除範圍。
- [ ] 裁定 unparseable（report `status="failed"`）legacy row 的 custody（Plan 13.5 Task C6
  交接）。這類 row 走 `_failed_item` 路徑——JSON 不可解析時 payload 直接被當成 `{}`，連
  `project_id` 都拿不到；或 `LegacyManualMappingDTO.model_validate` 失敗——兩種都**不經**
  `_quarantine` / `_retire_original`。結果是檔案仍留在 `projects/<p>/mappings/`，且仍會讓
  `LocalJsonProjectRepository.list_for_project` 拋 `StateCorruptionError`、炸掉整個 project
  的 mapping 列舉（`read_model` 對 `OSError` / `JSONDecodeError` / `ValidationError` 一律
  fail closed）。Plan 15 必須擇一並文件化：提供人工清理指引，或建立 last-resort 隔離區
  （無可信 project id，需以檔案路徑而非 project 分桶）。不得預設「migration 跑完就沒有殘留」。
- [ ] 確認 normal mapping repository／API／UI：**拒絕** legacy mapping shape，回傳穩定
  error（沿用或收斂 Plan 13 的 `legacy_mapping_type_read_only`），且無 silent dual-read。
- [ ] `rg -n "LegacyManualMapping|migrate-legacy-mappings|legacy_manual_mapping_migration|new_extension_component" src tests frontend/src`
  的 hit 全部分類為 remove／deprecated-test／docs；不得剩 active caller。

### Task 3c：拆分 `models/system_map.py`（「刪 v1 model」的硬前置）

> 來源：Plan 13.5 audit RA-8 / RB-10。**不先做這件事，Task 2／Task 3 的「移除 v1 model」
> 字面上不可執行**——`models/system_map.py` 目前同時裝著純 v1 contract 與整條 active
> scan path 共用的 DTO，直接刪檔會炸掉 v2 主路徑。

- [ ] 把下列 11 個 **與 v1 契約無關、active path 仍在用**的 symbol 從
  `src/kai_mind/core/models/system_map.py` 拆到中立 module：
  `Evidence`、`Endpoint`、`Flow`、`Edge`、`RiskHint`、`DetailScanResult`、
  `QueryTraceEvent`、`CodePathStep`、`DetailScanFinding`、`UnmappedComponent`、
  `ScanDepth`（`Literal["system", "component", "code_path"]`）。
- [ ] **這 11 個是 audit 當時的已知最小集，不是完整清單——動手前必須重新推導。** 至少
  `ComponentInstance` 與 `ComponentSlot` 也仍被 active 的 `ComponentDetectionService`
  （Step 4 detection）使用，同樣不能留在待刪的 v1 檔內。真正只剩 v1 契約的候選是
  `Classification` / `Project` / `ReferenceArchitecture` / `ScanSummary` /
  `RagSystemMap` / `ExtensionComponent`（加共用基底 `ContractModel`）。
  `system_map.py` 收斂到只剩這些，才可整檔刪除。
- [ ] 風險提示：這些 symbol 目前被 `src/` 內 37 個檔案 import（`tests/` 另計），而 census
  （`test_v2_cutover_consumer_allowlist.py`）只追 `LEGACY_NAMES` 內的名字，**看不見**
  這批共用 DTO——不能靠 census 綠燈判斷「v1 已無 active 依賴」。
- [ ] `RecommendedNextCheck` **已不在**待拆清單：Plan 13.5 Task A1 已把它搬到
  `src/kai_mind/core/models/recommended_next_check.py`。剩下 11 個。

### Task 3d：移除 `ai_system_map_v2.py` 的 Compatibility / Generic 型別群

> 來源：Plan 13.5 audit RA-9。這批型別是 00A adapter 的搬運形狀，v1 read support 一旦
> 移除就沒有 producer。

- [ ] 移除 `CompatibilityContractModel` 及其整棵子樹：`CompatibilityProject`、
  `GenericComponent(Metadata)`、`GenericEdge(Metadata)`、`GenericEndpoint(Metadata)`、
  `GenericRiskHint(Metadata)`、`GenericUnmappedFact`、`GenericCandidateFact(Metadata)`、
  `AiSystemMapV2CompatibilityView`，以及只被這棵子樹使用的 `Compatibility*` 型別別名
  （`CompatibilitySchemaVersion`、`CompatibilitySystemType`、`CompatibilityActivation`、
  `CompatibilityComponentStatus`、`CompatibilityComponentSemanticKind`、
  `CompatibilityEdgeStatus`、`CompatibilityEndpointType`、`CompatibilityRiskTargetType`）。
  以刪除當時的實況重跑一次 grep，確認 producer 只剩 `SystemMapV1ToV2Adapter`。
- [ ] **不在移除範圍：`CanonicalLayer` / `CanonicalCandidateKind`。** 這兩個型別在 Plan 13.5
  Stage D 已由 `CompatibilityLayer` / `CompatibilityCandidateKind` **改名**並移出
  Compatibility 群——它們是 canonical model 的欄位型別（`CanonicalComponent.layer`、
  `CanonicalCandidateFact.candidate_kind`），改名的目的正是防止 Plan 15 連坐誤刪。
  檔內 `:77-80` 已留下對應註解。
- [ ] 連帶確認 `legacy_slot_layer_map.py`（`SLOT_LAYER_BY_ID`）的去留：它 import
  `CanonicalLayer`，且同時服務 v1 adapter（刪）與 active `SystemMapV2NormalizeService`
  （留）。見「相關檔案」該條。

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
- [ ] `static-trace-plan/README.md` 與 `dynamic-trace-plan/README.md` 更新為
  `00A -> 13 -> Gate-1 -> 16 -> Gate-2 -> 14 -> Gate-3 -> 18 -> Gate-4 -> 15`
  的順序（與 `static-trace-plan/README.md`「建議執行順序」及 `epic1-phase2.md` §20 DAG 一致）。
- [ ] 文件明確記載：Plan 18（KAI TOML provider 主掃描退役）為 Plan 15 的 Gate-4 前置，不可跳過。

### Task 5b：Plan 13.5 交接的兩個「不要誤刪 / 不要多做」註記

- [ ] **`RecommendedNextCheckService` 不在 v1 retirement 移除範圍。** 它在 Plan 13.5 Task A1
  已從 v1 normalize service 抽出、成為 active v2 service，新路徑
  `src/kai_mind/core/services/recommended_next_check_service.py`：active 路徑由
  `SystemMapV2MaterializationService` 持有並呼叫 `derive`，結果再傳給
  `SystemMapV2NormalizeService.assemble`；規則檔
  `src/kai_mind/core/rules/recommended_next_check_rules.toml` 自此屬 active 資產。
  刪除 v1 `SystemMapNormalizeService`（rollback writer）時，只移除**它對這個 service 的
  import／DI 欄位**，不得連 service 或規則檔一起刪。
- [ ] **三個無版本後綴的 legacy service 名稱不另行 rename。**
  `SystemMapMaterializationService`、`SystemMapNormalizeService`、
  `SystemMapValidationService` 的名字沒有 `V1` 後綴（active 對應物才是
  `SystemMapV2MaterializationService` / `SystemMapV2NormalizeService`），是已知的命名陷阱。
  處置已定案：Plan 13.5 Stage D 只在 module docstring 標示各自的實際定位（materialization
  與 normalize 明寫 operator-rollback-only + 「Plan 15 removes it」；validation service 標明
  它仍服務 `CanonicalMapLoader` 的 v1 讀取與 rollback writer 兩條路徑），**一律不改名**
  （改名會動 census allowlist 的 symbol 欄位）；名字於 Plan 15 刪檔時自然消滅。
  不要在 Plan 15 另開 rename task。

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

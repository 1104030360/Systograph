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
的 validation report，且 Plan 18 已完成 Systograph TOML provider retirement。若 `00A`、`13`、
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
extension surface；Systograph TOML scan providers 的主掃描路徑退役由 Plan 18 在 Plan 14 parity
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
| `migrate-legacy-mappings` CLI（`--state-dir` 必填 + `--apply`；省略 `--apply` 即零寫入 dry run，沒有 `--dry-run` flag） | 刪除 command 註冊與實作 |
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

- `src/systograph/core/models/ai_system_map_v2.py`
- `src/systograph/core/services/system_map_v1_to_v2_adapter.py`
- `src/systograph/core/services/canonical_map_loader.py`
- `src/systograph/core/services/system_map_normalize_service.py`
- `src/systograph/core/services/system_map_materialization_service.py`
  （operator-rollback-only v1 materializer。module docstring 已於 Plan 13.5 Stage D 明寫
  「Plan 15 removes it」——本清單補列，讓該承諾在計畫端有對應項目。）
- `src/systograph/core/services/system_map_validation_service.py`
- `src/systograph/core/services/legacy_slot_layer_map.py`
  （Plan 13.5 Task C5 抽出的 `SLOT_LAYER_BY_ID` 單一來源。**不可**隨 v1 adapter 一起刪：
  它同時被 `system_map_v1_to_v2_adapter.py`（Plan 15 刪）與 **active** 的
  `system_map_v2_normalize_service.py`（`layer=SLOT_LAYER_BY_ID.get(slot.slot, ...)`）
  import；刪 adapter 時必須明確裁定此 module 去留——v2 側仍需要它，最小處置是保留並
  改名／搬到中立位置，不是刪除。）
- `src/systograph/core/providers/output_artifact_provider.py`
- `src/systograph/core/models/mapping_base.py`（確認 active enum 已無 `NEW_EXTENSION`）
- `src/systograph/core/services/legacy_manual_mapping_migration_service.py`（Plan 13 建、本計畫刪）
- Legacy DTO／`migrate-legacy-mappings` CLI 註冊處（Plan 13 建、本計畫刪）
- `schemas/ai-system-map.v2.schema.json`
- `tests/fixtures/ai_system_map/`
- `tests/contracts/test_ai_system_map_v2_schema.py`
- `frontend/src/types.ts`
- `docs/MODEL-CONTRACT.md`
- `docs/API-GUIDE.md`
- `frontend/API_CONTRACT.md`
- `docs/work/Timmy/schedule/plan/finish/s1-v2-cutover/13-retire-legacy-extension-contract.md`（Task 4 來源）

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
- [ ] `uv run pytest`、`ruff check src tests`、`mypy src tests`、
  `cd frontend && pnpm build && pnpm lint` 全部通過。

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

## 2026-08-06 補充：查核結果、使用者決策與新增前置

本節由 2026-08-06 的四路平行程式碼查核（v1 rollback/adapter、rag-core-v1 template、
建置管線、models/CLI/schemas 四個叢集）補入，含實測證據。**與上方原有內容衝突時，
以本節為準**（原有內容成文於 Plan 13 完成前）。

### 使用者決策（2026-08-06）

- **策略 A：只認 v2，拒絕讀／寫 v1。** 不做一次性 migration tool，不保留 dual-read。
- **讀不出來的舊 artifact 與歷史 build 直接刪除**（專案仍在開發期，無正式使用者資料）。
  此決策**同時涵蓋 `${SYSTOGRAPH_STATE_DIR:-~/.systograph}` 內的歷史 build state**，
  不只是 `outputs/` 下的檔案——見下方「策略 A 的實際爆炸半徑」。
- 本計畫已於同日由 `phase2/static-trace-plan/s3-retirement/` 移入
  `refactor/`，**編號 15 保留**以維持 issue／commit／report 對應。

### Gate 現況（2026-08-06 實測，**尚未通過**）

| 前置 | 狀態 |
|---|---|
| `00A` compatibility gate | 已完成 |
| `13` active v2 cutover | 已完成（2026-08-05 移入 `finish/`） |
| **`14` final validation** | **未完成**——`docs/work/Timmy/schedule/report/` 內查無任何 Plan 14 report |
| **`18` provider retirement** | **未完成**——issue **#239 仍 OPEN** |

**結論：Gate-4 未通過，本計畫維持 pending。** 現階段只能執行下方「Task 0」
（與 Gate 無關的純增測試）。

> **注意 issue 狀態與程式碼實況矛盾：** issue **#240
> 「refactor: retire legacy v1 compatibility」已於 2026-07-20 關閉並標記
> completed**，但它應退役的 v1 程式碼一行未動。疑為批次或提前關閉，
> 執行本計畫前應先釐清 #240 與本計畫的關係，避免重複開票或誤判進度。

### 查核結論：`ai-system-map/v1` 已隔離，active path 零執行（實測）

以 `tests/fixtures/rag_projects/basic_qdrant_ollama_rag` 實跑 `MapBuildService().build`
並對 `CanonicalMapLoader._load_v1` / `SystemMapV1ToV2Adapter.*` 插樁：

```text
CanonicalMapLoader.load: 1    _load_v2: 1
_load_v1: 0    adapt / to_canonical / adapt_to_canonical: 0
operator_rollback_active: False    migration_warnings: []
sys.modules 內 legacy_v1_rollback_service / system_map_materialization_service
             / system_map_normalize_service：皆為 False（未載入）
```

- `src/systograph/` 內含 census 詞彙（`ai-system-map/v1`、`RagSystemMap`、
  `ExtensionComponent`、`SystemMapValidationService`、`LegacyManualMappingType`、
  `NEW_EXTENSION`、`new_extension_component`）的 23 個檔案中，**沒有任何一處是死碼**
  ——全部經 operator rollback 或 v1-payload 讀取路徑可達。其中 20 個已登記於
  `tests/contracts/test_v2_cutover_consumer_allowlist.py`；另外三個
  （`cli/viewer_command.py`、`core/models/recommended_next_check.py`、
  `core/services/recommended_next_check_service.py`）只以子字串或註解形式出現，
  **逃過 census**——正是下方 Task 0 要補的盲區。
- Plan 13.5 Task B3 的 function-local import 隔離**今日仍然有效**。

### 新增前置事實：三個原有 Task 未涵蓋的約束

**(1) 型別共用造成的原子性約束（原計畫未標示）**

`canonical_output_configuration.py:12` 的 `LEGACY_CANONICAL_OUTPUT_VERSION`、
`models/map_build.py:28` 的 `SystemMapSchemaSelection`、`web/schemas.py:54,226` 與
`cli/map_command.py:52-58` 的 deprecated 輸入**共用同一個型別**。deprecated 輸入
依賴該型別的 v1 成員才能產生穩定的 `legacy_output_not_selectable` 錯誤碼。

→ **四者必須在同一個 change 內原子移除。** 分批處理會讓送 v1 的請求從穩定錯誤碼
退化成 pydantic 泛用 422，破壞 `docs/API-GUIDE.md:1043` 的錯誤碼契約。allowlist 內
四筆記錄各自寫「Plan 15 removes...」但未標示彼此相依，執行時勿被誤導。

**(2) `models/analysis_history.py:158-166` 的 v1 預設值是 load-bearing**

`MapBuildManifest.active/requested_schema_version` **預設值是 `"ai-system-map/v1"`**，
因為 pre-#202 寫入的 manifest JSON 沒有這兩欄，那些 build 本來就是 v1；
`BuildManifestService.load:136` 用它做 badge-vs-artifact fail-closed 比對。

→ **在策略 A 下，這是「歷史 build 讀不出來」的具體機制。** 依使用者決策，直接
接受並清除歷史 state；但**不得**用「把預設值改成 v2」來繞過——那會讓歷史 manifest
的 fail-closed 比對永久錯判，屬 P1 regression。正確做法是連同舊 state 一併清除。

**(3) import-graph 仍有 v1 洩漏（runtime 無行為，但模組會載入）**

`CanonicalMapLoader.__init__`（`:101-107`）在每次 active build 都**無條件建構**
`SystemMapValidationService()`（v1 驗證器）與 `SystemMapV1ToV2Adapter()`；
入口是 `BuildArtifactPublisher.__init__:82` → `ViewerSessionService.__init__:71`。

零 v1 **行為**執行（見上方插樁），但物件確實建構、模組確實載入。這與隔壁 rollback
物件圖的 lazy-import 紀律不一致（Plan 13.5 Task B3 未涵蓋此處）。移除 v1 時這條
import 鏈會自然消失；列此僅為避免執行者誤以為「active path 完全不碰 v1 模組」。

### 已知待修：發佈中的過時 migration warning

`system_map_v1_to_v2_adapter.py:119` 發出
`"active_output_remains_v1_until_plan_13"`。**Plan 13 早已完成、active output 已是
v2，此字串現在是假的**，且它會進入 `AiSystemMapV2.migration_warnings` → 發佈的
`ai_system_map.json` → `MapBuildResult.migration_warnings` → HTTP 回應
（`API-GUIDE.md:382,489`），任何載入歷史 v1 map 的使用者都會看到。
目前被 `tests/unit/core/test_system_map_v1_to_v2_adapter.py:244` 斷言凍結。

→ 本計畫移除 adapter 時一併消失；若 Gate-4 遲遲未過而需先行處理，屬獨立小修。

### `rag-core-v1` template：**不在本計畫範圍，且不得刪除**

查核確認 `rag-core-v1` **仍在 active v2 掃描路徑上執行**
（`system_map_v2_materialization_service.py:89`），並驅動：元件偵測的 13-slot
keyspace、`edges[]`（由 template `flows[].slot_order` 產生）、
`components[].layer` 與 `metadata.legacy_slot`、`recommended_next_checks[].target`、
manual mapping 的 `target_slot` 白名單、LLM proposal packet 的 `available_slots`，
以及含 "rag-core-v1" 字樣的使用者可見 risk hint 文案。

依本計畫第 17 行原文，`rag-core-v1@1.0.0`（凍結內容）**可保留為 scanner 內部
grounding**。因此：

- **本計畫只退役 `ai-system-map/v1` schema 那條線，不碰 `rag-core-v1` template。**
- template 從 Step 4 的移除由 **Plan 16G / 13.7 系列**負責，不在此。
- **`legacy_slot_layer_map.py` 必須單獨保留**（見下方 Task 3c 既有條目）——
  它同時服務 v1 adapter（刪）與 active `SystemMapV2NormalizeService`（留）。

### 移除順序（依實測依賴方向）

```text
rollback service → canonical_map_loader 的 v1 分支 → v1→v2 adapter → v1 validator
   ├─ 同一 change 內：型別共用四件組（見上方約束 1）
   └─ 單獨保留：legacy_slot_layer_map.py
```

`canonical_output_configuration` 是 leaf（只依賴 `models/map_build`）且守門全部路徑；
`LegacyV1RollbackService` → `CanonicalMapLoader` → `SystemMapV1ToV2Adapter` 為單向依賴。

---

## Task 0：補上 census gate 的盲區（**與 Gate-4 無關，現在就能做**）

`tests/contracts/test_v2_cutover_consumer_allowlist.py` 是本計畫的主要安全網，但
2026-08-06 查核發現它有**兩層盲區**，會讓執行者誤判「已無殘留」：

1. **`LEGACY_LITERALS` 完全不含 `rag-core-v1` 相關詞彙**——`RagTemplateService`、
   `RagTemplate`、`"rag-core-v1"`、`legacy_slot`、`components_by_slot`、
   `SLOT_LAYER_BY_ID` 一個都不在名單裡。gate 只管 `ai-system-map/v1` 那條線。
2. **AST 掃描只比對「完整字串常數相等」**（`node.value in LEGACY_LITERALS`），
   因此子字串形式的殘留全數逃脫，例如
   `models/system_map.py:37` 的 `SCHEMA_ID = "https://.../ai-system-map.v1.schema.json"`、
   `cli/viewer_command.py:19` help 字串內的 `ai-system-map/v1`、
   以及所有註解／docstring 內的提及。

- [ ] **Step 1: 為 `rag-core-v1` 詞彙建立獨立 census**（另一份 allowlist 或
  同檔新增分類），涵蓋上述六個符號；先以現況登記為 baseline，避免一次性大改
- [ ] **Step 2: 補上子字串偵測**（或明確記錄「僅偵測完整常數」的限制，並列出
  已知豁免清單），讓 gate 的宣稱與實際覆蓋一致
- [ ] **Step 3: 確認新增 census 對現況全綠**（純登記，不改產品碼）

> 為什麼先做：C1–C7 這批 `rag-core-v1` 滲透目前**沒有任何回歸保護**；Gate-4 通過
> 後才補會讓大批刪除失去安全網。此 Task 純增測試，不動產品碼，無 Gate 相依。

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

> **已於 2026-08-06 抽出為獨立計畫：`plan/finish/refactor/06-remove-v1-rollback-write-path.md`。**
> 抽出理由：v1 **寫入**路徑（operator rollback）與 v1 **讀取**路徑可分離，且
> Gate-4 的目的是「先證明既有 v1 artifact 能相容遷移」——移除產生 v1 的逃生口
> 不影響讀取能力。使用者已知悉「執行後無法回退到 v1 輸出」並接受（開發期、
> 無正式使用者資料）。
>
> **執行順序：** Plan 06 可先做；本 Task 於 Plan 06 完成後標記完成，**不得重複
> 執行**。Plan 06 刻意保留 `LEGACY_CANONICAL_OUTPUT_VERSION` 與
> `require_public_v2_selection()`（deprecated 輸入的穩定 422 仍依賴它們），
> 那組的收斂仍屬本計畫，見上方「新增前置事實 (1)」的原子性約束。

> **已由 `refactor/06` 於 2026-08-07 完成（#277）——本 Task 勿重複執行。**
> 三個服務檔已刪、`MapBuildService` / `MapBuildPipeline` 無 v1 分支、env 不再接受
> `ai-system-map/v1`、census 已同步（`operator_rollback` 分類本身已移除）。
> 本 Task 僅剩下方第二項的 `LEGACY_CANONICAL_OUTPUT_VERSION` 收斂。

- [x] 確認 `plan/finish/refactor/06-remove-v1-rollback-write-path.md` 已完成（三個服務檔已刪、
  pipeline 無 v1 分支、census 無 stale record）。
- [ ] 本計畫僅接手 Plan 06 明列的「不得更動」項：`LEGACY_CANONICAL_OUTPUT_VERSION`
  與 `require_public_v2_selection()` 的原子性收斂（連同 `SystemMapSchemaSelection`、
  `web/schemas.py`、`cli/map_command.py` 的 deprecated 輸入）。

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

- **`src/systograph/web/legacy_mapping_guards.py` 已與 migration module 解耦。** Plan 13.5
  Task B1 把 `new_extension_component` 內聯成字面值、移除對
  `legacy_manual_mapping_migration_service` 的 import。刪 module 前確認
  `rg legacy_manual_mapping_migration src/systograph/web/` 零命中即可，不需要再拆 web 層。
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
  - `<SYSTOGRAPH_STATE_DIR>/migration-backups/<project>/` —— `<mapping>.<token>.legacy.json`
    （原 payload 的 **re-serialization**）+ `index.json`。
  - `<SYSTOGRAPH_STATE_DIR>/migration-quarantine/<project>/` —— 兩種檔案：
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
  `src/systograph/core/models/system_map.py` 拆到中立 module：
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
  `src/systograph/core/models/recommended_next_check.py`。剩下 11 個。

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

### Task 3e：策略 A — 拒絕 v1 讀取並清除舊 state（2026-08-06 使用者決策）

原計畫的 expand-and-contract 假設「保留 migration 路徑」。使用者已明確選擇
**策略 A：只認 v2、拒絕讀寫 v1、不提供 migration tool**，理由是專案仍在開發期、
無正式使用者資料。因此：

- [ ] **Step 1: 讀到 `schema_version == "ai-system-map/v1"` 的 payload 時直接以穩定
  error code 失敗**，不再自動轉 v2（取代 `CanonicalMapLoader._load_v1` 分支）
- [ ] **Step 2: 清除本機歷史 state**——`${SYSTOGRAPH_STATE_DIR:-~/.systograph}`
  下的 pre-cutover build manifest（`active/requested_schema_version` 為 v1 或缺欄者）
  與其 `outputs/` artifacts。**這是有意的資料丟棄，不是遷移**
- [ ] **Step 3: 明文記錄「舊 build 無法回讀」於 `docs/SYSTOGRAPH-HARD-CUTOVER.md`
  或等價文件**，與 2026-07-28 identity 硬切換採同一種「不提供相容別名」的敘事
- [ ] **Step 4: 清除或標記需重產的 v1 fixtures**——
  `tests/fixtures/**/*.v1.json`、`valid_rich_frontend_sample.v1.json` 等；
  `cli/viewer_command.py` 的 dual-read 測試需一併改寫（見 Task 4）
- [ ] **Step 5: 不得以「把 `MapBuildManifest` 預設值改成 v2」繞過**——見上方
  「新增前置事實 (2)」，那會讓歷史 manifest 的 fail-closed 比對永久錯判

> **爆炸半徑提醒：** 策略 A 影響的不只 `outputs/` 下的檔案，還包括本機 state 內
> 的 build 歷史（latest pointer、build manifest、以 build_id 為 key 的一切）。
> 執行後使用者需重新掃描才會有可用的 build。開發期可接受，正式發佈前若已有
> 使用者資料則需重新評估。

### Task 4：收斂 loaders 與 consumers

- [ ] `CanonicalMapLoader` 移除 silent dual-read default；**依 Task 3e 策略 A，
  v1 分支直接刪除並改為穩定錯誤，不保留 explicit migration command**。
- [ ] `cli/viewer_command.py`（`validate-map`）的 v1 dual-read 一併移除；
  其 help 字串與 `tests/cli/test_viewer_command.py` 的 v1 fixture 需同步改寫。
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
- [ ] 文件明確記載：Plan 18（Systograph TOML provider 主掃描退役）為 Plan 15 的 Gate-4 前置，不可跳過。

### Task 5b：Plan 13.5 交接的兩個「不要誤刪 / 不要多做」註記

- [ ] **`RecommendedNextCheckService` 不在 v1 retirement 移除範圍。** 它在 Plan 13.5 Task A1
  已從 v1 normalize service 抽出、成為 active v2 service，新路徑
  `src/systograph/core/services/recommended_next_check_service.py`：active 路徑由
  `SystemMapV2MaterializationService` 持有並呼叫 `derive`，結果再傳給
  `SystemMapV2NormalizeService.assemble`；規則檔
  `src/systograph/core/rules/recommended_next_check_rules.toml` 自此屬 active 資產。
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
uv run ruff check src tests
uv run mypy src tests
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

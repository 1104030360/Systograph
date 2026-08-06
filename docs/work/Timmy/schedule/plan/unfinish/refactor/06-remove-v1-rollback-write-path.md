# 移除 legacy v1 rollback 寫入路徑實作計畫

Status: **done**（2026-08-07 完成，commit `7b091ac`；2026-08-06 起草；umbrella
issue #277。由 Plan 15 Task 2「移除 v1 write path」抽出獨立執行——見下方
「Gate 判定」對偏離 Plan 15 統一 gate 的說明）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填）

**Goal:** 移除 operator rollback 的 v1 **寫入**路徑（三個服務 + 兩個 pipeline
分支 + env 觸發），讓 `MapBuildService` 只有一條 v2 產出路徑。

**Architecture:** v1 的**寫入**路徑與**讀取**路徑是可分離的。本計畫只砍寫入
（產生 v1 artifact 的能力），**完整保留讀取**（`CanonicalMapLoader` 的 v1 分支、
`SystemMapV1ToV2Adapter`、v1 validator），因此既有 v1 artifact 仍可載入。
讀取路徑的退役屬 Plan 15 其餘 Task，受 Gate-4 約束。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、Ruff、mypy。

---

## Gate 判定（**執行前請確認你同意這個推論**）

`refactor/15-complete-legacy-v1-retirement-after-compatibility.md` 開頭寫「本計畫
只能在 **Gate-4** 通過後執行」，而 Gate-4 目前**未通過**（Plan 14 無 report、
Plan 18 的 issue #239 仍 OPEN）。本計畫是 Plan 15 Task 2 的抽出，因此嚴格說
也在該 gate 之下。

主張可以先做的理由：

- Gate-4 的目的是「**先證明 v1 artifact 能相容遷移，再移除相容能力**」。
  rollback writer 不是相容能力，它是**產生 v1 的緊急逃生口**；移除它不影響
  既有 v1 artifact 的可讀性（讀取路徑完整保留）。
- 使用者決策（2026-08-06）：專案仍在開發期、無正式使用者資料，且已選擇
  策略 A（只認 v2）。緊急回退到 v1 的實際需求不存在。

風險對價：**執行後就沒有「把輸出切回 v1」這個逃生口了。** 若 v2 輸出日後出現
無法即時修復的重大問題，只能往前修，不能回退。使用者已知悉並接受。

> 若你（或後續執行者）不同意此推論，正確作法是把本計畫壓回 Plan 15 Task 2
> 等 Gate-4，而不是部分執行。

---

## Source（判準基線，2026-08-06 對程式碼查核；2026-08-07 覆核行號未變）

- `map_build_service.py:104-127` `_build_legacy_v1_rollback_service()`
  （function-local import，檔頭註解自陳目的就是讓 Plan 15 好刪）
- `map_build_service.py:187-203` env 比較分支
- `map_build_pipeline.py:120-142`（`materialize` v1 分支）、
  `:187-205`（`materialize_existing_map` v1 分支）
- `canonical_output_configuration.py` 全檔（39 行）
- `system_map_materialization_service.py:1-8` docstring 自陳
  「Operator-rollback-only v1 materializer. Plan 15 removes it.」
- 實測（2026-08-06 插樁）：正常 v2 build 後三個 rollback 模組
  **皆不在 `sys.modules`**，隔離有效。

---

## Task 1: 刪除三個服務

三者是一個整體，不可只刪其一——`legacy_v1_rollback_service` 存在的唯一目的
就是驅動 materializer；`system_map_normalize_service` 在 src 內的唯一消費者
就是 materializer。

**Files:**
- Delete: `src/systograph/core/services/system_map_materialization_service.py`
- Delete: `src/systograph/core/services/system_map_normalize_service.py`
- Delete: `src/systograph/core/services/legacy_v1_rollback_service.py`

- [x] **Step 1: 刪除三檔**
- [x] **Step 2: 全樹 grep 三個類名確認無殘留 import**
  （`SystemMapMaterializationService`、`SystemMapNormalizeService`、
  `LegacyV1RollbackService`、`LegacyV1RollbackError`、`LegacyV1RollbackResult`）

## Task 2: 移除 pipeline 與 service 的 rollback 接線

**Files:**
- Modify: `src/systograph/core/services/map_build_service.py`
- Modify: `src/systograph/core/services/map_build_pipeline.py`

- [x] **Step 1: 刪除 `map_build_service.py:99-127`
  `_build_legacy_v1_rollback_service()` 整個函式**（含 `:99-103` 的責任註解）
- [x] **Step 2: 刪除 `:187-203` 的 `LEGACY_CANONICAL_OUTPUT_VERSION` 比較分支
  與 `rollback_service` 區域變數**
- [x] **Step 3: 移除 `MapBuildService.__init__` 的
  `legacy_v1_rollback_service` 建構參數**
- [x] **Step 4: 刪除 `map_build_pipeline.py:120-142` `materialize` 的 v1 分支，
  只留 else 的 v2 路徑（拆掉 if/else，改為直接呼叫）**
- [x] **Step 5: 刪除 `:187-205` `materialize_existing_map` 的 v1 分支**
- [x] **Step 6: 移除 `MapBuildPipeline` 的 `legacy_v1_rollback_service` 參數；
  `canonical_output_version` 必須保留**——`:291` 的
  `active_schema_version=self._canonical_output_version` 仍在讀它

## Task 3: 收斂 env 設定（**注意保留項**）

**Files:**
- Modify: `src/systograph/core/services/canonical_output_configuration.py`

- [x] **Step 1: `canonical_output_version_from_env()` 不再接受
  `ai-system-map/v1`**——設定該值時以穩定錯誤碼失敗
  （沿用 `invalid_canonical_output_version`，或新增明確的
  `legacy_rollback_removed`；擇一並在 API-GUIDE 記載）

> **不得移除：** `LEGACY_CANONICAL_OUTPUT_VERSION` 常數與
> `require_public_v2_selection()`。它們現在的職責是讓 API／CLI 送 v1 時回穩定的
> `legacy_output_not_selectable`(422)；`require_public_v2_selection` 被
> `scan_routes.py:174` 與 `map_build_service.py:228,293,333` 共四處呼叫。
> 移除常數會讓該錯誤碼退化成 pydantic 泛用 422，破壞
> `docs/API-GUIDE.md:1043` 的錯誤碼契約。這組的收斂屬 Plan 15
> （需與 `SystemMapSchemaSelection`、`web/schemas.py`、`cli/map_command.py`
> 的 deprecated 輸入**原子性一起移除**）。

## Task 4: 測試

- [x] **Step 1: 刪除 `tests/unit/core/test_legacy_v1_rollback_service.py`**
- [x] **Step 2: 刪除 `tests/unit/core/test_system_map_normalize_service.py`**
- [x] **Step 3: 改寫下列六檔中與 rollback 相關的案例**
  （移除 rollback 分支斷言，保留其餘）：
  `tests/unit/core/test_canonical_output_configuration.py`、
  `tests/unit/core/test_map_build_schema_selection.py`、
  `tests/unit/core/test_map_build_service_wiring.py`、
  `tests/integration/test_v2_active_cutover.py`、
  `tests/integration/test_build_manifest_service.py`、
  `tests/web/test_local_json_restart_recovery.py`。
  後兩檔沒有 rollback 分支斷言，各只有一行碰 `operator_rollback_active`
  （`:111` round-trip、`:134` 斷言 `False`），採 (A) 時不必動，採 (B) 才要改
- [x] **Step 4（易漏）: 改寫兩處把 `SystemMapNormalizeService` 當 fixture
  產生器的測試**——`tests/unit/core/test_graph_projection_service.py:366`、
  `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py:54`。
  它們與 rollback 無關但會跟著壞。**不能只換成
  `SystemMapV2NormalizeService`**：兩者是用 v1 writer 造出 `RagSystemMap`，再餵
  給**保留中的** v1 讀取路徑（`SystemMapValidationService.validate`；前者接
  `SystemMapV1ToV2Adapter.adapt_to_canonical`，後者直接斷言 `endpoint.slot`、
  `edge.from_slot` / `to_slot` 這些 v1-only 欄位）。`SystemMapV2NormalizeService
  .assemble` 的 kwargs 不同（要 `project_id` / `project_root` /
  `recommended_next_checks` / `no_snippets`，不吃 `template`）且回傳
  `AiSystemMapV2`，換過去等於刪掉 v1 讀取路徑的覆蓋。正解是改吃靜態 v1 fixture
  （`tests/fixtures/ai_system_map/*.v1.json`）當輸入
- [x] **Step 5: 新增 regression：env 設為 `ai-system-map/v1` 時以穩定錯誤碼
  失敗，且不產生任何 artifact**

## Task 5: census 同步（**必須與 Task 1 同一個 change**）

`tests/contracts/test_v2_cutover_consumer_allowlist.py` 是**雙向 fail-closed**：
刪掉模組卻留著 allowlist 記錄，會以 stale record 讓 contract test 失敗。這是
設計行為（Plan 15 Task 5b 已預先說明），不是意外。

- [x] **Step 1: 移除本計畫刪除模組對應的 `operator_rollback` 記錄**
  （現有 8 筆，逐筆比對哪些屬本次刪除範圍）
- [x] **Step 2（易漏）: `map_build_pipeline.py` 那筆 `operator_rollback` 記錄
  也會變 stale**——該檔在 Task 2 之後剩下的 v1 literal 只在 `:297`
  `operator_rollback_active=(... == "ai-system-map/v1")`，(A)(B) 兩個選項下都
  會消失。模組雖未刪，記錄仍須移除
- [x] **Step 3: 保留仍存在符號的記錄**——特別是
  `canonical_output_configuration.py` 那筆（allowlist 的 symbol 欄位是
  `ai-system-map/v1` literal，由 Task 3 保留的 `LEGACY_CANONICAL_OUTPUT_VERSION`
  持有）
- [x] **Step 4: `uv run pytest tests/contracts/` 全綠**

## Task 6: 檔頭呼叫鏈註解

本 repo 的 service/model 帶「責任 / 呼叫鏈」結構化註解，`CLAUDE.md` 要求改動
依賴前先讀它們。模組刪除而註解未改，呼叫鏈會指向不存在的東西。

- [x] **Step 1: `src/systograph/core/models/system_map.py:5`
  「只剩 migration（v1 讀取）與 operator rollback 在用」與 `:14`
  「v1 rollback writer：SystemMapNormalizeService → RagSystemMap」改寫**
- [x] **Step 2: `src/systograph/core/models/system_map.py:306`
  「被誰用（只剩 migration / operator rollback 兩條路）」與 `:310-311`
  「rollback 寫入：LegacyV1RollbackService → SystemMapMaterializationService →
  SystemMapNormalizeService」改寫**
- [x] **Step 3: `src/systograph/core/services/recommended_next_check_service.py`
  的 `:3`、`:7`（「兩條 build 路徑」在刪除後只剩一條）與 `:12-14`
  「SystemMapNormalizeService.assemble（v1 writer，operator rollback 用）」改寫**
- [x] **Step 4: `src/systograph/core/services/map_build_pipeline.py:89-93`
  的 `materialize` 責任註解改寫**——它明寫「operator rollback mode 才由隔離
  writer 產出 v1 artifact」與「LegacyV1RollbackService.materialize」，Task 2 只刪
  分支不會動到這段

## Task 7: 契約文件

- [x] **Step 1: `docs/API-GUIDE.md` 刪除〈Operator rollback 專用 error code〉
  整節（`:1050-1072`，該節一路到檔尾）**
- [x] **Step 2: `docs/API-GUIDE.md:709,710` 錯誤表移除
  `legacy_rollback_not_representable`、`legacy_rollback_detail_scan_unsupported`
  兩列，連同緊接其後 `:712-714` 的「兩者的優先順序」註記 block；`:1043` 提及
  `legacy_rollback_*` 的敘述改寫**
- [x] **Step 3: `docs/API-GUIDE.md:353-354`（「v1 rollback 不透過 request，而由
  process 啟動前的 operator setting 控制」）與 `:559-560`（Apply 段的 operator
  rollback 說明）改寫**
- [x] **Step 4: `docs/MODEL-CONTRACT.md` 移除 operator rollback 語意**——
  `:37`（「預設關閉的 operator rollback writer」）、`:331`（「v1（rollback writer）
  與 v2（active writer）兩條 build 路徑共用同一個 derive」）、`§7.2` 的
  `:593-595`（env 啟用說明；同節 `:577` 的 `operator_rollback_active` 欄位依下方
  (A)/(B) 決定去留）、`:757`（Frontend Checklist 第 1 條）
- [x] **Step 5: 全文 grep（不分大小寫）`rollback` 確認無殘留**——只 grep
  `operator rollback` / `legacy_rollback` 會漏掉跨行斷開的敘述，例如 API-GUIDE
  `:559-560` 的「Operator↵rollback」與 `:353-354` 的「operator↵setting」

---

## 需要你決定：`operator_rollback_active` 欄位去留

該欄位散佈 9 個非測試檔案，其中三處是**對外契約**：`web/schemas.py:98`、
`docs/API-GUIDE.md:381`、**前端 `frontend/src/contracts/viewer.ts:295`**
（zod 必填 boolean）。

| 選項 | 內容 | 代價 |
|---|---|---|
| **(A) 保留欄位、永遠 `false`**（**建議**） | 只砍 rollback 機制，欄位留在契約上 | 留一個永遠為 false 的欄位；零 breaking change，前端不動 |
| (B) 一併移除 | 契約乾淨 | breaking change：需同步改 `web/schemas.py:98,114`、`models/map_build.py:94`、`models/analysis_history.py:167`、`build_manifest_service.py:112,189`、`map_build_pipeline.py:296`、API-GUIDE（`:381,488,504`）、MODEL-CONTRACT（`:577,594`）、前端 zod 與**四個**前端測試（`contracts/viewer.test.ts:258`、`services/viewerApi.test.ts:45`、`services/mapBuildApi.test.ts:45`、`hooks/useMappingProposal.test.tsx:71`） |

建議 **(A)**——本計畫只處理「機制」，欄位收斂留給 Plan 15 一次做完，避免為了
一個 boolean 觸發跨 repo 的 breaking change。

- [x] **Step 0: 確認採用 (A) 或 (B)，並在此註記**
  → **裁定：採 (A)**（2026-08-07）。`operator_rollback_active` 欄位保留在
  `MapBuildResult` / `BuildManifest` / `web/schemas.py` / 前端 zod 上，
  `MapBuildPipeline._complete` 直接寫死 `False` 並附英文註解說明其為契約相容
  保留欄位。零 breaking change，前端與四個前端測試都不用動。欄位本身的收斂
  留給 Plan 15 一次做完。API-GUIDE 與 MODEL-CONTRACT 已補「恆為 `false`」敘述。

---

## 不得更動（讀取路徑，屬 Plan 15）

| 檔案 | 為什麼留 |
|---|---|
| `core/services/system_map_validation_service.py` | v1 驗證器；`CanonicalMapLoader._load_v1` 讀歷史 v1 artifact 時仍需要 |
| `core/services/system_map_v1_to_v2_adapter.py` | v1→v2 migration adapter |
| `canonical_map_loader.py` 的 v1 分支 | dual-read；移除屬 Plan 15 Task 4 |
| `core/services/legacy_slot_layer_map.py` | active `SystemMapV2NormalizeService` 也在用 |
| `LEGACY_CANONICAL_OUTPUT_VERSION` + `require_public_v2_selection()` | 見 Task 3 保留說明 |

---

## 驗收標準

1. 三個服務檔已刪除，全樹 grep 五個類名零命中。
2. `MapBuildService` / `MapBuildPipeline` 只剩一條 v2 產出路徑，無 v1 分支。
3. env 設為 `ai-system-map/v1` 時以穩定錯誤碼失敗，且不產生任何 artifact。
4. API／CLI 送 `system_map_schema_version: "ai-system-map/v1"` **仍回**
   `legacy_output_not_selectable`(422)——錯誤碼契約未退化。
5. 讀取既有 v1 artifact 的能力**不變**（`CanonicalMapLoader` v1 分支、
   CLI `validate-map` 仍可運作）。
6. `uv run pytest`、`ruff check`、`ruff format --check`、`mypy src tests` 全綠；
   census contract test 無 stale record。
7. API-GUIDE / MODEL-CONTRACT 無 operator rollback 殘留敘述；Task 6 列出的四處
   檔頭呼叫鏈註解已更新。

**驗收結果（2026-08-07）：** 七條全數通過。`uv run pytest` 1122 passed / 1 skipped
（baseline 1138 − 刪除的 rollback 測試），branch coverage 90.76%（gate 85%）；
`ruff check` / `ruff format --check` / `mypy src tests`（324 files）全綠；
`tests/contracts/` 46 passed 無 stale record；`uv run systograph validate-map`
對既有 v1 fixture 仍回 `loaded=true`。

---

## 執行紀錄與範圍追加（2026-08-07）

計畫外但一併處理的項目，全部在同一 commit：

1. **`map_build_pipeline.py` census 註解孤兒**（主 agent 事前指定的範圍追加）：
   `:115-119` 那段「every "ai-system-map/v1" literal in this file … must stay
   inline string literals」在 Task 2 刪分支後已無對應 literal，整段移除。
2. **census `operator_rollback` 分類本身移除**：Task 5 執行後該分類已無任何
   record（`canonical_output_configuration.py` 那筆依 Step 3 保留，但改標為
   `migration_only`——它現在的職責只剩 `legacy_output_not_selectable` 拒絕）。
   留著空分類等於留下「rollback 還在」的錯誤詞彙，故從 `Classification`
   Literal 與 `LEGAL_CLASSIFICATIONS` 一併刪除。
3. **`BuildArtifactPublisher.artifact_map` 移除**（計畫未列，但屬 v1 寫入路徑）：
   `_publish` 的 `write_json(artifact_map or system_map)` 正是「把 v1 map 寫上
   磁碟」那一步。rollback writer 消失後該參數恆為 `None`，留著等於留下可被任何
   caller 觸發的 v1 寫入能力。連同 `MapBuildPipeline._complete` 的同名參數移除。
4. **Task 4 Step 4 的靜態 fixture 是「刪除前擷取」的**：先用尚存的
   `SystemMapNormalizeService` 產出 `basic_qdrant_ollama_rag` /
   `openai_external_provider_rag` 兩份 v1 payload 存成
   `tests/fixtures/ai_system_map/*.v1.json`，兩處測試因此**斷言一字未改**，
   只是輸入從 live scan 換成凍結 artifact。既有的
   `valid_rich_frontend_sample.v1.json` 不含 endpoint-targeted risk 與
   `component_instance_id`，無法滿足 `test_endpoint_risks_attach_to_component_
   from_qdrant_fixture`，且被 13 個測試共用，不可改動——故新增而非沿用。
   代價：fixture 凍結在 2026-08-07 的 scanner 行為，不再隨 scanner 變動。
5. **`tests/unit/core/test_map_build_service_wiring.py` 全檔案都是 rollback
   wiring**（8 個 case 無一例外），因此不是「移除 rollback 案例」而是整檔改寫，
   換成三個守住新不變式的 guard：三個模組確實不存在（`find_spec is None`）、
   兩個 constructor 都沒有含 `rollback` 的參數、default service 的 materializer
   只有 v2 那一個。
6. **Task 7 的行號已過時**：計畫寫的 API-GUIDE `:1050-1072` / `:709-714` /
   `:1043` / `:559-560` 實際落在 `:920-940` / `:584-589` / `:918` / `:494-495`
   （Plan 08 縮短了該檔）。另外 `:353-354`「v1 rollback 不透過 request，而由
   process 啟動前的 operator setting 控制」**已不存在**於 API-GUIDE，先前計畫
   已移除，無事可做。
7. **Task 7 Step 5 的全文 grep 抓到兩處計畫未列的 live 文件**，一併修正：
   `README.md:23`（把 rollback 寫成已實作功能，違反 README「已實作 vs roadmap」
   規則）與 `frontend/API_CONTRACT.md:293`（宣稱「Operator rollback exists but is
   a process-level setting」——已成假敘述；該檔是 CLAUDE.md 列名的權威契約文件）。
   `docs/work/` 底下的歷史文件依指示不清。
8. **env 收斂沿用既有錯誤碼**：`canonical_output_version_from_env()` 不為 v1
   特例化，直接收斂成「只接受 `ai-system-map/v2`」，其餘一律
   `invalid_canonical_output_version`。不新增 `legacy_rollback_removed`。

## 風險

- **失去回退能力**：見「Gate 判定」。執行後無法把輸出切回 v1。
- **census stale record**：Task 5 未與 Task 1 同一 change 會讓 contract test
  紅燈，且錯誤訊息指向 allowlist 而非刪除本身，容易誤判。
- **兩處 fixture 測試易漏**（Task 4 Step 4）：它們用 v1 normalize service 造
  測試資料，與 rollback 無關，靜態閱讀時容易被跳過。
- **偏離 Plan 15 統一 gate**：本計畫先於 Gate-4 執行，Plan 15 其餘 Task 仍須
  等 gate；執行後應在 Plan 15 註記 Task 2 已完成，避免重複執行。

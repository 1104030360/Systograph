# Plan 13 v2 Cutover 殘留稽核 — 彙整報告（2026-07-28）

Status: audit-complete / read-only（未修改任何程式碼）

## 稽核方法

4 個 Opus subagent 分區逐檔實查（backend core v1 surface / mapping migration surface /
frontend handoff / allowlist gate 完整性），每條發現附 `檔案:行號`、真實 code 片段與
runtime probe 輸出。分區完整報告（共 53 條發現、2419 行）：

```
2026-07-28-plan13-residue/residue-A-core.md      RA-1..14  core v1 map surface
2026-07-28-plan13-residue/residue-B-mapping.md   RB-1..10  mapping migration + CLI/web
2026-07-28-plan13-residue/residue-C-frontend.md  RC-1..16  frontend handoff
2026-07-28-plan13-residue/residue-D-gate.md      RD-1..13  allowlist / docs 三方一致性
```

判準基線：`s1-v2-cutover/13-retire-legacy-extension-contract.md`、
`2026-07-17-phase2-plan13-v2-cutover-REP.md`、`CLAUDE.md` contract invariants。

---

## 總結論（一段話）

**Backend 的 cutover 本體是紮實的**：mapping legacy shape 的寫入/讀取三道防線全部實測封閉、
rollback 預設關閉且非法值 fail startup、`normalized_ai_system_map` 雙真相已完全移除、
census 35/35 與 SHA-256 digest 可精確重現、五個關鍵驗收 checkbox 抽查全部成立。
**但有三件事不乾淨**：(1) Task 5「normal build path 不得 import」的 `[x]` 與 code 不符——
normal path 每次建構都急切實例化整個 v1 rollback 物件圖，且 37 個 active 檔案仍 import
v1 module 的共用 DTO；(2) 守門的 allowlist census 有 4 個已證實盲點，最關鍵的
`legacy_mapping_guards.py`（legacy 停寫的唯一 runtime 防線）對 census 完全隱形，而
Plan 15 Task 3b 照字面執行會把它的 import 來源整個刪掉 → **ImportError 打爛 app 啟動**；
(3) frontend 的真實殘留是 8 檔 ~18 處 + sample 全檔重生，不是宣稱的「4 檔 5 筆」，
且其中 3 處在 API mode **現在就已經壞了**（replay 恆空、Sidebar 全 unknown、unmapped 邊判定死亡）。

---

## A. Cut 不乾淨（Plan 13 說完成、實際沒有）

| # | 發現 | 位置 | 嚴重度 |
|---|---|---|---|
| RA-1 | normal build 每次 `MapBuildService()` 都急切 import + 實例化 `LegacyV1RollbackService` → `SystemMapMaterializationService` → v1 normalize/validation 全鏈，連 v1-only 的 `recommended_next_check_rules.toml` 都讀進來（runtime probe 證實）。Task 5 `[x]`「normal build path 不得 import」與 code 不符 | `map_build_service.py:56-58,79-81,151-162` | P1（Plan 15 刪 v1 writer 時會直接撞斷 normal path） |
| RB-10 / RA-8 | 37 個 active 檔案 import v1 module `models/system_map.py` —— 因為 `Evidence`/`Endpoint`/`Flow`/`RiskHint`/`DetailScanResult`/`QueryTraceEvent` 等 **active scan-phase DTO 住在 v1 module 裡**。census 只掃 4 個 symbol 名，全部看不到。Plan 15「刪 v1 model」照字面不可執行 | `models/system_map.py` ← 37 檔 | P1（Plan 15 隱藏 blocker） |
| RA-4 | `recommended_next_checks` 在 v2 build **恆為空**（`AiSystemMapV2` 沒這欄位；只有讀 legacy v1 artifact 才會填）。產品可見行為在 cutover 中靜默改變，cutover report 未列 remaining warning；`RecommendedNextCheckService` + TOML 規則檔已實質 rollback-only 但無人標示、無人追蹤 | `viewer_session_service.py:111-124`、`system_map_normalize_service.py:91-264` | P1（需決策：補功能 or 正式退役） |
| RC-3/4/5 | API mode 現在就壞的三處：`sampleMap.getTraceEvents` 讀 v2 沒有的 `query_trace_events`（**replay 恆空**，且 API mode 也走這條）；`App.tsx` 讀 `scan_summary`/`scan_depth`（**Sidebar 全 unknown**）；`utils/graph.ts:197` 判 `edge.status === "needs_confirmation"` 但 backend `GraphEdgeModel` 根本沒有 `status` 欄位（**unmapped 邊視覺死亡**，只有 v1 sample 能讓它成立） | `sampleMap.ts:22`、`App.tsx:70,307`、`utils/graph.ts:197` | P1（使用者可見損壞） |
| RD-6 | executable gate 掃描範圍小於 Plan Task 5 宣告的 census 指令：`schemas/`、`scripts/*.py`、`frontend/` root、`tests/`、`docs/` 都不掃。Plan L278 明列 `ai-system-map.v1.schema.json` 為 allowlist 成員，但 gate 沒有這筆 record 也不掃該目錄 | `test_v2_cutover_consumer_allowlist.py:15-18` | P2 |

## B. 守門機制盲點（gate 守不住 Plan 15）

| # | 發現 | 位置 | 嚴重度 |
|---|---|---|---|
| RB-2 | **本次稽核最高風險。** Plan 15 Task 3b 要整檔刪除 `legacy_manual_mapping_migration_service.py`，但 `web/legacy_mapping_guards.py:9-13` import 它的 `LegacyManualMappingType`（active 防線，Task 3b 第 5 條又要求保留）。照字面執行 → `ImportError` 打爛 FastAPI 啟動；修掉 import 後若順手刪 guard → legacy write surface 重新打開。Task 3b 從頭到尾沒提 `LegacyManualMappingType` 該搬去哪 | Plan 15 Task 3b ↔ `legacy_mapping_guards.py:9-13` | **P0**（Plan 15 執行前必解） |
| RB-1 / RD-3 | `legacy_mapping_guards.py` 用 `LegacyManualMappingType.NEW_EXTENSION.value` 而非字面值 → AST census 與 rg gate **雙盲**。legacy 停寫的唯一 runtime 實作點不在 35 筆 allowlist 內 | `legacy_mapping_guards.py:13` | P1 |
| RD-4/RD-5 | census 逃逸面：裸字串 `"ExtensionComponent"`（`system_map_validation_service.py:109` 已是實例）、substring/f-string/註解/docstring/`getattr`/quoted annotation 全部逃逸（12 個 snippet 實測 9 個逃逸）。正面：直接 import、`Name`、module attribute、alias 都抓得到；stale 偵測雙向有效 | `test_v2_cutover_consumer_allowlist.py:334-350` | P2 |
| RC-14 | Plan 13 completion gate「frontend 5 筆歸零」是弱 gate：5 筆是 file×symbol 去重值（raw 9 行），`ui_extension`/`extensions[]`/`components_by_slot`/`query_trace_events` 全在雷達外。照現況收尾會把未解的 v1 依賴標成 complete | Plan 13 L546,564,575 | P1 |

## C. 不需要的過渡期寫法（現在就可清）

| # | 發現 | 位置 | 處置 |
|---|---|---|---|
| RB-3 | `_legacy_detail_scan` 46 行：#202 時代的過渡路徑，Plan 13 Task 6 之後前提永久消失（`lineage` 是 required 欄位），production 不可達，且是唯一繞過 `BuildCommitService` 直寫 session 的側門。13/15 都沒追蹤 | `detail_scan_routes.py:59-71,163-208` | **立刻可刪** |
| RA-5 | `ViewerSessionService.build()` / `project_to_graph()` 吃 v1 `RagSystemMap` 的公開 method，production **零 caller**（真實入口是 `build_loaded`/`build_canonical`），責任註解 100% 失真 | `viewer_session_service.py:149-196` | 立刻可降級 test-only / 刪除 |
| RA-6 | rollback 分支 dead call：`require_representable()` 回傳值被丟棄，下一行**無條件** raise 同一個 error code——「可表示」與「不可表示」回同一個碼，preflight 語意是假的 | `map_build_pipeline.py:174-180` | 立刻可修（改誠實 error code） |
| RA-3/RA-7/RA-12/RD-11 | 過時/缺失標示批次：`system_map_normalize_service.py:1-6` 仍自稱 "the active v1 writer"；`system_map_materialization_service.py` 零 legacy 標示（Task 5 `[x]` 說有）；`viewer.py:14` 說 "derived from ai-system-map/v1"；v1 schema JSON、adapter、rollback service、migration service 四檔全無 legacy 標記 | 各檔頭 | 立刻可修（純註解） |
| RD-10 | `docs/API-GUIDE.md:812,838` 仍把 `new_extension_component` 列為可送出的 mapping_type（「legacy compatibility only」）——實際送出必定 422。正在做 handoff 的前端就是讀這段 | `API-GUIDE.md:812,838` | 立刻可修 |
| RC-13 | 07-28 meeting 文件 L27「Frontend 仍會送（活路徑）」錯誤——proposal UI 是 setTimeout stub，`frontend/src/services/` 無 mapping client，payload 永遠離不開瀏覽器。兩份 handoff 文件因此把優先序排反（第 1 層不緊急，第 2 層才緊急） | 已併入 `meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md`（優先序已校正） | 立刻可修（文件已合併） |

## D. 需要決策 / 補進計畫的

| # | 發現 | 決策點 |
|---|---|---|
| RA-4 | `recommended_next_checks` 消失 | (a) 當 cutover 功能缺口，在 v2 producer 補回（列 Plan 14 blocker）；或 (b) 正式宣告由 profile registry per-node checks 取代，把整組 service+TOML+欄位補進 Plan 15 移除清單 |
| RB-4 | quarantined row 的原檔留在 `mappings/` glob 內 → active repository 讀整個 project 直接 `StateCorruptionError`（實測 500）。Plan 13「可以留作 migration evidence」的敘述實務上不成立 | 建議 `_quarantine` 成功後把原檔 move 出 `mappings/`（quarantine 已有完整副本）；並回修 Plan 13 Task 4 敘述 |
| RB-6 | migration 寫進 active `ManualMapping.audit_metadata` 的三個 legacy key（`legacy_mapping_migration_version` 等）在 Plan 15 刪 module 後變成「state 裡沒人認得的欄位」 | 建議保留為 audit provenance，但必須文件化進 MODEL-CONTRACT |
| RB-5 | Plan 15 Task 3b 要刪的「state-side migration report writers」**不存在**；真正的產物目錄 `migration-backups/`、`migration-quarantine/` 反而沒被任何文件記載 | 修 Plan 15 文字 + 補 retention 條款 |
| RA-9/RA-10 | `ai_system_map_v2.py` 的 Generic/Compatibility 過渡型別群（9 個 class）不在任何移除清單；`SLOT_LAYER_BY_ID` 在 active normalizer 與 migration adapter 各一份逐字複本，drift 會靜默破壞 v1/v2 等價性 | 補進 Plan 15；`CompatibilityLayer`/`CompatibilityCandidateKind` 被 canonical 在用，建議改名避免誤刪 |
| RC-9 | frontend union 缺 `non_baseline_capability_candidate`——「移除 legacy 值」實際是**替換**不是刪除，照字面刪會讓 backend active response parse 失敗 | 修 handoff 文件措辭 |
| RA-2/RD-13 | `MapBuildManifest` schema 欄位預設 v1（兩位稽核者判定相反，主稽核裁決）：**保留 v1 預設**——舊 manifest JSON 缺欄位時 v1 是正確的歷史 provenance，改成 v2 會讓 pre-cutover build 撞 badge mismatch fail closed。處置=補註解說明用途 | `analysis_history.py:148-153` |

## E. 確認乾淨（實測通過，不需動）

- **mapping legacy shape 三道防線全封閉**：model 層 enum 窮舉 + `assert_never`（`ManualMappingCreate(mapping_type='new_extension_component')` 實測 ValidationError）；API 層 guard 422 穩定碼；storage 層 `read_model` 對 ValidationError re-raise 成 `StateCorruptionError`，無 dict passthrough、無吞例外
- **rollback 預設關閉驗證通過**：env 缺省 v2、非法值 `invalid_canonical_output_version` fail startup（composition root 第一行）、public v1 selection 回 `legacy_output_not_selectable`（三條 build 入口都有）
- **census 35/35 與 SHA-256 digest 精確重現**；stale/unknown 雙向 fail-closed 實測有效
- **`normalized_ai_system_map` 雙真相完全移除**（只剩反向斷言測試）
- **`contradicted` 第六態零風險**：src/tests/schemas/frontend 全零命中
- **`CanonicalMapLoader` 唯一 dispatcher 宣稱成立**：全 repo 無 route/viewer/renderer 自行判斷 schema shape
- **`MarkdownSummaryService` 已在 `0a68ccd` 乾淨刪除**（僅剩 `system_map.py:12` 一行過時註解）
- **`web/session_store.py`（Plan 13 modify 清單內）零 legacy 殘留**
- 5 個關鍵 Plan 13 checkbox 抽查（唯一 canonical field / enum 無 NEW_EXTENSION / 預設 v2 / public v1 拒絕 / invalid env fail startup）**全部成立**，live pytest 15 passed

---

## 建議執行順序

**P0 — Plan 15 執行前必解（否則 Task 3b 會出事）**
1. RB-2：把 `_LEGACY_MAPPING_TYPE = "new_extension_component"` 內聯進 `legacy_mapping_guards.py`，切斷對 migration module 的 import；Plan 15 Task 3b 補明確條目
2. RB-1/RD-3/RD-4：census 修補——`LEGACY_NAMES` 加 `LegacyManualMappingType`/`NEW_EXTENSION`，`ast.Constant` 比對集合改 `LEGACY_NAMES | LEGACY_LITERALS`，補 guard 的 allowlist record

**P1 — 現在就可做的清理批（全部低風險）**
3. RB-3 刪 `_legacy_detail_scan`；RA-5 降級 v1-typed viewer methods；RA-6 修 dead call + error code
4. 註解/文件批：RA-3、RA-7、RA-12、RD-10、RD-11、RC-13、RD-12、RA-2 補註解
5. RA-1 改 lazy 建構（v1 rollback 只在 operator mode 實例化），並修 Task 5 checkbox 敘述

**P1 — frontend handoff scope 修正**
6. 把 07-15 handoff 文件從「4 檔 5 筆」擴成三層真實清單（RC 報告的第 1/2/3 層）；第 2 層（API mode 已壞的 4 檔）優先於第 1 層（census 可見但 UI 未接線）

**P2 — 計畫文件同步**
7. Plan 15 補：RB-10/RA-8 的 DTO 拆檔前置 task、RA-9 Generic 型別群、RB-4 quarantine 去向、RB-5 目錄名與 retention、RB-6 audit key 文件化
8. RD-8 三個 stable error code（`invalid_canonical_output_version`/`legacy_rollback_not_representable`/`unsupported_system_map_schema_version`）補進 API-GUIDE / MODEL-CONTRACT；RD-9 給 `CanonicalMapLoadError` 加 `.code`

## 與既有計畫的銜接

- 15A/15B 拆分建議（2026-07-27 討論）不變，且本稽核強化其依據：15A（Plan 13 遺留收尾）
  的前置現在多了 P0 兩項；15B 維持 Gate-4。
- `phase2.5/2.md`（web 層硬化計畫）與本稽核唯一交集是 `_legacy_detail_scan`（該計畫已知
  但列為 Plan 4 範圍）——若 P1 批先做，phase2.5 後續計畫可劃掉該項。

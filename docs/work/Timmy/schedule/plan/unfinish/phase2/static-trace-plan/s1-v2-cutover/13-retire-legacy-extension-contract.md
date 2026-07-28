# ai-system-map/v2 Active Cutover 實作計畫

Status: **backend-complete / frontend-handoff-required**（2026-07-17：normal backend output
已切為 `ai-system-map/v2`，public v1 selection、operator rollback 與 10-artifact atomic
visibility 已通過；依使用者 ownership boundary，所有 frontend 修改已還原，5 筆 active
frontend legacy hits 留待前端負責人遷移）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 僅在 Plan 00A compatibility gate 通過後，把正常 build 的 canonical output 從
`ai-system-map/v1` 切換成 00A 已驗證的 generic `ai-system-map/v2`；保留 v1 dual-read、
migration adapter，以及到 Plan 15 才移除的 operator-only v1 rollback writer。

**Architecture:** 本計畫是 expand-and-contract 的 **cutover 階段**，不是 final removal。
所有正常 backend producer 與 active backend consumer 都改用 00A 的 `AiSystemMapV2`、
`CanonicalMapLoader` 與 normalized view；v1 只保留為 legacy input 與隔離的 operator
rollback output。Plan 15 才是移除 rollback writer 與 migration-only surface 的 contract 階段。

**Tech Stack:** Python 3.11、Pydantic v2、JSON Schema、pytest、現有 CLI/FastAPI、
frontend TypeScript contracts。

## Global Constraints

- `CanonicalMapLoader` 是唯一 schema dispatch owner；routes、CLI、viewer、manifest loader、
  renderers 不得自行判斷 v1/v2 shape。
- 正常 CLI/API request 不得選擇 v1 output；rollback 只能由 process-level operator setting
  啟用，且同一次 build 只寫一個 canonical map。
- 不得把 legacy extension 或 legacy mapping edge 自動升格成 detected reference capability
  或 canonical edge。
- Existing v1 artifacts、manifests 與 mappings 必須先可讀／可遷移，才能切換 default。
- Phase2 P0 artifact lifecycle 的「atomic」定義是對 supported readers 的 **atomic
  visibility**，不是宣稱 filesystem 可把 10 個檔案當成單一 transaction。
- 所有 migration、rollback、publish failure 都要有 stable error code、可回讀報告與
  restart/reload test。

---

## 執行摘要

### 目標

完成 generic canonical map 的預設輸出切換，並證明既有 v1 artifacts 仍能透過
唯一 migration path 讀取。切換後正常 build 不得建立 legacy-shaped `RagSystemMap`
output 或 top-level `extensions`；唯一例外是明確啟用、可稽核、預設關閉的 operator-only
rollback writer，並由 Plan 15 負責移除。

### 背景

Plan 00A 已負責新增 generic v2 model/schema、v1-to-v2 adapter、dual-read loader 與
compatibility report。若 13 再自行重建 v2，會形成兩套 schema 與不一致 migration
semantics。本計畫只執行 gate review、consumer migration、persisted mapping migration、
active default cutover 與 legacy write-path isolation；physical removal 留給 Plan 15。

### 目前 code 狀態

本計畫開始前必須確認：

- v1 仍是預設 output，但 v1/v2 都能由 `CanonicalMapLoader` 載入。
- v1 fixtures 經 adapter 後，components、edges、evidence 與 readiness findings
  已通過 semantic-equivalence tests。
- `AiSystemMapV2` 可表示 grounded RAG、non-grounded LLM app、tool agent 與 workflow
  graph，不要求填入 RAG slots。
- compatibility report 沒有 unresolved blocker；degraded consumers 有明確 owner。

任一條不成立，都必須回到 00A 修正，不得在 13 直接繞過。

### 2026-07-17 Stage A gate evidence

- Profile inference 與 readiness 維持消費 normalized `AiSystemMapV2`；Viewer 由
  `build_loaded()` 統一投影 loader 產出的 normalized map。legacy v1 source payload 可留在
  compatibility response，但 Viewer 不再自行看 badge 或重建 `RagSystemMap`。
- `BuildManifestService.load()` 先呼叫 `CanonicalMapLoader`；native v1/v2 runtime reload
  均回傳 usable `MapBuildResult` 與 Viewer，native v2 不經 v2-to-v1 downgrade。
- 獨立保存的 grounded v1/native-v2 fixtures 已比較 project semantics、components、edges、
  evidence、endpoints、risk hints、unmapped components、candidate facts，以及 readiness
  finding id/status/evidence refs；測試不在 runtime 由 adapter 產生 native v2 fixture。
- `tests/contracts/test_v2_cutover_consumer_allowlist.py` 固定 51 筆 direct hits：35
  `migrate`、15 `migration_only`、1 `remove`；Python production AST、frontend runtime
  `.ts/.tsx/.json` 與 operational `scripts/*.sh` 都在 executable scope，每筆都有
  path/symbol/classification/removal plan，未知、新增與 stale hit 皆 fail closed。
  Census SHA-256：
  `34d9f531636bef94e67db32664063af014500eb8af832586cc46ce380f457e6f`。
  （2026-07-28 註記：此 51 筆與這個 SHA-256 是 Stage A 當時的歷史 baseline，不重算；
  現行 census 數字與 digest 見下方「2026-07-17 backend completion」段落。）
- `CanonicalMapLoader` 對 array/null/string/number JSON roots 回 typed error；manifest active
  badge 與 artifact schema 不一致時，v1→v2、v2→v1 兩方向都 fail closed。
- Viewer v1 compatibility helpers 已移到 no-I/O module；recommended-next-check
  characterization 鎖定完整欄位與順序，`ViewerSessionService` 為 243 physical / 218 AST
  statement-span LOC。
- Live normal build 仍回傳 `active_schema_version="ai-system-map/v1"`，且
  `MapBuildResult` 仍保留 v1 `ai_system_map` 與 v2 `normalized_ai_system_map`。這是 Task 1B/2
  的待遷移 contract，不是 Stage A 已退休項目。
- 2026-07-17 final audit repair 後 backend `987 passed`、Ruff 與 Mypy 通過；native v1/v2
  reload、non-object root 與雙向 badge mismatch runtime probes 通過。

每次進入下一階段前仍須重跑 census、tests 與 runtime reload probe；`ready` 只表示可開始
Task 1B/2，不表示 cutover 已完成。

### 2026-07-17 backend completion / frontend handoff evidence

- Normal CLI/API build 已直接產生唯一 normalized `AiSystemMapV2`；public v1 selection 回
  `legacy_output_not_selectable`，非法 operator env 回
  `invalid_canonical_output_version` 並阻止啟動。
- Persisted mapping migration 已驗證 dry-run 零寫入、apply、restart idempotence、owner-only
  backup、project lock、atomic replace、manual-review quarantine 與 secret redaction。
- Initial scan、Apply 與 Detail Scan 共用 `BuildCommitService`；10 個 public sibling artifacts
  通過 same-parent staging、rename、complete manifest、latest CAS 與逐 boundary fault injection。
- Executable consumer census 為 `38 records / 38 hits`：`migrate=5`、
  `migration_only=25`、`operator_rollback=8`。5 筆 `migrate` 全部位於原始 frontend，
  SHA-256 為
  `1b6dc56ee312122b1d25b986ac637f2280c172e1deef50501439889baac69096`。
  （2026-07-28 更新：Plan 13.5 Stage B 把 `LegacyManualMappingType`／`NEW_EXTENSION`
  補進 `LEGACY_NAMES`，封死 `Enum.MEMBER.value` 間接引用盲點，並把
  `web/legacy_mapping_guards.py` 的內聯字面值一起登記，因此 35→38 筆、
  `migration_only` 22→25。2026-07-17 的 `35 records / 35 hits` 與 SHA-256
  `59fa4f066a0e37c9f73ce488e64da96cccab7c8a9e6a429b0c073a738544714b` 為歷史值。）
- Final backend gate 為 `1031 passed`，scoped Plan 13 gate 為 `977 passed`；Ruff、Mypy、
  shell syntax與 live CLI/FastAPI restart 均通過。Frontend 已回復原始 tree，原始 Vitest為
  `3 files / 7 tests passed`，build／lint exit 0；先前對暫時 frontend cutover 的
  Playwright結果不再作 current completion evidence。Windows 本輪由跨平台
  fixtures/contracts 覆蓋，未宣稱 Windows host live QA。
- 完整實作、問題修復與 remaining warnings 記錄於
  `docs/work/Timmy/schedule/report/2026-07-17-phase2-plan13-v2-cutover-REP.md`。
- Frontend 要做的 4 個檔案、原因、實作順序與驗收清單記錄於
  `docs/work/Meeting-Sync/meeting_sync_2026_07_15/frontend-ai-system-map-v2-cutover.md`。

### 相關檔案

- Reuse: `src/kai_mind/core/models/ai_system_map_v2.py`
- Reuse: `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`
- Reuse: `src/kai_mind/core/services/canonical_map_loader.py`
- Reuse: `schemas/ai-system-map.v2.schema.json`
- Modify: `src/kai_mind/core/models/map_build.py`
- Modify: `src/kai_mind/core/models/analysis_history.py`
- Modify: `src/kai_mind/core/models/mapping_base.py`
- Modify: `src/kai_mind/core/models/mapping_candidates.py`
- Modify: `src/kai_mind/core/services/system_map_normalize_service.py`
- Modify: `src/kai_mind/core/services/system_map_materialization_service.py`
- Create: `src/kai_mind/core/services/legacy_v1_rollback_service.py`
- Modify: `src/kai_mind/core/services/map_build_service.py`
- Modify: `src/kai_mind/core/services/map_build_pipeline.py`
- Modify: `src/kai_mind/core/services/apply_confirmations_service.py`
- Modify: `src/kai_mind/core/services/apply_confirmations_contracts.py`
- Modify: `src/kai_mind/core/services/build_artifact_publisher.py`
- Modify: `src/kai_mind/core/services/build_manifest_service.py`
- Create: `src/kai_mind/core/services/build_commit_service.py`
- Modify: `src/kai_mind/core/services/map_build_query_service.py`
- Modify: `src/kai_mind/core/services/graph_projection_service.py`
- Modify: `src/kai_mind/core/services/graph_markdown_renderer.py`
- Modify: `src/kai_mind/core/services/graph_mermaid_renderer.py`
- Modify: `src/kai_mind/core/services/profile_inference_service.py`
- Modify: `src/kai_mind/core/services/readiness_report_service.py`
- Modify: `src/kai_mind/core/services/static_execution_artifact_service.py`
- Modify: `src/kai_mind/core/services/viewer_session_service.py`
- Modify: `src/kai_mind/core/services/system_map_index.py`
- Modify: `src/kai_mind/core/services/detail_scan_service.py`
- Modify: `src/kai_mind/core/services/detail_scan_build_service.py`
- Modify: `src/kai_mind/core/services/query_trace_service.py`
- Modify: `src/kai_mind/core/services/mapping_proposal_service.py`
- Modify: `src/kai_mind/core/services/mapping_proposal_candidates.py`
- Modify: `src/kai_mind/core/services/mapping_proposal_mapping_factory.py`
- Modify: `src/kai_mind/core/services/manual_mapping_service.py`
- Modify: `src/kai_mind/core/services/manual_mapping_materializer.py`
- Modify: `src/kai_mind/core/services/manual_mapping_support.py`
- Create: `src/kai_mind/core/services/legacy_manual_mapping_migration_service.py`
- Modify: `src/kai_mind/core/providers/output_artifact_provider.py`
- Modify: `src/kai_mind/core/providers/local_json_project_repository.py`
- Modify: `src/kai_mind/core/providers/local_json_history_repository.py`
- Modify: `src/kai_mind/core/providers/local_json_state_provider.py`
- Modify: `src/kai_mind/core/providers/local_json_state_storage.py`
- Modify: `src/kai_mind/cli/main.py`
- Modify: `src/kai_mind/cli/map_command.py`
- Modify: `src/kai_mind/cli/trace_command.py`
- Create: `src/kai_mind/cli/migrate_legacy_mappings_command.py`
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/routes/detail_scan_routes.py`
- Modify: `src/kai_mind/web/routes/trace_routes.py`
- Modify: `src/kai_mind/web/routes/mapping_proposal_routes.py`
- Modify: `src/kai_mind/web/session_store.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/proposal/EditForm.tsx`
- Modify: `frontend/src/data/scanTemplate.mock.ts`
- Modify: `frontend/src/data/frontend-json-sample.json`
- Test: `tests/contracts/test_ai_system_map_v2_schema.py`
- Create: `tests/contracts/test_v2_cutover_consumer_allowlist.py`
- Test: `tests/integration/test_map_build_service.py`
- Test: `tests/integration/test_build_manifest_service.py`
- Create: `tests/unit/core/test_build_commit_service.py`
- Create: `tests/unit/core/test_legacy_v1_rollback_service.py`
- Test: `tests/unit/core/test_viewer_session_service.py`
- Test: `tests/unit/core/test_detail_scan_service.py`
- Test: `tests/unit/core/test_query_trace_service.py`
- Create: `tests/unit/core/test_legacy_manual_mapping_migration_service.py`
- Test: `tests/web/test_project_scan_routes.py`
- Test: `tests/web/test_detail_scan_routes.py`
- Test: `tests/web/test_trace_routes.py`

### 實作步驟

先審核 00A gate 並凍結 direct reader/writer census；保持 v1 default 時先遷移 consumers，
再執行 persisted extension mapping dry-run/apply migration。所有 reload/API/CLI tests 通過後，
才啟用 v2 canary、切換 normal default、驗證 atomic visibility，最後實測 operator-only
rollback 與再次切回 v2。

### 摘要驗收條件

新 scan 預設產生 `ai-system-map/v2`；所有 active consumers 經
`CanonicalMapLoader` 取得 normalized v2；v1 artifact 仍可讀，v1 writer 只存在於預設關閉的
operator rollback boundary。完整 sibling artifacts 都引用同一 validated v2 build result，
explicit build-id/history reader 只能在 complete manifest 後看見完整 set，latest reader 則只在
pointer CAS promotion 後切換。Plan 14 完成 final validation 後，Plan 15 才可移除 rollback
writer 與 migration-only compatibility。

### 摘要風險

- 不得刪除 v1 schema、v1 fixtures、v1 reader 或 adapter。
- 不得把 legacy extension 自動升格為 detected capability。
- 不得用 temporary dual-write 掩蓋 consumer drift；如需 rollback，切回 v1 default，
  不是同時寫兩份互相競爭的 canonical output。
- v1 rollback 不得由一般 request body/query parameter 選擇；只能由 operator 在 process
  啟動前設定，並在 manifest/warning 記錄實際 output version。
- `profile_signals.json` 與 `readiness_report.json` 是 derived artifacts，不可反向改寫
  canonical facts。
- 不新增數字 `confidence`。Capability/profile status 統一為
  `detected / partial / undetermined / not_detected / conflicted`；legacy
  `contradicted` input 必須經 adapter 對應為 `conflicted`，不得形成第六種 active status。

## Plan 00A／13／14／15 ownership

| Plan | 擁有的工作 | 明確不做 |
| --- | --- | --- |
| 00A | v2 schema/model、v1 adapter、dual-read loader、compatibility gate | 不切 active default |
| 13 | consumer migration、persisted mapping migration、active enum/API/UI 收斂、v2 default flip、operator rollback、atomic visibility | 不刪 v1 reader/schema、legacy migration DTO/command 或 rollback writer |
| 14 | 真實 fixture/import、reload、rollback、semantic equivalence final validation | 不清除 compatibility code |
| 15 | 移除 operator v1 writer/env、legacy migration DTO/command/quarantine 與不再需要的 fixtures；將 dual-read 收斂成 migration-only 或刪除 | 不重新做 cutover，也不延後 Plan 13 的 active API/UI 停寫 |

## Rollback contract

Plan 13 不再同時要求「刪除 v1 writer」與「可切回 v1」。目標 contract 固定如下：

- Normal mode：`ai-system-map/v2`，所有一般 CLI/API build 都走這條路。
- Operator rollback mode：process-level setting
  `KAI_MIND_CANONICAL_OUTPUT_VERSION=ai-system-map/v1`；預設值是 v2，非法值 fail startup。
- 同一次 build 只能寫一份 `ai_system_map.json`，禁止 v1/v2 dual-write。
- Public `system_map_schema_version="ai-system-map/v1"` request 不再是 rollback surface；cutover
  期間回傳 stable `legacy_output_not_selectable`，Plan 15 再移除 deprecated input field/flag。
- Rollback mode 必須在 CLI/API result、manifest、structured warning 中標示
  `active_schema_version="ai-system-map/v1"` 與 `operator_rollback_active`。
- Rollback 使用同一版本 binary 的隔離 writer，因此仍可 dual-read 已存在的 v2 artifacts；
  不把「重新部署不支援 v2 的舊 binary」當成資料安全 rollback。
- Rollback branch 保留目前 v1 materialization path，但只在 operator boundary 內執行；產生 v1
  artifact 後立刻經 `CanonicalMapLoader` normalize 成 v2，所有 process 內 consumer 仍只接 v2。
  禁止用 generic v2 做有損 v2→v1 downgrade。
- Rollback preflight 只允許可由 legacy contract 完整表示的 build。若存在 v2-only component、
  endpoint/edge 或其他無法無損表示的 fact，回傳 `legacy_rollback_not_representable` 且不寫 artifact，
  不得靜默丟資料。
- Plan 15 只有在 Plan 14 報告證明不再需要 rollback 後，才能刪除 env setting 與 v1 writer。

## Active consumer / writer census baseline（2026-07-15）

這份 census 是執行基線，不是永久 allowlist。Task 1 必須重新跑 deterministic search，任何新增
direct v1 hit 都是 blocker，直到分類為 `migrate`、`operator-rollback`、`migration-only` 或
`remove`。

| Surface | 目前 direct files / symbols | Plan 13 target |
| --- | --- | --- |
| Request/result/schema selection | `core/models/map_build.py`、`core/models/analysis_history.py`、`cli/map_command.py`、`web/schemas.py`、`web/routes/scan_routes.py` | `MapBuildResult.ai_system_map` 成為唯一 v2 canonical field；移除 `normalized_ai_system_map` 雙真相；public v1 selection 失效 |
| Active producer | `system_map_normalize_service.py`、`system_map_materialization_service.py`、`map_build_service.py`、`map_build_pipeline.py`、`rag_template_service.py` | normal build 直接產生/驗證 v2；`rag-core-v1` 只留 compatibility grounding/rollback boundary |
| Artifact writer | `build_artifact_publisher.py`、`providers/output_artifact_provider.py`、planned `legacy_v1_rollback_service.py` | normal writer 接 `AiSystemMapV2`；v1 materializer/writer 只由 operator-only service 擁有 |
| Manifest/reload/history | `build_manifest_service.py`、`map_build_query_service.py`、`providers/local_json_history_repository.py`、`web/session_store.py` | loader 先 dispatch 再取得 normalized v2；manifest 不先呼叫 v1 validator；complete manifest 開放完整 history、latest pointer CAS 只切 active build |
| Rebuild/promotion orchestration | `apply_confirmations_service.py`、`apply_confirmations_contracts.py`、`detail_scan_build_service.py`、`web/routes/scan_routes.py` | 全部委派 `BuildCommitService`；不再各自排列 artifact/manifest/pointer，且傳入 expected latest id/revision |
| Viewer/projection | `viewer_session_service.py`、`graph_projection_service.py`、`system_map_index.py`、`cli/viewer_command.py`、`web/routes/viewer_routes.py`、`core/models/viewer.py` | 全部接 v2/GraphViewModel；schema branching 只在 loader |
| Detail scan | `detail_scan_service.py`、`detail_scan_build_service.py`、`web/routes/detail_scan_routes.py`、`web/schemas.DetailScanResponse` | input/output 改 v2；detail scan 不再建立/回傳 `ExtensionComponent` |
| Query trace | `query_trace_service.py`、`cli/trace_command.py`、`web/routes/trace_routes.py` | 以 v2 `endpoints[]` / `SystemMapIndex.endpoint_by_id` 找 endpoint；不再直接驗證/接收 `RagSystemMap` |
| Derived consumers | `profile_inference_service.py`、`readiness_report_service.py`、`static_execution_artifact_service.py`、`graph_projection_service.py`、`graph_markdown_renderer.py`、`graph_mermaid_renderer.py` | 只接 v2 或 GraphViewModel；保留 `source_schema_version` 作 provenance，不自行 dispatch |
| Provenance-only models | `core/models/ai_system_map_v2.py`、`profile_signal.py`、`readiness_report.py` | 可保留 v1/v2 literal 以描述 source；不得據此選 active producer、validator 或 UI shape |
| Extension detection/materialization | `component_detection_service.py`、`manual_mapping_materializer.py`、`manual_mapping_support.py`、`system_map_normalize_service.py` | normal path 只產生 unmapped/capability candidate，不建立 top-level extension |
| Mapping model/service | `models/mapping_base.py`、`models/mapping_candidates.py`、`manual_mapping_service.py`、`manual_mapping_materializer.py`、`manual_mapping_support.py`、`mapping_proposal_service.py`、`mapping_proposal_candidates.py`、`mapping_proposal_deterministic.py`、`mapping_proposal_decisions.py`、`mapping_proposal_mapping_factory.py`、`mapping_proposal_provider.py`、`mapping_proposal_repository.py`、`mapping_proposal_support.py` | 禁止新 `NEW_EXTENSION`；legacy value 只由 migration DTO/command 讀取 |
| Persisted mapping storage | `providers/local_json_project_repository.py`、`providers/local_json_state_storage.py`、`providers/local_json_state_provider.py` | migration command 先讀 raw JSON/Legacy DTO；active repository 只 parse 新 `ManualMapping`，project lock + per-file atomic replace |
| Web/frontend mapping | `web/routes/mapping_proposal_routes.py`、`frontend/src/types.ts`、`frontend/src/components/proposal/EditForm.tsx`、frontend mocks/sample | API/UI 只送 existing slot、non-baseline candidate、needs-info/skip 等 active types |
| Orphan/legacy renderer | `markdown_summary_service.py` | 若無 active caller，移除或移到 migration-only test helper；不得留成未測 v1 consumer |
| Migration-only allowlist | `core/models/system_map.py`、`system_map_validation_service.py`、`system_map_v1_to_v2_adapter.py`、`canonical_map_loader.py` v1 branch、`schemas/ai-system-map.v1.schema.json`、v1 fixtures/tests | Plan 13 保留；任何 normal route/service 直接 import 都失敗 allowlist test |

`SystemMapValidationService` 維持明確的 v1 validator，不把它改成第二個 schema dispatcher。
`CanonicalMapLoader` 讀 badge 後，分別委派 v1/v2 validator，再只把 normalized
`AiSystemMapV2` 交給下游。

## 2026-07-07 UA 整合對齊

Plan 13 cutover 不採用 UA Phase 3～7，也不改 canonical output 名稱。Active output 仍是
KAI-Mind 的 `ai_system_map.json`、`profile_signals.json` 與 `GraphViewModel`；UA
`ua-analysis-result` 只在 scan snapshot 內作 internal sidecar。Plan 13 的 gate 應確認
v2 active output 可消費 UA structural facts，但不得把 UA graph vocabulary 變成新的
canonical schema。

## Preconditions：審核 00A Compatibility Gate

| Gate evidence | 2026-07-17 state | Exit condition |
| --- | --- | --- |
| Direct reader/writer census | passed；51 筆都有分類與 removal plan，涵蓋 production Python、frontend runtime JSON/TS 與 operational shell scripts | `test_v2_cutover_consumer_allowlist.py` 通過，所有 hit 有分類 |
| v1 adapter evidence/location preservation | 00A 已覆蓋 | regression tests 維持通過 |
| Viewer/profile/readiness normalized consumers | passed for 00A；Viewer projection 與 manifest reload 先經唯一 loader，legacy active inputs留在 census 的 `migrate` 類 | native-v1/v2 reload probe 都通過，Viewer 不自行 schema dispatch/reconstruct |
| Grounded canonical facts/readiness semantic equivalence | passed；獨立 paired fixtures regression 通過 | v1-adapted 與 native-v2 paired fixture 的 project/components/edges/evidence/endpoints 與 readiness facts 等價 |
| Non-grounded/tool/workflow fixtures | 00A 已覆蓋 | schema + loader + consumer tests 維持通過 |
| Windows/macOS path fixtures | 00A 已覆蓋 | CI matrix 維持通過 |
| Backend tests、Ruff、Mypy | final audit repair 後 987 passed；Ruff/Mypy exit 0 | mutation 後全部再 exit 0，報告附 command/output summary |

- [x] `00A-introduce-ai-system-map-v2-compatibility-migration.md` Task 4/5 對應 checkbox 已由
  新測試證據改成 `[x]`。
- [x] `docs/work/Timmy/schedule/report/2026-07-10-00a-review-p1-fixes-REP.md` 已追加最新
  verification，remaining risks 不再包含 normalized consumer/readiness equivalence。
- [x] 本計畫的 consumer census 與 live AST/text facts 一致。
- [x] 已保存切換前 normal v1 default 證據；operator rollback command、invalid value 與
  rollback stop condition 保留給 Tasks 2/7，不在 Stage A 假造未實作命令。

上表 Stage A gate 已全數通過，因此本檔可由 `blocked` 改成 `ready`。Rollback configuration
是 cutover implementation/acceptance，不是啟動 Task 1B 的先決條件；仍須先執行 Task 1B
的 red test，再以 Task 2 轉綠，不得跳過測試直接切 default。

## Task 1：凍結 Cutover Gate 與 Executable Consumer Census

### Task 1A：Blocked 期間可完成的 green baseline

- [x] 先建立 `tests/contracts/test_v2_cutover_consumer_allowlist.py`；由 deterministic
  `rg`/AST search 列出所有 `RagSystemMap`、`ExtensionComponent`、
  `new_extension_component`、`ai-system-map/v1` 與直接 v1 validator hit。
- [x] allowlist 每筆必須包含 `path`、`symbol`、`classification` 與 `removal_plan`；只接受
  `migrate`、`operator_rollback`、`migration_only`、`remove` 四種分類，未知或新增 hit
  直接使測試失敗。
- [x] characterization tests 先鎖定目前 v1 default、dual-read reload 與 direct consumer
  baseline，並保持全套 quality gates green；報告保存 command、exit code 與 census digest。

### Task 1B：Status=`ready` 後的 red cutover contract

- [x] 先寫 failing tests，要求正常 build 的 `schema_version` 為 `ai-system-map/v2`，且
  `MapBuildResult` 只暴露一個 normalized canonical map，不再同時保留 v1
  `ai_system_map` 與 v2 `normalized_ai_system_map` 兩份 truth。
- [x] 測試 v2 output 不含 `extensions`、RAG-only required slots 或
  `system_type="rag"` 限制。
- [x] 測試 v1 input 仍由 loader + adapter 轉成 normalized v2；未知 schema version
  fail closed 並回傳 stable `unsupported_system_map_schema_version`。
- [x] 只允許上述新 cutover assertions 因尚未 flip 而 red；先確認失敗訊息正是 v1 default／
  dual-result contract，再立即進 Task 2。不得以 `xfail`、skip 或放寬 assertion 隱藏紅燈。

## Task 2：切換 Canonical Producer Default，隔離 Rollback Writer

- [x] `MapBuildService`、`MapBuildPipeline` 與 `SystemMapNormalizeService` 正常模式直接建立、
  驗證並回傳 00A 的 `AiSystemMapV2`；`MapBuildResult.ai_system_map` 是唯一 normalized
  canonical field，移除 `normalized_ai_system_map` 雙真相。
- [x] 即使 operator rollback writer 輸出 v1 檔案，process 內的 `MapBuildResult` 與下游
  consumer 仍只接 normalized v2；只有 manifest 的 `active_schema_version` 與實際
  `ai_system_map.json` schema 反映 rollback output。
- [x] 一般 CLI/API 的 `system_map_schema_version` 不再選擇 output。要求 v1 時回傳
  `legacy_output_not_selectable`；新 manifest 不再把 `requested_schema_version` 當決策欄位，
  舊 manifest 讀取時只視為 compatibility provenance。
- [x] composition root 讀取 `KAI_MIND_CANONICAL_OUTPUT_VERSION`，只接受
  `ai-system-map/v2` 或 `ai-system-map/v1`；缺省為 v2，非法值以 stable
  `invalid_canonical_output_version` 阻止 process 啟動。
- [x] 將現有 v1 materialization 封裝成 `LegacyV1RollbackService` operator-only boundary；normal
  producer 不建立 `RagSystemMap` 或 `ExtensionComponent`，同一次 build 不得 dual-write。
- [x] operator rollback branch 呼叫隔離的 legacy v1 materializer，寫出 v1 後立即透過 loader/
  adapter 得到 `MapBuildResult.ai_system_map: AiSystemMapV2`；不得建立 v2→v1 downgrade adapter。
- [x] rollback preflight 對 v2-only fact fail closed，回傳
  `legacy_rollback_not_representable`；測試證明失敗時沒有 manifest、latest promotion 或被截斷的
  v1 artifact。
- [x] `SystemMapValidationService` 保留為 v1 validator，不擴張成第二個 dispatcher；只有
  `CanonicalMapLoader` 依 schema badge 委派 v1/v2 validator，再回傳 normalized v2。
- [x] manifest 記錄 `active_schema_version`、`source_schema_version`、
  `operator_rollback_active` 與 migration warnings，consumer 不得從檔案 shape 猜版本。

## Task 3：遷移所有 Active Consumers

- [x] `BuildManifestService.load()` 先呼叫 `CanonicalMapLoader`，不得在 loader 前直接呼叫
  v1-only `SystemMapValidationService`；restart 後載入既有 v1 與新 v2 build 都回傳
  normalized v2。
- [x] Viewer、`SystemMapIndex`、graph projection、CLI/Web viewer、profile inference、
  readiness engine、static execution recoverers 與 renderers 只接 `AiSystemMapV2` 或
  `GraphViewModel`。
- [x] detail scan input/output 改用 v2，不建立或回傳 `ExtensionComponent`；query trace 改以
  v2 `endpoints[]` 與 `SystemMapIndex.endpoint_by_id` 尋找 endpoint。
- [x] Backend mapping proposal、manual mapping 與 component detection 只建立 existing-slot、
  non-baseline capability candidate、needs-more-information 或 skip 類型；routes 不自行判斷
  v1/v2 shape。
- [ ] Frontend contract 仍保留 legacy proposal type與 v1 sample，由前端負責人另行遷移。
- [x] v1 compatibility metadata 只作 provenance、migration warning/debug，不得形成產品分類、
  UI filter 或 readiness verdict；`primary_map_type` 只能由 report/projection 推導。
- [x] `rag-core-v1` 只保留為 legacy input grounding 或 operator rollback boundary；v2 不輸出
  compatibility-derived product verdict。citation/source mapping 留在
  `readiness_report.json.source_traceability`，不成為 canonical RAG-only hard requirement。
- [x] 若 `MarkdownSummaryService` 無 active caller，移除或降為 migration-only test helper；
  不得保留未測試、可被正常路徑誤用的 v1 renderer。

## Task 4：遷移 Persisted Legacy Extension Mappings

目前 persisted mapping JSON 會直接 parse 成 `ManualMapping`。若先刪除
`ManualMappingType.NEW_EXTENSION`，包含 `mapping_type="new_extension_component"` 的既有專案
會在 restart/load 階段直接失敗；因此 migration 必須在 enum 與 active loader 收斂前完成。

- [x] 建立 `LegacyManualMappingDTO` 與
  `LegacyManualMappingMigrationService`，先以隔離 DTO 讀 raw JSON，再轉成 active
  `ManualMapping`；normal repository 不得長期接受 legacy shape。
- [x] 建立 `migrate-legacy-mappings` CLI。預設只做 `--dry-run` 且零寫入；必須明確傳入
  `--apply` 才能更新 KAI-Mind state directory，禁止修改被掃描的 target project。
- [x] 轉換矩陣固定如下，實作者不得自行推測：

| Legacy row | Active result | 必須保留／禁止 |
| --- | --- | --- |
| `CONFIRMED` 且 `extension_id/name/kind` 完整 | `NON_BASELINE_CAPABILITY_CANDIDATE` + `CONFIRMED` | 對應到 `capability_candidate_id/name/kind`；保留 `mapping_id`、project/source、evidence、reason、proposal、decision source、created time；不得升格為 detected reference capability |
| `REJECTED`、`SKIP_FOR_NOW` 或 `NOT_APPLICABLE` 且欄位完整 | 相同 active mapping type + 原 decision | 保留稽核歷史；非 `CONFIRMED` 永不 materialize capability candidate |
| 任一 legacy row 缺少必要 extension 欄位 | `requires_manual_review`，不建立猜測值 | 原 row 只留 migration quarantine；若 decision 是 `CONFIRMED`，阻擋 v2 cutover |
| `extension_edges` 非空 | 不轉成 canonical edge | 將原 payload digest、opaque `quarantine_ref` 與 warning 寫入 audit metadata；不得保存/回傳 absolute path，關係需由後續 evidence-backed mapping 重新確認 |

前三列先決定 row 的 active mapping/decision；第四列是可與前三列同時套用的 modifier。也就是
完整且 confirmed 的 row 仍可轉 capability candidate，但其中的 `extension_edges` 一律隔離，絕不
偷偷轉成 v2 canonical edge。

- [x] migration 使用固定 `migration_version`，且必須 idempotent：成功轉換時只更新一次
  `updated_at` 與 `mapping_digest`；重跑相同輸入回報 `already_migrated`，不得重複產生 row。
- [x] `--apply` 先在 KAI-Mind state directory 建立原始 mapping backup 與 index。Backup 可能含
  legacy free-text，因此必須使用平台可提供的 owner-only access、不得寫入 target repo，也不得把
  payload 複製到 log/report；report 只記 opaque ref 與 digest。
- [x] 在 project-level lock 內以 same-directory temp + replace 原子更新每個 mapping file；單檔
  失敗不得留下半份 JSON，並回傳 stable `legacy_mapping_migration_failed`。若同一 project
  多檔 migration 中途失敗，標成 `partial_requires_retry` 並阻擋 cutover；idempotent rerun 從
  digest 判斷已完成 rows，不重複轉換。
- [x] migration report 至少包含 `scanned`、`converted`、`already_migrated`、
  `requires_manual_review`、`failed`、input/output digest 與 masked error；不得印出完整 evidence
  snippet、secret 或原始 payload。
- [x] Normal API 立即拒絕新 `new_extension_component` request，回傳
  `legacy_mapping_type_read_only`。所有 `CONFIRMED` legacy rows 都完成轉換後才可 flip backend v2；
  其他 unresolved quarantined rows 可以留作 migration evidence，但會繼續阻擋 Plan 15 cleanup。
- [ ] Frontend UI 仍可組出 legacy request；backend會 fail closed，但 UI contract需由前端負責人
  遷移。
- [x] migration apply 完成且 reload gate 通過後，從 active `ManualMappingType` 移除
  `NEW_EXTENSION`；相同字串只留在 migration-only `LegacyManualMappingDTO` enum。Plan 15 再刪
  DTO/command/quarantine，而不是把 active backend enum/API removal 延後。
- [x] 先測 dry-run 零寫入，再測 apply/restart、idempotence、crash recovery、backup、digest、
  concurrent project lock、缺欄位與 secret redaction。

## Task 5：停止正常 Extension Write Surface

- [x] Backend新 scan、manual mapping、mapping proposal與component detection不再建立
  top-level `extensions` 或接受 `NEW_EXTENSION` / `new_extension_component`。
- [ ] Frontend schema、mock與sample仍保留legacy extension/v1 contract，等待前端handoff。
- [x] 未確認 component 保留為 generic unmapped/candidate fact；使用者確認 non-baseline 後只寫入
  capability candidate，不建立 extension 類別或 legacy edge。
- [x] v1 schema/fixture、Legacy DTO、adapter 與 operator rollback serializer 明確標示
  legacy/read-only；normal build path 不得 import v1 **map contract**。lazy 化由 Plan 13.5
  Task B3（RA-1）完成：`MapBuildService` / `MapBuildPipeline` 只在 operator rollback
  （`canonical_output_version == ai-system-map/v1`）或呼叫端顯式注入時才 function-local import
  並建 rollback 物件圖；v2 模式下 `MapBuildService()`、`create_app()` 與 CLI 都不 import
  `legacy_v1_rollback_service`、`system_map_materialization_service`、
  `system_map_normalize_service`（`tests/unit/core/test_map_build_service_wiring.py`
  的 `test_active_v2_entry_points_import_no_v1_rollback_module` 以子行程 `sys.modules`
  探針逐一把關這三個 entry point）。scan-phase 共用 DTO（`models/system_map.py` 內的
  `Evidence`/`Endpoint`/`Flow` 等）仍被 active path import，其拆分不屬本條，歸 Plan 15
  （見 13.5 RA-8 / RB-10）。
- [x] Task 1 allowlist 是 executable gate；backend hit只能命中`operator_rollback`、
  `migration_only`或測試明列的legacy evidence；frontend-owned active hit分類為`migrate`：

```bash
rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1" \
  src tests frontend docs
```

Current backend-only boundary：`38 records / 38 hits`，其中5筆`migrate`全在frontend；每個hit
都能在allowlist找到相同path/symbol/classification，未知或stale仍fail closed。
（2026-07-28更新：Plan 13.5 Stage B補上`LegacyManualMappingType`／`NEW_EXTENSION`與
`web/legacy_mapping_guards.py`後由35筆增為38筆；`35 records / 35 hits`為歷史值。）

## Task 6：以 Staging Directory + Manifest + Latest Pointer 定義 Atomic Visibility

本計畫不宣稱一般 filesystem 能將 10 個檔案與 state repository 做成單一 transaction，也不把
「historical build 可查詢」與「active latest 已切換」混成同一件事。Contract 有兩個依序發生、
各自 atomic 的 visibility boundary：

1. **Artifact-set publish point**：同一 output parent 下的 staging directory 完成 10 檔驗證後，
   以 rename/replace 成唯一 final build directory；在此之前 final path 不存在。
2. **Active promotion point**：完整 manifest 保存後，`promote_latest_build()` 在 project lock 內用
   `expected_latest_build_id + expected_revision` CAS 原子替換 latest pointer。

因此 explicit build-id/history reader 最早可在 complete manifest 保存後讀到**完整但尚未是
latest**的 build；latest reader 在 pointer CAS 前永遠仍讀舊 build。這不是所有 reader 同時切換的
global transaction，但任何 supported reader 都不會看到 partial artifact set。

- [x] 建立 `BuildCommitService`，讓 initial scan、apply-confirmations 與 detail-scan build 共用
  同一 state machine，不再由各 route 自行排列 persist/promote/session-store 呼叫：

```text
PREPARING
  -> create <build_id>.staging under final output parent
  -> write 10 artifacts inside staging with same-directory temp + replace
  -> validate required set, scope ids, references and digests
  -> rename staging directory to unique final directory  # artifact-set publish
  -> persist immutable MapBuildManifest(status="complete")
  -> promote_latest_build(expected id/revision)           # active promotion
  -> expose result through API/session                     # ACTIVE
```

- [x] Final build directory 必須是新 path；若已存在就以 `build_output_conflict` fail closed，禁止
  overwrite。Staging/final 必須位於同一 filesystem parent；無法保證 atomic rename 時以
  `atomic_artifact_publish_unavailable` 中止，不退回逐檔公開。
- [x] `MapBuildQueryService.get/list` 只從 repository 的 complete manifest 找 build，不能掃描 raw
  output directory；`latest()` 必須先讀 CAS pointer，再載入該 manifest。Low-level path reader 不在
  supported-reader guarantee 內。

- [x] 同一 validated build result 產生 Phase2 P0 sibling set（對齊
  `docs/MODEL-CONTRACT.md`；**7 JSON + 3 render，共 10 檔**；`GraphViewModel` 是 ephemeral
  API projection，不是 required on-disk sibling）：
  - Canonical + assessment：`ai_system_map.json`、`profile_signals.json`、
    `readiness_report.json`。
  - Static execution：`call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、
    `evidence_table.json`。
  - Render outputs：`ai_system_map.md`、`system_map.mmd`、`execution_map.mmd`。
- [x] 10 個 sibling 與 manifest 共用同一 `scan_id`、`build_id`、`environment_id` 與
  `artifact_set_version`；manifest 保存每檔 digest/size/schema status。finding、component、edge、
  signal 與 execution step 只能引用存在的 evidence id。
- [x] producer 不重跑 scanner、UA 或 LLM 來補 canonical facts；所有 sibling 都由同一 immutable
  build result/projection 產生。
- [x] initial scan、apply-confirmations 與 detail-scan 都把開始時讀到的 latest id/revision 傳入
  `BuildCommitService`；若另一 build 先 promote，stale CAS 回傳 `stale_latest_revision`，新完整
  artifact set 可保留成 non-latest history 或依明確 cleanup policy 清除，但不得覆蓋較新 latest。
- [x] failure/recovery contract 固定如下：

| Failure point | Reader-visible result | Recovery |
| --- | --- | --- |
| staging 內任一 artifact write 前／中 | final path/manifest 不存在；history/latest 都看不到新 build | 清除 temp/staging；restart cleanup 依 build id/digest 判斷 orphan |
| staging 驗證失敗或 directory rename 前 | 同上 | 修正或丟棄 staging；不得 persist manifest |
| final directory rename 後、manifest 保存前 | raw final path 存在，但 supported history/latest 都看不到 | restart 驗證後補 manifest，或安全清除 orphan final directory |
| complete manifest 已保存、pointer 尚未 promote | build-id/history 可讀完整新 build；latest 仍是舊 build | 以原 expected revision 重試 promote；CAS stale 則保留 non-latest 或清除 |
| pointer CAS 已 promote | history/latest 都可讀完整新 build | API/session 寫入失敗不得破壞 committed build；回 stable warning 並可重建 projection |

- [x] 新 build 在 feature enabled 時缺任何 required sibling、scope id 不一致、reference dangling
  或 digest mismatch 都 fail closed，且不得 promote。舊 build 缺 optional sidecar 時可載入 base v2
  graph 並回傳 stable degraded warning；不得把舊 5-file subset 改寫成新 product contract。
- [x] fault-injection 測試覆蓋 10 個 artifact 的每個 write boundary、directory rename 前後、
  manifest 前後、pointer CAS 前後、concurrent build/reader 與 process restart；macOS/Windows 都
  驗證 same-parent staging rename、same-directory file replace 與 latest pointer 語意。直接指定任意
  檔案的低階 `validate-map` 不在 atomic visibility 保證內。

## Task 7：Rollback、Regression 與 Cutover Report

- [x] 在 staging fixture 流程執行 active v2 canary，驗證 CLI/API/viewer/detail/trace/reload 與
  10-artifact lifecycle。
- [x] 以 operator env 執行一次 v1 rollback build，確認同一 binary 仍能讀取既有 v1/v2、沒有
  資料破壞、manifest/warning 可稽核；再移除 env 切回 v2並確認 output deterministic。
- [x] 測試 invalid env fail startup，以及 public CLI/API v1 selection 回傳
  `legacy_output_not_selectable`。
- [x] 執行 scoped contract/unit/integration/web/frontend gates：

```bash
.venv/bin/pytest tests/contracts tests/unit/core tests/integration tests/web -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
cd frontend && npm run build && npm run lint
```

- [x] 更新 compatibility report 為 cutover report，至少記錄 gate/census digest、active version、
  persisted mapping migration counts、legacy read coverage、artifact commit/fault-injection、rollback
  結果與 remaining warnings。
- [ ] 待 frontend handoff 的5筆active hits歸零後，才把Status改為`complete`。

## 驗收標準

- [ ] Status 只有在 00A Task 4/5、executable consumer allowlist、reload probe 與完整 quality
  gates 通過後才可由 `blocked` 改成 `ready`；完成 Task 7 report 後才可改成 `complete`。
- [x] 新 build 預設輸出 `ai-system-map/v2`；一般 CLI/API 無法要求 v1，operator rollback
  預設關閉、可稽核且不 dual-write。
- [x] operator rollback 使用隔離 v1 producer 再 normalize，不做 v2→v1 downgrade；v2-only fact
  以 `legacy_rollback_not_representable` fail closed，沒有靜默資料遺失。
- [x] `MapBuildResult` 只有一個 normalized v2 canonical field；active consumer 不直接接
  `RagSystemMap` 或 v1 validator。
- [x] v2 是 generic AI system map，不預設 RAG/Agent 類別。
- [x] v1 artifacts 仍可透過唯一 loader/adapter path 讀取。
- [x] 所有 persisted `CONFIRMED` legacy extension mappings 已依轉換矩陣遷移；缺資料者會
  `requires_manual_review` 並阻擋 cutover，不會被猜測補值。
- [x] Active backend code/API不建立或接受`extensions` / `new_extension_component`；active
  `ManualMappingType` 已不含`NEW_EXTENSION`。
- [ ] Frontend仍有5筆active legacy hits；須完成handoff後才能宣稱API/UI全鏈路退場。
- [x] Phase2 P0 **10 public sibling artifacts**（7 JSON + 3 render）來自同一 validated v2
  build result；staging directory rename 前任何 supported reader 都不可見 partial set，complete
  manifest 後 history 可讀完整 build，pointer CAS 後 latest 才切換。若 dynamic `00` 尚未啟用，
  cutover report 必須明列 execution subset 為 `not_enabled`，但不得把 5-file subset 當成新的
  product contract。
- [x] 10 個 artifact write boundary、manifest/pointer 前後、concurrent reader 與 restart
  fault-injection tests 證明 latest 永不指向 partial/invalid set。
- [x] 五態 status、evidence traceability 與禁止 numeric confidence 的規則未破壞。
- [x] v1 rollback、v1/v2 reload、invalid env、切回 v2與 deterministic output 都已實測，cutover
  report 已保存。
- [ ] Plan 14 需等frontend handoff完成後，才可把本計畫視為full-stack complete。

## 風險與注意事項

- Plan 13 完成後，v1 是 compatibility input 與短期 operator rollback output，不是 normal
  product model。若某 active consumer 仍需 direct v1 access，就是 cutover blocker；不得用
  degraded exception 讓新舊 consumer 長期各自選一套 canonical truth。
- persisted mapping migration 是資料 contract，不只是 enum rename。先刪 enum、先換 loader 或
  自動猜測 legacy edge，都可能使 restart 失敗或製造無 evidence 的 canonical truth。
- Artifact-set publish 與 active promotion 是兩個不同 boundary：directory rename 保證檔案集合
  完整，complete manifest 開放 history lookup，latest pointer CAS 才切 active build。任何 reader
  直接掃 raw output directory，都會繞過 supported visibility 保證。
- operator v1 rollback writer 與 Legacy DTO/command 只在 Plan 13/14 暫存；Plan 15 必須依 report
  清除 env、writer、migration DTO/quarantine，不能把 rollback 變成永久第二輸出模式。Backend
  enum/API已停寫；frontend handoff必須在宣告full-stack complete前完成，不得誤列為Plan 15工作。

## Out Of Scope

- 不重新設計 00A 的 v2 model/schema。
- 不刪除 v1 read compatibility。
- 不在 Plan 13 物理刪除 operator rollback writer；這是 Plan 15 的責任。
- 不做完整 Langflow/Dify/Flowise importer 或 round-trip export。
- 不做 runtime component trace、runtime observability、RAG eval 或自動修 code。

## 外部研究依據（2026-07-15）

- [Icechunk specification](https://icechunk.io/en/v2.0.0-alpha.6/spec/) 的 open-source
  transaction model 先寫 immutable chunks/manifests/snapshot，最後原子更新 branch ref 才算
  commit。本計畫只借用「payload first、pointer last」的 visibility boundary，不照搬其 object
  store 或 optimistic concurrency 架構。
- [earth-mover/icechunk](https://github.com/earth-mover/icechunk) 用來確認上述 specification
  對應目前 active open-source repository；KAI-Mind 仍以 local same-directory replace、manifest
  digest 與 project lock 實作自己的較小範圍 contract。

## P0 Execution Mapping 補充（2026-07-03）

Active v2 cutover 必須包含 P0 execution artifacts 的 compatibility check：

- `13` 切換 active output 後，new builds 必須可產生 v2-backed `call_graph.json`、
  `dataflow_hints.json`、`execution_paths.json`、`evidence_table.json` 與 `execution_map.mmd`
  或明確標示 feature gate 尚未啟用。
- v1 artifacts 透過 00A adapter 載入時，execution artifacts 只能引用 normalized v2 ids。
- Cutover report 需列出 execution artifact status：produced、degraded 或 not enabled，並附
  limitations。
- Plan `15` 只能在本計畫與 Plan `14` 都確認 execution artifacts 不依賴 legacy v1/extension
  surface 後執行。

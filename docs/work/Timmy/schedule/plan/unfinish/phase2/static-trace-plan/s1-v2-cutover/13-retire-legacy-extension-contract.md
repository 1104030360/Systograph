# ai-system-map/v2 Active Cutover 實作計畫

Status: **blocked**（2026-07-15 live truth-check：00A normalized consumer migration 與
readiness semantic-equivalence 仍未完成；不得執行 active default flip）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 僅在 Plan 00A compatibility gate 通過後，把正常 build 的 canonical output 從
`ai-system-map/v1` 切換成 00A 已驗證的 generic `ai-system-map/v2`；保留 v1 dual-read、
migration adapter，以及到 Plan 15 才移除的 operator-only v1 rollback writer。

**Architecture:** 本計畫是 expand-and-contract 的 **cutover 階段**，不是 final removal。
所有正常 producer 與 active consumer 都改用 00A 的 `AiSystemMapV2`、
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

### 2026-07-15 verified blocker evidence

- `00A-introduce-ai-system-map-v2-compatibility-migration.md` Task 4 的 Viewer/profile/
  readiness normalized consumer migration 仍為 `[ ]`。
- 同一計畫 Task 5 的 readiness findings semantic-equivalence 仍為 `[ ]`。
- `docs/work/Timmy/schedule/report/2026-07-10-00a-review-p1-fixes-REP.md` 仍把上述兩點列為
  remaining risks。
- Live code 的 normal map build 仍回傳 `active_schema_version="ai-system-map/v1"`；
  `BuildManifestService.load()` 仍在 `CanonicalMapLoader` 前直接呼叫 v1-only
  `SystemMapValidationService`。

這些是目前 blocked 證據，不是永久事實。每次準備執行 Plan 13 前必須重新跑 census、
tests 與 runtime reload probe；只有 code、test 與 gate report 同時通過才能改 Status。

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
- Test: `tests/unit/core/test_build_manifest_service.py`
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

| Gate evidence | 2026-07-15 state | Exit condition |
| --- | --- | --- |
| Direct reader/writer census | partial；本計畫已補 baseline，但尚未有 executable allowlist | `test_v2_cutover_consumer_allowlist.py` 通過，所有 hit 有分類 |
| v1 adapter evidence/location preservation | 00A 已覆蓋 | regression tests 維持通過 |
| Viewer/profile/readiness normalized consumers | blocked；00A Task 4 仍 `[ ]` | normal consumer 不直接接 v1 model，reload probe 通過 |
| Grounded readiness semantic equivalence | blocked；00A Task 5 仍 `[ ]` | v1-adapted 與 native-v2 fixture 的 finding ids/status/evidence refs 等價 |
| Non-grounded/tool/workflow fixtures | 00A 已覆蓋 | schema + loader + consumer tests 維持通過 |
| Windows/macOS path fixtures | 00A 已覆蓋 | CI matrix 維持通過 |
| Backend tests、Ruff、Mypy | 需在當次 cutover 重跑 | 全部 exit 0，報告附 command/output summary |
| Rollback configuration | 尚未實作 | operator env、invalid value、v1 rollback、切回 v2 都實測 |

- [ ] `00A-introduce-ai-system-map-v2-compatibility-migration.md` Task 4/5 對應 checkbox 已由
  新測試證據改成 `[x]`。
- [ ] `docs/work/Timmy/schedule/report/2026-07-10-00a-review-p1-fixes-REP.md` 已追加最新
  verification，remaining risks 不再包含 normalized consumer/readiness equivalence。
- [ ] 本計畫的 consumer census 與 live `rg`/AST facts 一致。
- [ ] 保存切換前的 v1 default config、operator rollback command 與 rollback stop condition。

只有上表全數通過，才可把本檔 Status 從 `blocked` 改成 `ready`。Blocked 期間只允許執行
Task 1A 的 green characterization/census；不得先加入預期失敗的 v2 cutover assertion，也不得執行
Task 2 之後的 mutation。Status=`ready` 後才執行 Task 1B 的 red test，接著立刻以 Task 2
把它轉綠。

## Task 1：凍結 Cutover Gate 與 Executable Consumer Census

### Task 1A：Blocked 期間可完成的 green baseline

- [ ] 先建立 `tests/contracts/test_v2_cutover_consumer_allowlist.py`；由 deterministic
  `rg`/AST search 列出所有 `RagSystemMap`、`ExtensionComponent`、
  `new_extension_component`、`ai-system-map/v1` 與直接 v1 validator hit。
- [ ] allowlist 每筆必須包含 `path`、`symbol`、`classification` 與 `removal_plan`；只接受
  `migrate`、`operator_rollback`、`migration_only`、`remove` 四種分類，未知或新增 hit
  直接使測試失敗。
- [ ] characterization tests 先鎖定目前 v1 default、dual-read reload 與 direct consumer
  baseline，並保持全套 quality gates green；報告保存 command、exit code 與 census digest。

### Task 1B：Status=`ready` 後的 red cutover contract

- [ ] 先寫 failing tests，要求正常 build 的 `schema_version` 為 `ai-system-map/v2`，且
  `MapBuildResult` 只暴露一個 normalized canonical map，不再同時保留 v1
  `ai_system_map` 與 v2 `normalized_ai_system_map` 兩份 truth。
- [ ] 測試 v2 output 不含 `extensions`、RAG-only required slots 或
  `system_type="rag"` 限制。
- [ ] 測試 v1 input 仍由 loader + adapter 轉成 normalized v2；未知 schema version
  fail closed 並回傳 stable `unsupported_system_map_schema_version`。
- [ ] 只允許上述新 cutover assertions 因尚未 flip 而 red；先確認失敗訊息正是 v1 default／
  dual-result contract，再立即進 Task 2。不得以 `xfail`、skip 或放寬 assertion 隱藏紅燈。

## Task 2：切換 Canonical Producer Default，隔離 Rollback Writer

- [ ] `MapBuildService`、`MapBuildPipeline` 與 `SystemMapNormalizeService` 正常模式直接建立、
  驗證並回傳 00A 的 `AiSystemMapV2`；`MapBuildResult.ai_system_map` 是唯一 normalized
  canonical field，移除 `normalized_ai_system_map` 雙真相。
- [ ] 即使 operator rollback writer 輸出 v1 檔案，process 內的 `MapBuildResult` 與下游
  consumer 仍只接 normalized v2；只有 manifest 的 `active_schema_version` 與實際
  `ai_system_map.json` schema 反映 rollback output。
- [ ] 一般 CLI/API 的 `system_map_schema_version` 不再選擇 output。要求 v1 時回傳
  `legacy_output_not_selectable`；新 manifest 不再把 `requested_schema_version` 當決策欄位，
  舊 manifest 讀取時只視為 compatibility provenance。
- [ ] composition root 讀取 `KAI_MIND_CANONICAL_OUTPUT_VERSION`，只接受
  `ai-system-map/v2` 或 `ai-system-map/v1`；缺省為 v2，非法值以 stable
  `invalid_canonical_output_version` 阻止 process 啟動。
- [ ] 將現有 v1 materialization 封裝成 `LegacyV1RollbackService` operator-only boundary；normal
  producer 不建立 `RagSystemMap` 或 `ExtensionComponent`，同一次 build 不得 dual-write。
- [ ] operator rollback branch 呼叫隔離的 legacy v1 materializer，寫出 v1 後立即透過 loader/
  adapter 得到 `MapBuildResult.ai_system_map: AiSystemMapV2`；不得建立 v2→v1 downgrade adapter。
- [ ] rollback preflight 對 v2-only fact fail closed，回傳
  `legacy_rollback_not_representable`；測試證明失敗時沒有 manifest、latest promotion 或被截斷的
  v1 artifact。
- [ ] `SystemMapValidationService` 保留為 v1 validator，不擴張成第二個 dispatcher；只有
  `CanonicalMapLoader` 依 schema badge 委派 v1/v2 validator，再回傳 normalized v2。
- [ ] manifest 記錄 `active_schema_version`、`source_schema_version`、
  `operator_rollback_active` 與 migration warnings，consumer 不得從檔案 shape 猜版本。

## Task 3：遷移所有 Active Consumers

- [ ] `BuildManifestService.load()` 先呼叫 `CanonicalMapLoader`，不得在 loader 前直接呼叫
  v1-only `SystemMapValidationService`；restart 後載入既有 v1 與新 v2 build 都回傳
  normalized v2。
- [ ] Viewer、`SystemMapIndex`、graph projection、CLI/Web viewer、profile inference、
  readiness engine、static execution recoverers 與 renderers 只接 `AiSystemMapV2` 或
  `GraphViewModel`。
- [ ] detail scan input/output 改用 v2，不建立或回傳 `ExtensionComponent`；query trace 改以
  v2 `endpoints[]` 與 `SystemMapIndex.endpoint_by_id` 尋找 endpoint。
- [ ] mapping proposal、manual mapping 與 component detection 只建立 existing-slot、
  non-baseline capability candidate、needs-more-information 或 skip 類型；routes 與 frontend
  不自行判斷 v1/v2 shape。
- [ ] v1 compatibility metadata 只作 provenance、migration warning/debug，不得形成產品分類、
  UI filter 或 readiness verdict；`primary_map_type` 只能由 report/projection 推導。
- [ ] `rag-core-v1` 只保留為 legacy input grounding 或 operator rollback boundary；v2 不輸出
  compatibility-derived product verdict。citation/source mapping 留在
  `readiness_report.json.source_traceability`，不成為 canonical RAG-only hard requirement。
- [ ] 若 `MarkdownSummaryService` 無 active caller，移除或降為 migration-only test helper；
  不得保留未測試、可被正常路徑誤用的 v1 renderer。

## Task 4：遷移 Persisted Legacy Extension Mappings

目前 persisted mapping JSON 會直接 parse 成 `ManualMapping`。若先刪除
`ManualMappingType.NEW_EXTENSION`，包含 `mapping_type="new_extension_component"` 的既有專案
會在 restart/load 階段直接失敗；因此 migration 必須在 enum 與 active loader 收斂前完成。

- [ ] 建立 `LegacyManualMappingDTO` 與
  `LegacyManualMappingMigrationService`，先以隔離 DTO 讀 raw JSON，再轉成 active
  `ManualMapping`；normal repository 不得長期接受 legacy shape。
- [ ] 建立 `migrate-legacy-mappings` CLI。預設只做 `--dry-run` 且零寫入；必須明確傳入
  `--apply` 才能更新 KAI-Mind state directory，禁止修改被掃描的 target project。
- [ ] 轉換矩陣固定如下，實作者不得自行推測：

| Legacy row | Active result | 必須保留／禁止 |
| --- | --- | --- |
| `CONFIRMED` 且 `extension_id/name/kind` 完整 | `NON_BASELINE_CAPABILITY_CANDIDATE` + `CONFIRMED` | 對應到 `capability_candidate_id/name/kind`；保留 `mapping_id`、project/source、evidence、reason、proposal、decision source、created time；不得升格為 detected reference capability |
| `REJECTED`、`SKIP_FOR_NOW` 或 `NOT_APPLICABLE` 且欄位完整 | 相同 active mapping type + 原 decision | 保留稽核歷史；非 `CONFIRMED` 永不 materialize capability candidate |
| 任一 legacy row 缺少必要 extension 欄位 | `requires_manual_review`，不建立猜測值 | 原 row 只留 migration quarantine；若 decision 是 `CONFIRMED`，阻擋 v2 cutover |
| `extension_edges` 非空 | 不轉成 canonical edge | 將原 payload digest、opaque `quarantine_ref` 與 warning 寫入 audit metadata；不得保存/回傳 absolute path，關係需由後續 evidence-backed mapping 重新確認 |

前三列先決定 row 的 active mapping/decision；第四列是可與前三列同時套用的 modifier。也就是
完整且 confirmed 的 row 仍可轉 capability candidate，但其中的 `extension_edges` 一律隔離，絕不
偷偷轉成 v2 canonical edge。

- [ ] migration 使用固定 `migration_version`，且必須 idempotent：成功轉換時只更新一次
  `updated_at` 與 `mapping_digest`；重跑相同輸入回報 `already_migrated`，不得重複產生 row。
- [ ] `--apply` 先在 KAI-Mind state directory 建立原始 mapping backup 與 index。Backup 可能含
  legacy free-text，因此必須使用平台可提供的 owner-only access、不得寫入 target repo，也不得把
  payload 複製到 log/report；report 只記 opaque ref 與 digest。
- [ ] 在 project-level lock 內以 same-directory temp + replace 原子更新每個 mapping file；單檔
  失敗不得留下半份 JSON，並回傳 stable `legacy_mapping_migration_failed`。若同一 project
  多檔 migration 中途失敗，標成 `partial_requires_retry` 並阻擋 cutover；idempotent rerun 從
  digest 判斷已完成 rows，不重複轉換。
- [ ] migration report 至少包含 `scanned`、`converted`、`already_migrated`、
  `requires_manual_review`、`failed`、input/output digest 與 masked error；不得印出完整 evidence
  snippet、secret 或原始 payload。
- [ ] normal API/UI 立即拒絕新 `new_extension_component` request，回傳
  `legacy_mapping_type_read_only`。所有 `CONFIRMED` legacy rows 都完成轉換後才可 flip v2；
  其他 unresolved quarantined rows 可以留作 migration evidence，但會繼續阻擋 Plan 15 cleanup。
- [ ] migration apply 完成且 reload gate 通過後，從 active `ManualMappingType` 移除
  `NEW_EXTENSION`；相同字串只留在 migration-only `LegacyManualMappingDTO` enum。Plan 15 再刪
  DTO/command/quarantine，而不是把 active enum/API/UI removal 延後。
- [ ] 先測 dry-run 零寫入，再測 apply/restart、idempotence、crash recovery、backup、digest、
  concurrent project lock、缺欄位與 secret redaction。

## Task 5：停止正常 Extension Write Surface

- [ ] 新 scan、manual mapping、mapping proposal、component detection 與 frontend schema 不再建立
  top-level `extensions` 或接受 `NEW_EXTENSION` / `new_extension_component`。
- [ ] 未確認 component 保留為 generic unmapped/candidate fact；使用者確認 non-baseline 後只寫入
  capability candidate，不建立 extension 類別或 legacy edge。
- [ ] v1 schema/fixture、Legacy DTO、adapter 與 operator rollback serializer 明確標示
  legacy/read-only；normal build path 不得 import。
- [ ] Task 1 allowlist 是 executable gate；下列 search 只能命中
  `operator_rollback`、`migration_only` 或測試／文件明列的 legacy evidence：

```bash
rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1" \
  src tests frontend docs
```

Expected：active producer、consumer、request schema 與 frontend hit 為零；每個保留 hit 都能在
allowlist 找到相同 path/symbol/classification。

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

- [ ] 建立 `BuildCommitService`，讓 initial scan、apply-confirmations 與 detail-scan build 共用
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

- [ ] Final build directory 必須是新 path；若已存在就以 `build_output_conflict` fail closed，禁止
  overwrite。Staging/final 必須位於同一 filesystem parent；無法保證 atomic rename 時以
  `atomic_artifact_publish_unavailable` 中止，不退回逐檔公開。
- [ ] `MapBuildQueryService.get/list` 只從 repository 的 complete manifest 找 build，不能掃描 raw
  output directory；`latest()` 必須先讀 CAS pointer，再載入該 manifest。Low-level path reader 不在
  supported-reader guarantee 內。

- [ ] 同一 validated build result 產生 Phase2 P0 sibling set（對齊
  `docs/MODEL-CONTRACT.md`；**7 JSON + 3 render，共 10 檔**；`GraphViewModel` 是 ephemeral
  API projection，不是 required on-disk sibling）：
  - Canonical + assessment：`ai_system_map.json`、`profile_signals.json`、
    `readiness_report.json`。
  - Static execution：`call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、
    `evidence_table.json`。
  - Render outputs：`ai_system_map.md`、`system_map.mmd`、`execution_map.mmd`。
- [ ] 10 個 sibling 與 manifest 共用同一 `scan_id`、`build_id`、`environment_id` 與
  `artifact_set_version`；manifest 保存每檔 digest/size/schema status。finding、component、edge、
  signal 與 execution step 只能引用存在的 evidence id。
- [ ] producer 不重跑 scanner、UA 或 LLM 來補 canonical facts；所有 sibling 都由同一 immutable
  build result/projection 產生。
- [ ] initial scan、apply-confirmations 與 detail-scan 都把開始時讀到的 latest id/revision 傳入
  `BuildCommitService`；若另一 build 先 promote，stale CAS 回傳 `stale_latest_revision`，新完整
  artifact set 可保留成 non-latest history 或依明確 cleanup policy 清除，但不得覆蓋較新 latest。
- [ ] failure/recovery contract 固定如下：

| Failure point | Reader-visible result | Recovery |
| --- | --- | --- |
| staging 內任一 artifact write 前／中 | final path/manifest 不存在；history/latest 都看不到新 build | 清除 temp/staging；restart cleanup 依 build id/digest 判斷 orphan |
| staging 驗證失敗或 directory rename 前 | 同上 | 修正或丟棄 staging；不得 persist manifest |
| final directory rename 後、manifest 保存前 | raw final path 存在，但 supported history/latest 都看不到 | restart 驗證後補 manifest，或安全清除 orphan final directory |
| complete manifest 已保存、pointer 尚未 promote | build-id/history 可讀完整新 build；latest 仍是舊 build | 以原 expected revision 重試 promote；CAS stale 則保留 non-latest 或清除 |
| pointer CAS 已 promote | history/latest 都可讀完整新 build | API/session 寫入失敗不得破壞 committed build；回 stable warning 並可重建 projection |

- [ ] 新 build 在 feature enabled 時缺任何 required sibling、scope id 不一致、reference dangling
  或 digest mismatch 都 fail closed，且不得 promote。舊 build 缺 optional sidecar 時可載入 base v2
  graph 並回傳 stable degraded warning；不得把舊 5-file subset 改寫成新 product contract。
- [ ] fault-injection 測試覆蓋 10 個 artifact 的每個 write boundary、directory rename 前後、
  manifest 前後、pointer CAS 前後、concurrent build/reader 與 process restart；macOS/Windows 都
  驗證 same-parent staging rename、same-directory file replace 與 latest pointer 語意。直接指定任意
  檔案的低階 `validate-map` 不在 atomic visibility 保證內。

## Task 7：Rollback、Regression 與 Cutover Report

- [ ] 在 staging fixture 流程執行 active v2 canary，驗證 CLI/API/viewer/detail/trace/reload 與
  10-artifact lifecycle。
- [ ] 以 operator env 執行一次 v1 rollback build，確認同一 binary 仍能讀取既有 v1/v2、沒有
  資料破壞、manifest/warning 可稽核；再移除 env 切回 v2並確認 output deterministic。
- [ ] 測試 invalid env fail startup，以及 public CLI/API v1 selection 回傳
  `legacy_output_not_selectable`。
- [ ] 執行 scoped contract/unit/integration/web/frontend gates：

```bash
.venv/bin/pytest tests/contracts tests/unit/core tests/integration tests/web -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
cd frontend && npm run build && npm run lint
```

- [ ] 更新 compatibility report 為 cutover report，至少記錄 gate/census digest、active version、
  persisted mapping migration counts、legacy read coverage、artifact commit/fault-injection、rollback
  結果與 remaining warnings。只有報告可回讀且所有 exit condition 通過，才把 Status 改為
  `complete`。

## 驗收標準

- [ ] Status 只有在 00A Task 4/5、executable consumer allowlist、reload probe 與完整 quality
  gates 通過後才可由 `blocked` 改成 `ready`；完成 Task 7 report 後才可改成 `complete`。
- [ ] 新 build 預設輸出 `ai-system-map/v2`；一般 CLI/API 無法要求 v1，operator rollback
  預設關閉、可稽核且不 dual-write。
- [ ] operator rollback 使用隔離 v1 producer 再 normalize，不做 v2→v1 downgrade；v2-only fact
  以 `legacy_rollback_not_representable` fail closed，沒有靜默資料遺失。
- [ ] `MapBuildResult` 只有一個 normalized v2 canonical field；active consumer 不直接接
  `RagSystemMap` 或 v1 validator。
- [ ] v2 是 generic AI system map，不預設 RAG/Agent 類別。
- [ ] v1 artifacts 仍可透過唯一 loader/adapter path 讀取。
- [ ] 所有 persisted `CONFIRMED` legacy extension mappings 已依轉換矩陣遷移；缺資料者會
  `requires_manual_review` 並阻擋 cutover，不會被猜測補值。
- [ ] active code/API/UI 不建立或接受 `extensions` / `new_extension_component`；legacy hits
  全部在 executable allowlist 的 operator rollback、migration-only、fixture/test boundary；active
  `ManualMappingType` 已不含 `NEW_EXTENSION`。
- [ ] Phase2 P0 **10 public sibling artifacts**（7 JSON + 3 render）來自同一 validated v2
  build result；staging directory rename 前任何 supported reader 都不可見 partial set，complete
  manifest 後 history 可讀完整 build，pointer CAS 後 latest 才切換。若 dynamic `00` 尚未啟用，
  cutover report 必須明列 execution subset 為 `not_enabled`，但不得把 5-file subset 當成新的
  product contract。
- [ ] 10 個 artifact write boundary、manifest/pointer 前後、concurrent reader 與 restart
  fault-injection tests 證明 latest 永不指向 partial/invalid set。
- [ ] 五態 status、evidence traceability 與禁止 numeric confidence 的規則未破壞。
- [ ] v1 rollback、v1/v2 reload、invalid env、切回 v2與 deterministic output 都已實測，cutover
  report 已保存。
- [ ] Plan 14 依賴本計畫完成，不再接受 v1-only output 作 final success。

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
  清除 env、writer、migration DTO/quarantine，不能把 rollback 變成永久第二輸出模式。Active
  enum/API/UI 的停寫不得拖到 Plan 15。

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

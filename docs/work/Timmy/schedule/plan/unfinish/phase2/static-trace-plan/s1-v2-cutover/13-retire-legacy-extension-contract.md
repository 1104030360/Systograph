# ai-system-map/v2 Active Cutover 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 僅在 Plan 00A compatibility gate 通過後，把預設 canonical output 從
`ai-system-map/v1` 切換成 00A 已驗證的 generic `ai-system-map/v2`，同時保留 v1
dual-read、migration adapter 與 rollback 能力。

**Architecture:** 本計畫是 expand-and-contract 的 contract 階段，不再定義第二份
v2 model/schema。所有 active producer 與 consumer 都改用 00A 的 `AiSystemMapV2`、
`CanonicalMapLoader` 與 normalized view；v1 只保留為 legacy input contract。

**Tech Stack:** Python 3.11、Pydantic v2、JSON Schema、pytest、現有 CLI/FastAPI、
frontend TypeScript contracts。

---

## 執行摘要

### 目標

完成 generic canonical map 的預設輸出切換，並證明既有 v1 artifacts 仍能透過
唯一 migration path 讀取。切換後不得再由 active code 建立 legacy-shaped
`RagSystemMap` output 或 top-level `extensions`。

### 背景

Plan 00A 已負責新增 generic v2 model/schema、v1-to-v2 adapter、dual-read loader 與
compatibility report。若 13 再自行重建 v2，會形成兩套 schema 與不一致 migration
semantics。本計畫只執行 gate review、active default cutover、consumer migration 與
legacy write-path retirement。

### 目前 code 狀態

本計畫開始前必須確認：

- v1 仍是預設 output，但 v1/v2 都能由 `CanonicalMapLoader` 載入。
- v1 fixtures 經 adapter 後，components、edges、evidence 與 readiness findings
  已通過 semantic-equivalence tests。
- `AiSystemMapV2` 可表示 grounded RAG、non-grounded LLM app、tool agent 與 workflow
  graph，不要求填入 RAG slots。
- compatibility report 沒有 unresolved blocker；degraded consumers 有明確 owner。

任一條不成立，都必須回到 00A 修正，不得在 13 直接繞過。

### 相關檔案

- Reuse: `src/kai_mind/core/models/ai_system_map_v2.py`
- Reuse: `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`
- Reuse: `src/kai_mind/core/services/canonical_map_loader.py`
- Reuse: `schemas/ai-system-map.v2.schema.json`
- Modify: `src/kai_mind/core/models/map_build.py`
- Modify: `src/kai_mind/core/services/system_map_normalize_service.py`
- Modify: `src/kai_mind/core/services/system_map_validation_service.py`
- Modify: `src/kai_mind/core/services/viewer_session_service.py`
- Modify: `src/kai_mind/core/services/system_map_index.py`
- Modify: `src/kai_mind/core/services/detail_scan_service.py`
- Modify: `src/kai_mind/core/services/mapping_proposal_service.py`
- Modify: `src/kai_mind/core/providers/output_artifact_provider.py`
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `frontend/src/types.ts`
- Test: `tests/contracts/test_ai_system_map_v2_schema.py`
- Test: `tests/integration/test_map_build_service.py`
- Test: `tests/unit/core/test_viewer_session_service.py`
- Test: `tests/web/test_project_scan_routes.py`

### 實作步驟

先審核 00A gate 並建立 cutover characterization tests；再切換 producer default、遷移
active consumers、停用 v1 write/extension paths；最後驗證 rollback 與所有 artifacts。

### 驗收標準

新 scan 預設產生 `ai-system-map/v2`；所有 active consumers 經
`CanonicalMapLoader` 取得 normalized v2；v1 artifact 仍可讀但不再新寫；完整 sibling
artifacts 都引用同一 validated v2 build result；Plan 14 可直接執行 final validation，
通過後接續 active Plan 15 complete retirement。

### 風險與注意事項

- 不得刪除 v1 schema、v1 fixtures、v1 reader 或 adapter。
- 不得把 legacy extension 自動升格為 detected capability。
- 不得用 temporary dual-write 掩蓋 consumer drift；如需 rollback，切回 v1 default，
  不是同時寫兩份互相競爭的 canonical output。
- `profile_signals.json` 與 `readiness_report.json` 是 derived artifacts，不可反向改寫
  canonical facts。
- 不新增數字 `confidence`。Capability/profile status 統一為
  `detected / partial / undetermined / not_detected / conflicted`；legacy
  `contradicted` input 必須經 adapter 對應為 `conflicted`，不得形成第六種 active status。

## 2026-07-07 UA 整合對齊

Plan 13 cutover 不採用 UA Phase 3～7，也不改 canonical output 名稱。Active output 仍是
KAI-Mind 的 `ai_system_map.json`、`profile_signals.json` 與 `GraphViewModel`；UA
`ua-analysis-result` 只在 scan snapshot 內作 internal sidecar。Plan 13 的 gate 應確認
v2 active output 可消費 UA structural facts，但不得把 UA graph vocabulary 變成新的
canonical schema。

## Preconditions：審核 00A Compatibility Gate

- [ ] compatibility report 已列出所有 v1 direct readers/writers 與 migration 狀態。
- [ ] v1-to-v2 adapter 無 evidence id/location loss。
- [ ] grounded fixture 的 v1/v2 readiness 結論等價。
- [ ] non-grounded LLM app、tool agent、workflow graph fixtures 通過 v2 schema。
- [ ] Windows/macOS path fixtures 通過。
- [ ] backend contract/unit/web tests、Ruff、Mypy 通過。
- [ ] 保存切換前的 v1 default configuration 與 rollback command。

Gate 未全部通過時，本計畫狀態必須維持 blocked，不可執行 Task 1。

## Task 1：鎖定 Active Cutover 行為

- [ ] 先寫 failing tests，要求新 build 的 `schema_version` 為
  `ai-system-map/v2`。
- [ ] 測試 v2 output 不含 `extensions`、RAG-only required slots 或
  `system_type="rag"` 限制。
- [ ] 測試 v1 input 仍由 loader + adapter 轉成 normalized v2。
- [ ] 測試未知 schema version fail closed，並回傳穩定 error code。
- [ ] 測試 CLI/API 明確回傳 active schema version 與 migration warnings。

## Task 2：切換 Canonical Producer Default

- [ ] `MapBuildService` 與 `SystemMapNormalizeService` 預設建立 00A 的
  `AiSystemMapV2`。
- [ ] 移除 active producer 對 `RagSystemMap` 與 `ExtensionComponent` 的建立路徑。
- [ ] 保留 explicit rollback flag/config，可暫時回到 v1 output；預設不得 dual-write。
- [ ] `SystemMapValidationService` 依實際 schema version 驗證，schema branching 只委派
  `CanonicalMapLoader`。
- [ ] artifact manifest 記錄 canonical schema version，避免 consumer 猜測。

## Task 3：遷移 Active Consumers

- [ ] Viewer、index、detail scan、mapping proposal、profile inference、readiness engine
  與 renderers 只接 normalized v2 model。
- [ ] routes 與 frontend 不自行判斷 v1/v2 shape。
- [ ] v1 compatibility metadata 只能用於 migration warning/debug，不得出現在新產品
  分類或 UI filter。
- [ ] `rag-core-v1` 僅保留為 legacy v1 compatibility template；v2 不輸出
  compatibility-derived product verdict。
- [ ] citation / source mapping 已移到 `readiness_report.json` 的
  `source_traceability` finding，不作為 core readiness hard requirement。
- [ ] `primary_map_type` 僅由 report/projection 推導，不寫回 canonical truth。

## Task 4：停用 Legacy Write 與 Extension Contract

- [ ] 新 scan、manual mapping、component detection 不再建立 top-level
  `extensions`。
- [ ] 未確認 component 保留為 generic unmapped/candidate fact；使用者確認為
  non-baseline 後寫入 capability candidate，不建立 extension 類別。
- [ ] 舊 `NEW_EXTENSION` / `new_extension_component` 只允許存在於 v1 reader、fixture
  與 migration test。
- [ ] v1 schema 與 fixture 標示 legacy/read-only，禁止從正常 build path 寫出。
- [ ] 以 allowlist 檢查 legacy identifiers 僅存在於 migration boundary。

```bash
rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1" \
  src tests frontend docs
```

Expected：active hits 已移除；其餘 hits 都位於明確的 legacy reader、adapter、fixture、
test 或 migration 文件。

## Task 5：統一 Artifact Lifecycle

- [ ] 同一 validated v2 build result 以 **一次 atomic publish** 產生 Phase2 P0 sibling set
  （對齊 `docs/MODEL-CONTRACT.md` Artifact Lifecycle；**7 JSON + 3 render，共 10 檔**；另
  `GraphViewModel` 為 ephemeral API projection，**非** required on-disk sibling）：
  - **Canonical + assessment（Plan 03 lifecycle owner）：**
    - `ai_system_map.json`
    - `profile_signals.json`
    - `readiness_report.json`
  - **Static execution（dynamic `00` writer；Plan 03 協調 same-build publish）：**
    - `call_graph.json`
    - `dataflow_hints.json`
    - `execution_paths.json`
    - `evidence_table.json`
  - **Render outputs：**
    - `ai_system_map.md`
    - `system_map.mmd`
    - `execution_map.mmd`
- [ ] 上述 **10** 個 sibling 共用同一 `scan_id`、`build_id`、`environment_id`；不得混用不同
  scope 的 evidence refs。`GraphViewModel` 僅為 ephemeral API projection，不是 required
  on-disk sibling JSON。
- [ ] 每個 finding、component、edge、profile signal、static call edge、execution step 都只
  引用存在的 evidence id。
- [ ] profile/readiness/renderers/static execution recoverers 不重跑 scanner、UA 或 LLM 來
  建立 canonical facts。
- [ ] missing/invalid optional sidecar 或 execution artifact 時，viewer 仍載入 base v2
  graph 並回傳 stable degraded warning；不得 blocking canonical map load。
- [ ] artifact write failure 不留下內容互相矛盾的 partial set。

## Task 6：Rollback 與 Regression Gate

- [ ] 在 staging fixture 流程執行 active v2 build，驗證 CLI/API/viewer artifacts。
- [ ] 執行一次 explicit rollback，確認可回到 v1 default 且沒有資料破壞。
- [ ] 再切回 v2，確認 output deterministic。
- [ ] 執行 scoped contract/unit/integration/web/frontend gates：

```bash
.venv/bin/pytest tests/contracts tests/unit/core tests/integration tests/web -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
cd frontend && npm run build && npm run lint
```

- [ ] 更新 compatibility report 為 cutover report，記錄 active version、legacy read
  coverage、rollback 結果與 remaining warnings。

## 驗收標準

- [ ] 00A compatibility gate 是切換的必要前置，且有可回讀的報告。
- [ ] 新 build 預設輸出 `ai-system-map/v2`，不再輸出 v1 canonical artifact。
- [ ] v2 是 generic AI system map，不預設 RAG/Agent 類別。
- [ ] v1 artifacts 仍可透過唯一 loader/adapter path 讀取。
- [ ] active code 不建立 `extensions` 或 `new_extension_component`。
- [ ] Phase2 P0 **10 public sibling artifacts**（7 JSON + 3 render）來自同一 validated v2
  build result 與同一 atomic publish；若 dynamic `00` 尚未啟用，cutover report 必須明列
  execution subset 為 `not_enabled`，但不得把 5-file subset 當成新的 product contract。
- [ ] 五態 status、evidence traceability 與禁止 numeric confidence 的規則未破壞。
- [ ] rollback 已實測且 cutover report 已保存。
- [ ] Plan 14 依賴本計畫完成，不再接受 v1-only output 作 final success。

## 風險與注意事項

Plan 13 完成後，v1 是 compatibility input，不是 active product model。若某 consumer
尚需 v1 direct access，應視為 cutover blocker 或列入明確 degraded exception；不得
讓新舊 consumer 長期各自選一套 canonical truth。

## Out Of Scope

- 不重新設計 00A 的 v2 model/schema。
- 不刪除 v1 read compatibility。
- 不做完整 Langflow/Dify/Flowise importer 或 round-trip export。
- 不做 runtime component trace、runtime observability、RAG eval 或自動修 code。

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

# ai-system-map/v2 相容遷移實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 在不立即切換 active output 的前提下，引入可描述一般 AI system
repo 的 `ai-system-map/v2`、v1 reader 與 v1-to-v2 adapter，先證明相容性，再由
Plan 13 執行完整切換。

**Architecture:** 採 expand-and-contract。Expand 階段保留
`ai-system-map/v1` 讀寫行為，新增 generic v2 model、schema、normalization
boundary 與 migration adapter；所有下游服務先消費 normalized v2 view，但預設
output 仍可維持 v1。Contract 階段由 Plan 13 在 compatibility gate 通過後切換
active output，Plan 14 驗證真實專案。

**Tech Stack:** Python 3.11、Pydantic v2、JSON Schema、pytest、現有 scanner
providers、CLI/FastAPI contract tests。

---

## 2026-07-06 Legacy Template Boundary

本計畫是 Phase2 static path 的 migration 起點。`rag-core-v1` 只視為現行 legacy v1
surface，供舊 artifacts deterministic 遷移到 generic v2 facts。

Phase2 active product surface 由 generic v2 map、profiles、readiness findings 與
evidence artifacts 組成。v1-to-v2 adapter 的責任是保留 facts，不是產生
compatibility-derived verdict。

因此本計畫的 v1-to-v2 adapter 必須使用以下資料流：

```text
rag-core-v1 legacy slots / flows / evidence
  -> generic ai-system-map/v2 components / edges / evidence
  -> profile_signals.json
  -> readiness_report.json findings
```

產品主流程不再問「這個 repo 是不是某種 RAG」，也不再用 v1 slot completeness
產生獨立 report summary。

## 2026-07-07 UA 整合對齊

本計畫的 v1/v2 compatibility boundary 不新增 public UA artifact，也不改動
`ai_system_map.json` canonical contract。UA 整合只影響 scan snapshot：Plan 03A 的
`ScanSnapshot` 需保存 `ua-analysis-result` internal sidecar，以維持同一 `scan_id` snapshot
完整性；Phase2 Apply 只使用 `ScanSnapshot.scan_result`，不消費 semantic sidecar。它不是
v1/v2 dual-read loader 的輸入，也不列入 public sibling artifact set。

## 2026-07-06 Confirmed Assessment and Taxonomy Contract

本節取代本文任何三態、`partial`/`contradicted` 非一級狀態、或缺少 assessment scope
的舊規劃。完整決策見
[`../capability-map-assessment-decision-summary.md`](../capability-map-assessment-decision-summary.md)。

- v2 支援固定 10-plane / 52-node reference map 與 per-repo overlay。Reference node 是穩定能力
  座標；repo component 是目前 build/snapshot 以 evidence 支撐的實際元件，兩者不得混為
  同一種 canonical fact。
- Plane ids 固定為 `input_intent`、`control`、`ingestion_indexing`、`retrieval`、
  `extension_subsystems`、`evidence`、`generation`、`memory_state`、
  `governance_observability`、`deployment_topology`。Governance / observability 是
  canonical plane；cross-plane governance lens 只作 backend-derived view。
- 舊 8-plane / 35-node 是 superseded planning/prototype draft，不是 production catalog。
  00A 不新增 reference-catalog dual-read；若保留舊 fixture 作 regression 對照，使用 explicit
  plane/node id mapping 轉換，不得以 label/alias 猜測。00A 的 dual-read 仍只負責
  `ai-system-map/v1` 與 `ai-system-map/v2` schema。
- Capability/reference-node assessment 使用五態：`detected`、`partial`、
  `undetermined`、`not_detected`、`conflicted`。
- `activation` 使用 `enabled`、`disabled`、`conditional`、`unknown`、
  `conflicted`、`not_applicable`，且不由 assessment status 自動推導。只有 catalog
  metadata 宣告 node 本質上沒有 activation 語意時才可 `not_applicable`。
- Evidence 必須標示 `direct`、`indirect` 或 `explicit_negative`；`detected` 必須有
  direct evidence，indirect-only 一律 `partial`，多個 convergent indirect signals 也不能
  升級。Explicit negative 只接受明確 disabled/bypassed/forbidden 等；absence 不是。
- 每個 assessment 綁定 `build_id`、`scan_id` 與 environment scope；`scan_id` 同時識別該次
  immutable `ScanSnapshot`。Conflict 是
  field-specific，必須指出受影響欄位及 evidence refs。
- `not_detected` 只有在 capability-specific coverage gate 通過後才合法；coverage 不足
  必須為 `undetermined`。
- Canonical/profile contract 仍禁止任意數字 `confidence`。Mapping Completeness 是 derived
  projection/readiness metric，不是 canonical confidence；denominator 是全部固定
  reference nodes，activation/not_applicable 不排除 node。

## 執行摘要

### 目標

把輸入邊界從「RAG repo」擴成「AI system repo」，但不以一次性 breaking
rewrite 取代現有可讀的 v1 artifacts。

### 背景

現行 `SystemType = Literal["rag"]`、`RagSystemMap`、`rag-core-v1` 與 required
`extensions` 無法如實描述沒有 grounding 的 LLM app、tool-using agent 或
workflow-orchestrated system。直接就地修改 v1 會破壞既有 JSON、viewer、mapping
與 tests，因此必須先建立平行 v2 contract。

### 目前 code 狀態

- `src/kai_mind/core/models/system_map.py` 只接受 `system_type="rag"`。
- `schemas/ai-system-map.v1.schema.json` 是目前 active schema。
- `SystemMapNormalizeService` 直接產生 `RagSystemMap`。
- `ViewerSessionService`、detail scan、mapping 與 trace 都直接讀 v1 shape。
- `SystemMapValidationService` 明確拒絕任何 `confidence` 欄位。

### 相關檔案

- Create: `src/kai_mind/core/models/ai_system_map_v2.py`
- Create: `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`
- Create: `src/kai_mind/core/services/canonical_map_loader.py`
- Create: `src/kai_mind/core/providers/workflow_json_provider.py`
- Create: `schemas/ai-system-map.v2.schema.json`
- Create: `tests/contracts/test_ai_system_map_v2_schema.py`
- Create: `tests/unit/core/test_system_map_v1_to_v2_adapter.py`
- Modify: `src/kai_mind/core/services/system_map_validation_service.py`
- Modify: `src/kai_mind/core/services/system_map_normalize_service.py`
- Modify: `src/kai_mind/core/models/map_build.py`

### 實作步驟

先鎖定 v1 行為，再新增 generic v2 model/schema；接著實作 deterministic v1-to-v2
adapter、dual-read loader 與 opt-in v2 build；最後執行 semantic-equivalence、schema
與 consumer compatibility gate。未通過 gate 前不得切換預設 output。

### 驗收標準

同一份 v1 fixture 經 adapter 後，其 components、edges、evidence、endpoints、risks
與 legacy v1 evidence 語意不遺失；v1 artifacts 仍可載入；v2 可表示無 retrieval
的 LLM app、tool agent 與 workflow graph；預設 output 尚未切換。

### 風險與注意事項

不得把 v2 當成重新命名 v1。Generic component inventory 與
profile/readiness findings 是不同層；不得在 canonical facts 中加入數字 `confidence`、
raw prompt、完整 source extract 或絕對路徑。

## v2 Contract Boundary

`ai-system-map/v2` 的 input abstraction 是：

```text
AI system repo / workflow artifacts
  -> deterministic ScanFact + Evidence
  -> generic components + edges
  -> canonical AI system map
  -> capability overlays
  -> readiness findings and renderers
```

v2 至少需要：

- `system_type="ai_system"`；不預設 RAG 或 Agent。
- generic `components[]`，含 stable id、canonical type、layer、status、evidence ids。
- generic `edges[]`，含 source、target、relationship、status、evidence ids。
- evidence 使用 project-relative location、line/config-key/JSON pointer；不含完整 raw
  source 或任意數字 confidence。
- citation / source mapping 不屬於 hard baseline；它轉成 readiness report 的
  `source_traceability` finding。
- agent control、tools、memory、workflow、eval/observability 是 components/capabilities，
  不是 v1 template 必備 slots；它們不能單獨讓 repo 被判為特定 RAG 類型。
- `primary_map_type` 是 report/projection 的 derived summary，不是 canonical truth。

Assessment status 固定為：

```text
detected | partial | undetermined | not_detected | conflicted
```

每個 assessment 另有獨立 `activation`：

```text
enabled | disabled | conditional | unknown | conflicted | not_applicable
```

`partial` 與 `conflicted` 是一級 status。Coverage、implementation depth、missing signals、
direct/indirect/explicit-negative evidence 與 field-specific conflict refs 用來解釋狀態，
不得把它們壓回舊三態。`not_detected` 必須通過 coverage gate。

## Task 1：鎖定 v1 Characterization

- [ ] 為 v1 minimal/rich/legacy-extension fixtures 補 schema、runtime validation、
  viewer load、Markdown 與 mapping characterization tests。
- [ ] 固定 components、flows、evidence、risk、endpoint 與 extension compatibility
  的 semantic snapshot；不要只做整份 JSON 字串 snapshot。
- [ ] 執行：

```bash
.venv/bin/pytest tests/contracts/test_ai_system_map_schema.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_viewer_session_service.py -q
```

Expected：現行 v1 tests 全部通過，作為 adapter regression baseline。

## Task 2：定義 Generic v2 Model 與 Schema

- [ ] 先寫 failing contract tests，涵蓋 grounded RAG、non-grounded LLM app、
  tool-using agent、workflow graph 四種 fixtures。
- [ ] 新增 `CanonicalComponent`、`CanonicalEdge`、`CanonicalEvidenceLocation`、
  `GroundingReadiness` 與 `AiSystemMapV2`。
- [ ] 新增五態 assessment、六態 activation、direct/indirect/explicit-negative evidence
  kind、field-specific conflict 與 build/snapshot/environment scope models。
- [ ] Reference map schema 固定 10 planes / 52 nodes；repo overlay 只引用 reference node ids，不把
  reference nodes 複製成已偵測 repo components。
- [ ] `not_detected` validation 要求 capability-specific coverage gate 通過；coverage 不足
  reject 或降為 `undetermined`。
- [ ] `extra="forbid"`；遞迴拒絕 `confidence`。
- [ ] 產生並驗證 `schemas/ai-system-map.v2.schema.json`。
- [ ] 不在 v2 canonical model 放 profile rows、viewer node ids 或 runtime trace steps。
- [ ] 新增 generic workflow JSON provider：只在 validated object shape 含明確 node
  list與 edge endpoints 時 emit workflow components/edges；evidence location 使用 JSON
  pointer。不得用整份 JSON blob 的字串包含判斷平台或 component type。
- [ ] Provider 不宣告 Langflow/Dify/Flowise 完整相容；平台專用欄位只保留為
  project-relative evidence metadata。

## Task 3：實作 v1-to-v2 Adapter

- [ ] 將 v1 slots/instances 轉成 generic components，保留原始 slot id 作
  compatibility metadata。
- [ ] 將 v1 flows/edges 轉成 generic edges，保留 relationship 與 evidence ids。
- [ ] 將 legacy extensions 轉成 `legacy_extension` compatibility components；不得
  自動宣告任何 capability profile detected。
- [ ] 將 v1 unmapped、risk、endpoint 與 evidence 全量保留。
- [ ] 將 `rag-core-v1` slots / flows 轉成 generic v2 components / edges / evidence
  metadata；不得輸出 compatibility-derived product verdict。
- [ ] Adapter 必須 pure/read-only，不讀 filesystem、不呼叫 LLM、不寫 artifact。

## Task 4：新增 Dual-read Loader 與 Opt-in v2 Build

- [ ] `CanonicalMapLoader` 依 `schema_version` 驗證 v1/v2；v1 載入後透過 adapter
  提供 normalized v2 view。
- [ ] Map build 新增 explicit opt-in contract selection；compatibility 階段預設仍為
  v1，禁止 silent cutover。
- [ ] Viewer、profile inference、readiness renderer 逐步改讀 normalized view，不在
  routes 各自判斷 schema version。
- [ ] CLI/API 回傳實際 active schema version 與 migration warnings。

## Task 5：Compatibility Gate

- [ ] v1 fixture 經 adapter 後，所有 evidence ids 與 project-relative locations
  可解析。
- [ ] v1/v2 對同一 grounded fixture 的 generic components、edges、evidence 與
  readiness findings 可回溯且語意等價。
- [ ] v2 的非 grounded fixtures 不被強迫填入 RAG slots。
- [ ] v1 viewer/API clients 仍可使用既有 payload。
- [ ] Windows/macOS path fixtures 都通過。
- [ ] 完整 backend contract/unit/web tests、Ruff、Mypy 通過。
- [ ] 產生 compatibility report，列出已等價、需降級、尚未遷移的 consumers。

## Acceptance Criteria

- [ ] v1 remains readable and test-covered。
- [ ] v2 schema 可表示四象限 AI systems 與 workflow artifacts。
- [ ] v2 assessment 支援五態、六態 activation、field-specific conflict、三種 evidence
  kind 與 build/snapshot/environment scope。
- [ ] 固定 10-plane / 52-node reference map 與 per-repo overlay 可分開 validate。
- [ ] v1-to-v2 adapter deterministic、read-only、無 evidence loss。
- [ ] Dual-read loader 是 schema branching 的唯一 owner。
- [ ] 未通過 compatibility gate 前，active output 不切換至 v2。
- [ ] Plan 13 明確依賴本計畫的 compatibility report 與 gate。
- [ ] Plan 14 同時驗證 v1 migration fixtures 與 final active v2 output。

## Out Of Scope

- 不在本計畫切換 active output。
- 不在本計畫刪除 v1 models/schema 或 legacy extension reader。
- 不做 Langflow/Dify/Flowise 專用 importer。
- 不做 runtime observability、RAG eval 或自動修 code。

## P0 Execution Mapping 補充（2026-07-03）

`ai-system-map/v2` 必須能作為 P0 execution artifacts 的 source schema，但不把所有 execution
path 都寫回 canonical map：

- v2 canonical map 保留 components、edges、evidence、endpoints、risk hints 等 facts。
- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 是 sibling derived
  artifacts，source refs 指向 v2 component/edge/evidence ids。
- v1-to-v2 adapter 必須保留足以讓 dynamic `00` 建立 call graph / execution path 的
  evidence location、line number、JSON pointer 與 endpoint facts。
- Compatibility gate 新增檢查：同一 v1 fixture 經 adapter 後，derived execution artifacts
  不得遺失 evidence ids；但 output 仍不可在 00A 階段切換 active v2。
- 補充計劃的 `inferred` 不改 v2 `DetectionStatus` enum；以 static execution artifact 的
  `inference_kind="static_inferred"` 表達。

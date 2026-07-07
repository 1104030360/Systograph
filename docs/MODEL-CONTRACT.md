# KAI-Mind Phase 2 Model Contract

**Status:** Phase 2 static-readiness target contract（runtime query trace deferred）
**Audience:** frontend / viewer implementers
**Last updated:** 2026-07-08

HTTP endpoint 契約見 [`API-GUIDE.md`](API-GUIDE.md)。本文件定義欄位語意、artifact lifecycle、GraphViewModel 規則。實作以 `src/kai_mind/core/models/` 為準；本文件描述 **target contract**，不代表每欄位已在 current runtime 落地。

---

## 目錄

1. [契約原則](#1-契約原則)
2. [相關文件與程式碼](#2-相關文件與程式碼)
3. [契約分層與產物](#3-契約分層與產物)
4. [Identity · 評估語意 · Reference Map](#4-identity--評估語意--reference-map)
5. [ai-system-map/v2](#5-ai-system-mapv2)
6. [Profile · Step 6 · Readiness](#6-profile--step-6--readiness)
7. [Artifact Lifecycle](#7-artifact-lifecycle)
8. [Static Execution Artifacts](#8-static-execution-artifacts)
9. [GraphViewModel · ViewerLoadResult](#9-graphviewmodel--viewerloadresult)
10. [Manual Mapping · Capability Candidates](#10-manual-mapping--capability-candidates)
11. [Legacy v1 / rag-core-v1](#11-legacy-v1--rag-core-v1)
12. [Runtime Query Trace（deferred）](#12-runtime-query-tracedeferred)
13. [Frontend Checklist](#13-frontend-checklist)
14. [附錄 A · 型別速查](#14-附錄-a--型別速查)

---

## 1. 契約原則

### 1.1 範圍與 Identity

| 項目 | 規則 |
|------|------|
| 輸入 | AI system repo / workflow artifact；**不**假設一定是 RAG |
| Active schema | `ai-system-map/v2`；v1 僅 legacy-readable（00A adapter） |
| Scope 三元組 | `scan_id`（immutable snapshot）+ `build_id`（一次 materialization）+ `environment_id` |
| `environment_id` | Phase2 固定 `environment:default-static` |
| **禁止** | 獨立 `snapshot_id`；數值 `confidence` |
| Viewer 地圖 | 固定 **10 plane / 52 node** reference map + repo overlay；語意種類不同 |

### 1.2 五態 · Activation · Evidence

| 維度 | 值 | 要點 |
|------|-----|------|
| **Assessment（五態）** | `detected` / `partial` / `undetermined` / `not_detected` / `conflicted` | `detected` **必須**有 direct evidence；僅 indirect → 永遠 `partial` |
| **Activation（六態）** | `enabled` / `disabled` / `conditional` / `unknown` / `conflicted` / `not_applicable` | 與 assessment **獨立** |
| **Evidence kind** | `direct` / `indirect` / `explicit_negative` | explicit negative 需明確 disabled/bypass/forbidden 宣告；**缺席 ≠ negative** |
| **`not_detected`** | — | 需 capability-specific coverage gate；gate 未過 → `undetermined` |
| **Conflict** | — | field-specific；保留兩側 evidence |
| **Mapping Completeness** | weights: detected=1, partial=0.5, not_detected=1, undetermined/conflicted=0 | 分母 = **全部 52 格**；`not_applicable` 不移除分母；**不是** confidence |

`ProfileInferenceService` 是 52 格五態與 15 profiles 的 **唯一定案 owner**；frontend **不得**反推或覆寫。

### 1.3 Canonical Map 與 Bridge

- Step 3 產出 `ScanFact[]` + `Evidence[]`（facts only）
- Step 4 **`component_bridge_registry`**（typed Python，Plan 01B）決定 canonical `components[]` / `edges[]` / `unmapped_components[]`
- **禁止：** LLM slot guessing、以 `rag-core-v1` slot 順序組裝、reference node 直接當 blueprint
- `rag-core-v1`：legacy template only（shipped `1.0.0`，13 slots，2 flows）；**不**定義 product readiness
- 52-node capability map 在 **Step 6** 評估，**不是** Step 4 組裝藍圖

### 1.4 UA Staged Rollout

| Phase | 狀態 | 說明 |
|-------|------|------|
| **A** | current runtime | TOML providers 為 Step 3 主路；UA sidecar 可缺席 |
| **B** | target after Gate-1 | UA structural 為主；KAI providers 僅 parity report |
| **C** | target after Plan 14 | Plan 18 退役 transitional KAI path |

**UA 邊界（Phase2 active path）：**

- 僅 deterministic import-map / batching / structural extraction
- **`ua-analysis-result.json` wrapper：** Phase B/C 可選保存 structural wrapper 於 scan snapshot；
  `semantic` payload 維持 `null`、不產生、不消費；整體不列 API artifact path，frontend 不得依賴
- Step 6 **純 Python**；Plan 17 `AssessmentOrchestrator` **deferred**
- **Apply 不重跑 UA**：replay 同 `scan_id` 的 `scan_result` → 新 `build_id`；semantic sidecar 不變
- Rescan → 新 `scan_id` + 重跑 UA
- UA fail-closed：無效 sidecar 不得進 Step 4
- **不採用** Understand-Anything Phase 3–7、`knowledge-graph.json`、其 dashboard

### 1.5 Mapping Proposal vs Deferred AI

Step 9 `MappingProposalService` 為 Phase2 active（deterministic 為主；LLM optional assist）。**不是** UA semantic 或 Plan 17。Proposal **不得**決定 profile 五態 / readiness / canonical truth。

---

## 2. 相關文件與程式碼

| 用途 | 路徑 |
|------|------|
| HTTP API | `docs/API-GUIDE.md`、`frontend/API_CONTRACT.md` |
| Phase2 設計 | `docs/design/epic1-phase2.md` |
| 執行計畫 | `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md` |
| JSON 範例 | `docs/work/Timmy/design/EPIC1/frontend-json-handoff/` |
| UA 邊界 | `ref-opensource/kai-mind-understand-anything-integration-boundary.md` |
| Pipeline 對照 | `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` |
| Runtime trace（deferred） | `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/deferred/12-add-runtime-component-trace-contract.md` |

**Current implementation source of truth：**

- `src/kai_mind/core/models/system_map.py`、`viewer.py`、`mapping.py`
- `src/kai_mind/core/templates/rag-core-v1.json`

**Phase2 planned target modules（尚未全部存在）：**

- `src/kai_mind/core/services/component_bridge_registry.py`
- `src/kai_mind/core/services/profile_inference_service.py`（Step 6-1）
- `src/kai_mind/core/services/graph_projection_service.py`（Step 7）

---

## 3. 契約分層與產物

```text
scan / manual decisions
        ↓
ai-system-map/v2          ← canonical
        ├─ profile-signals/v1
        ├─ readiness-report/v1
        ├─ static execution JSON（call_graph, dataflow_hints, execution_paths, evidence_table）
        ├─ GraphViewModel     ← ephemeral API projection（不寫磁碟）
        └─ Markdown / Mermaid render
```

| 層 | Artifact / Model | Canonical? | Frontend 用途 |
|----|------------------|:----------:|---------------|
| Canonical map | `ai_system_map.json` | Yes | components, edges, evidence, endpoints |
| Profile sidecar | `profile_signals.json` | No | 52 格五態、15 profiles、candidates |
| Readiness | `readiness_report.json` | No | findings, verdict, next checks |
| Evidence table | `evidence_table.json` | No | 扁平 evidence rows（debug / join） |
| Static execution | `call_graph.json` 等 | No | static inferred path（**非** runtime proof） |
| Viewer | `GraphViewModel` | No | canvas nodes/edges/filters |
| Mapping API | proposals / manual mappings | Durable decision | 使用者確認 |
| Runtime trace | future | No | **deferred** |
| SystemMapIndex | internal | — | frontend **不得**依賴 |

**Phase2 P0 — 對外計數（避免「11 個 artifact」混淆）：**

| 類別 | 數量 | 說明 |
|------|:----:|------|
| **Public sibling artifacts**（atomic publish 磁碟檔） | **10** | 7 JSON + 3 render（見下） |
| **Ephemeral graph projection** | **+1** | `GraphViewModel` — API inline；**非** sibling 磁碟檔 |

舊文件寫「11 sibling artifacts（7 JSON + 3 render）」為 **計數錯誤**（7+3=10）；若把
`GraphViewModel` 算進 build 產物，應寫 **「10 public siblings + 1 ephemeral projection」**，
不要把 projection 與 atomic publish 混為同一包 sibling 檔。

**Atomic publish set（`output/{build_id}/`，10 檔）：**

```text
JSON（7）
  ai_system_map.json          ← Step 4 canonical
  profile_signals.json        ← Step 6-1
  readiness_report.json       ← Step 6-2
  call_graph.json             ← Step 6-3
  dataflow_hints.json         ← Step 6-4
  execution_paths.json        ← Step 6-5
  evidence_table.json         ← Step 6-6

Render（3）— export / report；不參與 scoring；Viewer 主畫布不依賴
  ai_system_map.md            ← Epic 1 人類可讀報告（Plan 17 / `GET /api/map/report`）
  system_map.mmd              ← Plan 06 架構 Mermaid export（lazy `artifact_refs`）
  execution_map.mmd           ← dynamic 00 static execution Mermaid export（lazy）
```

**不計入上述 7 JSON 的 persistence JSON（不同 identity / 路徑 / 生命週期）：**

| 檔案 / 儲存 | Step | Identity | 角色 |
|-------------|------|----------|------|
| `scans/{scan_id}/snapshot.json` | 3 | `scan_id` | immutable raw scan truth；**build 輸入**，非 build sibling |
| `mappings/{mapping_id}.json` | 9 | `mapping_id` | 使用者 confirmed manual mapping；**下次 build 輸入**，非 sidecar 輸出 |
| `project.json`、`builds/.../manifest.json` | 1 / 7 | project / build | state metadata；非 public artifact set |

同一 build 的 **10 siblings** 共享 `scan_id`、`build_id`、`environment_id`、
`generated_from_build_id`（同 build 時 **MUST** `generated_from_build_id === build_id`）。
Parent lineage 用 `based_on_build_id`。Apply 重用同一 `snapshot.json`、新 `build_id`、
新一套 10 siblings。

---

## 4. Identity · 評估語意 · Reference Map

### 4.1 核心列舉

```ts
type AssessmentStatus = "detected" | "partial" | "undetermined" | "not_detected" | "conflicted";
type ActivationState = "enabled" | "disabled" | "conditional" | "unknown" | "conflicted" | "not_applicable";
type AssessmentEvidenceKind = "direct" | "indirect" | "explicit_negative";
```

### 4.2 Reference Map（catalog version `1`）

**10 planes：**

| `plane_id` | Display name |
|------------|--------------|
| `input_intent` | Input & Intent Plane |
| `control` | Control Plane |
| `ingestion_indexing` | Ingestion & Indexing Plane |
| `retrieval` | Retrieval Plane |
| `extension_subsystems` | Extension Subsystems Plane |
| `evidence` | Evidence Plane |
| `generation` | Generation Plane |
| `memory_state` | Memory & State Plane |
| `governance_observability` | Governance & Observability Plane |
| `deployment_topology` | Deployment Topology Plane |

**52 reference nodes（identity = id，非 label）：**

| `plane_id` | Reference node ids | Count |
|------------|-------------------|------:|
| `input_intent` | `user_input`, `session_context`, `query_classifier` | 3 |
| `control` | `planner`, `router`, `agent_loop`, `orchestrator`, `stop_policy`, `human_approval_gate` | 6 |
| `ingestion_indexing` | `document_loader`, `parser`, `chunker`, `metadata_extractor`, `embedder`, `index_builder` | 6 |
| `retrieval` | `dense_retriever`, `sparse_retriever`, `hybrid_retriever`, `graph_retriever`, `memory_retriever`, `web_retriever` | 6 |
| `extension_subsystems` | `graph_rag_system`, `rag_anything_system`, `infini_memory_system`, `corag_federated_system` | 4 |
| `evidence` | `reranker`, `conflict_checker`, `citation_mapper`, `evidence_pack` | 4 |
| `generation` | `context_composer`, `prompt_builder`, `llm_answerer`, `tool_using_generator`, `output_guardrail` | 5 |
| `memory_state` | `session_state`, `working_memory`, `long_term_memory`, `memory_reader`, `memory_writer` | 5 |
| `governance_observability` | `input_guardrail`, `permission_policy`, `human_approval`, `trace_store`, `eval_harness`, `cost_monitor`, `latency_monitor` | 7 |
| `deployment_topology` | `client_app`, `api_server`, `agent_runtime`, `worker_queue`, `tool_network`, `federated_clients` | 6 |

**Repo overlay 規則：**

- Reference node =「可存在什麼」；repo component =「此 repo 有什麼」
- Frontend **不得**把 reference node 當成 detected repo component
- Backend 發射 **全部** reference nodes（含 `partial` / `undetermined` / `not_detected` / `conflicted`）；非 detected-only
- `reference_capability` 與 `repo_component` 為不同 `semantic_kind`

---

## 5. ai-system-map/v2

Plan 13 cutover 後的 active target。00A 期間可 opt-in normalized view。

### 5.1 頂層欄位

| 欄位 | 說明 |
|------|------|
| `schema_version` | `"ai-system-map/v2"` |
| `system_type` | `"ai_system"` |
| `scan_id` / `build_id` / `environment_id` / `generated_from_build_id` | scope + lineage |
| `project` | 專案 metadata |
| `components[]` | `component_id`, `display_name`, `canonical_type`, `layer`, `status`, `activation`, `evidence_ids`, `metadata` |
| `edges[]` | `edge_id`, `source`, `target`, `relationship`, `status`, `evidence_ids` |
| `evidence[]` | canonical evidence refs |
| `endpoints[]` | API entrypoints |
| `risk_hints[]` | risk hints |
| `unmapped_components[]` | 待使用者決策的 ambiguous components |

### 5.2 Step 4 Bridge Pipeline

```text
Step 3  ScanFact[] + Evidence[]
   ↓
Step 4  component_bridge_registry  (deterministic Python)
   ↓
        components[] / edges[] / unmapped_components[]
   ↓
        normalize + validate → ai-system-map/v2
```

**Apply 路徑：** 跳 Step 3 / UA → **4-1 bridge replay** → **4-2 confirmed mappings** → 重跑 Step 4 normalize 至 Step 7。

Canonical map 只含 evidence-backed facts。Grounding readiness、profiles、`primary_map_type`、viewer ids **不得**寫回 canonical。

---

## 6. Profile · Step 6 · Readiness

### 6.1 Active Profile Registry（15 MVP）

Frontend：**不得** hard-code label / count / order。Profiles 為 **一層**；無 nested signal / profile 分類層。

| # | `profile_id` | Label | Primary axis |
|--:|---|---|---|
| 1 | `rag-grounding` | RAG Grounding | `grounding` |
| 2 | `agentic-control` | Agentic Control | `agent_control` |
| 3 | `tool-calling` | Tool Calling | `tool_use` |
| 4 | `memory` | Memory | `memory` |
| 5 | `workflow-orchestration` | Workflow Orchestration | `workflow_orchestration` |
| 6 | `hybrid-retrieval` | Hybrid Retrieval | `retrieval_strategy` |
| 7 | `reranking` | Reranking | `retrieval_strategy` |
| 8 | `corrective-retrieval` | Corrective Retrieval | `retrieval_strategy` |
| 9 | `self-reflection` | Self Reflection | `agent_control` |
| 10 | `graph-retrieval` | Graph Retrieval | `knowledge_structure` |
| 11 | `hierarchical-retrieval` | Hierarchical Retrieval | `knowledge_structure` |
| 12 | `contextual-retrieval` | Contextual Retrieval | `context_enrichment` |
| 13 | `multimodal-grounding` | Multimodal Grounding | `data_modality` |
| 14 | `modular-composition` | Modular Composition | `design_paradigm` |
| 15 | `multi-query-retrieval` | Multi-query Retrieval | `retrieval_strategy` |

Legacy alias（`advanced-rag` 等）僅 fixture / 討論用；active output 前須映射到上表。

### 6.2 Step 6 Assessment（6-1～6-6）

邏輯在 Step 6；**atomic 寫檔**在 Step 7（Plan 03 + 06）。Step 5 `SystemMapIndex` 僅 read-only lookup。

| 子步 | Owner | 輸出 |
|------|--------|------|
| **6-1** | `ProfileInferenceService` | `profile_signals.json` |
| **6-2** | `ReadinessReportService` | `readiness_report.json` |
| **6-3** | `StaticCallGraphService` | `call_graph.json` |
| **6-4** | `ShallowDataflowService` | `dataflow_hints.json` |
| **6-5** | `ExecutionPathRecoveryService` | `execution_paths.json` |
| **6-6** | dynamic `00` + Plan `03` | `evidence_table.json` |

**名詞對照：**

| 名詞 | 說明 |
|------|------|
| `ProfileInferenceResult` | domain 型別 ≡ `profile-signals/v1` payload |
| `profile_signals.json` | 磁碟 sibling 檔名 |
| `profile_inference_result` | `ViewerLoadResult` API 欄位（同 build 已驗證 sidecar） |

Metadata catalogs（TOML only，executable rules 在 Python）：

- `capability_reference_map.toml` — 52 node 座標、labels、activation_applicable
- `profile_registry.toml` — 15 profile presentation metadata

### 6.3 profile-signals/v1

Read-only sidecar。Build validation / CI strict mode 可 fail-closed；**viewer load** 缺/invalid sidecar 仍載 canonical map + warning（`profile_signals_missing` / `profile_signals_invalid`）。

| 區塊 | 規則 |
|------|------|
| `reference_capability_assessments[]` | **52 rows**（catalog v1）；五態 canonical 落點 |
| `profiles[]` | 15 profile findings；**不得**用於反推 52 格 |
| `capability_candidate_components[]` | confirmed non-baseline only |
| `mapping_completeness` | 見 §1.2 |

**Profile status 約束（摘要）：**

- `detected` → 非空 `direct_evidence_ids`；通常 `implementation_depth_level >= 3`
- `partial` → indirect-only 或部分 direct；保留 missing signals
- `not_detected` → `implementation_depth_level=0` 且 `not_detected_coverage_gate_passed=true`
- `conflicted` → 非空 `conflict_fields` + 兩側 evidence
- **禁止** `confidence`；`implementation_depth_level` 是 observed scope，不是 confidence
- Deterministic、local-only；**不**呼叫 mapping proposal / LLM

### 6.4 readiness-report/v1

| 欄位 | 說明 |
|------|------|
| `release_verdict` | `ready` / `needs_review` / `blocked` — backend 定案，frontend 只顯示 |
| `findings[]` | `finding_id`, `category`, `severity`, `status`（五態）, `evidence_ids`, `recommended_next_checks` |
| `primary_map_type` | optional derived summary；**非** canonical |
| Registry | `finding_registry_version: "readiness-finding-registry/v1"` |

**禁止** naming：`confidence`、`quality`、`accuracy`、score、pass/fail。

---

## 7. Artifact Lifecycle

### 7.0 Build output vs project state

```text
State store（${KAI_MIND_STATE_DIR}/projects/{project_id}/）
  project.json
  mappings/{mapping_id}.json     ← ManualMapping（Step 9 決策）
  scans/{scan_id}/snapshot.json  ← ScanSnapshot（Step 3）
  builds/{build_id}/manifest.json
  latest.json

Build output（output/{build_id}/ 或等價 run directory）
  10 public sibling artifacts（上表 7 JSON + 3 render）
  + GraphViewModel（Step 7 投影，僅 API；不寫入 sibling 路徑）
```

Frontend **不得**把 state-store JSON 當 build `artifact_refs` 或 merge 進
`ViewerLoadResult` 主載入路徑。

### 7.1 ArtifactRef

Target API 用 safe refs（**不**暴露 absolute path）。Current v1 `*_path` 為 compatibility-only。

```ts
type ArtifactRef = {
  artifact_id: string;
  artifact_type:
    | "ai_system_map" | "ai_system_map_markdown" | "system_map_mermaid"
    | "profile_signals" | "readiness_report"
    | "call_graph" | "dataflow_hints" | "execution_paths"
    | "evidence_table" | "execution_map_mermaid" | "map_error";
  file_name: string;   // basename only
  media_type: string;
  sha256: string;
  size_bytes: number;
};
```

### 7.2 Build / Viewer 模型

```ts
type MapBuildResult = {
  status: string;
  scan_id: string;
  build_id: string;
  environment_id: string;
  generated_from_build_id: string;
  artifacts: ArtifactRef[];
  viewer_load_result?: ViewerLoadResult | null;
  warnings: string[];
  error?: string | null;
};
```

Viewer **不得**在 load 時重算 profile inference。Sidecar 缺/invalid → base graph + warning。

`evidence_table.json` 與 `ai_system_map.json.evidence[]` 目的不同：前者為 flattened query-friendly table。

---

## 8. Static Execution Artifacts

Owner：dynamic Plan `00`。Phase2 P0 必填。**永遠** `runtime_verified: false`。

共用 header（`StaticArtifactHeader`）：`schema_version`, `scan_id`, `build_id`, `environment_id`, `generated_from_build_id`, `runtime_verified: false`, `limitations[]`

| 檔案 | 內容 |
|------|------|
| `call_graph.json` | `StaticCallEdge[]` — static inferred call edges |
| `dataflow_hints.json` | `DataflowHint[]` — shallow dataflow |
| `execution_paths.json` | `ExecutionPath[]` — ordered static paths |
| `evidence_table.json` | `EvidenceTableRow[]` — flattened evidence |
| `execution_map.mmd` | Mermaid render |

Frontend 用語：**「static evidence suggests」** / **「appears to flow」** — **禁止**「executed」/「traversed」。

---

## 9. GraphViewModel · ViewerLoadResult

**Render-only** projection。`GraphProjectionService.project(system_map, profile_result=...)` 從 **validated in-memory build results** 建構 — **不是** viewer load 時 merge sibling JSON。

`GraphViewModel` 為 **ephemeral API projection**；**不是** atomic-publish sibling 檔案。

### 9.1 ViewerLoadResult 要欄位

| 欄位 | 說明 |
|------|------|
| `loaded`, `error_reason`, `warnings` | 載入狀態 |
| `scan_id`, `build_id`, `environment_id`, `generated_from_build_id`, `based_on_build_id` | lineage |
| `applied_mapping_ids` | Apply 後已套用 mapping |
| `artifact_refs` | safe refs（lazy-load 用；不含 absolute path） |
| `ai_system_map` | canonical map object |
| `graph_view_model` | canvas projection（ephemeral；**非**磁碟 sibling） |
| `profile_inference_result` | nullable；≡ 同 build `profile_signals.json` |
| `readiness_report` | nullable sidecar |

**載入策略（Phase2 target）：**

| 來源 | `ViewerLoadResult` 欄位 | 載入 |
|------|-------------------------|------|
| `ai_system_map.json` | `ai_system_map` | **inline** |
| `profile_signals.json` | `profile_inference_result` | **inline** |
| `readiness_report.json` | `readiness_report` | **inline** |
| Step 7 投影 | `graph_view_model` | **inline**（非磁碟檔） |
| static execution 三件套 | — | **`artifact_refs` lazy** |
| `evidence_table.json` | — | **`artifact_refs` lazy** |
| `*.md` / `*.mmd` render | — | **`artifact_refs` lazy** |

**主畫布 ≠ merge 六份 Step 6 JSON。** 只有 **6-1 Profile Inference**（經 Step 7
`GraphProjectionService`）進主 canvas；`readiness_report` 供 report 面板；static execution
與 `evidence_table` 供 Inspector / debug lazy surface。

### 9.2 GraphNodeModel 重點

| 欄位群 | 說明 |
|--------|------|
| Identity | `id`, `source_id`, `type`, `slot`, `label`, `subtitle`, `badges` |
| Assessment | `status`, `activation`, `semantic_kind`, `plane_id`, `reference_node_id` |
| Evidence | `evidence_ids`, `direct_evidence_ids`, `indirect_evidence_ids`, `explicit_negative_evidence_ids`, `conflict_fields` |
| Profile | `profile_id`, `primary_anchor_node_id`, `anchor_node_ids`, related candidate/unmapped ids |
| Risk | `risk_hint_ids` |

`semantic_kind` 含：`reference_capability`, `repo_component`, `canonical_component`, `grounding_component`, `slot_placeholder`, `unmapped_component`, `capability_candidate`, `profile_attachment` 等。

### 9.3 Filters · Lenses

**Owner：** `GraphProjectionService` 獨占填充 `filters.available[]` 與 `filters.lenses[]`。Frontend 只做 highlight/dim — **不得**從 label / topology / filename 推 membership。

| 控制 | 規則 |
|------|------|
| `filter:profile_attachments` | 正 filter；預設 inactive |
| `filters.behavior` | target: `highlight_and_dim` |
| Lenses（6 固定 id） | 非互斥 membership；切換不刪 node/edge |

| Lens id | 語意 |
|---------|------|
| `lens:data` | ingestion, indexing, retrieval data movement |
| `lens:control` | orchestration, routing, agent loops, tools |
| `lens:evidence` | grounding, citations, provenance |
| `lens:governance` | policy, guardrails, privacy boundaries |
| `lens:source` | loaders, connectors, traceability |
| `lens:risk` | risk hints, exposure, conflicts |

Unsupported lens：`supported=false` + `unavailable_reason` — frontend 顯示 disabled，不猜原因。

完整 TS 定義見 `src/kai_mind/core/models/viewer.py` 與 [附錄 A](#14-附錄-a--型別速查)。

---

## 10. Manual Mapping · Capability Candidates

### 10.1 Manual Mapping

| `mapping_type` | 語意 |
|----------------|------|
| `existing_slot_mapping` | ambiguous component → grounding slot |
| `non_baseline_capability_candidate` | 非 baseline → capability inference |
| `new_extension_component` | **legacy only**；v2 happy path 禁用 |

| `decision` | `confirmed` / `rejected` / `skip_for_now` / `not_applicable` |

Phase2 **無** profile-level manual mapping UI。Reject/skip 須 durable audit（Plan 01）。

### 10.2 capability_candidate_components

- 出現在 **`profile_signals.json`**，**不在** `ai_system_map.json`
- `status: "confirmed_non_baseline"` only
- Phase2 **不**產出 AI assessment candidates（Plan 17 deferred）

---

## 11. Legacy v1 / rag-core-v1

### rag-core-v1 template

- 檔案：`src/kai_mind/core/templates/rag-core-v1.json`
- Shipped：`rag-core-v1@1.0.0`，13 slots，2 flows（`indexing`, `query_answer`）
- Optional slots：`query_processing`, `guardrails`, `observability`
- Phase2 **凍結**；擴充需 separate approved migration
- **`1.1.0` 未 shipped** — 勿當 runtime truth

### ai-system-map/v1

Legacy-readable via 00A。Plan 13 後非 active output。

| v1 `SlotStatus` | 意義 |
|-----------------|------|
| `detected` | slot 有 evidence |
| `missing` | required grounding slot 無 evidence |
| `not_configured` | slot 適用但未配置 |
| `not_applicable` | slot 不適用此 map shape |

**新 Phase2 UI：** 不要求使用者建 `extensions`。Confirmed non-baseline → `capability_candidate_components`，非 canonical map。

v1 → v2：**無** stable 1:1 slot→component id；adapter 內部 normalize 後才進 public artifacts。

---

## 12. Runtime Query Trace（deferred）

Epic 1 Phase 3 follow-up。**不**屬 Phase 2 MVP。

| 問題 | 契約 |
|------|------|
| Static projection | 「哪些 component/profile **看起來**存在？」 |
| Runtime trace | 「此 query **實際**走過哪些 component？」 |

Frontend：trace replay 為 **transient UI**；不得 persist 成 map/profile artifact。Unknown ref → warning，**不**新建 graph node。

Planned `TraceComponentRef` / `QueryTraceEvent` 擴充見 deferred Plan 12。Current trace API 行為見 `API-GUIDE.md` §4。

---

## 13. Frontend Checklist

| # | 規則 |
|---|------|
| 1 | Canonical **system map** = `ai_system_map.json` v2；readiness verdict 在 `readiness_report.json` |
| 2 | `profile_signals.json` = read-only enrichment；缺 sidecar 仍可 render base graph |
| 3 | Canvas 來自 `GraphViewModel`；**禁止** frontend 推 topology / 五態 |
| 4 | 顯示 backend 提供的五態 + 六 activation + evidence kind legend |
| 5 | 顯示 `scan_id`, `build_id`, `environment_id`, Mapping Completeness（分母 52） |
| 6 | **禁止** hard-code profile label / count / order |
| 7 | **禁止** frontend-only reference / overlay nodes |
| 8 | Assessment UI 一層：reference rows + repo overlay；無 nested profile 層 |
| 9 | `filter:profile_attachments` 當一般正 filter 使用 |
| 10 | Query trace = transient overlay；**禁止** write-back |

JSON 範例與 step-by-step handoff：`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`。

---

## 14. 附錄 A · 型別速查

完整定義以 `src/kai_mind/core/models/` 為準。以下為 frontend 常用速查。

```ts
type ReferenceCapabilityAssessment = {
  reference_node_id: string;
  status: AssessmentStatus;
  activation: ActivationState;
  direct_evidence_ids: string[];
  indirect_evidence_ids: string[];
  explicit_negative_evidence_ids: string[];
  conflict_fields: string[];
  conflict_evidence_ids: string[];
  not_detected_coverage_gate_passed: boolean;
};

type MappingCompleteness = {
  numerator: number;
  denominator: number; // 52
  value: number;
  weights: { detected: 1; partial: 0.5; undetermined: 0; not_detected: 1; conflicted: 0 };
};

type ProfileFinding = {
  profile_id: string;
  label: string;
  status: AssessmentStatus;
  activation: ActivationState;
  primary_axis: string;
  secondary_axes: string[];
  implementation_depth_level: 0 | 1 | 2 | 3 | 4;
  direct_evidence_ids: string[];
  indirect_evidence_ids: string[];
  explicit_negative_evidence_ids: string[];
  evidence_ids: string[];
  evidence_strength: "static_multiple_signals" | "static_single_signal" | "weak_or_ambiguous_signal" | "not_detected";
  not_detected_coverage_gate_passed: boolean;
  source: "deterministic_static";
  // + coverage_*, conflict_*, related_* , recommended_next_checks, uncertainty, description
};

type CapabilityCandidateComponent = {
  id: string;
  name: string;
  observed_kind: string;
  status: "confirmed_non_baseline";
  evidence_ids: string[];
  source_unmapped_component_id?: string | null;
  proposal_id?: string | null;
  decision_source?: string | null;
};

type ReadinessFinding = {
  finding_id: string;
  category: string;
  severity: "blocker" | "high" | "medium" | "low" | "info";
  status: AssessmentStatus;
  evidence_ids: string[];
  recommended_next_checks: string[];
  limitations: string[];
};

type GraphViewModel = {
  scan_id: string;
  build_id: string;
  environment_id: string;
  generated_from_build_id: string;
  reference_map_version: string; // "1"
  mapping_completeness: MappingCompleteness;
  nodes: GraphNodeModel[];
  edges: GraphEdgeModel[];
  details: { evidence_by_id; risk_hints_by_id; profile_findings_by_id?; ... };
  filters: { lenses?: GraphLensModel[]; available: GraphFilterModel[]; behavior?: string };
};
```

Implementation depth：`0`=無實作，`1`=concept/config，`2`=module 存在但 path 未證明，`3`=完整 profile pipeline in path，`4`=+ eval/observability hardening。

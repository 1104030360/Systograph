# Systograph Phase 2 Model Contract

**Status:** Phase 2 S1 implemented contract + later projection/cutover targets（runtime query trace deferred）
**Audience:** frontend / viewer implementers
**Last updated:** 2026-07-28

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
| Active public schema | `ai-system-map/v2`；v1 僅保留 historical read/migration 與預設關閉的 operator rollback writer |
| Build scope | `scan_id`（immutable snapshot）+ `build_id`（一次 materialization）+ `environment_id` + `artifact_set_version` |
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

- `src/kai_mind/core/models/system_map.py`、`ai_system_map_v2.py`、`viewer.py`、`mapping.py`
- `src/kai_mind/core/models/profile_signal.py`、`readiness_report.py`、`analysis_history.py`
- `src/kai_mind/core/services/component_bridge_registry.py`、`profile_inference_service.py`
- `src/kai_mind/core/services/map_build_pipeline.py`、`apply_confirmations_service.py`
- `src/kai_mind/core/rules/capability_reference_map.toml`
- `src/kai_mind/core/templates/rag-core-v1.json`

**Later target module（尚未存在）：**

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
| Readiness | `readiness_report.json` | No | findings, readiness summaries, next checks |
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

### 3.1 Step 2 inventory provenance

`scan_inventory_rules.toml` 是 KAI-owned default path policy 的唯一 executable source of
truth。Git、recursive 與 Git-error fallback 共用 ordered last-match-wins matcher；Python只保留
outside-root symlink、binary、size、unreadable與Git metadata等不可覆寫 safety。

| Candidate source | 行為與刻意差異 |
|---|---|
| `git` | `git ls-files --cached --others --exclude-standard`；tracked file 即使命中 ignore仍保留，並套用 `.git/info/exclude` / configured global excludes |
| `recursive` | 只讀 target tree內 `.gitignore`，不讀 Git private/global state |
| `fallback_after_git_error` | Git listing失敗後的 recursive結果；source mode與run digest不得冒充正常Git |

每次新 inventory / snapshot 保存 `inventory_policy_schema_version`、
`inventory_policy_digest`、`candidate_set_digest`、`filesystem_safety_version`、
`boundary_decision_digest`、`final_inventory_digest`、`inventory_source_mode`、
`inventory_run_digest` 與 content-free `inventory_policy_audit[]`。Run digest綁定candidate set、
catalog bytes、filesystem safety version、帶 `selection_scope`／fingerprint 的runtime decisions與
final result。

Plan 20在default policy之上增加 **one-run delta**，不是永久偏好或Manual Mapping：

```text
metadata-only preflight
  → included / soft_excluded / hard_blocked / missing
  → exact_file 或 bounded recursive_directory proposal
  → re-enumerate + metadata/manifest revalidation
  → hard safety > exact > deepest directory > ancestor > default
  → post-decision openat/no-follow + fstat + binary probe + content hash
  → one final FileInventory → current providers → snapshot
```

只有`soft_excluded`可被`scan_this_run`重新納入；filesystem `hard_blocked`不可覆寫。
Directory hard bounds固定5,000 observed regular files、500,000,000 selectable bytes、64層，
同preflight最多20 scopes；parent/child overlap以canonical file path去重。Preflight proposal的file
fingerprint只含`path + target_type + size_bytes + mtime_ns`；directory fingerprint則涵蓋完整
metadata manifest、policy digest與safety version。兩者在使用者決定前都不讀內容。

Final `FileRecord`可攜帶internal `metadata_fingerprint`與`content_fingerprint`。Content SHA-256
只在decision/default outcome確定納入後，從已通過逐層no-follow與`fstat`的同一file handle建立；
snapshot寫入前再次透過相同adapter比對，不使用`Path.read_bytes()`重新開啟。Snapshot的
`file_fingerprints`是detail-scan stale check的content binding，不輸出file content。

Git tracked-but-missing path保留為`base_outcome="missing"`／`reason="missing_at_scan"`，並計入
preflight `missing_count`；它沒有actionable proposal，未被decision指向時不阻擋其他檔案。

`InventoryPolicyAuditEntry` additive保存`base_outcome`、`effective_outcome`、
`decision_origin`、`boundary_decision`、`decision_target_path`、`decision_scope`、
`decision_fingerprint`、`override_applied`與`preflight_request_id`。Directory decision展開成
per-file audit；每筆`path`是實際file，而`decision_target_path`保留winning directory。
`inventory_selection_summary`只由final audit投影，不是第二份inventory truth。

舊 snapshot 缺上述欄位時仍可讀，`inventory_provenance_status` 必須是
`legacy_inventory_policy_unknown`；不得以目前catalog digest回填歷史scan。新snapshot與
manifest使用`recorded`。

Plan 13 active output 中，7 個 JSON siblings 全部共享 `scan_id`、`build_id`、
`environment_id`、`artifact_set_version` 與 `generated_from_build_id`（同 build 時
**MUST** `generated_from_build_id === build_id`）。3 個 render siblings 在文件 metadata
保存相同 scope；complete manifest 再保存每檔 digest、size 與 schema status。Parent lineage
用 `based_on_build_id`。Apply 重用同一 `snapshot.json`、新 `build_id`、新一套 10 siblings。

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
- `reference_node_id` 與 repo `component_id` 是不同 identity；只接受 backend bridge / assessment 關聯，不以相同 label 或字串相等推定對應
- Frontend **不得**把 reference node 當成 detected repo component
- Backend 發射 **全部** reference nodes（含 `partial` / `undetermined` / `not_detected` / `conflicted`）；非 detected-only
- `reference_capability` 與 `repo_component` 為不同 `semantic_kind`

---

## 5. ai-system-map/v2

Plan 13 已切換的 active public contract；正常 CLI/API build 只能產生 v2。

### 5.1 頂層欄位

| 欄位 | 說明 |
|------|------|
| `schema_version` | `"ai-system-map/v2"` |
| `system_type` | `"ai_system"` |
| `scan_id` / `build_id` / `environment_id` / `artifact_set_version` / `generated_from_build_id` | scope + lineage |
| `project` | 專案 metadata |
| `components[]` | `component_id`, `display_name`, `canonical_type`, `layer`, `status`, `activation`, `evidence_ids`, `metadata` |
| `edges[]` | `edge_id`, `source`, `target`, `relationship`, `status`, `evidence_ids` |
| `evidence[]` | canonical evidence refs |
| `endpoints[]` | API entrypoints |
| `risk_hints[]` | risk hints |
| `unmapped_components[]` | 待使用者決策的 ambiguous components |
| `recommended_next_checks[]` | deterministic scan-fact checks；見 §5.3 |

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

### 5.3 `recommended_next_checks[]`（System 1 · scan-fact checks）

由 `RecommendedNextCheckService` 從 normalized scan signals（components / endpoints / risk hints）deterministic 推導；reason / action 文案來自 `recommended_next_check_rules.toml`，v1（rollback writer）與 v2（active writer）兩條 build 路徑共用同一個 derive。

| 欄位 | 說明 |
|------|------|
| `id` | `check:<rule_id>:<slug(target_type)>:<slug(target)>`；同 rule + 同 target 只出現一次。`rule_id` 原樣保留，後兩段經 **slug 化**：連續非英數字元折成單一 `-`、去頭尾 `-`、轉小寫。例：`component_instance` + `component:embedding_model:openai` → `check:privacy_exposure:component-instance:component-embedding-model-openai` |
| `target_type` / `target` | 四種取值：`component_instance` / `component_slot` / `endpoint` / `system`。前三種為 **evidence-targeted**，指向具體實體；`system` 是 **fallback**——觸發訊號解析不到任何 component / slot / endpoint 時，該 check 針對整個系統，此時 `target` 固定為 `"system"` |
| `reason` | 觸發這條 check 的靜態掃描事實 |
| `action` | 建議人工執行的下一步驗證動作 |

- `system` fallback 的取值來自 rule TOML 的 `default_target_type`，只在 target 解析失敗時使用，**不是**整體性評語的入口：即使 target 退回 `system`，`reason` 仍必須是可查證的掃描事實、`action` 仍必須是具體的人工驗證動作。
- **不是 score、不是 verdict**：只列「靜態證據尚未涵蓋、需人工確認」的項目；**禁止** `confidence` 或 pass/fail 語彙。
- 關注面是 runtime readiness 與 privacy exposure（missing runtime-critical slot、published port、external provider、secret-like config…），**不**評估 capability。
- 依 `id` 排序；同一 `scan_id` 重跑結果一致。

**Additive schema migration：** 此欄位為 `ai-system-map/v2` 的 additive 欄位，不在 schema `required`，因此缺此欄位的舊 artifact 仍可載入。但 root `additionalProperties` 為 `false`，**pin 了舊 v2 schema copy 的 strict validator 必須先更新 schema copy**，才能驗證帶此欄位的新 artifact。

**與 System 2 的分工（兩者不互斥、不互相覆蓋）：**

| | System 1 · scan-fact checks | System 2 · capability review checks |
|---|---|---|
| Owner | `RecommendedNextCheckService`（Step 4） | `ProfileInferenceService` + `profile_registry.toml`（Step 6） |
| 落點 | `ai_system_map.json` 的 `recommended_next_checks[]` | `readiness_report.json`（頂層 `recommended_next_checks[]` 與 `findings[].recommended_next_checks`）、profile finding → profile attachment node 的 `recommended_next_checks` |
| 關注面 | runtime / privacy 的掃描事實 | 52 格 capability 與 15 profiles 評估後的後續驗證 |

Markdown report 在 `## Recommended Next Checks` 下**並列兩段**：`### Scan-fact checks`（System 1）與 `### Capability review checks`（System 2，per-node），各自去重；任一段為空時仍保留標題並標示 no checks，兩段不得互相遮蔽。

**歷史狀態：** Plan 13 v2 cutover 期間，v2 build 未接上 derive，此欄位恆為空（RA-4 缺口）；Plan 13.5 回補後正常 build 才有值，該期間產出的 v2 artifact 屬已知歷史狀態。

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
| 8 | `corrective-retrieval` | Corrective Retrieval | `agent_control` |
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

Catalog / rule ownership：

- `capability_reference_map.toml` — 52 node 座標、labels、activation_applicable
- `profile_rule_definitions.py` — 15 stable profile ids、executable required nodes 與 wiring
- `profile_registry.toml` — labels、description、axes、display order、default uncertainty 與
  recommended next checks；由 `ProfileRegistryLoader` strict/fail-closed 載入
- `ProfileRegistryProjectionService` — validated TOML 的 deterministic
  `profile-registry/v1` read-only projection；Profile Engine 不讀回 JSON，也沒有新增 API 或
  per-build artifact

`default_evidence_strength`、conditions、thresholds、coverage gates、required nodes 與 wiring
不得進入 profile TOML；evidence strength 仍由實際 status 與 direct evidence 計算。Frontend
不得複製或重新排序 15 profile ids；未來若需要 registry consumer，必須消費 validated
projection contract。

### 6.3 profile-signals/v1

Read-only sidecar。Build validation / CI strict mode可 fail-closed；**viewer load** 缺/invalid sidecar仍載 canonical map + 單一穩定 warning：`profile_signals_missing_or_invalid`。

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
- Current absence convention：`explicit_negative` evidence 的 `rule_id` 使用 `coverage.reference.<reference_node_id>`；沒有這種 capability-specific coverage evidence 時只能是 `undetermined`
- 高特異性 profile 除 required nodes 外還要通過 registry 的 relationship gate；只有節點、沒有 wiring 時最高為 `partial`

### 6.4 readiness-report/v1

| 欄位 | 說明 |
|------|------|
| Scope | `schema_version`, `source_schema_version`, `scan_id`, `build_id`, `environment_id`, `artifact_set_version`, `generated_from_build_id` |
| `mapping_completeness` | 與 profile sidecar 相同的 52 格摘要 |
| `grounding` | applicability、status、dimensions、evidence 與 reason |
| `capability_summaries[]` | `profile_id`, `status`, `activation`, `evidence_ids` |
| `findings[]` | `finding_id`, `category`, `status`（五態）, `title`, `reason`, `evidence_ids`, `recommended_next_checks` |
| `recommended_next_checks[]` / `limitations[]` | 後續驗證與靜態分析限制；此處為 capability 面的 System 2 checks，與 map 的 scan-fact checks 分工見 §5.3 |
| `primary_map_type` | optional derived summary；**非** canonical |

Current contract 不輸出 `release_verdict`、`severity` 或 `finding_registry_version`。**禁止** naming：`confidence`、`quality`、`accuracy`、score、pass/fail。

---

## 7. Artifact Lifecycle

### 7.0 Build output vs project state

```text
State store（${KAI_MIND_STATE_DIR}/projects/{project_id}/）
  project.json
  mappings/{mapping_id}.json     ← ManualMapping（Step 9 決策）
  scans/{scan_id}/snapshot.json  ← ScanSnapshot（Step 3，含 inventory provenance）
  scans/{scan_id}/manifest.json  ← schema/digest/source mode/run digest摘要
  builds/{build_id}/manifest.json
  latest.json

Legacy mapping migration 側車目錄（${KAI_MIND_STATE_DIR}/，與 projects/ 同層）
  migration-backups/{project_id}/{mapping_id}.{token}.legacy.json
  migration-backups/{project_id}/index.json
  migration-quarantine/{project_id}/{mapping_id}.{token}.legacy.json
  migration-quarantine/{project_id}/{mapping_id}.{token}.original.json

Build output（output/{build_id}/ 或等價 run directory）
  10 public sibling artifacts（上表 7 JSON + 3 render）
  + GraphViewModel（Step 7 投影，僅 API；不寫入 sibling 路徑）
```

Frontend **不得**把 state-store JSON 當 build `artifact_refs` 或 merge 進
`ViewerLoadResult` 主載入路徑。

#### 7.0.1 Legacy mapping migration 目錄（`migrate-legacy-mappings --apply` 產物）

Owner：`LegacyManualMappingMigrationService`（Plan 13 Task 4 建立，Plan 15 決定去留）。
只有 `--apply` 會寫；`--dry-run` 零寫入。三種 artifact：

| Artifact | 內容 | 何時產生 |
|---|---|---|
| `migration-backups/…/{mapping}.{token}.legacy.json`（+ 同目錄 `index.json`） | 原 payload 的 **re-serialization**（sorted keys、normalized indent） | 每一筆實際轉換或隔離的 row |
| `migration-quarantine/…/{mapping}.{token}.legacy.json` | 同為 re-serialization，外層包 `migration_version` 與 `input_digest` | 缺欄位的 row，**以及**乾淨轉換但被丟棄 `extension_edges` 的 row |
| `migration-quarantine/…/{mapping}.{token}.original.json` | **byte-exact** 原檔（由 `mappings/` move 進來，非複製） | 只有無法轉換（`requires_manual_review`）的 row |

- 權限：檔案為 owner-only `0600`；**目錄維持預設 `0755`**——保護做在檔案層，不在目錄層。
  Windows 上 `os.chmod` 只影響 read-only bit，與 backup／quarantine 既有行為一致。
- 內容可能含 legacy free-text（原始 mapping 的 reason／evidence 欄位），因此不得複製到
  log、report 或 target repo；migration report 只帶 opaque `quarantine_ref` 與 digest。
- 為什麼要 move 而不是原地保留：`projects/{project_id}/mappings/*.json` 是
  `LocalJsonProjectRepository.list_for_project` 逐檔 parse 成 active `ManualMapping` 的 glob，
  留一筆 legacy row 會讓整個 project 的 mapping 列舉拋 `StateCorruptionError`。
- **保留策略（load-bearing，兩件事同時成立）：**
  1. quarantine 袋是 cutover gate 的 durable 記錄——只要
     `migration-quarantine/*/*.original.json` 還存在，`cutover_blocked` 就維持 `True`
     （per-run 計數之外的第二個判準；row 被 move 走後，後續 run 已掃不到它）。
     因此**清空袋子＝放行 cutover gate 的操作行為**，不是清暫存檔。
  2. 同一個動作也會銷毀唯一的 byte-exact 遷移前證據——兩份 `*.legacy.json` 都是
     re-serialization，只有 `*.original.json` 是原檔。
  操作者必須在「已人工處理完該 row」之後才刪除；自動化流程不得代為清理。
  `*.legacy.json` **不可**當 gate 判準：乾淨轉換的 row 也會留一份，拿它當 gate 會永久誤擋。
- migration report（`LegacyMappingMigrationReport`，CLI 回傳值，**不落地成檔案**）帶
  additive 欄位 `unresolved_quarantined`＝袋內 `*.original.json` 數量。`cutover_blocked`
  才是 gate；`status`（`dry_run` / `complete` / `requires_manual_review` /
  `partial_requires_retry`）只描述該次 run。
- **無法解析的 row 不入袋**：JSON 讀不出或 DTO 驗證失敗者記為 `failed`，仍留在 `mappings/`，
  仍會炸掉 `list_for_project`。其處置由 Plan 15 裁定。

`ManualMapping.audit_metadata` 的三個 key 是**永久 audit provenance**，不是暫時 migration
殘留，遷移完成後仍保留（裁定：RB-5／RB-6）：

| key | 語意 |
|---|---|
| `legacy_mapping_migration_version` | 轉換這筆 row 的 migration 版本；idempotence 判準（同版本＝`already_migrated`，不重轉） |
| `legacy_payload_digest` | 遷移前 payload 的 SHA-256 digest；對應 backup/quarantine 檔名的 `token`（digest 前 16 字元） |
| `quarantine_ref` | opaque `quarantine:<token>` ref，指向被隔離的原 payload。在 `audit_metadata` 內**只**出現於「成功轉換但 `extension_edges` 被丟棄」的 row（欄位不完整的 row 根本不會產生 `ManualMapping`，它的 ref 只存在於 migration report item）。不得存 absolute path |

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

### 7.2 Current S1 Build / Viewer 模型

```ts
type MapBuildScopedResponse = {
  project_id: string;
  scan_id: string;
  build_id: string;
  based_on_build_id: string | null;
  build_reason: "initial_scan" | "apply_confirmations" | "detail_scan";
  applied_mapping_ids: string[];
  build_result: {
    status: "ok" | "error";
    project_name: string;
    active_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    requested_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    source_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    operator_rollback_active: boolean;
    migration_warnings: string[];
    warnings: string[];
    profile_signals_available: boolean;
    readiness_report_available: boolean;
    profile_inference_result: ProfileInferenceResult | null;
    readiness_report: ReadinessReport | null;
  };
  viewer_load_result: ViewerLoadResult;
};
```

這個 build-scoped S1 envelope 不暴露 `output_run_dir` 或 `*_path`。`ArtifactRef[]` 是
Plan 06 後續 safe lazy-load contract，尚未放進 current response。Viewer **不得**在 load
時重算 profile inference。Sidecar 缺/invalid → base graph + `build_result.warnings`。
成功的 public build 之 `requested_schema_version` 固定為 v2；要求 v1 會先回
`legacy_output_not_selectable`。Operator rollback 只能由 process env 啟用，並以
`active_schema_version`、`source_schema_version`、`operator_rollback_active` 與 migration
warnings 稽核。Detail Scan 若讀不到 parent profile sidecar，
回 `409 profile_sidecar_unavailable`，不可把未知 candidates 靜默當成空集合發布 child。

`evidence_table.json` 與 `ai_system_map.json.evidence[]` 目的不同：前者為 flattened query-friendly table。

---

## 8. Static Execution Artifacts

Owner：`StaticExecutionArtifactService`。Phase2 P0 必填，內容語意固定為
deterministic static inference，**不是** runtime proof。

共用 scope（`ScopedExecutionArtifact`）：`schema_version`, `scan_id`, `build_id`,
`environment_id`, `artifact_set_version`, `generated_from_build_id`。Current schema 沒有 `runtime_verified` 或
`limitations` 欄位；不得由欄位缺席反推 runtime 已驗證。

| 檔案 | 內容 |
|------|------|
| `call_graph.json` | `nodes[]` + `edges[]` — static inferred call graph |
| `dataflow_hints.json` | `hints[]` — shallow dataflow edges |
| `execution_paths.json` | `paths[][]` — ordered static component ids |
| `evidence_table.json` | `rows[]` — flattened evidence + durable `review_state` |
| `execution_map.mmd` | Mermaid render |

Frontend 用語：**「static evidence suggests」** / **「appears to flow」** — **禁止**「executed」/「traversed」。

---

## 9. GraphViewModel · ViewerLoadResult

`GraphViewModel` 是 **ephemeral API projection**，不是 atomic-publish sibling 檔案。
`ViewerSessionService` 接收 normalized v2，再由
`GraphProjectionService.project(system_map, profile_result=...)` 將 52-node reference map 與
repo overlay 投影進主 canvas；viewer load 不得在前端任意 merge sibling JSON。

### 9.1 Current response boundary

| 欄位 | 說明 |
|------|------|
| `MapBuildScopedResponse` | project / scan / build lineage、`applied_mapping_ids` |
| `build_result` | warnings、schema state、inline `profile_inference_result` 與 `readiness_report` |
| `viewer_load_result.loaded`, `error_reason` | base map 載入狀態 |
| `viewer_load_result.map_json`, `ai_system_map` | normalized v2 canonical payload；historical v1 先經 loader/adapter |
| `viewer_load_result.graph_view_model` | current v2 + profile projection |

Sidecar 缺失或 invalid 時，`viewer_load_result` 仍可 loaded，warning 位於
`build_result.warnings`。`profile_inference_result` 與 `readiness_report` 不在 core
`ViewerLoadResult` 內，避免破壞 legacy viewer contract。

### 9.2 Current GraphNodeModel 與 Plan 06 target

| 欄位群 | 說明 |
|--------|------|
| Current identity | `id`, `source_id`, `type`, `slot`, `label`, `subtitle`, `badges` |
| Current evidence | `evidence_ids`, `risk_hint_ids` |
| Plan 06 assessment | `status`, `activation`, `semantic_kind`, `plane_id`, `reference_node_id` |
| Plan 06 profile | `profile_id`, `primary_anchor_node_id`, `anchor_node_ids`, related candidate/unmapped ids |
| Profile next checks | `recommended_next_checks: string[]` — **System 2** 的 capability review checks，由 `ProfileAttachmentOverlayBuilder` 從 `ProfileFinding.recommended_next_checks` 帶進 profile attachment node；純字串，與 graph-level 的 typed list（§14）**不同型別、不同來源** |
| Risk | `risk_hint_ids` |

Plan 06 `semantic_kind` 將包含：`reference_capability`, `repo_component`,
`canonical_component`, `grounding_component`, `slot_placeholder`,
`unmapped_component`, `capability_candidate`, `profile_attachment` 等。

### 9.3 Filters · Lenses

`GraphProjectionService` 獨占填充 `filters.available[]`、`filters.lenses[]` 與 optional
`behavior`；
frontend 只做 highlight/dim，不得從 label / topology / filename 推 membership。

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
`evidence_table.json.rows[].review_state` 使用 `confirmed` / `rejected` /
`needs_confirmation` / `not_required`；`skip_for_now` 保留
`needs_confirmation`，`not_applicable` 對應 `not_required`。

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
| 1 | canonical `ai_system_map.json` 預設是 v2；v1 只可 historical read 或 operator rollback |
| 2 | `profile_signals.json` = read-only enrichment；缺 sidecar 仍可 render base graph |
| 3 | Canvas 來自 `GraphViewModel`；**禁止** frontend 推 topology / 五態 |
| 4 | 顯示 backend 提供的五態 + 六 activation + evidence kind legend |
| 5 | 顯示 `scan_id`, `build_id`, `environment_id`, `artifact_set_version`, Mapping Completeness（分母 52） |
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
  plane_id: string;
  status: AssessmentStatus;
  activation: ActivationState;
  semantic_kind: "reference_capability";
  evidence_ids: string[];
  direct_evidence_ids: string[];
  indirect_evidence_ids: string[];
  explicit_negative_evidence_ids: string[];
  conflict_fields: { field: string; evidence_ids: string[] }[];
  not_detected_coverage_gate_passed: boolean;
  related_component_ids: string[];
  related_unmapped_component_ids: string[];
  related_capability_candidate_component_ids: string[];
  build_id: string;
  scan_id: string;
  environment_id: string;
};

type MappingCompleteness = {
  numerator: number;
  denominator: number; // 52
  value: number;
  status_counts: { detected: number; partial: number; undetermined: number; not_detected: number; conflicted: number };
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
  name: string | null;
  observed_kind: string;
  status: "confirmed_non_baseline";
  evidence_ids: string[];
  source_unmapped_component_id?: string | null;
  source_file?: string | null;
  proposal_id?: string | null;
  decision_source?: string | null;
};

type ReadinessFinding = {
  finding_id: string;
  category: string;
  status: AssessmentStatus;
  title: string;
  reason: string;
  evidence_ids: string[];
  recommended_next_checks: string[];
};

// Current GraphViewModel；由 backend projection 填入，frontend 不重建。
type GraphViewModel = {
  scan_id: string;
  build_id: string;
  environment_id: string;
  generated_from_build_id: string;
  reference_map_version: string; // "1"
  mapping_completeness: MappingCompleteness;
  nodes: GraphNodeModel[];
  edges: GraphEdgeModel[];
  endpoints: GraphEndpointModel[];                       // additive
  recommended_next_checks: GraphRecommendedNextCheckModel[]; // additive；System 1
  details: { evidence_by_id; risk_hints_by_id; profile_findings_by_id?; ... };
  filters: { lenses?: GraphLensModel[]; available: GraphFilterModel[]; behavior?: string };
};

// Graph-level 的 System 1 scan-fact checks（typed；來源是 map 的
// recommended_next_checks[]，見 §5.3）。與 GraphNodeModel.recommended_next_checks
// （string[]，System 2 profile checks，見 §9.2）是兩個不同欄位，不得互相取代。
type GraphRecommendedNextCheckModel = {
  id: string;
  target_type: string;
  target: string;
  reason: string;
  action: string;
};
```

Implementation depth：`0`=無實作，`1`=concept/config，`2`=module 存在但 path 未證明，`3`=完整 profile pipeline in path，`4`=+ eval/observability hardening。

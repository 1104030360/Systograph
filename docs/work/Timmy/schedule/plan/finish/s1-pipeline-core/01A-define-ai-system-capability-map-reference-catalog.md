# AI System Capability Map Reference Catalog 實作計畫

> **2026-07-11 backend execution status：** package-bundled 10-plane/52-node catalog、
> strict loader、forbidden-key/dependency guards 與 backend overlay boundary 已完成並測試。
> Frontend projection 實作不在本次 backend-only 範圍；完成證據見
> `docs/work/Timmy/schedule/report/2026-07-11/2026-07-11-phase2-s1-pipeline-core-REP.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將「固定 AI system capability map」定義成 data-only reference catalog，提供
planes、reference nodes 與顯示 metadata，讓 backend projection 可把實際 repo evidence
overlay 到共同底圖；catalog 不得成為 scanner truth、偵測規則或 executable DSL。

**Architecture:** 新增 package-bundled
`src/systograph/core/rules/capability_reference_map.toml`。TOML 只擁有 reference
planes/nodes metadata與 declarative `activation_applicable`；Python 擁有 component/profile
判定、五態 status、evidence、anchor、edge、activation outcome 與 overlay projection。
DeepResearch 只作概念與 UX 參考，不複製其 HTML、CSS、
JavaScript node records、edge arrays、示範 evidence或分數；本計畫把經確認的
10-plane / 52-node taxonomy 重新定義成獨立、可驗證的 production catalog contract。

**Tech Stack:** Python 3.11, Pydantic v2, TOML, pytest, existing rule catalog loader
patterns.

---

## 問題與決策

共同能力地圖可幫助使用者比較不同 AI / RAG / Agent repo，但必須區分兩種真相：

```text
Capability reference map
  = 固定、data-only 的閱讀座標
  = 可以列出某能力未偵測、尚不清楚或不適用

Repository overlay
  = scanner 從 code/config/workflow facts 與 evidence 推導的實際結果
  = 由 Python 建立，不由 TOML 或 frontend 猜測
```

### 2026-07-06 taxonomy superseding decision

- Active reference catalog 改為固定 10 planes / 52 reference nodes。
- `retrieval` 拆成 `ingestion_indexing` 與 `retrieval`，分開離線建索引和線上取回。
- `state_observability` 拆成 `memory_state` 與 `governance_observability`。
- `specialized_capabilities` 改為 `extension_subsystems`。這只是 reference-map 閱讀分組，
  不恢復 legacy `ExtensionComponent` product contract，也不代表 plugin ownership。
- Governance 現在是 canonical `governance_observability` plane；UI 仍可提供跨 plane
  governance lens，但 lens 只能由 backend memberships 投影，不得建立第二套 canonical facts。
- 舊 8-plane / 35-node 定義只作 superseded planning/prototype 對照，不再是 active target。

## Catalog Ownership Boundary

### TOML 可以擁有

- catalog id / version / display name / description。
- `planes[]`：stable id、label、description、display order、visual group metadata。
- `nodes[]`：stable reference id、label、description、plane id、display order、icon/token
  hints、optional documentation aliases、declarative `activation_applicable`。
- accessibility / localization 所需的 display metadata。

### Pipeline 使用位置

`capability_reference_map.toml` 只在 Step 6 / Step 7 使用：

```text
Step 4 component bridge
  -> 不讀 capability_reference_map.toml
  -> 不輸出 plane_id / reference_node_id

Step 6 ProfileInferenceService
  -> 讀此 catalog 作固定座標
  -> Python 決定 repo facts 是否支撐各 reference node

Step 7 GraphProjectionService
  -> 讀 Step 6 結果與此 catalog metadata
  -> 畫 fixed reference map + repo overlay
```

因此本 catalog 不得被拿來做 scan matching、`rule_id` 對應、profile trigger、
MappingProposal candidate 或 manual decision lifecycle。

### Canonical ten-plane ids

Reference catalog 固定使用以下十個 plane ids 與 display names：

| Plane id | Display name |
|---|---|
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

Data、Control、Evidence、Governance、Source、Risk 六個固定 lenses 由 backend 依
node/edge/evidence/risk memberships 建立。Governance lens 可以跨 plane 顯示風險與政策，
但 `governance_observability` plane 是唯一 canonical governance/observability 分組；不得為
UI filter 重複建立 canonical facts。

### Fixed initial 52-node ids

Initial catalog 固定包含以下 52 個 reference node ids。這是共同閱讀座標，不代表 target
repo已偵測到對應能力；其中 framework/product-like名稱也是 reference concept，不得直接作為
dependency detector或 canonical component truth。

| Plane id | Fixed reference node ids | Count |
|---|---|---:|
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

Canonical display labels 與順序固定如下：

```text
AI Agent / RAG System (Normalized)
├── 1. Input & Intent Plane
│   ├── User Input
│   ├── Session Context
│   └── Query Classifier
│
├── 2. Control Plane
│   ├── Planner
│   ├── Router
│   ├── Agent Loop
│   ├── Orchestrator
│   ├── Stop Policy
│   └── Human Approval Gate
│
├── 3. Ingestion & Indexing Plane
│   ├── Document Loader
│   ├── Parser
│   ├── Chunker
│   ├── Metadata Extractor
│   ├── Embedder
│   └── Index Builder
│
├── 4. Retrieval Plane
│   ├── Dense Retriever
│   ├── Sparse Retriever
│   ├── Hybrid Retriever
│   ├── Graph Retriever
│   ├── Memory Retriever
│   └── Web Retriever
│
├── 5. Extension Subsystems Plane
│   ├── GraphRAG Subsystem
│   ├── RAG-Anything / Multimodal Subsystem
│   ├── Infini Memory / Long-term Memory Subsystem
│   └── CoRAG / Federated Subsystem
│
├── 6. Evidence Plane
│   ├── Reranker
│   ├── Conflict Checker
│   ├── Citation Mapper
│   └── Evidence Pack
│
├── 7. Generation Plane
│   ├── Context Composer
│   ├── Prompt Builder
│   ├── LLM Answerer
│   ├── Tool-Using Generator
│   └── Output Guardrail
│
├── 8. Memory & State Plane
│   ├── Session State
│   ├── Working Memory
│   ├── Long-term Memory
│   ├── Memory Reader
│   └── Memory Writer
│
├── 9. Governance & Observability Plane
│   ├── Input Guardrail
│   ├── Permission Policy
│   ├── Human Approval
│   ├── Trace Store
│   ├── Eval Harness
│   ├── Cost Monitor
│   └── Latency Monitor
│
└── 10. Deployment Topology Plane
    ├── Client App
    ├── API Server
    ├── Agent Runtime
    ├── Worker / Queue
    ├── Tool Network
    └── Federated Clients
```

Loader contract test 必須 assert exactly 10 planes、52 unique node ids，且每個 node 只屬於一個
plane。新增、刪除或 rename node屬 catalog contract migration，不是一般 metadata edit。

### Superseded 8-plane / 35-node draft mapping

- `retrieval` 中的 ingestion nodes 移到 `ingestion_indexing`；retriever nodes 留在新版
  `retrieval`，並補齊 dense、sparse、web 等固定座標。
- `specialized_capabilities` 重新命名為 `extension_subsystems`。
- `state_observability` 拆為 `memory_state` 與 `governance_observability`。
- `unmapped_orchestrator`、`approval_gate`、`tool_agent` 分別 rename 為 `orchestrator`、
  `human_approval_gate`、`tool_using_generator`；`unknown_tool_adapter` 不進新版固定底圖。
- 若保留舊 prototype fixture 或 snapshot 作 regression 對照，轉換必須使用 explicit id
  mapping；不得靠 display label 或 alias 猜測。因 production catalog 尚未建立，本計畫不新增
  8-plane catalog dual-read runtime。

### TOML 不可以擁有

- regex、AST query、dependency/import/call pattern。
- threshold、weight、score、priority calculation 或 status transition。
- `if/then`、boolean expression、rule chaining、template expansion、script/hook。
- component/profile detection、edge inference、activation outcome、anchor selection。
- runtime trace、risk verdict、readiness verdict 或 mapping decision。

禁止把 TOML 演進成 scanner DSL。`activation_applicable`只宣告該 reference node在本質上
是否具有「啟用 / 停用」概念，不表示該 capability對目前 repo是否適用，也不得判定
capability五態。Python只能用此 boolean決定是否產生 activation assessment：`true`時才根據
repo evidence判定 activation；`false`時 activation語意為 `not_applicable`，但 capability
state仍須獨立判定。若新增欄位可改變
`detected / partial / undetermined / not_detected / conflicted`、canonical edge、
risk/readiness finding 或 user review queue，該欄位必須由 Python model/service 擁有並有
focused tests。

## Proposed Catalog Shape

```toml
catalog_id = "ai-system-capability-reference-map"
version = "1"

[[planes]]
id = "input_intent"
label = "Input & Intent Plane"
description = "Understand requests, tasks, and context."
display_order = 10

[[planes]]
id = "control"
label = "Control Plane"
description = "Plan, route, approve, and stop work."
display_order = 20

[[planes]]
id = "ingestion_indexing"
label = "Ingestion & Indexing Plane"
description = "Load, parse, enrich, embed, and index source material."
display_order = 30

[[planes]]
id = "retrieval"
label = "Retrieval Plane"
description = "Fetch and select relevant information."
display_order = 40

[[planes]]
id = "extension_subsystems"
label = "Extension Subsystems Plane"
description = "Represent graph, multimodal, long-term-memory, and federated subsystems."
display_order = 50

[[planes]]
id = "evidence"
label = "Evidence Plane"
description = "Rank, validate, and preserve evidence."
display_order = 60

[[planes]]
id = "generation"
label = "Generation Plane"
description = "Compose context and generate guarded output."
display_order = 70

[[planes]]
id = "memory_state"
label = "Memory & State Plane"
description = "Represent session, working, and long-term memory state."
display_order = 80

[[planes]]
id = "governance_observability"
label = "Governance & Observability Plane"
description = "Represent guardrails, permissions, approvals, traces, evaluations, cost, and latency."
display_order = 90

[[planes]]
id = "deployment_topology"
label = "Deployment Topology Plane"
description = "Represent process, service, tool-network, and federated boundaries."
display_order = 100

[[nodes]]
id = "hybrid_retriever"
plane_id = "retrieval"
label = "Hybrid Retriever"
description = "Retrieves candidate evidence from one or more sources."
display_order = 10
aliases = ["semantic_retriever", "vector_retriever"]
activation_applicable = true
```

`aliases` 只協助文件、migration 與 display lookup；不得直接觸發偵測。

## Implementation Tasks

### Task 1: Define loader models and rejection tests

**Files:**
- Create: `src/systograph/core/models/capability_reference_map.py`
- Create: `src/systograph/core/services/capability_reference_map_loader.py`
- Test: `tests/unit/core/test_capability_reference_map_loader.py`

- [ ] 先寫 failing tests，涵蓋 duplicate plane/node id、unknown plane ref、invalid order。
- [ ] 定義 immutable plane/node/catalog models，拒絕 unknown fields。
- [ ] 加入 forbidden-key tests，拒絕 `pattern`、`query`、`condition`、`threshold`、
  `weight`、`script`、`hook`、`detector` 等 executable/logic ownership 欄位。
- [ ] Loader 只能讀 package-bundled catalog，不讀 target repo 或 remote URL。

### Task 2: Add the package-bundled metadata catalog

**Files:**
- Create: `src/systograph/core/rules/capability_reference_map.toml`
- Test: `tests/unit/core/test_capability_reference_map_loader.py`

- [ ] 建立固定 10 planes / 52 reference nodes initial catalog，並以 exact-id snapshot test 鎖定。
- [ ] 使用 `extension_subsystems` 作 reference grouping；不得恢復 legacy
  `ExtensionComponent` product contract。
- [ ] `activation_applicable`只宣告 node本質上有無啟用/停用概念；Python僅據此決定是否
  產生 activation assessment，不得據此推論 capability五態。
- [ ] Catalog 不含 DeepResearch 的硬編碼 quality、example focus 或 source path。

### Task 3: Define the Python-owned overlay contract

**Files:**
- Modify: `docs/MODEL-CONTRACT.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-a-index-projection/06-deepen-graph-projection-module.md`
- Test: `tests/unit/core/test_capability_reference_map_loader.py`

- [ ] 定義 reference node 與 backend `GraphViewModel` repo overlay 的 id mapping boundary。
- [ ] 實際五態 status、evidence ids、profile attachment、activation outcome與
  risk/readiness details由 Python
  projection 提供。
- [ ] Catalog node 沒有 repo evidence 時，不得被渲染成「系統確實存在的 component」。
- [ ] Frontend 不從 label、plane 或 aliases 自行推論 capability。

### Task 4: Lock dependency boundaries

- [ ] Source-dependency test 禁止 loader import scanner providers、mapping/proposal、LLM、
  query trace、filesystem scan 或 web routes。
- [ ] Plan 02 profile inference 與 Plan 10/11 profile metadata catalog不得依賴 reference
  node labels進行判定。
- [ ] Plan 06/42 只能消費 validated catalog + backend overlay，不得複製 catalog 到 frontend。

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_capability_reference_map_loader.py -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
git diff --check
```

## Acceptance Criteria

- `capability_reference_map.toml` 初始 active 版本固定 exactly 10 planes / 52 node ids，可承載
  display metadata與 `activation_applicable`，但不能加入偵測 DSL。
- Python 是 capability五態/status/evidence/edge/anchor與 applicable node activation outcome
  的唯一 owner；catalog boolean只控制 activation assessment是否適用。
- `Extension Subsystems Plane` 是 reference-map grouping，不是 legacy extension truth。
- Reference map 與 repo overlay 在 contract 中可明確區分，不會把固定底圖冒充掃描事實。
- DeepResearch 只列為設計參考；production code、frontend assets 與資料不從該目錄複製。

## Dependencies and Follow-ups

- 依賴 Plan `00A` 的 generic `ai-system-map/v2` boundary 與 Plan `01` 的 non-baseline
  capability decision semantics。
- Plan `02`、`06`、`10`、`11` 應對齊本 catalog 的 ownership boundary，但不得把 profile
  detection logic移入 TOML。
- Phase4 `39A` 增加 governance/observability deterministic detection，輸出對位
  `governance_observability` plane 並保留跨 plane governance lens memberships。
- Phase5 `42` 才建立完整 AI System Capability Map Graph Studio。

## Out of Scope

- 不實作 Graph Studio、Validation Simulator、runtime trace 或 edit/build workflow。
- 不建立 remote catalog、marketplace、plugin hooks 或 user-authored detector rules。
- 不把 reference catalog寫入 `ai_system_map.json` 作 canonical truth。

# Epic 1 Phase 2 Design: Evidence-backed AI System Mapping

Status: accepted design baseline

Implementation status: planned; acceptance criteria 尚未代表已完成

Owner: Timmy

Audience: backend scanner、API、frontend viewer、QA 與 reviewer

Last updated: 2026-07-07

> 本文件是 Phase2 設計摘要。實作細節與驗收順序以
> `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`
> 及其 `00`～`19` 計畫為準；UA 整合邊界以
> `ref-opensource/systograph-understand-anything-integration-boundary.md` 為準。若本文件與計畫衝突，以較新的 accepted decision 為準。

## 2026-07-07 UA 整合決策

| 決策面 | 定案 |
|---|---|
| Step 3 scanner | staged rollout：Phase A 先以現有 Systograph scan TOML providers 打通 Step 1～9；Gate-1 後 Phase B 改由 `UnderstandAnythingAnalysisService` / UA structural primary、TOML providers 僅做 parity；Plan 14 通過後由 Plan 18 進入 Phase C UA-only |
| UA sidecar 範圍 | Phase2 active path 只執行 deterministic structural extraction：`extract-import-map` → `compute-batches` → `extract-structure`；不執行 `scan-project.mjs`，其 enrichment 移植到 Step 2 inventory；不執行 `file-analyzer` bounded LLM，`ua-analysis-result.json` / semantic sidecar 保持 nullable deferred |
| Step 6 評估 | Phase2 純 Python deterministic `ProfileInferenceService`；Plan 17 `AssessmentOrchestrator` / AI semantic candidate flow deferred，不阻擋 Plan 14 |
| Apply / Rescan | Apply 不重跑 Step 3 / UA，重放 `scan_id` 對應的 immutable scan 後重跑 Step 4～7；Rescan 才建立新 `scan_id`，Phase B/C 才重跑 UA |
| Public contract | semantic sidecar 是 reserved nullable scan internal sidecar，不列 public artifact；frontend contract 不新增欄位；Phase2 無 consumer；Phase B/C 只對 deterministic structural extraction / Node / necessary batch 失敗 fail-closed |

## 1. 產品定位

AI-Mind 的 input 是：

```text
AI system repo / workflow artifacts
```

它不預設輸入一定是 RAG 或 Agent。Phase2 會掃描 source code、dependency files、
configuration、workflow JSON、deployment files 與 prompt metadata，產生可回溯證據的
系統地圖與交付前健檢結果。

產品描述：

> AI-Mind 是 AI/RAG/Agent repo 的證據式系統地圖與交付前健檢工具。

Phase2 與 Langflow 類工具的邊界：

| 面向 | Langflow 類 builder | AI-Mind Phase2 |
|---|---|---|
| 主要工作 | 建立、調整與執行 workflow | 掃描既有 repo / artifacts |
| 使用時機 | 原型與流程組裝 | 接手、review、demo、交付或 CI 前 |
| 真相來源 | 使用者建立的 flow | code、config、workflow facts 與 evidence |
| 輸出 | 可執行 flow | system map、execution map、profiles、readiness |

AI-Mind 不做：

- RAG 單一類型分類器。
- 單純 Mermaid 圖產生器。
- RAG / Agent builder 或 framework。
- runtime observability 或完整 RAG eval 平台。
- 任意 framework repo 的完整 source-code understanding。

## 2. 核心產品承諾

```text
Input repo / workflow artifacts
  -> deterministic scan facts
  -> evidence-backed canonical system map
  -> static inferred execution artifacts
  -> capability overlays
  -> readiness findings
  -> JSON + Markdown + Mermaid + viewer payload
```

Scanner 先自動產生結果。使用者不需要先做 manual mapping 才能看到 map、profiles 或
readiness；不確定項目以 `undetermined`、limitations 或 review indicator 呈現。

Manual mapping 只用來確認 scanner 無法自動定案的 component mapping。確認結果是可重播、
可追責的 durable decision，會在下一次 normalize/build 時套用。它不是 profile 分類問卷，
也不阻塞第一次掃描。

## 3. Source Of Truth 與遷移策略

### 3.1 Canonical target

Phase2 的 canonical target 是 generic `ai-system-map/v2`。UA semantic sidecar 不屬於 canonical
map 或 frontend public contract；它只作 scan internal sidecar 保存，Phase2 沒有 semantic consumer。

`rag-core-v1@1.1.0` 只保留為 v1 grounding compatibility template，不是新產品的通用
canonical schema。產品主流程使用 Capability Map / profile / readiness findings 表達
retrieval、grounding 與交付前缺口；frontend 只消費 backend artifacts，不自行判斷 repo
類型或產生額外 readiness layer。

### 3.2 Expand-and-contract

遷移不得直接 rewrite v1：

```text
00A 新增 v1/v2 dual-read、v1-to-v2 adapter 與 compatibility gate
01-12 建立新 mapping/profile/artifact/index/projection contracts
13  compatibility gate 通過後切換 active v2 output
14  以 fixtures 與 real-world repo 驗證 final static path
15  00A、13、14 全數通過後才退役 legacy v1 compatibility
16  Gate-1 後建立 UA sidecar service（UnderstandAnythingAnalysisService）
17  deferred；不阻擋 Plan 14 / 18 / 15
18  Plan 14 parity gate 通過後退役 TOML scan providers
19  Plan 16 前補 Step 2 inventory metadata
```

在 Plan 13 前，v1 仍可作 active compatibility output；Plan 13 後，新 build 以 v2 為
active output。Plan 15 是獨立 breaking cleanup，不得跳過相容驗證提前執行。

### 3.3 Canonical 與 derived data

`ai_system_map.json` 保存 components、edges、evidence、endpoints 與其他 canonical facts。
Profile、readiness、static execution paths 與 renderer outputs 都是 sibling derived artifacts，
不得反向改寫 canonical facts。

`primary_map_type` 只可作 report/readiness 的 derived summary，不是 canonical truth。

## 4. Canonical System Map

### 4.1 Components

Component taxonomy 至少涵蓋：

| Layer | 代表元件 |
|---|---|
| input | user input、file input、API、webhook |
| knowledge | loader、parser、chunker、embedder、stores、indexes |
| retrieval | retriever、hybrid retriever、graph retriever、reranker、filter |
| context | context builder、compressor、summarizer、memory、permission filter |
| control | agent、planner、router、tool selector、evaluator、retry、query rewriter |
| generation | LLM、VLM、prompt template、output parser、citation builder |
| ops | API、worker、scheduler、cache、deployment、eval、tracing |

V2 component 至少包含 stable id、canonical type、layer、status、evidence ids 與必要的
compatibility metadata。不得把 viewer node id、profile row 或 runtime trace event 塞進
canonical component。

### 4.2 Edges

Edge 描述 static evidence 能支撐的 relationship，例如 call、data flow、control flow 或
configuration linkage。每條 edge 必須能回溯 evidence。

Static edge 不等於已觀測到的 runtime execution。推導深度與限制由 derived execution
artifact 表達。

### 4.3 Evidence

Evidence 使用 project-relative location，可包含 line range、config key 或 JSON pointer。
對外 artifact 不保存完整 source、raw prompt、raw query/output、retrieved chunk、secret 或
local absolute path。

Canonical/profile contracts 禁止數字型 `confidence`。證據可信度改用可稽核的
`evidence_strength`、coverage、implementation depth、reason 與 limitations 表達。

## 5. Grounding Readiness

`grounding-baseline/v1` 是 conditional policy，不是 universal RAG template。

只有偵測到 retrieval/grounding evidence 時，才評估：

1. input source
2. knowledge representation
3. retrieval
4. context assembly
5. generation
6. citation

沒有 grounding evidence 的 tool-using agent 或一般 LLM app，不得因缺少 RAG slots 被判成
不完整 RAG。

`rag-core-v1@1.1.0` 的 10 slots 只服務 v1 compatibility。query processing、guardrails 與
observability 雖移出 compatibility template，相關 evidence 與 readiness value不能遺失。

## 6. Capability Overlay

### 6.1 定義

Profile 是 stackable capability overlay，不是互斥的 RAG variant class。

`profile-signals/v1` 的 active registry 包含：

```text
rag-grounding
agentic-control
tool-calling
memory
workflow-orchestration
hybrid-retrieval
reranking
corrective-retrieval
self-reflection
graph-retrieval
hierarchical-retrieval
contextual-retrieval
multimodal-grounding
modular-composition
multi-query-retrieval
```

每次 build 都輸出 active registry 的完整 rows，避免 consumer 猜測缺列原因。

### 6.2 Status contract

Profile、reference-node assessment 與 canonical detection status 固定為五態：

```text
detected | partial | undetermined | not_detected | conflicted
```

語意：

| Status | 意義 |
|---|---|
| `detected` | direct evidence + capability-specific gate 足以支持能力成立 |
| `partial` | 只有 indirect evidence 或局部 wiring；不得因數量多就升級 |
| `undetermined` | 有相關 evidence，但 wiring、coverage 或 depth 不足以定案 |
| `not_detected` | bounded coverage gate 完成後仍沒有支持 evidence |
| `conflicted` | 同 build / environment / field 內存在無法消解的明確矛盾 evidence |

`detected` 必須有 direct evidence。`not_detected` 不可只靠 absence；必須先確認 coverage gate。
`undetermined` / `partial` 必須保留 reason、related refs 或 recommended next checks，讓 reviewer
知道缺的是 evidence、coverage 還是 wiring。

### 6.3 Detection ownership

Python 擁有：

- trigger logic 與 threshold。
- implementation depth。
- cross-field validation。
- related-ref selection。
- graph attachment projection。
- fail-closed contract validation。

`profile_registry.toml` 只擁有：

- profile id 與顯示名稱。
- short label、description 與 static axes。
- display order、default uncertainty 與 recommended next checks。

TOML 不得包含 regex、condition、threshold、required slot、prompt、provider、mapping action
或 acceptance logic，也不得包含 `default_evidence_strength`、required nodes、wiring 或
Mapping Completeness weights。Evidence strength 仍由 Python 依實際 status 與 direct evidence
計算。

Plan 11 已由 `ProfileRegistryLoader` strict/fail-closed 載入 package-bundled TOML，並由
`ProfileRegistryProjectionService` 產生 deterministic `profile-registry/v1` read-only
projection。Profile Engine 不讀回 JSON；本階段沒有增加 public API、frontend 欄位或
per-build artifact。Frontend 不得複製 15 profile ids 或 display order。

Phase2 assessment 完全 deterministic，`ProfileInferenceService` 是五態唯一 owner。Plan 17
`AssessmentOrchestrator` / AI semantic candidate flow deferred；UA semantic sidecar 是 reserved
nullable slot，Phase2 active path 不產生、不參與 assessment，也不得建立 canonical facts 或提升
status。

## 7. Manual Mapping 與 Proposal 邊界

### 7.1 Active mapping types

新流程只接受：

```text
existing_slot_mapping
non_baseline_capability_candidate
```

`new_extension_component` 只作 legacy read/replay/migration compatibility，不再是新產品入口。

### 7.2 狀態流

```text
staged scanner（A: TOML primary；B: UA primary + TOML parity；C: UA only）
  -> automatic canonical result
  -> ambiguous component marked for review
  -> optional mapping proposal
  -> optional user confirmation
  -> durable mapping decision
  -> next normalize/build applies decision
```

Profile inference 消費已套用完成的 canonical map 與 confirmed capability candidates；它不呼叫
`ManualMappingService`，也不把 mapping proposal 當 profile truth。

Mapping proposal 是 pending suggestion。Profile finding 是 read-only derived result。兩者有
不同 lifecycle、schema、API 與 mutation boundary。

### 7.3 Staged scan 與 Step 6 deterministic boundary

Step 2 先建立 Systograph allowlisted inventory，並移植 `scan-project.mjs` 的 language /
fileCategory / line count enrichment；Systograph 不執行 `scan-project.mjs`，避免 Understand-Anything
另行決定掃描邊界。

Phase A 先由現有 Systograph scan TOML providers 打通 Step 1～9，且
`ua_analysis_result=null` 必須可完成 build / Apply。Gate-1 通過後，Phase B 的 Step 3 才由
Python `UnderstandAnythingAnalysisService` 呼叫 UA sidecar：

```text
FileInventory
  -> extract-import-map
  -> compute-batches
  -> extract-structure
  -> file-analyzer（bounded LLM）deferred；不執行
  -> ua-analysis-result.json nullable deferred sidecar
```

Phase B UA structural output 是 primary facts/evidence 來源，Systograph matching providers 只並跑
parity；Plan 14 保存通過的 parity / fail-closed / Apply replay report 後，Plan 18 進入 Phase C，
並退役 `code_pattern`、`dependency_manifest`、`docker_image` 與 config patterns 的主掃描
ownership。Risk、next-check、reference、profile、inventory 與 LLM config 等 Metadata／設定
catalogs 保留。UA semantic output 保存為 scan internal sidecar，不列 public artifact、不新增
frontend public 欄位，Phase2 也沒有 consumer。

Step 6 由純 Python `ProfileInferenceService` 直接讀 validated map、index、metadata catalogs 與
confirmed non-baseline candidates後定五態。Plan 17 deferred，不啟動 AI candidate workflow。
`detected` 仍必須有 direct evidence。Phase B/C 的 UA schema 不合法、Node runtime 缺失或必要
batch 失敗時 fail-closed；Phase A 的 nullable sidecar 不屬於 failure。

Apply 不重跑 Step 3 / UA；它重放 `scan_id` 對應的 immutable facts/evidence 與 nullable
`ua-analysis-result` 後重跑 Step 4～7。Semantic payload 仍不被 Phase2 assessment 消費。
Rescan 才建立新 `scan_id`，並在 Phase B/C 重跑 UA sidecar。

## 8. Static Execution Mapping

Phase2 P0 需要回答 query 大致可能如何流動：

```text
entrypoint
  -> handler/service
  -> retriever/reranker/context builder
  -> LLM
  -> output
```

它是 evidence-backed inferred execution map，不是 runtime proof。

Static execution artifacts 必須使用：

- `inference_kind="static_inferred"` 或等效 type。
- `runtime_verified=false`。
- `analysis_depth`。
- `evidence_strength`。
- `limitations` 與 recommended next checks。
- 可解析到 canonical component/edge/evidence 的 refs。

不得新增 `inferred` canonical/profile status。無法可靠推導時用 `undetermined`，不要補出
不存在的 path。

Static execution mapping 由 `dynamic-trace-plan/00` 實作，但屬於 Phase2 P0 final static
validation 的前置條件。`dynamic-trace-plan/01` 才是未來 runtime trace implementation。

Plan 12 只記錄 static/runtime 邊界，不包含 runtime implementation tasks，也不阻塞 static
MVP。

## 9. Output Artifact Contract

一次成功 scan/build 至少產生下列獨立 sibling files：

| Artifact | 角色 | Owner |
|---|---|---|
| `ai_system_map.json` | canonical AI system facts | 00A / 13 |
| `call_graph.json` | static inferred call edges | dynamic 00 |
| `dataflow_hints.json` | shallow static dataflow hints | dynamic 00 |
| `execution_paths.json` | inferred query paths | dynamic 00 |
| `evidence_table.json` | flattened evidence rows | 03 / dynamic 00 |
| `profile_signals.json` | capability overlays | 02 / 03 |
| `readiness_report.json` | readiness dimensions與 findings | 03 |
| `ai_system_map.md` | human-readable report | 03 / 06 |
| `system_map.mmd` | component/readiness map | 06 |
| `execution_map.mmd` | static inferred execution map | dynamic 00 |

需求草案中的 `canonical-map.json`、`capability-profiles.json` 等名稱只作概念對照，
不得再產生第二套 truth。

每個 JSON artifact 都必須有自己的 schema/model、writer、path、validation gate 與 failure
behavior。不得把 call graph、profiles、readiness 或 evidence table 全塞進
`ai_system_map.json`。

`evidence_table.json` 必須是實體獨立檔案。它可展開 canonical evidence，但 row 仍保留
`evidence_id`、location、emitted refs、review state 與 source artifact refs，讓 Phase2 後可
映射成獨立 database table。

同一次 build 的 artifacts 必須在同一 run directory，使用 same-run ids。失敗 build 不得留下
不同版本的 partial outputs。

`ua-analysis-result.json` / semantic sidecar 是 reserved nullable scan internal sidecar，不屬於上述
public artifact set，也不會改變 `ViewerLoadResult` / `GraphViewModel` frontend contract；Phase2
不產生、不消費。

## 10. Viewer 與 API

Viewer/API 讀取 validated build result，不自行重新推論 profile 或 execution path。

一般 viewer load 的規則：

- base map valid 時先載入 base graph。
- `profile_signals.json`、readiness 或 execution artifacts 缺失/invalid 時，回傳 degraded
  warnings，不阻塞 base graph。
- strict validation、CI contract validation 或 map build gate 才可 fail closed。
- 不得在 load-time 偷跑 profile inference 填補缺失 sidecar。

Profile attachment node：

- 只為 `detected` profile 建立。
- 必須有 deterministic `primary_anchor_node_id` 與 `anchor_node_ids`。
- 無可靠 anchor 時只留在 details/report，不建立 floating node。
- attachment connector 是 UI affordance，不進 `GraphViewModel.edges[]`。
- profile detail read-only，不提供 profile-level confirm/mutation action。
- canvas 不顯示 evidence count、related refs count 或 per-profile uncertainty。

Frontend 只 render backend projection，不從 node label、dependency 名稱或 topology 自行推論
capability。

## 11. Read-only Lookup 與 Projection

`SystemMapIndex` 是同一次 build 的 read-only lookup boundary，提供 component、edge、
evidence、unmapped、capability candidate、profile 與 artifact refs 的一致解析。

Plan 05 建立最小 index，Plan 07 擴成 shared lookup contract，Plan 08 遷移 mapping
consumers，Plan 09 收斂 legacy lookups。這些計畫保持分開，避免一次重構過大。

`GraphProjectionService` 與 renderers 消費 canonical map、profiles、readiness 及 validated
execution refs；不得各自重新建立 topology。

## 12. 執行順序

```text
S0  00 -> 00A -> Gate-0
S1  01 -> 01B -> 01A -> 02 -> 03 -> 03A -> 04
      Track-A: 05 -> 06 -> 07 -> 08 -> 09
      Track-B: 10 -> 11
      Track-C: dynamic/00 after 03/05, before 14
      Track-D: 19 before 16
    13 -> Gate-1（TOML-primary Step 1～9 + Apply；sidecar=null）
S2  16 -> Gate-2（UA structural + internal sidecar + parity）
S3  14 -> Gate-3 -> 18 -> Gate-4 -> 15

Deferred: 17 AssessmentOrchestrator / AI semantic candidates
Boundary only: 12
Post-Phase2: dynamic/01 runtime trace
```

執行時以依賴 gate 為準；不得因文件排序而跳過 00A compatibility、01A reference
catalog、13 cutover、14 final validation 或 15 complete retirement。

### 12.1 Fixed Reference Map 與 Repo Overlay

- 固定底圖使用 10 個 planes / 52 reference nodes：Input & Intent、Control、
  Ingestion & Indexing、Retrieval、Extension Subsystems、Evidence、Generation、
  Memory & State、Governance & Observability、Deployment Topology。
- Plan 01A 的 `capability_reference_map.toml` 只存 plane/reference-node 顯示 metadata；
  executable mapping/status logic 留在 Python。
- Reference node 永遠屬於共同底圖；repo component/edge 必須由 evidence-backed scan facts
  建立。Frontend 切換 Repo Overlay 時不得把未偵測 reference node 當成 repo component。
- Capability assessment 統一五態：`detected / partial / undetermined / not_detected /
  conflicted`。`not_detected` 需要 scanner coverage gate，單純缺少 evidence 不足以成立。
- `activation` 與 capability status 分開，只對 metadata 宣告 applicable 的節點使用
  `enabled / disabled / conditional / unknown / conflicted`；其他節點為 `not_applicable`。
- Mapping Completeness 使用 `(detected + not_detected + partial * 0.5) / reference_node_count`，
  並必須與五態 counts 一起顯示；不得描述為 readiness 或產品品質。
- 完整規則與範例以
  `docs/work/Timmy/schedule/plan/unfinish/phase2/capability-map-assessment-decision-summary.md`
  為準。

## 13. 驗收矩陣

### 13.1 Contract

- [ ] V1 fixtures 可經 00A adapter 無 evidence loss 轉成 normalized v2。
- [ ] V2 可表示 grounded RAG、non-grounded LLM app、tool agent 與 workflow graph。
- [ ] Capability/profile status 只使用統一五態，沒有數字 `confidence`。
- [ ] Mapping Completeness 可由五態 counts 重算，且 `activation` 不參與公式。
- [ ] Gate-1 先證明 Phase A TOML-primary Step 1～9 與 `sidecar=null` Apply；Phase B 才以 UA
      structural 作 primary，Plan 14 parity gate 通過後由 Plan 18 進入 Phase C UA-only。
- [ ] Apply 重放 `scan_id` 對應的 immutable scan 並重跑 Step 4～7，不重跑 UA；Rescan 才建立
      新 `scan_id`，Phase B/C 才重跑 UA。
- [ ] Grounding readiness 只在 applicable 時評估。
- [ ] `primary_map_type` 不進 canonical truth。

### 13.2 Artifacts

- [ ] 每個 JSON 是獨立 sibling file，且各自通過 schema/model validation。
- [ ] `evidence_table.json` 為實體檔案，不是另一 JSON 內的 nested field。
- [ ] Same-run refs 可解析，失敗 build 不留下版本不一致的 partial artifacts。
- [ ] `system_map.mmd` 與 `execution_map.mmd` 都非空，且角色不混淆。

### 13.3 Profiles 與 mapping

- [ ] Registry 15 個 capability ids 全部出現在 profile result。
- [ ] `detected` 有足夠 evidence；弱訊號不被提升成 detected。
- [ ] `undetermined` 有 evidence/related refs、reason 與 review next check。
- [ ] Manual review 不阻塞第一次 scan。
- [ ] Confirmed mapping 只在後續 normalize/build 改變 derived result。
- [ ] Legacy extension 可讀，但不再是新 mapping 的 product surface。

### 13.4 Static execution

- [ ] Call/dataflow/path refs 全部可回查 canonical map/evidence。
- [ ] 每條 path 明示 `runtime_verified=false` 與 limitations。
- [ ] 至少兩個 direct-import targets 產生非空 execution path；若無法推導則輸出誠實的
  `undetermined` 與 next checks。
- [ ] Workflow JSON 只宣告已驗證的 nodes/edges/config facts，不宣稱平台 runtime semantics。

### 13.5 Viewer/API

- [ ] Base map valid 時，missing/invalid enrichment 只產生 warnings。
- [ ] Viewer 不在 load-time 重跑 inference。
- [ ] Profile attachment 只有 detected 且有可靠 anchor 時建立。
- [ ] Frontend 不自行推論 profile 或 graph relationship。

### 13.6 Migration

- [ ] 00A compatibility report 通過後才執行 13。
- [ ] 13 active v2 cutover 通過後才執行 14 final validation。
- [ ] 00A、13、14 全數通過後才執行 15 完全遷移。

## 14. 範圍外

- Langflow、Dify、Flowise 專用 importer 或 round-trip export。
- 完整 runtime tracing、replay 或 observability backend。
- 完整 RAG eval framework。
- 自動修改 target repo。
- 支援所有語言與所有 AI framework。
- 複雜 interprocedural dataflow 或完整 call graph reconstruction。
- EPIC2、EPIC3 與 page-aware assistant。

## 15. Accepted Decisions

以下決策取代本文件舊版 14.1～14.26 的衝突內容：

1. Canonical target 是 `ai-system-map/v2`；v1 只保留相容遷移。
2. Profile 是 generic capability overlay，registry 為 15 個 ids，不是 12 個 RAG variants。
3. Capability/profile status 為 `detected / partial / undetermined / not_detected / conflicted`。
4. Sidecar 缺失不阻塞一般 viewer load；strict gate 與一般 load 分離。
5. Manual mapping optional，scanner 先產生結果。
6. `extensions` 只作 legacy compatibility；新流程使用 capability candidate。
7. Static execution artifacts 是 P0，但不是 runtime proof。
8. Phase2 artifacts 分檔輸出，為後續資料庫 table boundary 保留清楚 ownership。
9. Python 擁有 profile detection logic；TOML 只擁有 metadata。
10. 先相容遷移，再 active cutover；Plan 14 通過後，active Plan 15 完全退役 v1。
11. 固定 10-plane / 52-node reference map 與 repo evidence overlay 是不同資料角色；Frontend 只 render backend projection。
12. DeepResearch 是研究/視覺參考，不直接修改或複製其 frontend source。
13. Step 3 採 Phase A TOML-primary → Phase B UA-primary + TOML parity → Phase C UA-only staged rollout。
14. Step 6 在 Phase2 純 Python deterministic；Plan 17 `AssessmentOrchestrator` deferred。
15. Apply 不重跑 UA；Rescan 才重跑 UA。
16. UA semantic sidecar 是 reserved nullable scan internal slot，不列 public artifact、不新增 frontend public 欄位，Phase2 active path 不產生、不消費。
17. 不採用 UA Phase 3～7、`knowledge-graph.json` 或 dashboard 作為 Systograph canonical truth。

## 16. Source Of Truth

依優先序：

1. executable code、schemas、tests 與 generated artifacts。
2. `docs/MODEL-CONTRACT.md` 與 `docs/API-GUIDE.md`。
3. `ref-opensource/systograph-understand-anything-integration-boundary.md`。
4. `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`。
5. static plans `00`～`18` 與 `dynamic-trace-plan/00`。
6. 本文件。

Review triggers：canonical schema、profile registry/status、artifact list、viewer degraded-load
policy、manual mapping lifecycle、UA sidecar boundary、Plan 17 是否重新啟動、
static/runtime boundary 或 migration gates 發生變更。

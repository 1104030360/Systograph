# Epic 1 Phase 2 Open Decisions

Status: active decision queue；2026-07-07 late superseding staged-rollout decisions resolved

Implementation status: planned; settled decisions 仍需由各計畫與測試落地

Owner: Timmy

Audience: backend、frontend、QA 與 reviewer

Last updated: 2026-07-07

## Purpose

只記錄會改變 Phase2 `00`～`19` 或 dynamic `00` 實作的未決事項。已被 current plan、
MODEL-CONTRACT、API-GUIDE 或 accepted design 定案的問題，不再重新詢問。

## Current Scope

目前範圍：

- `static-trace-plan/00A`～`19`，含 `01A`、`03A`、`16`、`18`、`19`。
- `static-trace-plan/03A` 的 Apply、Build lineage 與 local JSON persistence。
- `dynamic-trace-plan/00` 的 static inferred execution mapping。
- `12` 只作 runtime boundary 文件。
- Plan `15` 屬目前 active scope，但只能在 `00A`、`13`、`14` 通過後執行。
- Plan `16`（UA sidecar service）、`18`（TOML scan providers 退役）、`19`（inventory metadata）屬 active staged rollout；Plan `17` deferred，不阻擋 `14` / `18` / `15`。
- `dynamic-trace-plan/01` runtime implementation 延後到 active Plan `15` 完成後。

不討論 EPIC2、EPIC3、完整 assistant/copilot、完整 runtime observability、完整平台
importer、MCP handoff 或企業級資安差異化。

## Source Priority

1. code、schemas、tests 與 generated artifacts。
2. `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`。
3. `ref-opensource/kai-mind-understand-anything-integration-boundary.md`（2026-07-07 Accepted UA 整合邊界）。
4. `static-trace-plan/README.md` 與 `00`～`18`。
5. `epic1-phase2-design.md`。
6. 本 decision queue。
7. `raw-data/`。

## Settled Decisions

| 項目 | Current decision |
|---|---|
| Input | AI system repo / workflow artifacts，不預設 RAG 或 Agent |
| Canonical target | generic `ai-system-map/v2` |
| Migration | 00A 相容、13 cutover、14 驗證、15 完全遷移 |
| V1 baseline | `rag-core-v1@1.1.0` 只作 compatibility template |
| Product baseline | Capability Map / profile / readiness findings 是 active assessment surface |
| Profile | single-level、multi-label、registry-driven capability overlays |
| Registry | 15 個 generic capability ids |
| Capability/profile status | `detected / partial / undetermined / not_detected / conflicted`；backend/API/CLI/report/frontend 一致 |
| Status semantics | `partial` 只含間接/不完整 evidence；`conflicted` 只含同 build、同 environment、同欄位且無法依 precedence 消解的明確矛盾 |
| Readiness status | `readiness_report.json.findings[].status` 使用統一五態；overall summary 若需要另行定義，不重用 RAG check status |
| Confidence | canonical/profile 禁止數字 `confidence` |
| Review UI | user-facing 名稱為 `Review scanner suggestions` / `檢查 scanner 建議`；不把 `Manual Mapping` 當主要 UI 名稱 |
| Manual decision lifecycle | internal/durable lifecycle 可保留 `manual_mapping` / `ManualMappingService` |
| New non-baseline flow | `non_baseline_capability_candidate` |
| Legacy extension | read/replay/migration only，不是新產品入口 |
| Sidecar load | 一般 viewer degraded；strict validation 才 fail closed |
| Reference map / repo overlay | 固定 10-plane / 52-node reference map；repo/build assessment 以 overlay 呈現，不把 reference node 冒充 repo fact；舊 8-plane / 35-node 只作 superseded planning/prototype 對照 |
| Profile attachment | detected-only、需要可靠 anchor、read-only；與固定 reference node assessment 分開 |
| Profile rule ownership | Python 擁有 logic；TOML 只擁有 metadata |
| Activation | capability status 與 `activation` 分離；activation 可用 `enabled / disabled / conditional / unknown / conflicted / not_applicable` |
| Mapping Completeness | `detected=1`、`not_detected=1`、`partial=0.5`、`undetermined/conflicted=0`；不是 readiness 或品質分數 |
| Static execution | P0 derived artifacts，不是 runtime proof |
| Artifact shape | 多個 sibling files，各自 schema/writer/validation |
| Evidence table | 獨立 `evidence_table.json` 實體檔案 |
| Platform workflow JSON | generic facts only；不承諾專用 importer/runtime semantics |
| Viewer assessment copy | `已確認 / 部分確認 / 無法判斷 / 未偵測到 / 證據衝突`；review lifecycle 另用 `Needs review / Confirmed / Skipped` |
| Scan / Build identity | `scan_id` 是一次 immutable repo scan snapshot 的唯一 domain identity，不另設第二層 snapshot identity；`build_id` 代表從該 scan materialize 的一組 artifacts |
| Apply UX | 按鈕使用「套用 N 項確認並建立新版本」；Apply 不重新掃描 repo |
| Apply API | `POST /api/map-builds/{base_build_id}/apply`；內部共用 Map Build pipeline |
| Build lineage | 使用 `based_on_build_id`、`build_reason`、`applied_mapping_ids`、`generated_at`；不再新增模糊 `run_id` |
| Phase2 persistence | repository protocols + atomic local JSON adapter；database adapter 留 Phase2 完成後 |
| Build history | B1 immutable；Apply 建立 B2 並在完整驗證後 atomic switch latest Viewer |
| External test repos | 完整第三方 repo 預計放 `tests/fixtures/external_projects/` 並由根 `.gitignore` 排除；repo 只提交 pinned-SHA manifest 與自建小型 fixtures |
| Validation simulator | 僅作開發測試概念，不建立產品 UI；Plan 14 使用 tests 內 fixtures/repos 驗證 |
| DeepResearch | 只作研究與視覺參考，不修改或直接複製其 HTML/CSS/JS 到 production frontend |
| Step 3 scanner | 2026-07-07 late superseding：Phase A TOML-primary → Gate-1 → Phase B UA-primary + TOML parity → Plan 14 / 18 → Phase C UA-only |
| UA sidecar scope | 2026-07-07 superseded：Phase2 active path 只採 deterministic structural extraction：`extract-import-map` → `compute-batches` → `extract-structure`；不執行 `scan-project.mjs`；不執行 `file-analyzer` bounded LLM，`ua-analysis-result.json` / semantic sidecar 保持 nullable deferred |
| Step 2 enrichment | 2026-07-07 resolved：`scan-project.mjs` 的 language / fileCategory / line count enrichment 移植到 KAI Step 2 inventory |
| Step 6 AI orchestration | 2026-07-07 late superseding：Phase2 不建立 `AssessmentOrchestrator`；Plan 17 / AI semantic candidate flow deferred |
| Step 6 authority | 純 Python deterministic `ProfileInferenceService` 唯一定案五態，`detected` 必須有 direct evidence |
| Apply / Rescan UA behavior | Apply 不重跑 Step 3 / UA，重放同 `scan_id` immutable scan 後重跑 Step 4～7；Rescan 才建立新 `scan_id`，Phase B/C 才重跑 UA |
| Semantic sidecar | reserved nullable scan internal sidecar，不列 public artifact、不新增 frontend public 欄位，Phase2 不產生、不消費 |
| UA failure behavior | Phase A `sidecar=null` 可建置；Phase B/C schema 不合法、Node 缺失或必要 batch 失敗時 fail-closed，不進 Step 4 |
| UA product scope | 2026-07-07 resolved：不採用 UA Phase 3～7、`knowledge-graph.json` 或 dashboard；canonical 仍是 `ai_system_map.json` + `profile_signals.json` + `GraphViewModel` |
| MappingProposal boundary | Step 9 MappingProposal 保留不變，與 deferred Plan 17 / AI assessment experiment 相互獨立 |

## Superseded Decisions

下列舊問題不得再作 current implementation 前提：

- `ai-system-map/v1` 永久作 canonical output。
- 12-row RAG variant matrix。
- binary detected/not_detected profile status。
- profile sidecar 缺失就阻塞 base graph。
- `extensions` 作 non-baseline 新流程。
- runtime query trace 是 Phase2 static MVP blocker。
- Plan 13 extension retirement延後到不確定的 Phase3+。
- 只輸出 map/profile/readiness 五個 artifacts。
- KAI scan TOML providers 作為 Phase2 長期主掃描器。
- Plan 17 / AI semantic candidate flow 作為 Phase2 或 Plan 14 prerequisite。
- 不得再把 Apply 設計成重新掃 repo 或重新執行 UA sidecar。
- 不得將 reserved nullable semantic sidecar 作為 public artifact 或 frontend public contract 欄位。
- UA `knowledge-graph.json` / dashboard 作為 KAI-Mind canonical truth。

## Settled Implementation Policies

### OD-2026-07-07-01: Understand-Anything integration boundary

Status: **Resolved — late superseding staged rollout accepted on 2026-07-07**

Resolved decisions:

| Open decision | Resolution |
|---|---|
| Step 3 scanner owner | Phase A 現有 KAI providers primary；Gate-1 後 Phase B `UnderstandAnythingAnalysisService` / UA structural primary + TOML parity；Plan 14 後 Plan 18 進入 Phase C UA-only。 |
| UA sidecar call chain | Phase2 active path：`extract-import-map` → `compute-batches` → `extract-structure`。`file-analyzer` bounded LLM / `ua-analysis-result.json` deferred。 |
| `scan-project.mjs` | 不執行；其 language / fileCategory / line count enrichment 移植到 KAI Step 2 inventory。 |
| Step 6 boundary | Phase2 純 Python deterministic assessment；Plan 17 `AssessmentOrchestrator` / AI semantic candidates deferred。 |
| Assessment authority | `ProfileInferenceService` 唯一定案五態，`detected` 必須有 direct evidence。 |
| Apply vs Rescan | Apply 不重跑 Step 3 / UA，重放同 `scan_id` immutable scan 並重跑 Step 4～7；Rescan 才建立新 `scan_id`，Phase B/C 才重跑 UA。 |
| semantic sidecar public status | reserved nullable scan internal sidecar，不列 public artifact、不新增 frontend public 欄位，Phase2 不產生、不消費。 |
| UA failure handling | Phase A `sidecar=null` 可建置；Phase B/C deterministic structural extraction invalid、Node missing、required batch failed 才 fail-closed。 |
| UA Phase 3～7 | 不採用 UA Phase 3～7、`knowledge-graph.json` 或 dashboard；KAI canonical 仍是 `ai_system_map.json` + `profile_signals.json` + `GraphViewModel`。 |
| Step 9 proposal | MappingProposal 流程保留不變，與 deferred Plan 17 / AI assessment experiment 相互獨立。 |

### OD-2026-07-03-01: 08/09 是否可與第一輪 14 驗證交錯

Status: settled — 採 B；05/07 後可跑 informal smoke，08/09/13 後才跑正式 Plan 14

Recommended: `08`、`09` 應在 Plan 14 final gate 前完成；但可在 development 過程先用
05/07 的 shared lookup 跑一輪非正式 smoke import。

需要決定：

```text
A. 嚴格序列：08 -> 09 -> 13 -> 14
B. 先 smoke：05/07 後跑非正式 import，08/09 完成後再跑正式 14 gate
```

建議 B。它可提早發現 real-world scanner gap，又不把未完成 consumer migration 的結果
誤當 final validation。

不論選擇何者，Plan 14 的正式 acceptance report 都必須在 08/09 與 13 完成後產生。

### OD-2026-07-03-02: Same-run artifact commit strategy

Status: settled — JSON core artifacts 先在 temp build directory 完整驗證，再 atomic promote

Recommended: temp run directory + validate all + atomic directory promotion。

需要在 Plan 03 / dynamic 00 實作前確認 failure behavior：

- JSON writer/schema validation 任一失敗時，是否整個 run 不 publish。
- Mermaid/Markdown renderer 失敗是否也阻塞 publish，或允許 JSON-only degraded run。
- API 如何標示 incomplete run，避免 consumer 混讀不同 build 的 sibling files。

建議 P0 將 7 個 JSON 視為 atomic core；Markdown/Mermaid 可依明確 policy 選擇 strict 或
degraded，但不得無標記地留下 partial run。

### OD-2026-07-03-03: Readiness overall verdict vocabulary

Status: settled for current scope — 不新增 opaque readiness overall score；保留 evidence dimensions/findings，Mapping Completeness 另行命名

Recommended: 先使用 evidence-based dimensions/findings，不急著加入單一總分。

若需要 overall summary，候選詞應與 status contract 分離，例如：

```text
ready | review_required | incomplete
```

不得把 profile `partial` 或 canonical `undetermined` 混成 opaque readiness score。

### OD-2026-07-03-04: Direct-import fixture ownership

Status: settled — 自建 deterministic fixtures 可提交；第三方完整 repo 由 pinned manifest 下載/放入 gitignored directory

Recommended: Plan 14 固定 curated local fixtures 與版本/commit；外部 repo live scan 只作補充。

需確認：

- 哪些 fixture 可提交到 repo。
- 哪些只能透過 script 下載。
- license、size 與 deterministic test boundary。
- dynamic framework 行為太多時，預期輸出是 `undetermined` 還是 unsupported。

### OD-2026-07-06-01: 收斂 active assessment surface

Status: settled — Capability Map
plane/component model 是 active classification 與 assessment surface。

Confirmed boundary:

- Product flow 不再先判斷 repo 是否符合某個 legacy baseline；active report 直接來自
  Capability Map、profile signals 與 readiness findings。
- `rag-core-v1@1.1.0` 只保留給 legacy v1 compatibility、adapter migration、舊
  fixtures/manual decisions 的解讀。
- Retrieval、grounding、source traceability、reranking、Agentic RAG、Graph RAG、
  Hybrid RAG 等，都由 Capability Map planes/components、profile signals 與 readiness
  findings 表達。
- Frontend / report 不顯示 legacy baseline summary、固定維度摘要或 slot drilldown。
- 若 backend adapter 仍讀到 legacy slot facts，必須在 public artifact 前轉成 generic v2
  components、edges、profiles 或 findings。

#### 2026-07-03 confirmed sub-decision: Review Queue item selection

Decision: choose **A. 只放 high-impact ambiguous items**。

Why:

- Scanner 必須先自動產出可用結果；使用者不需要先完成 manual review 才能看到
  map、profile、readiness 或 execution artifacts。
- Manual review 的產品定位是例外處理：只處理「scanner 不該自動定案、且會改變交付判斷」
  的 ambiguous evidence。
- 低影響 ambiguous evidence 應保留在 warnings、`evidence_table.json` 或 debug details；
  不應造成 Review Queue 過大，避免使用者覺得「還是要自己判斷，為什麼要用 scanner」。

Definitions:

- `artifact` 在本決策中指 **Phase2 output artifact**，不是 input artifact。
- Input artifacts 是被掃描的 source code、dependency files、configuration files、
  workflow JSON/YAML、deployment files、prompt files。
- Output artifacts 是 AI-Mind 產生的 run result，例如 `ai_system_map.json`、
  `evidence_table.json`、`profile_signals.json`、`readiness_report.json` 與 static
  execution artifacts。
- Review Queue high-impact 判斷只看 machine-readable output artifacts 的 semantic diff；
  Markdown / Mermaid render outputs 不參與 high-impact scoring。

#### 2026-07-04 confirmed sub-decision: Viewer naming and review copy

Decision: do not use **Manual Mapping** as the primary user-facing UI name.

Naming boundary:

- User-facing action name: `Review scanner suggestions`。
- 中文 UI 名稱：`檢查 scanner 建議`。
- Internal/durable lifecycle name may remain `manual_mapping` / `ManualMappingService`
  because it describes persisted user decisions and replay behavior.
- `Manual Mapping` may appear in backend/internal plan text only when referring to the
  implementation lifecycle, repository classes, API records, or compatibility behavior.

Viewer status copy:

| Status | Meaning |
|---|---|
| `Detected` | scanner 已有足夠 evidence 自動定案 |
| `Not detected` | scanner 沒看到該能力或 readiness evidence |
| `Unclear` | evidence 模糊但不需要使用者立刻處理；保留在 details / evidence table |
| `Needs review` | high-impact ambiguous item，會影響 map、readiness、profile 或 execution path |
| `Confirmed` | 使用者已確認 scanner suggestion 或 mapping decision |
| `Skipped` | 使用者略過，scanner 保留原本自動結果與 warning |

UI copy rules:

- Do not show `Manual Mapping` as the primary navigation, CTA, modal title, or empty-state
  name.
- Use `Review scanner suggestions` / `檢查 scanner 建議` for the main surface.
- For high-impact ambiguous evidence, show `Needs review` and explain:
  `這項判斷會影響 system map 或 readiness report。`
- For low-impact ambiguous evidence, show `Unclear` and explain:
  `已保留在 evidence details，不影響目前報告。`
- `recommended_next_checks` in findings is not a request to redo scanner judgment; it is a
  next-check hint for the user.

Output artifact impact boundary:

| Output artifact | Review Queue scoring role |
|---|---|
| `ai_system_map.json` | Canonical facts；component / edge / evidence refs 改變時影響最高 |
| `evidence_table.json` | Evidence/debug source；支撐判斷與日後 DB table，不單獨讓 item 高影響 |
| `call_graph.json` | 支撐 topology / execution path diff |
| `dataflow_hints.json` | 支撐 query/document/context/prompt flow 是否可信 |
| `execution_paths.json` | 判斷主要 static inferred query/answer path 是否改變 |
| `profile_signals.json` | 判斷 capability overlay status / findings 是否改變 |
| `readiness_report.json` | 判斷 delivery-readiness finding 是否改變 |
| `ai_system_map.md` | Render/report output；不參與 scoring |
| `system_map.mmd` | Render output；不參與 scoring |
| `execution_map.mmd` | Render output；不參與 scoring |

Legacy RAG compatibility boundary:

- 舊 grounding baseline / RAG readiness policy names 只保留為歷史討論與 migration
  context；active product contract 使用 Capability Map / profile / readiness findings。
- `rag-core-v1@1.1.0` 只保留給 v1 compatibility、legacy map/manual mapping 與 fixtures。
- 不寫入 `ai_system_map.json`、`profile_signals.json`、`readiness_report.json` 或
  `evidence_table.json` 的 compatibility-derived readiness 欄位。
- `citation / source mapping` 直接表達為 `readiness_report.json.findings[]` 的
  `source_traceability` finding。

Readiness finding contract:

```json
{
  "finding_id": "source_traceability_not_detected",
  "category": "source_traceability",
  "title": "Source traceability not detected",
  "status": "not_detected",
  "severity": "medium",
  "description": "Retrieved context cannot be traced back to source documents in the final answer.",
  "affected_components": ["retriever_1", "context_builder_1"],
  "affected_edges": ["edge_003"],
  "evidence_ids": ["ev_010", "ev_011"],
  "recommended_next_checks": [
    "確認 retriever output 是否保留 source metadata。",
    "確認 final answer/API response 是否輸出 sources/citations。"
  ]
}
```

Rules:

- `readiness_report.json.findings[]` 使用固定 shape；不得讓每種 finding 自行定義欄位。
- 每個 finding 必須有 `finding_id`、`category`、`title`、`status`、`severity`、
  `description`。
- 每個 finding 必須至少有 `evidence_ids`，或明確寫 `evidence_gap` 說明缺口是
  evidence absence 而非 scanner omission。
- 不允許只有自然語言、沒有 evidence reference 或 evidence gap。
- `source_traceability` 在 Phase2 預設 `severity = "medium"`。
- `recommended_next_checks` 是給使用者下一步確認，不是要求使用者重新判斷整個 scanner
  結果。

#### 2026-07-03 confirmed sub-decision: Source traceability finding

Decision: `citation / source mapping` 不屬於 legacy RAG slot/check；它是交付前 readiness finding，category 為
`source_traceability`，中文顯示為 **來源可追溯性**。

Meaning:

- 有 citation / source mapping：代表 answer path 保留足夠 metadata，可讓使用者回到
  source document、chunk、page、URL 或 node。
- 沒有 citation / source mapping：不代表不是 RAG；只代表交付前缺少來源可追溯性
  evidence。

Scanner should inspect:

- Retrieval result models / objects 是否保留 `source`、`metadata`、`document_id`、
  `doc_id`、`chunk_id`、`node_id`、`page`、`page_number`、`url`、`uri`、`file_path`、
  `source_id` 等欄位。
- Loader / parser / chunker 是否把 source metadata 寫入 Document / Node / chunk。
- Vector store / index upsert 是否把 metadata 一起寫入。
- Retriever output 是否把 metadata 帶到 downstream context builder。
- Context / prompt assembly 是否保留 source markers、chunk ids、document ids 或 metadata，
  而不是只把 raw text 拼進 prompt。
- Response / answer builder 是否輸出 `citations`、`sources`、`references`、
  `source_documents`、`context_docs`、`nodes`、`metadata` 或等價欄位。
- Workflow JSON/YAML 是否有 citation/source/reference node、output schema、answer composer
  或 source mapping configuration。
- API response schema、Pydantic model、TypeScript type 或 JSON sample 是否包含 sources /
  citations 類欄位。

Status rules:

- `detected`：retrieval/context/answer path 至少有一條 evidence-backed metadata path，
  且 final answer or API output 有 source/citation/reference 類欄位。
- `undetermined`：retrieval result 或 documents 有 metadata，但 scanner 無法證明 metadata
  會一路進入 final answer/API output。
- `not_detected`：沒有找到 source metadata preservation，也沒有找到 final answer 的
  source/citation/reference output。

Readiness / severity rules:

- 在 `readiness_report.json.findings[]` 產生 `source_traceability` finding。
- Phase2 預設 severity 固定為 `medium`。
- Phase2 不做 domain-sensitive severity escalation；升級規則延後到後續 phase。
- 不得把缺少 citation/source mapping 解讀成 repo type 或 legacy RAG check failure。

Output:

- finding id: `source_traceability_not_detected` 或
  `source_traceability_undetermined`。
- location: `readiness_report.json.findings[]`。
- affected outputs: report / frontend readiness panel only；不得反向修改 canonical map。
- evidence: 必須引用 component ids、edge ids、evidence ids；不能只用文字推論。

`readiness_finding_change` meaning:

- 不是讓使用者手動修改 `readiness_report.json`。
- Scanner 應在 memory 裡做 counterfactual diff：對同一 ambiguous item 套用 candidate A/B，
  重跑 readiness engine，檢查 readiness findings 是否新增、移除、status/priority/severity
  改變。
- 例如某段 evidence 可能是 `retriever`，也可能只是 general helper；若選 `retriever`
  會讓 `retrieval_not_detected` finding 消失，則此 item 具備 readiness finding impact。

Topology change 判斷:

- Topology change 只能由 backend deterministic facts、static execution artifacts 與
  evidence refs 支撐；frontend 不得自行從 node label 或畫布位置推論 topology。
- 需要掃描的資訊包含：
  source code / AST、import/call/class/function patterns、dependency files、configuration
  files、workflow JSON/YAML nodes and edges、API/CLI/worker entrypoints、static call graph、
  shallow dataflow hints 與 evidence table。
- 下列 diff 才算 topology impact：
  component canonical type/layer 改變、edge 改變、main execution path 改變、agent/router/tool
  control relation 改變，或 `primary_map_type` derived summary 會改變。
- `primary_map_type` 仍只能是 readiness/report summary，不得寫回 canonical truth。

Initial high-impact rule:

```text
Only ambiguous item enters review scoring.

review_score =
  output_artifact_impact_score
+ topology_impact_score
+ uncertainty_signal_score

default_threshold = 40
```

Initial weights:

| Signal | Points | Meaning in AI-Mind |
|---|---:|---|
| `retrieval_grounding_finding_change` | 30 | 會改變 retrieval / grounding / source traceability 相關 readiness finding |
| `readiness_finding_change` | 25 | 會改變 `readiness_report.json` finding 的存在、status、priority 或 severity |
| `profile_status_change` | 20 | 會改變 `profile_signals.json` capability finding 狀態 |
| `primary_map_type_change` | 20 | 會改變 report/projection 的 derived topology summary |
| `execution_path_change` | 20 | 會改變 `execution_paths.json` 的主要 static inferred path |
| `edge_or_control_relation` | 15 | ambiguous item 是 edge/control relation，不只是孤立 component |
| `critical_component_neighbor` | 10 | 連到 agent、router、tool selector、retriever、context builder、llm 等核心元件 |
| `low_evidence_strength` | 10 | evidence strength 是 weak / ambiguous，而非 strong deterministic evidence |
| `close_candidate_gap` | 10 | top candidates 的規則解釋很接近，scanner 不應自動定案 |
| `conflicting_evidence` | 10 | 同一 evidence 被不同 rule 指到互斥解釋 |

Threshold rationale:

- `40` 是 Phase2 initial calibration default，不是業界標準，也不是永久產品真理。
- 它要求「至少一個重大輸出影響 + 一個不確定性或 topology 影響」才進 Review Queue。
- 例：`retrieval_grounding_finding_change` + `low_evidence_strength` = 30 + 10 = 40，
  應進 Review Queue。
- 例：`execution_path_change` + `edge_or_control_relation` + `close_candidate_gap`
  = 20 + 15 + 10 = 45，應進 Review Queue。
- 例：只有 `low_evidence_strength` + `close_candidate_gap` + `conflicting_evidence`
  = 30，但沒有核心 output impact，應留在 warnings / `evidence_table.json`，不進 Review Queue。

Contract boundary:

- Numeric review score 只可作 Review Queue ranking、debug 或 Plan 14 calibration。
- Numeric confidence 仍不得進 canonical/profile contracts；若 frontend 需要顯示，應顯示
  reason labels、impact category、affected outputs 與 evidence refs，而不是把 score 當成
  使用者要相信的結論。
- Plan 14 benchmark 應校準 threshold，使 median Review Queue size 保持小而有用，並驗證
  major readiness/profile/execution diffs 不被漏掉。

## Questions Closed By Current Plans

| 舊問題 | 關閉原因 |
|---|---|
| 產品是否與 Langflow 做 builder 競爭 | 已定為 inspector/readiness scanner |
| Profile 是否要使用互斥分類 | 已定為 stackable overlays |
| 是否加入五態 status | 已定為 `detected / partial / undetermined / not_detected / conflicted` |
| 是否加入 confidence score | 禁止 |
| 使用者是否先 review 才能看結果 | 否；scanner 先產生結果 |
| Sidecar 缺失是否阻塞 viewer | 否；一般 load degraded |
| TOML 是否擁有 trigger logic | 否；Python 擁有 logic |
| Execution map 是否等於 runtime trace | 否；static inferred 與 runtime observed 分離 |
| 是否把所有 outputs 塞進單一 JSON | 否；獨立 sibling artifacts |
| 是否立刻移除 v1 | 否；先 00A/13/14，再 15 |
| Apply 是否重新掃描 repo | 否；沿用同一 `scan_id` snapshot 建立新 `build_id` |
| Apply 是否需要專用 build logic | 否；API 名稱用 apply，內部仍呼叫共用 Map Build pipeline |
| Phase2 是否先導入 database | 否；先用 local JSON persistence，後續只替換 repository adapter |
| Step 3 是否仍以 KAI TOML providers 為主 | Phase A 是；Gate-1 後 Phase B 才切 UA-primary + parity，Plan 18 後 Phase C UA-only |
| Apply 是否重跑 UA | 否；只重放同 `scan_id` 的 `ScanSnapshot.scan_result`，internal `ua-analysis-result` 保持不變且不消費；Rescan 才在 Phase B/C 重跑 UA |
| Step 6 是否需要 AI orchestrator | Phase2 否；Plan 17 deferred，Step 6 維持純 Python deterministic |
| semantic sidecar 是否進 public artifact/frontend contract | 否；reserved nullable scan internal slot，Phase2 active path 不產生、不消費 |
| 是否採用 UA `knowledge-graph.json` / dashboard | 否；KAI canonical 與 projection 不變 |

## Review Triggers

只有發生以下變更才重開相關決策：

- `ai-system-map/v2` 或 `profile-signals/v1` schema 變更。
- 15 個 profile registry ids 增刪或 status enum 變更。
- artifact list、same-run lifecycle 或 database table boundary 變更。
- viewer degraded-load 改成 hard-block。
- Review scanner suggestions / manual decision lifecycle 從 optional 改成 blocking。
- static execution 企圖宣稱 runtime verified。
- LLM assist 可以建立 canonical facts 或提升 status。
- Step 3 UA sidecar call chain、fail-closed policy 或 Plan 14/18 parity-retirement gate 變更。
- Plan 17 被重新納入 Phase2 critical path 或 AI semantic candidate 取得五態定案權。
- semantic sidecar 被加入 public artifact set 或 frontend public contract。
- 不得將 Apply 改成重跑 UA、讓 Apply 消費 internal UA sidecar，或不重放同 `scan_id` 的 `ScanSnapshot.scan_result`。
- 00A、13、14、15 migration gate 順序變更。

## Decision Order

目前不再需要重開 legacy baseline readiness 命名問題；該產品概念已移除。若實作前又出現新的
contract conflict，只需依序處理：

1. OD-2026-07-03-02：same-run publish/failure policy。
2. OD-2026-07-03-01：是否先跑非正式 smoke import。
3. OD-2026-07-03-04：fixtures 的 durable ownership。
4. OD-2026-07-06-01：收斂 active assessment surface。
5. OD-2026-07-03-03：overall readiness wording，可延後到 report UI 前。

2026-07-07 的 UA integration questions 已由 OD-2026-07-07-01 關閉，不再列入 open decision order。

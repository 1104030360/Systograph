# Static Call Graph 與 Execution Path MVP 實作計畫

> **For agentic workers:** 本計畫雖放在 `dynamic-trace-plan/`，但實作的是
> **static inferred execution mapping**，不是 runtime tracing。使用
> `superpowers:test-driven-development` 逐 task 執行；不得啟動 target repo 或發送
> runtime requests。

**Goal:** 讓 AI-Mind P0 從 component inventory 升級為 evidence-backed inferred execution
map，輸出 bounded static `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、
`evidence_table.json` 與 `execution_map.mmd`。

**Architecture:** 以 deterministic scanner facts、Python AST、shallow import resolution、
workflow JSON nodes/edges 與既有 `AiSystemMapV2` components/edges 為輸入。Call graph、
dataflow 與 execution path 都是 derived artifacts，必須標示 static-only limitations 與
`runtime_verified=false`，不得寫回 canonical `ai_system_map.json`。

**Tech Stack:** Python 3.11、`ast`、Pydantic v2、JSON Schema、pytest、現有
`CodePathScanService`、`EndpointDetectionService`、`FlowDerivationService`、
`OutputArtifactProvider`。

---

## 執行摘要

### 目標

建立 P0 architecture-oriented call graph、shallow dataflow 與 execution path recoverer，
讓使用者看得出 query 可能如何經過 entrypoint、handler、retriever、reranker、context builder、
LLM 與 output。

### 背景

補充計劃明確指出 P0 不應只列出 retriever / LLM / vector store；它要提供
evidence-backed inferred execution map。但 P0 也不承諾 runtime 100% 正確，因為實際 path
仍受 route、config、dependency injection、agent decision 與 input state 影響。

### 目前 code 狀態

- `CodePathScanService` 目前只做 bounded call-like hints，供 detail scan 使用。
- `EndpointDetectionService` 可從 config/compose/code facts 建 endpoint evidence。
- `FlowDerivationService` 仍偏 template slot order，不是 source-level call graph。
- 尚無 typed `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 或
  `execution_map.mmd` artifact lifecycle。

### 相關檔案

- Create: `src/systograph/core/models/static_execution.py`
- Create: `src/systograph/core/services/static_call_graph_service.py`
- Create: `src/systograph/core/services/shallow_dataflow_service.py`
- Create: `src/systograph/core/services/execution_path_recovery_service.py`
- Create: `src/systograph/core/renderers/execution_mermaid_renderer.py`
- Modify: `src/systograph/core/services/code_path_scan_service.py`
- Modify: `src/systograph/core/services/endpoint_detection_service.py`
- Modify: `src/systograph/core/services/flow_derivation_service.py`
- Modify: `src/systograph/core/providers/output_artifact_provider.py`
- Modify: `src/systograph/core/services/map_build_service.py`
- Test: `tests/unit/core/test_static_call_graph_service.py`
- Test: `tests/unit/core/test_shallow_dataflow_service.py`
- Test: `tests/unit/core/test_execution_path_recovery_service.py`
- Test: `tests/unit/core/test_execution_mermaid_renderer.py`
- Test: `tests/integration/test_static_execution_artifacts.py`

### 實作步驟

先定義 artifact models 與 schema，再從 entrypoints / AST calls / workflow JSON edges
建立 bounded call graph；接著做 same-function shallow dataflow hints，最後 recover ordered
execution paths 並寫入 artifacts / Mermaid。

### 驗收標準

- [ ] P0 build 可在同一 output run 產生 `call_graph.json`、`dataflow_hints.json`、
  `execution_paths.json`、`evidence_table.json`、`execution_map.mmd`。
- [ ] 每個 call edge、dataflow hint、execution step 都有 evidence ids 或明確
  `not_detected/undetermined` reason。
- [ ] 所有 artifacts 都標示 static-only limitations；不得使用 `executed`、`traversed`
  或 runtime proof 語意。
- [ ] 不啟動 target app、不安裝 target dependencies、不對外發送 request。

### 風險與注意事項

Call graph 很容易膨脹成 whole-program static analysis。本計畫只做 architecture-oriented
bounded extraction：same-file call、simple cross-file import call、route -> handler、
handler -> service/pipeline、LangGraph / workflow JSON 明確 edge。複雜 dynamic dispatch、
dependency injection、reflection 與 agent runtime decision 一律以 limitations 表示。

## Contract

### Status 與 inferred 語意

Phase2 canonical/profile status 仍固定：

```text
detected
undetermined
not_detected
```

補充計劃中的 `inferred` 在本計畫中不作為 canonical/profile status。Static execution artifacts
可使用以下欄位表達推導性：

```json
{
  "status": "undetermined",
  "inference_kind": "static_inferred",
  "evidence_strength": "indirect",
  "analysis_depth": "same_file_dataflow",
  "runtime_verified": false,
  "limitations": ["Static analysis only.", "Runtime execution not confirmed."]
}
```

### Artifact shape

最小 artifact set：

```text
call_graph.json
dataflow_hints.json
execution_paths.json
evidence_table.json
execution_map.mmd
```

這些是同一 run directory 底下的獨立 sibling artifacts，不是包在
`ai_system_map.json` 裡的 nested sections。`ai_system_map.json.evidence[]` 是 canonical
map 內的 evidence refs；`evidence_table.json` 是獨立、可查詢、可日後落 DB table 的
flattened evidence artifact。

每個 JSON 必須包含：

- `schema_version`
- `source_schema_version`
- `project`
- `generated_from_build_id`
- `runtime_verified=false`
- `limitations[]`
- 對 `ai_system_map.json.evidence[]` 的 evidence refs

## Implementation Tasks

### Task 1：Static execution models 與 schema

- [ ] 新增 `StaticCallGraph`, `StaticCallEdge`, `DataflowHint`, `ExecutionPath`,
  `ExecutionStep`, `ExecutionArtifactBundle` models。
- [ ] 新增 `EvidenceTable` / `EvidenceTableRow` models 與 schema；rows 以
  `evidence_id` 作 primary key candidate，包含 artifact type、project-relative path、
  line range、JSON pointer、rule id、extract/snippet summary、source artifact refs。
- [ ] 所有 refs 使用 v2 component/edge/evidence ids；v1 refs 只能透過 00A adapter 進入。
- [ ] Contract tests 驗證缺 evidence id、unknown component ref、`runtime_verified=true`
  都會 fail closed。
- [ ] Contract tests 驗證 `evidence_table.json` 是獨立 artifact path，不允許只依賴
  `ai_system_map.json.evidence[]` 取代輸出檔。

### Task 2：Entrypoint 與 route-to-handler extraction

- [ ] 擴充 existing endpoint detection 或新增 entrypoint adapter，支援 FastAPI、Flask、
  CLI `main.py` / `if __name__ == "__main__"`、LangGraph compiled graph start、workflow JSON
  start node。
- [ ] Endpoint/entrypoint evidence 使用 project-relative path、line number 或 JSON pointer。
- [ ] 不把 Docker/network endpoint 當成 query entrypoint，除非有 route/handler evidence。

### Task 3：Architecture-oriented call graph

- [ ] 從 Python AST 抽 same-file function/method call。
- [ ] 支援簡單 import resolution：`from x import y`、`import x` 後的 direct call。
- [ ] 支援 route -> handler、handler -> service/pipeline、LangGraph `add_edge` /
  `add_conditional_edges`、workflow JSON nodes/edges。
- [ ] 設定 bounds：max files、max functions、max edges、max evidence snippets。

### Task 4：Shallow dataflow hints

- [ ] 在同一 function 內追 `query -> retriever.invoke`、retriever output -> reranker、
  docs/context -> prompt builder、prompt -> LLM、LLM output -> response。
- [ ] 只做 assignment / return-to-argument / obvious variable flow；不做 interprocedural dataflow
  engine。
- [ ] 若只能看到 dependency/name signal，status 保持 `undetermined`。

### Task 5：Execution path recoverer

- [ ] 將 entrypoints、call graph、dataflow hints、canonical components/edges 組成 ordered
  execution paths。
- [ ] Step role 使用固定 vocabulary：`entrypoint`, `handler`, `pipeline`, `retrieval`,
  `reranking`, `context_construction`, `generation`, `output`, `agent_control`,
  `query_rewrite`, `evaluation`。
- [ ] 無法排序時輸出 partial path + limitations，不硬湊完整 RAG pipeline。

### Task 6：Artifact lifecycle 與 renderer

- [ ] `OutputArtifactProvider` 增加 deterministic paths 與 writers。
- [ ] `MapBuildService` 在 canonical v2 validation 後寫 derived execution artifacts。
- [ ] `OutputArtifactProvider.write_evidence_table(...)` 從同一 validated evidence store
  寫出 `evidence_table.json`，並保持 stable ordering。
- [ ] `ExecutionMermaidRenderer` 輸出 `execution_map.mmd`，優先用 sequence diagram 或簡潔
  flowchart；不得取代 `system_map.mmd`。
- [ ] Markdown report 加一節 static execution summary，語意使用 "appears to flow" /
  "static evidence suggests"，不得寫 "runtime executed"。

### Task 7：Fixtures 與 validation

- [ ] 新增 fixtures：FastAPI RAG、plain CLI RAG、LangGraph agentic RAG、workflow JSON。
- [ ] Plan 14 direct import targets 至少抽兩個 bounded execution path regression。
- [ ] `git status --short` 驗證 scanner 對 target repo read-only。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_static_call_graph_service.py -q
.venv/bin/pytest tests/unit/core/test_shallow_dataflow_service.py -q
.venv/bin/pytest tests/unit/core/test_execution_path_recovery_service.py -q
.venv/bin/pytest tests/unit/core/test_execution_mermaid_renderer.py -q
.venv/bin/pytest tests/integration/test_static_execution_artifacts.py -q
.venv/bin/ruff check src/systograph/core/services src/systograph/core/models src/systograph/core/renderers
.venv/bin/mypy src
```

## 相依關係

- 需要 `00A` normalized v2 contract。
- 需要 `03` artifact lifecycle pattern 與 `05` lookup primitives。
- 必須在 `14` final validation 前完成，因為 Plan 14 需要驗證 execution artifacts。
- Dynamic `01` runtime trace 可以消費這些 ids 做 component ref resolution，但不得把 static
  inferred path 當 runtime proof。

## 不在範圍內

- 不做 whole-program call graph 或 CodeQL 等級 dataflow。
- 不啟動 target app、不做 runtime tracing、不發送 query。
- 不做 OpenTelemetry、trace persistence 或 replay UI。
- 不把 execution artifacts 寫回 `ai_system_map.json`、`profile_signals.json` 或 manual
  mapping storage。

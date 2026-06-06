# Task 18: Implement Viewer Session Graph Projection

## Research 查證修正（2026-06-06）

本節承接使用者 research，並依目前前端程式碼與外部來源校正 Task 18 的實作邊界。

### 已查證正確的方向

- 「後端輸出語義 graph、前端負責 layout/interaction」是正確方向。目前前端 `frontend/src/utils/graph.ts` 已用 React Flow + ELK 在前端把 nodes/edges 排版成畫布座標；React Flow 官方文件也把 layouting 視為由 dagre/ELK 等外部 layout 工具在前端處理的工作。後端 `GraphViewModel` 因此不得輸出 `x` / `y` / `position`。
- Prefect 可以作為「workflow graph response schema」的概念參考。Prefect `prefect.server.schemas.graph` 的 `Node` / `Edge` / `Graph` 模型表達 flow/task run、parents/children、state/artifacts 等拓撲與狀態資料，沒有畫布座標。這支持 Task 18 的 graph projection 只輸出 topology/state semantics。
- LangGraph 可以作為「節點、邊、狀態流轉」的概念參考。LangGraph 官方文件以 `StateGraph.add_node()` / `add_edge()` 建構 state graph，node 回傳 state updates，並可用 `get_graph().draw_mermaid_png()` 視覺化；可參考其把 graph wiring 與 runtime state 分開的邊界，但不要把 LangGraph 的 agent runtime model 搬進 KAI-Mind。
- Marquez 可以作為「lineage/provenance id」的概念參考。Marquez lineage API 用 `nodeId` 查 lineage graph，回傳 graph node id、node type、inEdges/outEdges；Task 18 應採同樣可追溯精神，但使用 KAI-Mind canonical `source_id`、`evidence_ids`、`risk_hint_ids`，而不是引入 Marquez dataset/job namespace。
- FastAPI route 使用 `response_model` / Pydantic response model 仍是正確做法。官方文件說 `response_model` 會做 response 文件、驗證、轉換與過濾；Task 18 的 route handler 應只做 request schema 轉換、呼叫 service、回 typed payload。

### 需要修正的研究結論

- invalid map 的錯誤狀態不是放在 `GraphViewModel.loaded`。目前前端 `frontend/src/types.ts` 與 `frontend/API_CONTRACT.md` 明確要求 `loaded` / `error_reason` 位於 `viewer_load_result` 層：

```text
viewer_load_result
├─ loaded
├─ error_reason
├─ ai_system_map
└─ graph_view_model
```

因此 `GraphViewModel` 應保持 rendering projection；載入狀態由 `ViewerLoadResult.loaded` / `error_reason` 表達。invalid map 時 HTTP 可回 200 且 payload `viewer_load_result.loaded=false`，這是 KAI-Mind frontend contract 的 graceful degradation，不是 Prefect 的直接規範。

- `ViewerSessionService` 可以提供 `load_map(path)` 讀取並 validate `ai_system_map.json`，但真正的 projection 函式必須保持無 FastAPI dependency、無 provider dependency、無重新掃描 project folder。換句話說：讀檔/validate 是 viewer session load 邊界；`project_to_graph(canonical_map)` 才是純 projection 邊界。

- `source_id` 不只給 node，也要給 edge。前端 `makeGraphIndexes()` 會把 node/edge 的 `id` 與 `source_id` 都建立索引，SSE progress / replay 會依 `node_id`、`edge_id`、`component_id`、`source_id`、`slot` 尋找 highlight 目標。

### 外部查證來源

- Prefect graph schema：`https://docs.prefect.io/v3/api-ref/python/prefect-server-schemas-graph` 與 `https://raw.githubusercontent.com/PrefectHQ/prefect/main/src/prefect/server/schemas/graph.py`
- LangGraph graph API：`https://docs.langchain.com/oss/python/langgraph/use-graph-api`
- Marquez lineage API：`https://marquezproject.ai/docs/api/get-lineage/`
- React Flow layouting：`https://reactflow.dev/learn/layouting/layouting`
- React Flow Node type：`https://reactflow.dev/api-reference/types/node`
- FastAPI response model：`https://fastapi.tiangolo.com/tutorial/response-model/`

## 目標
實作 `ViewerSessionService` 與 local web viewer API，將 canonical `ai_system_map.json` 轉成 GUI 可消費的 `GraphViewModel`。Graph projection 只表達 backend domain semantics，不做前端 layout。

## 為什麼要先做這個
設計文件明確決定 `GraphViewModel` 由 backend 轉，frontend 只渲染。因為 Epic 1 優先 GUI/local web UI，本任務要直接提供 viewer API，避免前端自行讀 JSON 後重做 backend 判斷。

## 承接 Task 16 延後功能
- 承接 Task 16 「不實作完整 `ViewerSessionService` graph projection」與「不做 viewer command」的延後範圍。
- Task 16 的 `GraphViewModel` 只允許是 minimal shell；本任務要把它升級成完整 projection。
- 若 Task 16 已建立 `GET /api/map` / `GET /map` minimal wrapper，本任務要保留 endpoint 相容性，只替換內部 projection service，不破壞 `frontend/src/types.ts`。
- viewer command / map validate CLI 若在本任務補上，只能呼叫 `ViewerSessionService`，不得直接讀 raw JSON 後自行推 graph。

## 前置需求
- Task 15 已完成 map validation。
- Task 16 已能產生 map JSON。
- Task 17 已確認 artifact output 流程。

## 實作範圍
- 建立 `GraphViewModel` models。
- 建立 `ViewerSessionService.load_map()`。
- 使用 FastAPI 建立 local web viewer route / handler。
- 更新 Epic 1 local API guide，加入 viewer graph endpoint、request/response、invalid map error state。
- 載入 map 後再次 validate。
- 將 components、extensions、unmapped、flows、risk hints 轉成 nodes/edges/details。
- 確保每個 node/edge/detail 都能追回 canonical `source_id` / evidence id。
- invalid map 回傳 `viewer_load_result.loaded=false` 與 `error_reason`；`GraphViewModel` 本身只保留 rendering projection 欄位。
- Local web API 完成後，可補 CLI `viewer` / map validate thin adapter；CLI 只能呼叫同一個 `ViewerSessionService`。

## 不包含範圍
- 不做實際 GUI。
- 不做 zoom/pan/drag。
- 不重新掃描 project folder。
- 不做 filter UI，只提供可 highlight 的 metadata。
- 不做 CLI viewer command 的完整 UX；若補 CLI，只做 validate/load result。
- 不在 backend graph node/edge 輸出 `x`、`y`、`position` 或 ELK/React Flow layout 狀態。

## 建議實作步驟
1. 建立或補齊 `src/kai_mind/core/models/graph_view.py`。若 Task 16 已有 `core/models/viewer.py`，此檔可作為相容 re-export，避免破壞既有 import 與前端 schema。
2. 建立 `src/kai_mind/core/services/viewer_session_service.py`。
3. 實作 map JSON load + validation。
4. 實作 standard slot component nodes。
5. 實作 extension/unmapped nodes。
6. 實作 flow edges 與 details lookup。
7. 建立 FastAPI viewer route，回傳 `ViewerPayload`；valid map 時更新 latest session，invalid map 時也用 `loaded=false` payload 更新 session，避免前端只看到空白畫布。
8. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補上 viewer graph API 與 invalid map response 範例。
9. 可選補上 CLI viewer/map validate thin adapter，輸出 loaded/error status。
10. 寫測試：valid map loaded、invalid map error、viewer 不呼叫 providers、API 不掃 project folder。

## 預期輸出
- `src/kai_mind/core/models/graph_view.py`
- `src/kai_mind/core/services/viewer_session_service.py`
- `src/kai_mind/web/routes/viewer_routes.py`
- `src/kai_mind/cli/viewer_command.py` 或等價 validate command
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_viewer_session_service.py`
- `tests/web/test_viewer_routes.py`
- `tests/cli/test_viewer_command.py` 或等價 CLI validate test

## 驗收標準
- valid JSON 產生 graph nodes/edges/details。
- invalid JSON 回傳 `loaded=false` 與 error_reason。
- unmapped component 顯示 `needs_confirmation`。
- filter metadata 可支援 highlight，不移除 graph elements。
- local web viewer API 不直接讀 project folder，只讀 map JSON / validated map input。
- API guide 已同步記錄 viewer graph API、invalid map error state、response 欄位用途。

## 可能風險與注意事項
- GraphViewModel 不能變第二份 truth；所有欄位都要可追回 canonical JSON。
- 不要把 frontend layout 決策放進 backend。
- Viewer load invalid JSON 時不應顯示空白 graph。
- invalid map 的 `loaded=false` / `error_reason` 必須在 `viewer_load_result` 層，不能漂移到 `graph_view_model` 層。
- 若 `GraphViewModel` response 欄位變更，必須同步更新 API guide，避免 frontend / desktop app 用錯 contract。

## 新手提示
Graph projection 是把 JSON 排成前端好畫的形狀，不是重新理解專案。

## 視覺化說明
```text
┌──────────────────────┐
│ ai_system_map.json    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Validate again        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ViewerSessionService  │
└──────┬────────┬──────┘
       │        │
       ↓        ↓
┌──────────────┐ ┌──────────────┐
│ Graph nodes  │ │ Graph edges  │
└──────────────┘ └──────┬───────┘
                        ↓
┌──────────────────────┐
│ Details evidence/risk │
└──────────────────────┘
```

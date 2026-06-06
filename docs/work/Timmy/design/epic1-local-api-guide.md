# Epic 1 Local API Guide

## 讀法

這份文件是 Local API 的協作契約。FastAPI OpenAPI 可以輔助產生欄位文件，但這份 Markdown 保留設計意圖、local-only 安全原則、frontend viewer payload 規則，以及未來 Task 18/21/22 的 API 邊界。

```text
GUI / Desktop / CLI
        ↓
Local API / CLI adapter
        ↓
MapBuildService
        ↓
validated ai_system_map.json
        ↓
ViewerSessionService
        ↓
viewer_load_result.graph_view_model
```

## Local-Only 原則

- 預設 server bind 應只使用 `127.0.0.1`。
- 預設 CORS allowlist 只允許 `http://127.0.0.1:5173` 與 `http://localhost:5173`。
- 不使用 `allow_origins=["*"]` 作為本地 scanner API 預設。
- API 只接受 local path project import；不支援 upload / zip / multipart。
- Scanner 行為沿用 core providers 的 read-only 與 skip policy，不因 API request 放寬大檔、binary、model weights、dependency dirs 的掃描限制。

## Canonical Truth

`ai_system_map.json` 是唯一 canonical scanner truth。它只包含 `ai-system-map/v1` 的掃描事實、evidence、endpoints、flows、risk hints 與 recommended next checks。

`viewer_load_result` 與 `graph_view_model` 是 API/viewer projection，不能寫進 `ai_system_map.json`。

## POST /api/map/build

用途：一次性 local demo / development flow。送入 project path 後觸發 L1 map build，寫出 artifact，並回傳 build result 與 viewer wrapper。

Request:

```json
{
  "project_path": "/absolute/or/local/project/path",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false
}
```

Response:

```text
MapBuildResult
├─ status: ok | error
├─ project_name
├─ output_run_dir
├─ map_json_path
├─ map_markdown_path
├─ map_error_path
├─ viewer_load_result
├─ ai_system_map
├─ warnings[]
└─ error
```

規則：

- `status="ok"` 時必須有 `map_json_path`、`map_markdown_path`、`viewer_load_result` 與 `ai_system_map`。
- `status="error"` 且 precondition 有可寫 output run 時，寫出 `map-error.md`，不寫 normal map。
- 已存在 artifact 時，輸出到 timestamped run directory。
- Route handler 不做 scanner logic，只轉換 request 並呼叫 `MapBuildService`。

## GET /api/map

用途：frontend API mode 載入目前 session 最新 viewer payload。

Fallback:

```http
GET /map
```

Response:

```json
{
  "viewer_load_result": {
    "loaded": true,
    "error_reason": null,
    "map_json": "{...}",
    "ai_system_map": {},
    "graph_view_model": {
      "schema_version": "graph-view-model/v1",
      "source_schema_version": "ai-system-map/v1",
      "nodes": [
        {
          "id": "node:component:component-vector-store-qdrant",
          "source_id": "component:vector_store:qdrant",
          "type": "vector_db",
          "slot": "vector_store",
          "status": "detected",
          "label": "Qdrant",
          "subtitle": "Vector Store",
          "badges": ["detected", "vector_db"],
          "evidence_ids": ["evidence:docker:qdrant-service"],
          "risk_hint_ids": []
        }
      ],
      "edges": [
        {
          "id": "graph:edge:query_answer:retriever:vector_store",
          "source_id": "edge:query_answer:retriever:vector_store",
          "flow_id": "flow:query_answer",
          "from": "node:component:component-retriever-qdrant-retriever",
          "to": "node:component:component-vector-store-qdrant",
          "relationship": "queries_vector_store",
          "label": "Queries Vector Store",
          "evidence_ids": ["evidence:code_pattern:retriever"],
          "risk_hint_ids": []
        }
      ],
      "details": {
        "evidence_by_id": {},
        "risk_hints_by_id": {}
      },
      "filters": {
        "available": [],
        "behavior": "highlight"
      }
    }
  }
}
```

Graph rules:

- `graph_view_model` 是 rendering projection，不是 canonical truth。
- Node/edge 都可帶 `source_id`，對應 canonical component、slot、extension、unmapped component 或 edge id。
- Node/edge 不輸出 `x`、`y`、`position`；React Flow + ELK 在 frontend 做 layout。
- `details.evidence_by_id` 與 `details.risk_hints_by_id` 是 id lookup table，供 detail panel 使用。
- `filters.available` 只提供 highlight metadata，不要求 frontend 移除 graph elements。

尚未 build 前，API 仍回傳 contract-compatible payload：

```json
{
  "viewer_load_result": {
    "loaded": false,
    "error_reason": "no_map_loaded",
    "ai_system_map": {},
    "graph_view_model": {
      "nodes": [],
      "edges": [],
      "details": {
        "evidence_by_id": {},
        "risk_hints_by_id": {}
      },
      "filters": {
        "available": []
      }
    }
  }
}
```

## POST /api/viewer/load

用途：載入一份已存在的 `ai_system_map.json`，再次 validate 後轉成目前 session 最新 viewer payload。這個 endpoint 不掃描 project folder，也不呼叫 scanner providers。

Request:

```json
{
  "map_json_path": "outputs/ai_system_map.json"
}
```

Valid response:

```json
{
  "viewer_load_result": {
    "loaded": true,
    "error_reason": null,
    "map_json": "{...}",
    "ai_system_map": {},
    "graph_view_model": {
      "schema_version": "graph-view-model/v1",
      "source_schema_version": "ai-system-map/v1",
      "summary": {
        "project_name": "sample-health-rag",
        "scan_depth": "system",
        "node_count": 15,
        "edge_count": 9
      },
      "nodes": [],
      "edges": [],
      "details": {
        "evidence_by_id": {},
        "risk_hints_by_id": {}
      },
      "filters": {
        "available": [],
        "behavior": "highlight"
      }
    }
  }
}
```

Invalid map response still uses HTTP 200 so the local viewer can render an explicit broken-map state instead of crashing:

```json
{
  "viewer_load_result": {
    "loaded": false,
    "error_reason": "invalid_map: Field 'confidence' is not allowed at $.confidence",
    "map_json": null,
    "ai_system_map": {},
    "graph_view_model": {
      "schema_version": "graph-view-model/v1",
      "nodes": [],
      "edges": [],
      "details": {
        "evidence_by_id": {},
        "risk_hints_by_id": {}
      },
      "filters": {
        "available": [],
        "behavior": "highlight"
      }
    }
  }
}
```

規則：

- `loaded=false` / `error_reason` 位於 `viewer_load_result`，不是 `graph_view_model`。
- Valid 或 invalid load 都會更新 latest `/api/map` payload。
- `map_json_path` 只代表 map artifact load；不得拿它重新掃描 project folder。
- CLI `validate-map` 使用同一個 `ViewerSessionService`，只做 thin adapter。

## GET /api/map/report

用途：frontend 直接檢視目前 session 最新的 Markdown report。這個 endpoint 讀取 `POST /api/map/build` 成功後保存於 latest build result 的 `map_markdown_path`，不接受任意 filesystem path。

View:

```http
GET /api/map/report
```

Download:

```http
GET /api/map/report?download=true
```

Response:

```text
Content-Type: text/markdown; charset=utf-8

# KAI-Mind System Map
...
```

下載模式會增加：

```text
Content-Disposition: attachment; filename="ai_system_map.md"
```

規則：

- Markdown report 是 human-readable report view，不是 schema source。
- Canonical scanner truth 仍然只有 `ai_system_map.json`。
- Endpoint 只讀 latest session 的受控 `map_markdown_path`。
- Endpoint 不接受 `path`、`file` 或任何 raw local path 作為讀檔來源。
- 尚未 build、build 失敗、或 Markdown artifact 不存在時，回傳 HTTP 404，`detail="map_markdown_not_available"`。

## POST /api/projects/import

用途：建立 local path project session shell。

Request:

```json
{
  "source_type": "local_path",
  "project_path": "/Users/example/rag-project"
}
```

Response:

```json
{
  "project_id": "project:...",
  "source_type": "local_path",
  "project_name": "rag-project",
  "project_path": "/Users/example/rag-project"
}
```

規則：

- MVP 只接受 `source_type="local_path"`。
- 這是 in-memory session，backend process 重啟後不保留。
- Persistent session store / scan history 留 Task 26。

## POST /api/scans

用途：用已 import 的 `project_id` 啟動 L1 system scan。Task 16 MVP 採同步 build，完成後更新 `/api/map` 的 latest viewer payload。

Request:

```json
{
  "project_id": "project:...",
  "scan_depth": "system",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false
}
```

Response:

```json
{
  "scan_id": "scan:...",
  "project_id": "project:...",
  "status": "completed",
  "build_result": {}
}
```

規則：

- Unknown `project_id` 回傳 HTTP 404。
- `scan_depth` 目前只允許 `system`。
- `status` 依 `MapBuildResult.status` 對應為 `completed` 或 `error`。

## GET /api/scan/events

用途：提供 frontend progress strip 的 SSE contract。Task 16 可以只送 deterministic completed event。

Headers:

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Event:

```json
{
  "event": "scan_progress",
  "status": "completed",
  "stage": "validate",
  "message": "Scan completed.",
  "percent": 100,
  "node_id": null,
  "edge_id": null,
  "component_id": null,
  "source_id": null,
  "slot": null,
  "evidence_id": null,
  "scan_depth": "system",
  "timestamp": "2026-06-05T..."
}
```

Frontend target priority:

1. `node_id`
2. `edge_id`
3. `component_id`
4. `source_id`
5. `slot`

IDs may be graph IDs or canonical source IDs. Frontend maps both when possible.

## Common Error Format

Precondition failure is represented inside `MapBuildResult`:

```json
{
  "status": "error",
  "map_error_path": "outputs/map-error.md",
  "error": {
    "scan_stage": "precondition",
    "project_path": "...",
    "failure_reason": "project_path_not_found"
  }
}
```

Request validation errors use FastAPI 422. Unknown imported projects use HTTP 404 with `detail`. Viewer map load failures use `viewer_load_result.loaded=false` for contract-compatible graceful degradation.

## Compatibility Rule

Any task that adds, removes, renames, or changes endpoint paths, request fields, response fields, error status, SSE event fields, or viewer payload shape must update this guide in the same change.

## 後續邊界

- Task 21: progressive L2/L3 detail scan endpoint；append-only detail evidence，不直接改 canonical facts。
- Task 22: opt-in runtime query trace；不得由 Task 16 map build 預設觸發。
- Task 25: project upload ingestion；獨立處理 archive size limit、path traversal、binary/model/dependency skip policy。
- Task 26: persistent session store / scan history；獨立處理 storage、retention、masking、migration。

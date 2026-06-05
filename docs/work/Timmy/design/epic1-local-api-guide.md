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
MinimalViewerProjectionService
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
├─ map_error_path
├─ viewer_load_result
├─ ai_system_map
├─ warnings[]
└─ error
```

規則：

- `status="ok"` 時必須有 `map_json_path`、`viewer_load_result` 與 `ai_system_map`。
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
      "schema_version": "graph-view-model/minimal-v1",
      "source_schema_version": "ai-system-map/v1",
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

Request validation errors use FastAPI 422. Unknown imported projects use HTTP 404 with `detail`.

## Compatibility Rule

Any task that adds, removes, renames, or changes endpoint paths, request fields, response fields, error status, SSE event fields, or viewer payload shape must update this guide in the same change.

## 後續邊界

- Task 18: full `ViewerSessionService` / complete `GraphViewModel` projection、filter metadata、invalid map viewer state。
- Task 21: progressive L2/L3 detail scan endpoint；append-only detail evidence，不直接改 canonical facts。
- Task 22: opt-in runtime query trace；不得由 Task 16 map build 預設觸發。
- Task 25: project upload ingestion；獨立處理 archive size limit、path traversal、binary/model/dependency skip policy。
- Task 26: persistent session store / scan history；獨立處理 storage、retention、masking、migration。

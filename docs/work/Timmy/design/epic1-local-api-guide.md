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
- Scan boundary decisions 只存在於本次 `POST /api/scans` request，不能寫回被掃描 repo、不能保存成長期偏好，也不能修改既有 artifact。

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
    "map_json": null,
    "ai_system_map": {},
    "graph_view_model": {
      "schema_version": "graph-view-model/v1",
      "source_schema_version": null,
      "map_json": null,
      "summary": null,
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
- 同一個 `project_id` 若已有 confirmed manual mappings，下一次 scan / normalize 會套用這些 decisions；API 不會直接修改既有 `ai_system_map.json`。
- Scan boundary review 內嵌在 `POST /api/scans`。若本次 scan 有未決 suspicious file，API 先回 `requires_boundary_decision`，不建立 map；使用者帶本次 `boundary_decisions` 重送後才正式掃描。

## Detail Scan Routes

用途：frontend 使用者點選 graph target 後，針對目前 loaded map 的 target-related files 做 bounded lazy loading。這是 Task 21 的 L2/L3 靜態 detail scan，不是重新掃整個 repo，也不是 runtime trace。

資料流：

```text
project_id + target_type + target
  -> latest scanned ai_system_map
  -> DetailScanService
  -> ComponentDetailScanService / CodePathScanService
  -> append evidence[] + target.evidence_ids + detail_scans[]
  -> SystemMapValidationService
  -> refresh latest /api/map viewer payload
```

### POST /api/detail-scans

Request:

```json
{
  "project_id": "project:...",
  "target_type": "unmapped_component",
  "target": "unmapped:src_router_py:route:code_pattern_custom_router",
  "scan_depth": "code_path"
}
```

Allowed `scan_depth`:

- `component`：L2，抽取 target-related Python files 的 imports、class/function signatures、decorators。
- `code_path`：L3，在 L2 基礎上加上 static call-like hints，例如 `Router.build_chain(...)`。這些 hints 一律是 `best_effort=true`，不代表 runtime path 已確認。

Allowed `target_type`:

- `component_slot` 或 alias `slot`
- `component_instance` 或 alias `component`
- `extension`
- `unmapped_component` 或 alias `unmapped`
- `edge`
- `evidence`

Response:

```json
{
  "project_id": "project:...",
  "detail_scan": {
    "id": "detail-scan:code_path:unmapped_component:...",
    "target_type": "unmapped_component",
    "target": "unmapped:...",
    "scan_depth": "code_path",
    "status": "completed",
    "best_effort": true,
    "context_limits": {
      "max_files_per_target": 4,
      "max_symbols_per_file": 24,
      "max_snippet_chars": 320,
      "best_effort": true
    },
    "findings": [
      {
        "kind": "detail_scan_call_like",
        "summary": "Static call-like hint: Router.build_chain",
        "evidence_ids": ["evidence:detail-scan:..."],
        "best_effort": true
      }
    ],
    "code_path": [
      {
        "file": "src/router.py",
        "symbol": "Router.build_chain",
        "line_start": 11,
        "line_end": 11,
        "evidence_id": "evidence:detail-scan:...",
        "best_effort": true
      }
    ],
    "warnings": []
  },
  "ai_system_map": {}
}
```

規則：

- `project_id` 不存在回傳 HTTP 404 `project_not_found`。
- `project_id` 尚未有 loaded map 回傳 HTTP 404 `map_not_loaded`。
- target id 不存在回傳 HTTP 422 `target_not_found`，且不得寫入 latest map。
- Detail scan 只讀 target 既有 evidence file / source file，不接受 client 提供 arbitrary file path。
- Detail scan 不執行目標專案、不使用 `sys.settrace`、不呼叫 runtime endpoint；runtime evidence 留給 Task 22 opt-in query trace。
- 所有 snippet / value 寫入前都必須經過 `SecretMaskingService`。
- 新 signal 必須同時追加到 `ai_system_map.evidence[]` 與 target 的 `evidence_ids`，再把 `DetailScanResult` 追加到 `detail_scans[]`。
- `MappingEvidencePacketBuilder` 只讀 canonical `evidence[]` 與 target `evidence_ids`；它不需要理解 `detail_scans[]` 結構，也不能讀 raw source file。
- 追加後整份 map 必須通過 `SystemMapValidationService.validate()`；validation 失敗時不得保存變更。

### GET /api/detail-scans/{detail_scan_id}

用途：依 detail scan id 讀回目前 session 中已完成的 detail scan 與更新後的 canonical map。

規則：

- 找不到 detail scan 時回傳 HTTP 404 `detail_scan_not_found`。
- Response shape 與 `POST /api/detail-scans` 相同。

## Query Trace Route

用途：使用者明確指定 project、endpoint 與 query 後，對 `ai_system_map.endpoints[]` 中的 endpoint id 做一次 bounded black-box runtime trace。這是 Task 22 的 opt-in replay evidence，不是 L1/L2/L3 static scan。

資料流：

```text
project_id + endpoint_id + query
  -> latest scanned ai_system_map
  -> project_path/pyproject.toml [tool.kai-mind.trace] config
  -> QueryTraceService
  -> EndpointCallProvider
  -> transient TraceRunResult
```

### POST /api/trace

Request:

```json
{
  "project_id": "project:...",
  "endpoint_id": "endpoint:local:rag-chat",
  "query": "raw query sent once to the endpoint",
  "timeout_seconds": 30
}
```

Response:

```json
{
  "trace_id": "trace:...",
  "status": "completed",
  "query_sent": true,
  "endpoint_id": "endpoint:local:rag-chat",
  "events": [
    {
      "event_type": "request_sent",
      "query_sent": true,
      "input": {
        "query": {
          "type": "string",
          "length": 32,
          "masked": "[MASKED]"
        }
      }
    },
    {
      "event_type": "response_received",
      "status": "completed",
      "output": {}
    }
  ],
  "warnings": [],
  "error_reason": null
}
```

規則：

- `project_id` 不存在回傳 HTTP 404 `project_not_found`。
- `project_id` 尚未有 loaded map 回傳 HTTP 404 `map_not_loaded`。
- `endpoint_id` 找不到時仍回 HTTP 200，但 body 為 `status="endpoint_not_found"`、`query_sent=false`，且不得送任何 HTTP request。
- timeout、transport error 或 HTTP error 回 `status="partial"`，保留 `request_sent` 與 `error` event，讓 replay 可以停在失敗點。
- `query`、response output、`retrieved_chunks` 進入 event 前必須遮蔽/摘要化；API response、CLI output、report 不保存 raw query 或 raw answer。
- retrieved chunks 欄位預設依序讀 `retrieved_chunks`、`chunks`、`documents`。若被掃描專案的 `pyproject.toml` 提供 `[tool.kai-mind.trace] retrieved_chunks_keys`，web route 會從 project session 的 `project_path` 讀取並注入 `QueryTraceService`。
- CLI 不從 map artifact 猜測專案位置；需要使用專案設定時必須顯式傳入 `--project-root /abs/path/to/scanned-project`。
- `retrieved_chunks_keys` 必須是非空字串陣列；設定存在但格式錯時 fail fast，避免 trace 看似成功但漏掉 retrieved chunks。
- Trace result 是 transient `TraceRunResult`；不得寫回 canonical `ai_system_map.query_trace_events[]`，也不得修改 `flows`、`extensions`、manual mappings 或 proposal state。
- 如果 runtime response metadata 指向已知 `unmapped_component_id`，只在 event 標示 `step_type="unknown"` 與 `needs_mapping_confirmation`，真正確認與持久化交給 manual mapping / mapping proposal。
- `POST /api/scans`、`POST /api/map/build`、`GET /api/map` 與 `POST /api/viewer/load` 不會自動觸發 query trace。

Project config example:

```toml
[tool.kai-mind.trace]
retrieved_chunks_keys = [
  "retrieved_chunks",
  "chunks",
  "documents",
  "docs",
  "retrieved_docs",
  "context",
]
```

## Manual Mapping Routes

用途：保存使用者對 `unmapped / needs_confirmation` 元件做出的 project-level decision。這些 endpoints 只寫入 KAI-Mind-managed mapping store / repository，不直接 mutate 既有 map artifact。

### GET /api/mappings

Request:

```http
GET /api/mappings?project_id=project:...
```

Response:

```json
{
  "project_id": "project:...",
  "available_actions": [
    "confirm",
    "edit",
    "reject",
    "skip_for_now",
    "mark_not_applicable"
  ],
  "mappings": [
    {
      "mapping_id": "mapping:...",
      "project_id": "project:...",
      "mapping_type": "existing_slot_mapping",
      "decision": "confirmed",
      "source_unmapped_id": "unmapped:requirements_txt:line_1:dependency_vector_store_client_chromadb",
      "source_file": "requirements.txt",
      "observed_kind": "dependency_candidate",
      "evidence_ids": ["evidence:..."],
      "target_slot": "vector_store",
      "component_name": "Chroma",
      "component_kind": "vector_db",
      "mapping_digest": "sha256:...",
      "created_at": "2026-06-07T...",
      "updated_at": "2026-06-07T..."
    }
  ]
}
```

### POST /api/mappings

Request for confirmed existing slot mapping:

```json
{
  "project_id": "project:...",
  "mapping_type": "existing_slot_mapping",
  "decision": "confirmed",
  "source_unmapped_id": "unmapped:...",
  "source_file": "requirements.txt",
  "observed_kind": "dependency_candidate",
  "evidence_ids": ["evidence:..."],
  "target_slot": "vector_store",
  "component_name": "Chroma",
  "component_kind": "vector_db"
}
```

Request for audit-only decisions:

```json
{
  "project_id": "project:...",
  "mapping_type": "existing_slot_mapping",
  "decision": "rejected",
  "source_unmapped_id": "unmapped:...",
  "source_file": "requirements.txt",
  "evidence_ids": ["evidence:..."],
  "reason": "User rejected this mapping."
}
```

Response:

```text
ManualMapping
├─ mapping_id
├─ project_id
├─ mapping_type
├─ decision
├─ source_unmapped_id
├─ source_file
├─ observed_kind
├─ evidence_ids[]
├─ target_slot / extension fields
├─ proposal_id / decision_source
├─ mapping_digest
├─ created_at
└─ updated_at
```

### PATCH /api/mappings/{mapping_id}

用途：更新既有 decision，例如把 `skip_for_now` 改成 `rejected`，或補上 reason。

Request:

```json
{
  "decision": "rejected",
  "reason": "User rejected this mapping."
}
```

規則：

- Confirmed existing slot mapping 必須引用有效 `target_slot`、`component_name` 與至少一個 `evidence_id`。
- Confirmed extension mapping 必須有 extension id/name/kind；若附 extension edge，endpoint 必須存在於已知 slot 或該 extension。
- `rejected`、`skip_for_now`、`not_applicable` 是 audit-only decision，不會產生 component、extension 或 flow edge。
- Mapping payload 不得包含 raw source code、raw AI prompt、unmasked secret-like values 或 `confidence`。
- `source_file` 必須是 POSIX relative path，不得是 absolute path 或跳出 project。
- Response 提供 `mapping_digest`，讓 report metadata / UI 可追蹤 applied decision。
- Confirmed mapping 只有在下次 scan / normalize 且 source evidence 仍存在時才會影響 canonical map。
- Route handler 只呼叫 `ManualMappingService`；不得直接讀寫 DB row、artifact JSON 或被掃描 repo。

## Mapping Proposal Routes

用途：針對目前 map 中的 `unmapped / needs_confirmation` 元件產生 pending-only 候選對應建議。Proposal 是使用者決策前的草稿，不是 canonical `ai_system_map.json` 事實。

資料流：

```text
latest ai_system_map.unmapped_components[]
  -> MappingEvidencePacketBuilder
  -> masked MappingEvidencePacket
  -> MappingProposalService
  -> deterministic candidates / optional provider
  -> pending_user_confirmation proposal
  -> user decision
  -> optional ManualMapping draft
```

### GET /api/mapping-proposals

Request:

```http
GET /api/mapping-proposals?project_id=project:...
```

Response:

```json
{
  "project_id": "project:...",
  "available_actions": ["accept", "edit", "reject", "skip_for_now"],
  "proposals": [
    {
      "proposal_id": "proposal:...",
      "project_id": "project:...",
      "source_unmapped_id": "unmapped:...",
      "status": "pending_user_confirmation",
      "provider_name": "deterministic",
      "provider_error_reason": null,
      "evidence_packet": {
        "source_file": "requirements.txt",
        "observed_kind": "dependency_candidate",
        "evidence_ids": ["evidence:..."],
        "masked_evidence_values": ["chromadb"],
        "available_slots": ["vector_store", "retriever"]
      },
      "candidates": [
        {
          "candidate_id": "candidate:1",
          "candidate_type": "existing_slot_mapping",
          "target_slot": "vector_store",
          "component_name": "Chroma",
          "component_kind": "vector_db",
          "label": "Map evidence to Vector Store",
          "rationale": "...",
          "evidence_ids": ["evidence:..."],
          "rank": 1,
          "recommendation_level": "strong_candidate",
          "uncertainty_reason": "Static evidence only."
        }
      ]
    }
  ]
}
```

### POST /api/mapping-proposals

Request:

```json
{
  "project_id": "project:...",
  "source_unmapped_id": "unmapped:...",
  "user_description": "This may be the vector store client."
}
```

規則：

- API 會從 requested `project_id` 對應的 latest scanned `ai_system_map` 找 `source_unmapped_id`，再用 canonical evidence 建立 masked `MappingEvidencePacket`；不得使用 process-wide latest scan 的其他 project evidence。
- Client 不提交 raw evidence、raw source、project root 或 provider prompt。
- 若 `project_id` 不存在，回傳 HTTP 404 `project_not_found`。
- 若尚未 scan / load map，回傳 HTTP 404 `map_not_loaded`。
- 若 `source_unmapped_id` 不存在，回傳 HTTP 404 `unmapped_not_found`。
- Proposal status 一律先是 `pending_user_confirmation`。
- Provider unavailable、timeout、HTTP error 會回到 deterministic candidates，`provider_error_reason` 使用 stable code `provider_unavailable`。
- Provider invalid JSON、`confidence` 欄位、unknown evidence / slot / edge reference、unmasked secret、超出 bounded output limits 都會被拒絕並 fallback 到 deterministic candidates，`provider_error_reason` 使用 stable code `provider_invalid_output`。
- Proposal create 不會修改 latest `/api/map` payload，也不會修改 `components_by_slot`、`extensions`、`flows`、`query_trace_events`。

### POST /api/mapping-proposals/{proposal_id}/decision

Request for accepting one candidate:

```json
{
  "decision": "accept",
  "candidate_id": "candidate:1"
}
```

Request for rejecting a proposal:

```json
{
  "decision": "reject",
  "reason": "Not part of the RAG path."
}
```

Request for editing a proposal:

```json
{
  "decision": "edit",
  "edited_mapping": {
    "project_id": "project:...",
    "mapping_type": "existing_slot_mapping",
    "decision": "confirmed",
    "source_unmapped_id": "unmapped:...",
    "evidence_ids": ["evidence:..."],
    "target_slot": "vector_store",
    "component_name": "Edited Chroma",
    "component_kind": "vector_db"
  }
}
```

Response excerpt (abbreviated; do not use this as the full frontend type):

```json
{
  "proposal": {
    "proposal_id": "proposal:...",
    "status": "accepted"
  },
  "manual_mapping": {
    "mapping_id": "mapping:...",
    "proposal_id": "proposal:...",
    "decision_source": "proposal_accept",
    "target_slot": "vector_store"
  }
}
```

規則：

- `accept` 會把候選轉成 `ManualMappingCreate`，再交給 `ManualMappingService` 驗證與保存。
- `accept` 必須提供 `candidate_id`，且不可同時提供 `edited_mapping`。
- `edit` 必須提供完整 `edited_mapping`，不可同時提供 `candidate_id`，並同樣交給 `ManualMappingService` 驗證。
- `reject` / `skip_for_now` 只更新 proposal status，不建立 manual mapping。
- `reject` / `skip_for_now` 不可帶 `candidate_id` 或 `edited_mapping`。
- 只有 `pending_user_confirmation` proposal 可以 decision；已 accepted / edited / rejected / skipped 的 proposal 再次 decision 會回 HTTP 422。
- 上方 response 是節錄；實際 FastAPI response 會包含完整 serialized `MappingProposal`，若有建立 manual mapping 則包含完整 serialized `ManualMapping`。前端型別應以 backend OpenAPI / `frontend/src/types.ts` 對齊，不要直接照這個短版 JSON 建完整 type。
- 即使 accept 成功，canonical map 仍要等同一個 `project_id` 下次 `/api/scans` / normalize 才會生效。
- Response 不得包含 unmasked secret、raw prompt、raw source 或 `confidence`。

## Scan Boundary Proposal Routes

用途：scan boundary review 已整合進 `POST /api/scans`，用 same-run gate 讓使用者在正式掃描前決定本次要不要掃 `.env`、secret-like config、vector persistence path 等 suspicious target。這不是 component mapping，也不是 template import，也不是長期 policy store。

資料流：

```text
project_id
  -> POST /api/scans builds deterministic FileInventory
  -> ScanBoundaryReviewService
  -> if unresolved: ScanCreateResponse.status = requires_boundary_decision
  -> user sends boundary_decisions in POST /api/scans
  -> ProjectScanService provider collection
  -> MapBuildService writes map artifacts
```

### POST /api/scans boundary decision request

```json
{
  "project_id": "project:...",
  "scan_depth": "system",
  "output": "outputs",
  "boundary_decisions": [
    {
      "target_path": ".env",
      "fingerprint": "sha256:...",
      "decision": "scan_this_run",
      "reason": "Need this config for the current scan."
    }
  ]
}
```

Response excerpt when a decision is required:

```json
{
  "scan_id": "scan:...",
  "project_id": "project:...",
  "status": "requires_boundary_decision",
  "build_result": null,
  "available_boundary_actions": ["scan_this_run", "skip_this_run"],
  "boundary_proposals": [
    {
      "proposal_id": "scan-boundary-proposal:...",
      "status": "pending_user_confirmation",
      "target": {
        "path": ".env",
        "risk_type": "secret_like_config",
        "fingerprint": "sha256:..."
      },
      "evidence_packet": {
        "masked_evidence_values": ["[MASKED]"],
        "context_limits": {
          "raw_file_contents_included": false,
          "project_root_included": false
        }
      }
    }
  ]
}
```

規則：

- 必須走 project session flow：`POST /api/projects/import` -> `POST /api/scans`。
- 若有 unresolved boundary proposal，`POST /api/scans` 不會寫 artifact，也不會更新 latest `/api/map` payload。
- `scan_this_run` 只讓 matching `target_path + fingerprint` 在本次 scan 進入 provider collection。
- `skip_this_run` 只讓 matching target 在本次 scan 進入 skipped summary，reason 為 `skipped_by_policy_overlay`。
- Decision 不保存到 repository，不會形成歷史偏好或永久跳過。
- `POST /api/map/build` 不建立 `project_id`，也不走 scan boundary gate。
- Response 只回傳 project-relative path、fingerprint、risk type、masked/bounded evidence packet，不得包含 raw secret、本機絕對路徑或 raw file contents。

### Optional NVIDIA NIM Provider

Phase 20 可注入 `NvidiaNimProposalProvider` 作為 hosted NIM adapter。它只接收 masked packet 與 schema summary，非敏感預設值由 bundled TOML `src/kai_mind/core/configs/llm_proposal.toml` 提供，例如模型 ID `google/gemma-4-31b-it` 與 endpoint `https://integrate.api.nvidia.com/v1/chat/completions`。此 adapter 是 explicit opt-in，不是 production default；必須同時設定 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` 與 `NVIDIA_API_KEY` 才會啟用。沒有 enable flag、沒有 key 或 provider 失敗時，proposal flow 必須 deterministic fallback。

Local development can opt in through `.env`; API key must stay in `.env` / environment variables and must not be committed:

```env
KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true
NVIDIA_API_KEY=nvapi-...
```

The following non-secret values have TOML defaults and can be temporarily overridden through `.env` during local testing:

```env
NVIDIA_NIM_MODEL=google/gemma-4-31b-it
NVIDIA_NIM_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions
NVIDIA_NIM_TIMEOUT_SECONDS=8.0
NVIDIA_NIM_MAX_TOKENS=16384
NVIDIA_NIM_TEMPERATURE=1.0
NVIDIA_NIM_TOP_P=0.95
NVIDIA_NIM_STREAM=false
NVIDIA_NIM_ENABLE_THINKING=true
```

Only runtime/provider defaults belong in TOML or `.env`. Mapping proposal
output limits, such as maximum candidate count, candidate label/rationale
length, evidence id count, suggested edge count, and `provider_error_reason`
length, are Pydantic schema limits in `src/kai_mind/core/models/mapping.py`;
they are intentionally not configurable through TOML because they are part of
the API and safety contract.

The provider request mirrors NVIDIA Platform's non-streaming chat completion shape:

```json
{
  "model": "google/gemma-4-31b-it",
  "messages": [{"role": "user", "content": "...masked packet..."}],
  "max_tokens": 16384,
  "temperature": 1.0,
  "top_p": 0.95,
  "stream": false,
  "chat_template_kwargs": {"enable_thinking": true}
}
```

`.env` is ignored by Git and must not be committed. Tests use mock HTTP transports and never call the real NVIDIA endpoint.

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

# Epic 1 Viewer Frontend API Contract

This document records the frontend-facing contract for the local Python API.

The frontend can run in two modes:

- `Sample`: uses the committed `frontend-json-sample.json`.
- `API`: loads from a local Python backend. Default base URL is `http://127.0.0.1:8000` and can be changed in the UI or through `VITE_API_BASE_URL`.

## Map Loading

Preferred endpoint:

```http
GET /api/map
Accept: application/json
```

Temporary fallback endpoint:

```http
GET /map
Accept: application/json
```

Response shape must match the sample file:

```ts
{
  viewer_load_result: {
    loaded: boolean;
    error_reason?: string | null;
    map_json?: string;
    ai_system_map: {
      schema_version?: string;
      system_type?: string;
      scan_depth?: string;
      query_trace_events?: QueryTraceEvent[];
      unmapped_components?: unknown[];
    };
    graph_view_model: {
      nodes: GraphNode[];
      edges: GraphEdge[];
      details: {
        evidence_by_id: Record<string, object>;
        risk_hints_by_id: Record<string, object>;
      };
      filters: {
        available: GraphFilter[];
        behavior?: string;
      };
    };
  };
}
```

The frontend treats `graph_view_model` as the rendering input. It does not rescan files and does not infer canonical facts.

### Load an existing map artifact

API mode can ask the backend to validate and load an existing map JSON:

```http
POST /api/viewer/load
Content-Type: application/json
```

```json
{
  "map_json_path": "C:\\path\\to\\ai_system_map.json"
}
```

The path is resolved by the local backend. Browser code does not read the file
directly. The response is the same `ViewerPayload` shape as `GET /api/map`.
When `viewer_load_result.loaded` is false, the frontend reports
`error_reason` and retains the currently displayed graph.

### Latest Markdown report

```http
GET /api/map/report
Accept: text/markdown
```

The route returns the latest controlled Markdown report artifact. Before a
successful build/load with an available report, it returns:

```json
{
  "detail": "map_markdown_not_available"
}
```

Download uses the same controlled artifact:

```http
GET /api/map/report?download=true
```

The backend supplies `Content-Disposition: attachment;
filename="ai_system_map.md"`. The frontend never accepts an arbitrary report
path.

## Project-Scoped Scan Flow

The API mode can start a scan from a local project path. The frontend first imports the project path, then starts a scan with the returned project id. It does not call `/api/map/build` for this interactive flow.

```http
POST /api/projects/import
Content-Type: application/json
```

Request:

```json
{
  "source_type": "local_path",
  "project_path": "C:\\path\\to\\project"
}
```

Response:

```ts
{
  project_id: string;
  source_type: "local_path";
  project_name: string;
  project_path: string;
}
```

The frontend then starts the scan:

```http
POST /api/scans
Content-Type: application/json
```

Request:

```ts
{
  project_id: string;
  boundary_decisions?: Array<{
    target_path: string;
    fingerprint: string;
    decision: "scan_this_run" | "skip_this_run";
    reason?: string;
  }>;
}
```

Completed response:

```ts
{
  scan_id: string;
  project_id: string;
  status: "completed" | "error";
  build_result?: unknown;
}
```

Boundary review response:

```ts
{
  scan_id: string;
  project_id: string;
  status: "requires_boundary_decision";
  available_boundary_actions: Array<"scan_this_run" | "skip_this_run">;
  boundary_proposals: Array<{
    proposal_id: string;
    project_id: string;
    status: "pending_user_confirmation";
    target: {
      path: string;
      target_type: string;
      risk_type: string;
      reason: string;
      size_bytes?: number | null;
      fingerprint: string;
    };
    evidence_packet: {
      project_id: string;
      target_path: string;
      risk_type: string;
      reason: string;
      evidence_ids: string[];
      rule_ids: string[];
      masked_evidence_values: string[];
      masked_snippets: string[];
      context_limits: Record<string, string | number | boolean>;
    };
    available_actions: Array<"scan_this_run" | "skip_this_run">;
    created_at: string;
    updated_at: string;
  }>;
}
```

When `requires_boundary_decision` is returned, the frontend must not refresh the graph or imply the scan completed. The user's boundary decision only applies to the current scan request and must not be presented as a saved preference.

After a completed scan, the frontend reloads `GET /api/map` and renders the latest `viewer_load_result.graph_view_model`.

## Scan Progress SSE

Preferred endpoint:

```http
GET /api/scan/events
Accept: text/event-stream
```

Supported event names:

- default `message`
- `scan_progress`

Payload:

```ts
{
  event?: string;
  type?: string;
  status?: string;
  stage?: string;
  message?: string;
  percent?: number;
  node_id?: string;
  edge_id?: string;
  component_id?: string;
  source_id?: string;
  slot?: string;
  evidence_id?: string;
  scan_depth?: string;
  timestamp?: string;
}
```

The frontend highlights the first resolvable target in this order:

1. `node_id`
2. `edge_id`
3. `component_id`
4. `source_id`
5. `slot`

IDs may be either graph IDs or canonical source IDs. The frontend maps both when possible.

## Query Replay

For this checkpoint, query replay is rendered from:

```ts
viewer_load_result.ai_system_map.query_trace_events
```

The UI already supports replay ordering by `sequence_index`. A future API endpoint can return the same `QueryTraceEvent[]` shape after an explicit opt-in trace request.

## Detail Scan

For this checkpoint, L2/L3 panels render the sample `detail_scan_result_sample` and `mapping_proposal_result_sample`.

The future frontend request should stay aligned with Timmy's design:

```json
{
  "target_type": "component_slot | component | edge | trace_step",
  "target": "node-or-edge-or-source-id",
  "scan_depth": "component | code_path"
}
```

The result should be append-only evidence/detail data. It must not silently rewrite canonical facts before validation or user confirmation.

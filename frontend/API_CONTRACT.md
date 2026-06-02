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

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

The frontend first requests the backend-owned metadata-only inventory review:

```http
POST /api/projects/{project_id}/scan-preflights
Content-Type: application/json
```

```ts
type ScanInventoryPreflightRequest = {
  scan_depth?: "system";
  requested_paths?: string[]; // project-relative POSIX; root is "."
  reviewable_excluded_cursor?: string | null;
  reviewable_excluded_limit?: number; // 1..200
};

type InventoryRequestedTargetView = {
  target_path: string;
  target_kind: "file" | "directory";
  status:
    | "reviewable"
    | "hard_blocked"
    | "missing"
    | "empty_directory"
    | "directory_limit_exceeded";
  proposal: ScanBoundaryProposal | null;
  reason_code: string | null;
  limit_context: {
    limit_kind: string;
    limit: number;
    observed_at_least: number;
  } | null;
};

type ScanInventoryPreflightResponse = {
  preflight_request_id: string;
  project_id: string;
  generated_at: string;
  source_mode: "git" | "recursive" | "fallback_after_git_error";
  inventory_policy_schema_version: string;
  inventory_policy_digest: string;
  candidate_set_digest: string;
  filesystem_safety_version: string;
  summary: {
    default_included_file_count: number;
    required_review_count: number;
    reviewable_excluded_count: number;
    hard_blocked_count: number;
    missing_count: number;
    collapsed_directory_count: number;
  };
  required_boundary_proposals: ScanBoundaryProposal[];
  reviewable_excluded_page: {
    items: ScanBoundaryProposal[];
    next_cursor: string | null;
    total: number;
  };
  requested_target_results: InventoryRequestedTargetView[];
  blocked_summaries: Array<{
    path: string;
    reason_code: string;
    outcome: "hard_blocked" | "collapsed_directory";
    can_expand: boolean;
  }>;
  warnings: string[];
};
```

Directory proposals expose bounded counts and a manifest fingerprint only; internal descendant
`entries[]`, file contents, snippets, absolute paths, and secret values must never appear in this payload.
Preflight does not create a scan, snapshot, build, output directory, or latest pointer.

The frontend then starts the scan:

```http
POST /api/scans
Content-Type: application/json
```

Request:

```ts
{
  project_id: string;
  preflight_request_id?: string;
  boundary_decisions?: Array<{
    target_path: string;
    fingerprint: string;
    decision: "scan_this_run" | "skip_this_run";
    selection_scope?: "exact_file" | "recursive_directory";
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
  preflight_request_id?: string;
  inventory_selection_summary?: {
    included_file_count: number;
    skipped_file_count: number;
    directory_scope_results: Array<{
      target_path: string;
      decision: "scan_this_run" | "skip_this_run";
      observed_file_count: number;
      included_file_count: number;
      hard_blocked_file_count: number;
      post_decision_blocked_file_count: number;
    }>;
  };
}
```

Boundary review response:

```ts
{
  project_id: string;
  status: "requires_boundary_decision";
  preflight_request_id?: string;
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
    selection_context?: {
      base_outcome: "included" | "soft_excluded" | "mixed";
      review_kind: "required_confirmation" | "optional_override";
      default_decision: "scan_this_run" | "skip_this_run" | null;
      decision_required: boolean;
      override_allowed: boolean;
      exclusion_sources: string[];
      matched_inventory_policy_ids: string[];
      target_kind: "file" | "directory";
      selection_scope: "exact_file" | "recursive_directory";
      directory_summary?: Record<string, unknown> | null;
    } | null;
  }>;
}
```

When `requires_boundary_decision` is returned, `scan_id` is absent. The frontend must not refresh the
graph or imply the scan completed. The user's boundary decision only applies to the current scan request
and must not be presented as a saved preference. A stale/changed selection uses
`{detail:{code,message,retryable,context}}`; refresh preflight rather than silently reusing decisions.

`Apply` reuses the saved snapshot and does not preflight or read the repo. `Rescan` starts a new preflight
and does not carry decisions forward.

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

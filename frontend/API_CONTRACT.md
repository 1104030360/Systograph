# Epic 1 Viewer Frontend API Contract

This document records the frontend-facing contract for the local Python API.

The frontend can run in two modes:

- `Sample`: uses the committed `frontend-json-sample.json`.
- `API`: loads from a local Python backend. Default base URL is `http://127.0.0.1:8000` and can be changed in the UI or through `VITE_API_BASE_URL`.

## Map Loading

Preferred endpoint (build-scoped, requires a `project_id`):

```http
GET /api/projects/{project_id}/map-builds/latest
Accept: application/json
```

A pinned historical build loads by id instead:

```http
GET /api/map-builds/{build_id}
Accept: application/json
```

Removed fallback endpoints — **retired on 2026-08-07**, they now return 404:

```http
GET /api/map
GET /map
```

`GET /api/map` and its bare alias `GET /map` used to return the process-wide
latest viewer payload, carrying no `project_id`. Both were removed on
2026-08-07, together with the demo writer `POST /api/map/build` that fed them
and the arbitrary-path loader `POST /api/viewer/load`; the backend answers 404
on all four. Loading a map is now always build-scoped and always requires a
`project_id`.

Removing `POST /api/viewer/load` **is** the fix for the #140 path oracle. The
endpoint took a client-supplied `map_json_path` and read that file off the
server's disk, so any caller could probe whether an arbitrary local path
existed and harvest absolute paths and errno detail from the error responses.
#140 was closed by deleting the endpoint rather than allowlisting it. Loading
an existing `ai_system_map.json` now lives only in the CLI command
`systograph validate-map`, where an operator names a local file and no remote
caller can reach it.

The frontend still contains the fallback branch that tries these two paths
after the build-scoped request fails. It is dead code — every attempt hits a
404 — and its removal belongs to the FE-2 work package. Do not build on it.

Both build-scoped endpoints above (`map-builds/latest` and
`map-builds/{build_id}`) answer with the same envelope,
`MapBuildScopedResponse`: six lineage fields at the top level, then
`build_result` (validated profile and readiness sidecars) and
`viewer_load_result` (the base graph projection). `viewer_load_result` is
**not** the whole response — reading only that key loses the lineage the
viewer is required to display.

```ts
type MapBuildScopedResponse = {
  project_id: string;
  scan_id: string;
  build_id: string;
  based_on_build_id: string | null;
  build_reason: "initial_scan" | "apply_confirmations" | "detail_scan";
  applied_mapping_ids: string[];
  build_result: {
    status: "ok" | "error";
    project_name: string;
    active_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    requested_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    source_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    operator_rollback_active: boolean;
    migration_warnings: string[];
    warnings: string[];
    profile_signals_available: boolean;
    readiness_report_available: boolean;
    profile_inference_result: ProfileInferenceResult | null;
    readiness_report: ReadinessReport | null;
  };
  viewer_load_result: {
    loaded: boolean;
    error_reason?: string | null;
    map_json?: string | null;
    ai_system_map: {
      schema_version?: string;
      system_type?: string;
      scan_depth?: string;
      query_trace_events?: QueryTraceEvent[];
      unmapped_components?: unknown[];
    };
    graph_view_model: {
      scan_id: string | null;
      build_id: string | null;
      environment_id: string | null;
      artifact_set_version: string | null;
      mapping_completeness?: MappingCompleteness | null;
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
};
```

The envelope does not expose `output_run_dir` or any `*_path`; artifacts are
returned as content only. The identity strip the viewer must render
(`MODEL-CONTRACT.md` §13 rule 5 — `scan_id`, `build_id`, `environment_id`,
`artifact_set_version`, Mapping Completeness over 52) is assembled from these
fields: `scan_id` and `build_id` from the envelope, `environment_id` and
`artifact_set_version` from `graph_view_model` (which repeats `scan_id` and
`build_id` for the same build), and completeness from
`graph_view_model.mapping_completeness`. The full field list lives in
`docs/API-GUIDE.md` §2 and `docs/MODEL-CONTRACT.md` §7.2.

The frontend treats `graph_view_model` as the rendering input. It does not rescan files and does not infer canonical facts.

## Project-Scoped Scan Flow

The API mode can start a scan from a local project path. The frontend first imports the project path, then starts a scan with the returned project id. This is the only HTTP path that scans a project from scratch. `POST /api/detail-scans` and `POST /api/map-builds/{base_build_id}/apply` also mint new build ids, but both work inside an existing `scan_id` rather than starting a new scan.

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

The frontend then starts the scan. `preflight_request_id` is required: a scan without one is
rejected with `422 preflight_request_id_required` before any enumeration, snapshot, or build runs,
so there is no implicit path that starts a scan straight from the project id.

```http
POST /api/scans
Content-Type: application/json
```

Request:

```ts
{
  project_id: string;
  preflight_request_id: string; // required; from the preflight above
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
  preflight_request_id: string; // echoed from the request
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
  preflight_request_id: string; // echoed from the request
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

After a completed scan, the frontend reloads `GET /api/projects/{project_id}/map-builds/latest` and renders the latest `viewer_load_result.graph_view_model`.

## Retired Legacy Write Surfaces

Two stable `422` codes exist purely to fail closed on contract surfaces the v2 cutover retired.
Both return the plain-string form `{"detail": "<code>"}` — not the
`{detail:{code,message,retryable,context}}` envelope used by stale-selection errors. Neither is
recoverable by retrying the same payload; the frontend must stop sending the retired shape.

| `detail` | Endpoints | Meaning |
| --- | --- | --- |
| `legacy_mapping_type_read_only` | `POST /api/mappings`, `PATCH /api/mappings/{mapping_id}`, `POST /api/mapping-proposals/{proposal_id}/decision` | The request carries `mapping_type: "new_extension_component"` (checked at top level and inside `edited_mapping`). The legacy extension mapping type is read-only: migration tooling may still read it, but no API accepts it as a write. Active values are `existing_slot_mapping` and `non_baseline_capability_candidate`. |
| `legacy_output_not_selectable` | `POST /api/scans` | The request asked for `system_map_schema_version: "ai-system-map/v1"`. Canonical output is `ai-system-map/v2`; `system_map_schema_version` is a deprecated input kept until Plan 15. No build path writes v1 any more — not through a request, and not through a process setting — so there is no payload the frontend can send to obtain v1. |

`POST /api/scans` rejects before any enumeration or scan work runs, so an invalid selection costs no
scan time and leaves no persisted snapshot or output directory behind. The same is true of the
`{detail:{code,message,retryable,context}}`-shaped `preflight_request_id_required` rejection.

The frontend still has type definitions and form paths able to assemble
`new_extension_component`; those must be removed rather than error-handled — the proposal UI is
currently an unwired stub, so the payload never reaches the backend today.

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

API mode runs Detail Scan against the current immutable project build:

```http
POST /api/detail-scans
Content-Type: application/json
```

```json
{
  "project_id": "project:<uuid>",
  "build_id": "build:<uuid>",
  "target_type": "component_instance | unmapped_component | edge | evidence",
  "target": "backend-declared-canonical-id",
  "scan_depth": "component | code_path"
}
```

The frontend requires `build_id` even though the backend retains an optional latest-build fallback for older clients.
It builds targets only from backend-declared `semantic_kind`, `component_id` and `source_id`; labels, badges,
graph positions and id prefixes are not identity sources.

Success returns the immutable child identity and projection:

```ts
{
  project_id: string;
  source_build_id: string;
  build_id: string;
  scan_id: string;
  detail_scan: DetailScanResult;
  ai_system_map: object;
  viewer_load_result: ViewerLoadResult;
  warnings: string[];
}
```

The UI immediately consumes this child projection, then requests
`GET /api/map-builds/{build_id}` for the complete build-scoped envelope. It never issues an
extra map reload after Detail Scan. Parent/historical builds remain immutable, and
`base_build_not_latest` / `scan_snapshot_stale` require reloading the current build before a new request.

L2 renders bounded summaries, safe evidence references, warnings and context limits. L3 renders only
backend-provided project-relative POSIX paths, symbols and exact line ranges. The parser rejects drive,
UNC, absolute, backslash and parent-traversal paths on both Windows and macOS. Raw evidence values,
retrieved chunks, source blobs and full secrets are not rendered.

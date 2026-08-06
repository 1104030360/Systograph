#!/usr/bin/env bash
# Shared helpers for the per-endpoint API trace scripts under scripts/.
#
# This file is meant to be sourced, not executed directly. Each endpoint
# script sources it, parses common flags, optionally boots a local FastAPI
# server, prepares any prerequisite session state, then calls exactly one
# target endpoint with full request/response tracing.

# Resolve repo root from this file location (scripts/lib/ -> repo root).
SYSTOGRAPH_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Defaults (override via env or common flags).
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
PROJECT_PATH="${PROJECT_PATH:-$SYSTOGRAPH_ROOT_DIR/tests/fixtures/rag_projects/custom_router_rag}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs}"
SERVER_LOG="${SERVER_LOG:-$SYSTOGRAPH_ROOT_DIR/outputs/api-trace-server.log}"

START_SERVER=0
SERVER_PID=""
SYSTOGRAPH_EXTRA_ARGS=()

# Bind address for --start-server, derived from API_BASE_URL.
SERVER_BIND_HOST=""
SERVER_BIND_PORT=""

# Globals populated by api_call / setup_* helpers.
LAST_STATUS=""
LAST_BODY=""

systograph_die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    systograph_die "Missing required command: $1"
  fi
}

require_tools() {
  require_cmd curl
  require_cmd jq
}

# Parse flags common to every endpoint script. Endpoint-specific flags are
# collected into SYSTOGRAPH_EXTRA_ARGS for the caller to handle. Each caller must
# define a usage() function before calling this.
systograph_parse_common_args() {
  SYSTOGRAPH_EXTRA_ARGS=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --start-server)
        START_SERVER=1
        shift
        ;;
      --api-base-url)
        API_BASE_URL="${2:?missing value for --api-base-url}"
        shift 2
        ;;
      --project-path)
        PROJECT_PATH="${2:?missing value for --project-path}"
        shift 2
        ;;
      --output)
        OUTPUT_DIR="${2:?missing value for --output}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        SYSTOGRAPH_EXTRA_ARGS+=("$1")
        shift
        ;;
    esac
  done
}

systograph_cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

# Readiness probe. `/openapi.json` is served by FastAPI itself, is read-only,
# and is not a product endpoint, so it cannot be retired out from under the
# whole trace suite the way a demo endpoint can.
wait_for_api() {
  local attempt
  for attempt in $(seq 1 60); do
    if curl -fsS "$API_BASE_URL/openapi.json" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "Backend did not become available at $API_BASE_URL" >&2
  if [[ -f "$SERVER_LOG" ]]; then
    echo "Server log tail ($SERVER_LOG):" >&2
    tail -n 40 "$SERVER_LOG" >&2 || true
  fi
  exit 1
}

# Resolve SERVER_BIND_HOST / SERVER_BIND_PORT from API_BASE_URL for
# --start-server. Anything this cannot bind exactly is a hard error: guessing a
# default port while wait_for_api probes the URL as written turns a typo into a
# ~30s "Backend did not become available" timeout instead of a clear message.
# Not meant to be a general URL parser — bracketed IPv6 hosts fail closed here.
systograph_resolve_server_bind() {
  local rest hostport
  case "$API_BASE_URL" in
    http://*) rest="${API_BASE_URL#http://}" ;;
    *)
      systograph_die \
        "--start-server needs an http:// --api-base-url, got: $API_BASE_URL"
      ;;
  esac
  hostport="${rest%%/*}"
  SERVER_BIND_HOST="${hostport%%:*}"
  SERVER_BIND_PORT="${hostport#*:}"
  [[ -n "$SERVER_BIND_HOST" ]] \
    || systograph_die "--api-base-url has no host: $API_BASE_URL"
  if [[ "$SERVER_BIND_PORT" == "$hostport" ]] \
    || [[ ! "$SERVER_BIND_PORT" =~ ^[0-9]+$ ]]; then
    systograph_die \
      "--start-server needs an explicit numeric port in --api-base-url (e.g. http://127.0.0.1:8000), got: $API_BASE_URL"
  fi
}

# Boot a local server when --start-server was passed, then block until ready.
# When --start-server is not passed, just wait for an already running server.
# The started server binds the host/port of API_BASE_URL, so --start-server and
# --api-base-url stay consistent instead of silently disagreeing.
systograph_bootstrap_server() {
  cd "$SYSTOGRAPH_ROOT_DIR"
  if [[ "$START_SERVER" -eq 1 ]]; then
    if [[ ! -x ".venv/bin/uvicorn" ]]; then
      systograph_die "Cannot find executable .venv/bin/uvicorn (create the venv first)"
    fi
    systograph_resolve_server_bind
    mkdir -p "$(dirname "$SERVER_LOG")"
    .venv/bin/uvicorn systograph.web.app:create_app --factory \
      --host "$SERVER_BIND_HOST" --port "$SERVER_BIND_PORT" >"$SERVER_LOG" 2>&1 &
    SERVER_PID="$!"
    trap systograph_cleanup EXIT
    echo "Started FastAPI PID=$SERVER_PID log=$SERVER_LOG url=$API_BASE_URL"
  fi
  wait_for_api
}

systograph_section() {
  echo
  echo "==================== $* ===================="
}

# Short Traditional Chinese progress line before an API call / phase step.
systograph_progress() {
  echo ">> $*"
}

# Full request/response trace for the target endpoint under test.
# Usage: api_call METHOD ENDPOINT [JSON_BODY]
api_call() {
  local method="$1"
  local endpoint="$2"
  local body="${3:-}"
  local url="$API_BASE_URL$endpoint"
  local tmp status

  echo "-------------------- REQUEST --------------------"
  echo "$method $url"
  if [[ -n "$body" ]]; then
    echo "Content-Type: application/json"
    echo "Body:"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
  fi

  tmp="$(mktemp)"
  if [[ -n "$body" ]]; then
    status="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -d "$body")"
  else
    status="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" \
      -H 'Accept: application/json')"
  fi

  echo "-------------------- RESPONSE -------------------"
  echo "HTTP $status"
  jq '.' "$tmp" 2>/dev/null || cat "$tmp"
  echo

  LAST_STATUS="$status"
  LAST_BODY="$(cat "$tmp")"
  rm -f "$tmp"
}

# Quiet helpers used to build prerequisite session state. They fail fast and
# echo the raw response body to stdout for capture with $(...).
setup_post() {
  local endpoint="$1"
  local body="$2"
  curl -fsS -X POST "$API_BASE_URL$endpoint" \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "$body"
}

setup_get() {
  local endpoint="$1"
  curl -fsS "$API_BASE_URL$endpoint" -H 'Accept: application/json'
}

systograph_urlencode() {
  jq -rn --arg v "$1" '$v|@uri'
}

# Import PROJECT_PATH and echo the resulting project_id.
systograph_import_project() {
  local path="${1:-$PROJECT_PATH}"
  [[ -d "$path" ]] || systograph_die "Project path does not exist: $path"
  systograph_progress "現在要匯入專案：$path" >&2
  local body project_id
  body="$(jq -n --arg p "$path" \
    '{source_type:"local_path", project_path:$p}')"
  project_id="$(setup_post "/api/projects/import" "$body" | jq -r '.project_id')"
  [[ -n "$project_id" && "$project_id" != "null" ]] \
    || systograph_die "Failed to import project: $path"
  systograph_progress "匯入完成，project_id=$project_id" >&2
  echo "$project_id"
}

# Open a metadata-only preflight for a project_id and echo its
# preflight_request_id. A rescan must always open a new preflight.
systograph_open_scan_preflight() {
  local project_id="$1"
  local preflight_id
  systograph_progress "現在要開 scan preflight，project_id=$project_id" >&2
  preflight_id="$(
    setup_post "/api/projects/${project_id}/scan-preflights" '{}' \
      | jq -r '.preflight_request_id // empty'
  )"
  [[ -n "$preflight_id" ]] \
    || systograph_die "Failed to open scan preflight for $project_id"
  echo "$preflight_id"
}

# Run a system scan for a project_id and echo the full scan response JSON.
# POST /api/scans always requires a preflight_request_id, so this opens a
# preflight first. Trace fixtures carry no required boundary reviews, so a
# requires_boundary_decision response means the fixture drifted.
systograph_run_scan() {
  local project_id="$1"
  local preflight_id
  preflight_id="$(systograph_open_scan_preflight "$project_id")"
  systograph_progress "現在要建立 scan（系統掃描）project_id=$project_id" >&2
  local body scan status build_id
  body="$(jq -n --arg id "$project_id" --arg out "$OUTPUT_DIR" \
    --arg preflight_id "$preflight_id" \
    '{project_id:$id, scan_depth:"system", output:$out, redact_root_path:true, no_snippets:false, preflight_request_id:$preflight_id, boundary_decisions:[]}')"
  scan="$(setup_post "/api/scans" "$body")"
  status="$(echo "$scan" | jq -r '.status')"
  if [[ "$status" == "requires_boundary_decision" ]]; then
    systograph_die "Scan needs boundary decisions this trace does not make"
  fi
  [[ "$status" == "completed" ]] \
    || systograph_die "Scan did not complete (status=$status)"
  build_id="$(echo "$scan" | jq -r '.build_result.lineage.build_id // empty')"
  if [[ -n "$build_id" ]]; then
    systograph_progress "掃描完成，build_id=$build_id" >&2
  else
    systograph_progress "掃描完成（無 lineage.build_id）" >&2
  fi
  echo "$scan"
}

# Echo a target_slot for an existing_slot manual mapping, derived from the
# ai-system-map/v2 scan response. v2 has no components_by_slot: the legacy
# 13-slot label lives on components[].metadata.legacy_slot, which every emitted
# component carries, so prefer a slot this map actually detected. Maps that
# detected no components at all (e.g. the custom_router_rag fixture) fall back
# to `vector_store`, a real rag-core-v1 slot accepted by ManualMappingService's
# allowed-slot check — a manual mapping asserts a slot, it does not have to
# already be detected.
systograph_demo_slot() {
  local scan_json="$1"
  echo "$scan_json" | jq -r '
    [.build_result.ai_system_map.components[]?.metadata.legacy_slot
     | select(type == "string")][0] // "vector_store"'
}

# Echo the first evidence id from a scan response JSON (v2: evidence[].evidence_id).
systograph_first_evidence_id() {
  local scan_json="$1"
  echo "$scan_json" \
    | jq -r '.build_result.ai_system_map.evidence[0].evidence_id // empty'
}

# Create one confirmed existing_slot manual mapping using a real slot key and a
# real evidence id derived from a scan response. Echoes the created mapping JSON.
# Usage: systograph_create_demo_mapping PROJECT_ID SCAN_JSON [COMPONENT_NAME]
systograph_create_demo_mapping() {
  local project_id="$1"
  local scan_json="$2"
  local component_name="${3:-TraceDemoComponent}"
  local slot evidence_id body

  slot="$(systograph_demo_slot "$scan_json")"
  evidence_id="$(systograph_first_evidence_id "$scan_json")"
  [[ -n "$slot" && "$slot" != "null" ]] \
    || systograph_die "Could not derive a target slot from the scan"
  [[ -n "$evidence_id" ]] \
    || systograph_die "Could not derive an evidence id from the scan"

  systograph_progress "現在要建立 manual mapping（slot=${slot}）" >&2
  body="$(jq -n \
    --arg id "$project_id" \
    --arg slot "$slot" \
    --arg name "$component_name" \
    --arg ev "$evidence_id" \
    '{project_id:$id, mapping_type:"existing_slot_mapping", decision:"confirmed",
      target_slot:$slot, component_name:$name, evidence_ids:[$ev]}')"
  setup_post "/api/mappings" "$body"
}

# Echo the first unmapped component id from a scan response JSON.
# v2 names this field unmapped_components[].unmapped_id.
systograph_first_unmapped_id() {
  local scan_json="$1"
  echo "$scan_json" \
    | jq -r '
      .build_result.ai_system_map.unmapped_components[0].unmapped_id // empty'
}

# Create a pending mapping proposal for an unmapped component and echo the
# proposal JSON. Falls back to a deterministic provider when no NVIDIA key.
# Usage: systograph_create_proposal PROJECT_ID UNMAPPED_ID
systograph_create_proposal() {
  local project_id="$1"
  local unmapped_id="$2"
  systograph_progress "接著呼叫 mapping proposal（unmapped=${unmapped_id}）" >&2
  local body
  body="$(jq -n --arg id "$project_id" --arg u "$unmapped_id" \
    '{project_id:$id, source_unmapped_id:$u}')"
  setup_post "/api/mapping-proposals" "$body"
}

# Summarize a ViewerPayload JSON (stdin or arg) for Track A graph projection QA.
# Expects root shape: { viewer_load_result: { loaded, error_reason, graph_view_model: {...} } }
systograph_summarize_viewer_payload() {
  local json="${1:-}"
  if [[ -z "$json" ]]; then
    json="$(cat)"
  fi
  echo "$json" | jq '{
    loaded: .viewer_load_result.loaded,
    error_reason: .viewer_load_result.error_reason,
    schema_version: .viewer_load_result.graph_view_model.schema_version,
    source_schema_version: .viewer_load_result.graph_view_model.source_schema_version,
    project_id: .viewer_load_result.graph_view_model.project_id,
    scan_id: .viewer_load_result.graph_view_model.scan_id,
    build_id: .viewer_load_result.graph_view_model.build_id,
    generated_from_build_id: .viewer_load_result.graph_view_model.generated_from_build_id,
    reference_map_version: .viewer_load_result.graph_view_model.reference_map_version,
    node_count: (.viewer_load_result.graph_view_model.nodes | length),
    edge_count: (.viewer_load_result.graph_view_model.edges | length),
    relationship_count: ((.viewer_load_result.graph_view_model.relationships // []) | length),
    semantic_kind_counts: (
      [.viewer_load_result.graph_view_model.nodes[]?.semantic_kind // "null"]
      | group_by(.)
      | map({key: .[0], value: length})
      | from_entries
    ),
    reference_assessment_count: (
      (.viewer_load_result.graph_view_model.details.reference_assessments_by_id // {}) | length
    ),
    profile_finding_count: (
      (.viewer_load_result.graph_view_model.details.profile_findings_by_id // {}) | length
    ),
    capability_candidate_count: (
      (.viewer_load_result.graph_view_model.details.capability_candidates_by_id // {}) | length
    ),
    lens_ids: [(.viewer_load_result.graph_view_model.filters.lenses // [])[].id],
    filter_behavior: .viewer_load_result.graph_view_model.filters.behavior,
    mapping_completeness: (
      .viewer_load_result.graph_view_model.mapping_completeness
      | if . == null then null else {numerator, denominator, value} end
    )
  }'
}

# Soft asserts for a loaded ViewerPayload. Fail only when map is expected loaded.
# Usage: systograph_assert_graph_projection_loaded "$LAST_BODY"
systograph_assert_graph_projection_loaded() {
  local json="$1"
  local loaded schema lenses refs behavior
  loaded="$(echo "$json" | jq -r '.viewer_load_result.loaded')"
  [[ "$loaded" == "true" ]] || systograph_die "Expected viewer_load_result.loaded=true, got: $loaded"
  schema="$(echo "$json" | jq -r '.viewer_load_result.graph_view_model.schema_version // empty')"
  [[ "$schema" == "graph-view-model/v1" ]] \
    || systograph_die "Expected graph schema_version=graph-view-model/v1, got: $schema"
  lenses="$(echo "$json" | jq -r '(.viewer_load_result.graph_view_model.filters.lenses // []) | length')"
  [[ "$lenses" == "6" ]] || systograph_die "Expected 6 graph lenses, got: $lenses"
  behavior="$(echo "$json" | jq -r '.viewer_load_result.graph_view_model.filters.behavior // empty')"
  [[ "$behavior" == "highlight_and_dim" ]] \
    || systograph_die "Expected filters.behavior=highlight_and_dim, got: $behavior"
  refs="$(echo "$json" | jq -r '(.viewer_load_result.graph_view_model.details.reference_assessments_by_id // {}) | length')"
  [[ "$refs" == "52" ]] \
    || systograph_die "Expected 52 reference assessments, got: $refs"
}

# Summarize MapBuildResult-shaped JSON (root or .build_result) for projection sidecar QA.
systograph_summarize_map_build_result() {
  local json="$1"
  echo "$json" | jq '{
    status,
    build_id: .lineage.build_id,
    map_json_path,
    profile_signals_path,
    readiness_report_path,
    profile_available: (.profile_inference_result != null),
    readiness_available: (.readiness_report != null),
    warnings,
    migration_warnings,
    component_count: ((.ai_system_map.components // []) | length),
    edge_count: ((.ai_system_map.edges // []) | length),
    evidence_count: ((.ai_system_map.evidence // []) | length),
    unmapped_count: ((.ai_system_map.unmapped_components // []) | length),
    graph: (
      if .viewer_load_result == null then null
      else {
        loaded: .viewer_load_result.loaded,
        node_count: (.viewer_load_result.graph_view_model.nodes | length),
        edge_count: (.viewer_load_result.graph_view_model.edges | length),
        relationship_count: ((.viewer_load_result.graph_view_model.relationships // []) | length),
        reference_assessment_count: (
          (.viewer_load_result.graph_view_model.details.reference_assessments_by_id // {}) | length
        ),
        profile_finding_count: (
          (.viewer_load_result.graph_view_model.details.profile_findings_by_id // {}) | length
        ),
        lens_count: ((.viewer_load_result.graph_view_model.filters.lenses // []) | length),
        mapping_completeness: (
          .viewer_load_result.graph_view_model.mapping_completeness
          | if . == null then null else {numerator, denominator, value} end
        )
      }
      end
    )
  }'
}

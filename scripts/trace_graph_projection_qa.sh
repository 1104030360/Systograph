#!/usr/bin/env bash
# Trace: Track A graph projection QA
#
# Flow:
#   1. import + scan
#   2. GET /api/map → summarize + assert graph projection
#   3. GET /api/map-builds/{build_id} → summarize + assert profile_signals and
#      graph projection
#   4. Compare node_count / relationship_count between session and build-scoped
#      responses; die on mismatch
#
# Surfaces Track A SystemMapIndex / GraphProjection fields for manual QA.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace Track A graph projection QA (session map vs build-scoped)

Usage:
  scripts/trace_graph_projection_qa.sh [common options]

Common options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
systograph_parse_common_args "$@"
[[ ${#SYSTOGRAPH_EXTRA_ARGS[@]} -eq 0 ]] || systograph_die "Unknown option: ${SYSTOGRAPH_EXTRA_ARGS[*]}"
systograph_bootstrap_server

systograph_section "準備：匯入專案並掃描"
PROJECT_ID="$(systograph_import_project)"
SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
BUILD_ID="$(echo "$SCAN_JSON" | jq -r '.build_result.lineage.build_id')"
[[ -n "$BUILD_ID" && "$BUILD_ID" != "null" ]] \
  || systograph_die "Scan response missing build_result.lineage.build_id"
systograph_progress "將比對 session GET /api/map 與 build-scoped GET /api/map-builds/$BUILD_ID"

systograph_section "Session map：GET /api/map"
systograph_progress "現在要讀取 session viewer map..."
api_call GET "/api/map"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
SESSION_BODY="$LAST_BODY"
systograph_section "Session graph projection 摘要"
systograph_summarize_viewer_payload "$SESSION_BODY"
systograph_assert_graph_projection_loaded "$SESSION_BODY"

SESSION_NODES="$(echo "$SESSION_BODY" | jq -r '.viewer_load_result.graph_view_model.nodes | length')"
SESSION_RELS="$(echo "$SESSION_BODY" | jq -r '(.viewer_load_result.graph_view_model.relationships // []) | length')"

systograph_section "Build-scoped map：GET /api/map-builds/{build_id}"
systograph_progress "現在要讀取 build-scoped viewer projection..."
api_call GET "/api/map-builds/$BUILD_ID"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
BUILD_BODY="$LAST_BODY"

systograph_section "Build-scoped graph projection 摘要"
systograph_summarize_viewer_payload "$(echo "$BUILD_BODY" | jq '{viewer_load_result}')"
echo "$BUILD_BODY" | jq '{
  profile_signals_available: .build_result.profile_signals_available,
  readiness_report_available: .build_result.readiness_report_available
}'

PROFILE_OK="$(echo "$BUILD_BODY" | jq -r '.build_result.profile_signals_available')"
[[ "$PROFILE_OK" == "true" ]] \
  || systograph_die "Expected build_result.profile_signals_available=true, got: $PROFILE_OK"
systograph_assert_graph_projection_loaded "$(echo "$BUILD_BODY" | jq '{viewer_load_result}')"

BUILD_NODES="$(echo "$BUILD_BODY" | jq -r '.viewer_load_result.graph_view_model.nodes | length')"
BUILD_RELS="$(echo "$BUILD_BODY" | jq -r '(.viewer_load_result.graph_view_model.relationships // []) | length')"

systograph_section "比對 session vs build-scoped counts"
systograph_progress "session nodes=${SESSION_NODES} rels=${SESSION_RELS}；build nodes=${BUILD_NODES} rels=${BUILD_RELS}"
[[ "$SESSION_NODES" == "$BUILD_NODES" ]] \
  || systograph_die "node_count mismatch: session=$SESSION_NODES build=$BUILD_NODES"
[[ "$SESSION_RELS" == "$BUILD_RELS" ]] \
  || systograph_die "relationship_count mismatch: session=$SESSION_RELS build=$BUILD_RELS"
systograph_progress "比對通過：node_count 與 relationship_count 一致"

#!/usr/bin/env bash
# Trace: Track A graph projection QA
#
# Flow:
#   1. import + scan
#   2. GET /api/projects/{project_id}/map-builds/latest → summarize + assert
#      graph projection
#   3. GET /api/map-builds/{build_id} → summarize + assert profile_signals and
#      graph projection
#   4. Compare node_count / relationship_count between the project-latest and
#      the explicitly addressed build; die on mismatch
#
# Surfaces Track A SystemMapIndex / GraphProjection fields for manual QA, and
# keeps the project latest pointer honest against the build it should resolve
# to.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace Track A graph projection QA (project latest vs addressed build)

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
systograph_progress "將比對 GET /api/projects/$PROJECT_ID/map-builds/latest 與 GET /api/map-builds/$BUILD_ID"

systograph_section "Project latest：GET /api/projects/{project_id}/map-builds/latest"
systograph_progress "現在要讀取該 project 的最新 build..."
api_call GET "/api/projects/$PROJECT_ID/map-builds/latest"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
LATEST_BODY="$LAST_BODY"
LATEST_BUILD_ID="$(echo "$LATEST_BODY" | jq -r '.build_id')"
[[ "$LATEST_BUILD_ID" == "$BUILD_ID" ]] \
  || systograph_die "latest build_id mismatch: latest=$LATEST_BUILD_ID scan=$BUILD_ID"
systograph_section "Project latest graph projection 摘要"
systograph_summarize_viewer_payload "$(echo "$LATEST_BODY" | jq '{viewer_load_result}')"
systograph_assert_graph_projection_loaded "$(echo "$LATEST_BODY" | jq '{viewer_load_result}')"

LATEST_NODES="$(echo "$LATEST_BODY" | jq -r '.viewer_load_result.graph_view_model.nodes | length')"
LATEST_RELS="$(echo "$LATEST_BODY" | jq -r '(.viewer_load_result.graph_view_model.relationships // []) | length')"

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

systograph_section "比對 project latest vs 指定 build 的 counts"
systograph_progress "latest nodes=${LATEST_NODES} rels=${LATEST_RELS}；build nodes=${BUILD_NODES} rels=${BUILD_RELS}"
[[ "$LATEST_NODES" == "$BUILD_NODES" ]] \
  || systograph_die "node_count mismatch: latest=$LATEST_NODES build=$BUILD_NODES"
[[ "$LATEST_RELS" == "$BUILD_RELS" ]] \
  || systograph_die "relationship_count mismatch: latest=$LATEST_RELS build=$BUILD_RELS"
systograph_progress "比對通過：node_count 與 relationship_count 一致"

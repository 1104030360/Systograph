#!/usr/bin/env bash
# Trace: GET /api/map
#
# Input  : none (reads the latest session viewer payload).
# Output : ViewerPayload {viewer_load_result:{loaded, error_reason, map_json,
#          ai_system_map, graph_view_model:{nodes, edges, details, filters}}}
#
# By default this script first builds a map so the payload is non-empty. Pass
# --no-setup to call GET /api/map against whatever is already in the session
# (returns loaded:false / no_map_loaded when nothing was built yet).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

NO_SETUP=0

usage() {
  cat <<'USAGE'
Trace GET /api/map

Usage:
  scripts/trace_map_get.sh [common options] [--no-setup]

Options:
  --no-setup              Do not build a map first; show the raw current state.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to build before reading (unless --no-setup).
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
for arg in ${KAI_EXTRA_ARGS[@]+"${KAI_EXTRA_ARGS[@]}"}; do
  case "$arg" in
    --no-setup) NO_SETUP=1 ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
done
kai_bootstrap_server

if [[ "$NO_SETUP" -eq 0 ]]; then
  kai_section "準備：先掃描，讓 /api/map 有內容"
  PROJECT_ID="$(kai_import_project)"
  kai_run_scan "$PROJECT_ID" >/dev/null
fi

kai_section "讀取地圖：GET /api/map"
kai_progress "現在要讀取最新 viewer map..."
api_call GET "/api/map"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Graph summary"
echo "$LAST_BODY" | jq '{
  loaded: .viewer_load_result.loaded,
  error_reason: .viewer_load_result.error_reason,
  node_count: (.viewer_load_result.graph_view_model.nodes | length),
  edge_count: (.viewer_load_result.graph_view_model.edges | length)
}'

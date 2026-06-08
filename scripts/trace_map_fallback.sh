#!/usr/bin/env bash
# Trace: GET /map  (legacy fallback for GET /api/map)
#
# Input  : none.
# Output : identical ViewerPayload shape as GET /api/map.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

NO_SETUP=0

usage() {
  cat <<'USAGE'
Trace GET /map (legacy fallback)

Usage:
  scripts/trace_map_fallback.sh [common options] [--no-setup]

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
  kai_section "Setup: build a map so /map has content"
  PROJECT_ID="$(kai_import_project)"
  kai_run_scan "$PROJECT_ID" >/dev/null
fi

kai_section "GET /map"
api_call GET "/map"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Graph summary"
echo "$LAST_BODY" | jq '{
  loaded: .viewer_load_result.loaded,
  node_count: (.viewer_load_result.graph_view_model.nodes | length),
  edge_count: (.viewer_load_result.graph_view_model.edges | length)
}'

#!/usr/bin/env bash
# Trace: GET /map  (legacy fallback for GET /api/map)
#
# Input  : none.
# Output : identical ViewerPayload shape as GET /api/map, including Track A
#          graph_view_model projection fields (lenses, relationships, details).
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
systograph_parse_common_args "$@"
for arg in ${SYSTOGRAPH_EXTRA_ARGS[@]+"${SYSTOGRAPH_EXTRA_ARGS[@]}"}; do
  case "$arg" in
    --no-setup) NO_SETUP=1 ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
done
systograph_bootstrap_server

if [[ "$NO_SETUP" -eq 0 ]]; then
  systograph_section "準備：先掃描，讓 /map 有內容"
  PROJECT_ID="$(systograph_import_project)"
  systograph_run_scan "$PROJECT_ID" >/dev/null
fi

systograph_section "讀取地圖（legacy）：GET /map"
systograph_progress "現在要呼叫 legacy /map fallback..."
api_call GET "/map"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Graph projection 摘要（Track A）"
systograph_summarize_viewer_payload "$LAST_BODY"
if [[ "$NO_SETUP" -eq 0 ]]; then
  systograph_assert_graph_projection_loaded "$LAST_BODY"
fi

#!/usr/bin/env bash
# Trace: GET /api/mappings?project_id=...
#
# Input  : project_id query parameter (required).
# Output : ManualMappingListResponse {project_id, mappings:[...], available_actions}
#
# By default this script imports + scans + creates one mapping so the list is
# non-empty. Pass --project-id to list an arbitrary project (often empty).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROJECT_ID=""

usage() {
  cat <<'USAGE'
Trace GET /api/mappings?project_id=...

Usage:
  scripts/trace_mappings_list.sh [common options] [--project-id ID]

Options:
  --project-id ID         List mappings for this project_id (skip setup).
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import/scan when no --project-id is given.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
systograph_parse_common_args "$@"
i=0
while [[ $i -lt ${#SYSTOGRAPH_EXTRA_ARGS[@]} ]]; do
  arg="${SYSTOGRAPH_EXTRA_ARGS[$i]}"
  case "$arg" in
    --project-id)
      i=$((i + 1))
      PROJECT_ID="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --project-id}"
      ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
systograph_bootstrap_server

if [[ -z "$PROJECT_ID" ]]; then
  systograph_section "準備：匯入 + 掃描 + 先建一筆 mapping"
  PROJECT_ID="$(systograph_import_project)"
  SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
  systograph_create_demo_mapping "$PROJECT_ID" "$SCAN_JSON" >/dev/null
fi

ENCODED_ID="$(systograph_urlencode "$PROJECT_ID")"
systograph_section "列出 mappings：GET /api/mappings"
systograph_progress "現在要列出此專案的 manual mappings..."
api_call GET "/api/mappings?project_id=$ENCODED_ID"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Mappings summary"
echo "$LAST_BODY" | jq '{
  project_id,
  mapping_count: (.mappings | length),
  available_actions
}'

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
kai_parse_common_args "$@"
i=0
while [[ $i -lt ${#KAI_EXTRA_ARGS[@]} ]]; do
  arg="${KAI_EXTRA_ARGS[$i]}"
  case "$arg" in
    --project-id)
      i=$((i + 1))
      PROJECT_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --project-id}"
      ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

if [[ -z "$PROJECT_ID" ]]; then
  kai_section "Setup: import + scan + create one mapping"
  PROJECT_ID="$(kai_import_project)"
  SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
  kai_create_demo_mapping "$PROJECT_ID" "$SCAN_JSON" >/dev/null
fi

ENCODED_ID="$(kai_urlencode "$PROJECT_ID")"
kai_section "GET /api/mappings"
api_call GET "/api/mappings?project_id=$ENCODED_ID"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Mappings summary"
echo "$LAST_BODY" | jq '{
  project_id,
  mapping_count: (.mappings | length),
  available_actions
}'

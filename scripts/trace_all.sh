#!/usr/bin/env bash
# Smoke-test runner: trace every local KAI-Mind API endpoint once.
#
# Boots a single backend (when --start-server is passed), then runs each
# per-endpoint trace script against the same base URL and prints a PASS/FAIL
# summary. Each child script prepares its own session state, so order does not
# matter and a failure in one endpoint does not block the others.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

VERBOSE=0

usage() {
  cat <<'USAGE'
Run every endpoint trace script once (smoke test).

Usage:
  scripts/trace_all.sh [common options] [--verbose]

Options:
  --verbose               Print full output of every script (default: summary tail).
  --start-server          Start one local FastAPI server for the whole run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project used by every script. Default: custom_router_rag fixture.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
for arg in ${KAI_EXTRA_ARGS[@]+"${KAI_EXTRA_ARGS[@]}"}; do
  case "$arg" in
    --verbose) VERBOSE=1 ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
done

# Boot one shared server (if requested) and wait until it is reachable.
kai_bootstrap_server

# Each entry: "<label>|<script> <extra args>". Children inherit the shared
# base URL / project / output but never start their own server.
COMMON_CHILD_ARGS=(
  --api-base-url "$API_BASE_URL"
  --project-path "$PROJECT_PATH"
  --output "$OUTPUT_DIR"
)

SCRIPTS=(
  "POST /api/projects/import|trace_projects_import.sh"
  "POST /api/map/build|trace_map_build.sh"
  "GET /api/map|trace_map_get.sh"
  "GET /api/map/report|trace_map_report.sh"
  "GET /map|trace_map_fallback.sh"
  "POST /api/viewer/load|trace_viewer_load.sh"
  "POST /api/scans|trace_scans_create.sh"
  "GET /api/scan/events|trace_scan_events.sh"
  "POST /api/trace|trace_query_trace.sh"
  "POST /api/detail-scans|trace_detail_scans_create.sh"
  "GET /api/detail-scans/{id}|trace_detail_scans_get.sh"
  "POST /api/mappings|trace_mappings_create.sh"
  "GET /api/mappings|trace_mappings_list.sh"
  "PATCH /api/mappings/{id}|trace_mappings_update.sh"
  "POST /api/mapping-proposals|trace_mapping_proposals_create.sh"
  "GET /api/mapping-proposals|trace_mapping_proposals_list.sh"
  "POST /api/mapping-proposals/{id}/decision|trace_mapping_proposals_decision.sh"
)

RESULTS=()
FAIL_COUNT=0

for entry in "${SCRIPTS[@]}"; do
  label="${entry%%|*}"
  script="${entry##*|}"
  kai_section "RUN $label  ($script)"

  log="$(mktemp)"
  if bash "$SCRIPT_DIR/$script" "${COMMON_CHILD_ARGS[@]}" >"$log" 2>&1; then
    status="PASS"
  else
    status="FAIL"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  if [[ "$VERBOSE" -eq 1 || "$status" == "FAIL" ]]; then
    cat "$log"
  else
    tail -n 12 "$log"
  fi
  rm -f "$log"

  RESULTS+=("$status  $label")
done

kai_section "SUMMARY"
for line in "${RESULTS[@]}"; do
  echo "$line"
done
echo
echo "Total: ${#SCRIPTS[@]}  Failed: $FAIL_COUNT"

[[ "$FAIL_COUNT" -eq 0 ]] || exit 1

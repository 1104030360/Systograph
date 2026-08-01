#!/usr/bin/env bash
# Trace: PATCH /api/mappings/{mapping_id}
#
# Input  : ManualMappingUpdate (partial), e.g. {reason, decision, target_slot,
#          component_name, component_kind, provider, audit_metadata}.
# Output : updated ManualMapping (re-validated, new mapping_digest + updated_at).
#          404 mapping_not_found, 422 on validation errors.
#
# A mapping must exist first, so this script imports + scans + creates one,
# then PATCHes its reason (unless --mapping-id is supplied).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

MAPPING_ID=""
NEW_REASON="Updated via trace_mappings_update.sh"

usage() {
  cat <<'USAGE'
Trace PATCH /api/mappings/{mapping_id}

Usage:
  scripts/trace_mappings_update.sh [common options] \
    [--mapping-id ID] [--reason TEXT]

Options:
  --mapping-id ID         Existing mapping id to update. If omitted, one is created.
  --reason TEXT           New reason value to PATCH. Default: a demo string.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import/scan when creating a mapping.
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
    --mapping-id)
      i=$((i + 1)); MAPPING_ID="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --mapping-id}" ;;
    --reason)
      i=$((i + 1)); NEW_REASON="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --reason}" ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
systograph_bootstrap_server

if [[ -z "$MAPPING_ID" ]]; then
  systograph_section "準備：匯入 + 掃描 + 先建一筆 mapping"
  PROJECT_ID="$(systograph_import_project)"
  SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
  CREATED="$(systograph_create_demo_mapping "$PROJECT_ID" "$SCAN_JSON")"
  MAPPING_ID="$(echo "$CREATED" | jq -r '.mapping_id')"
  [[ -n "$MAPPING_ID" && "$MAPPING_ID" != "null" ]] \
    || systograph_die "Failed to create a mapping to update"
  systograph_progress "已建立 mapping_id=$MAPPING_ID"
fi

ENCODED_ID="$(systograph_urlencode "$MAPPING_ID")"
systograph_section "更新 mapping：PATCH /api/mappings/{id}"
REQUEST_BODY="$(jq -n --arg reason "$NEW_REASON" '{reason:$reason}')"
systograph_progress "現在要更新 mapping 的 reason..."
api_call PATCH "/api/mappings/$ENCODED_ID" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Updated mapping summary"
echo "$LAST_BODY" | jq '{
  mapping_id, decision, reason, mapping_digest, created_at, updated_at
}'

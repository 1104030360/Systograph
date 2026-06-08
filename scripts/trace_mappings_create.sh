#!/usr/bin/env bash
# Trace: POST /api/mappings
#
# Input  : ManualMappingCreate. Minimum: {project_id, mapping_type, decision,
#          evidence_ids:[...]}. A confirmed existing_slot_mapping also requires
#          {target_slot (a known rag-core-v1 slot), component_name}.
# Output : ManualMapping {mapping_id, mapping_digest, created_at, updated_at, ...}
#          422 on validation errors (e.g. missing evidence / unknown slot).
#
# This script imports + scans to obtain a real slot + evidence id, then creates
# a confirmed existing_slot mapping.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace POST /api/mappings

Usage:
  scripts/trace_mappings_create.sh [common options]

Common options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
[[ ${#KAI_EXTRA_ARGS[@]} -eq 0 ]] || kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
kai_bootstrap_server

kai_section "Setup: import + scan to obtain a real slot and evidence id"
PROJECT_ID="$(kai_import_project)"
SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
SLOT="$(echo "$SCAN_JSON" | jq -r '.build_result.ai_system_map.components_by_slot | keys[0]')"
EVIDENCE_ID="$(echo "$SCAN_JSON" | jq -r '.build_result.ai_system_map.evidence[0].id // empty')"
[[ -n "$SLOT" && "$SLOT" != "null" ]] || kai_die "Could not derive a target slot"
[[ -n "$EVIDENCE_ID" ]] || kai_die "Could not derive an evidence id"

kai_section "POST /api/mappings"
REQUEST_BODY="$(jq -n \
  --arg id "$PROJECT_ID" \
  --arg slot "$SLOT" \
  --arg ev "$EVIDENCE_ID" \
  '{project_id:$id, mapping_type:"existing_slot_mapping", decision:"confirmed",
    target_slot:$slot, component_name:"TraceDemoComponent", evidence_ids:[$ev]}')"
api_call POST "/api/mappings" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Mapping summary"
echo "$LAST_BODY" | jq '{
  mapping_id, project_id, mapping_type, decision, target_slot, component_name,
  mapping_digest, created_at
}'

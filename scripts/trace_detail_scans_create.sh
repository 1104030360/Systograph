#!/usr/bin/env bash
# Trace: POST /api/detail-scans
#
# Input  : {project_id, target_type, target, scan_depth:"component"|"code_path"}
#          target_type accepts: component_slot|component_instance|extension|
#          unmapped_component|edge|evidence (plus aliases slot/component/unmapped).
# Output : DetailScanResponse {project_id, detail_scan, ai_system_map}
#          404 project_not_found / map_not_loaded, 422 target_not_found.
#
# Requires a project with a loaded map, so this script imports + scans first,
# then picks the first component slot as the target (overridable).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

TARGET_TYPE="component_slot"
TARGET=""
SCAN_DEPTH="component"

usage() {
  cat <<'USAGE'
Trace POST /api/detail-scans

Usage:
  scripts/trace_detail_scans_create.sh [common options] \
    [--target-type TYPE] [--target ID] [--scan-depth component|code_path]

Options:
  --target-type TYPE      Detail scan target type. Default: component_slot
  --target ID             Target id. Default: first component slot from the scan.
  --scan-depth DEPTH      component (L2) or code_path (L3). Default: component
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan.
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
    --target-type)
      i=$((i + 1)); TARGET_TYPE="${KAI_EXTRA_ARGS[$i]:?missing value for --target-type}" ;;
    --target)
      i=$((i + 1)); TARGET="${KAI_EXTRA_ARGS[$i]:?missing value for --target}" ;;
    --scan-depth)
      i=$((i + 1)); SCAN_DEPTH="${KAI_EXTRA_ARGS[$i]:?missing value for --scan-depth}" ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

kai_section "Setup: import + scan to obtain a loaded map"
PROJECT_ID="$(kai_import_project)"
SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"

if [[ -z "$TARGET" ]]; then
  TARGET="$(echo "$SCAN_JSON" | jq -r '.build_result.ai_system_map.components_by_slot | keys[0]')"
  [[ -n "$TARGET" && "$TARGET" != "null" ]] \
    || kai_die "Could not derive a default target slot from the scan"
  echo "[setup] default target ($TARGET_TYPE) = $TARGET" >&2
fi

kai_section "POST /api/detail-scans"
REQUEST_BODY="$(jq -n \
  --arg id "$PROJECT_ID" \
  --arg tt "$TARGET_TYPE" \
  --arg t "$TARGET" \
  --arg sd "$SCAN_DEPTH" \
  '{project_id:$id, target_type:$tt, target:$t, scan_depth:$sd}')"
api_call POST "/api/detail-scans" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Detail scan summary"
echo "$LAST_BODY" | jq '{
  detail_scan_id: .detail_scan.id,
  target_type: .detail_scan.target_type,
  target: .detail_scan.target,
  scan_depth: .detail_scan.scan_depth,
  status: .detail_scan.status,
  finding_count: (.detail_scan.findings | length),
  evidence_total: (.ai_system_map.evidence | length)
}'

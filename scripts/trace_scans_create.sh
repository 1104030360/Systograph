#!/usr/bin/env bash
# Trace: POST /api/scans
#
# Input  : {project_id, scan_depth:"system", output, redact_root_path,
#          no_snippets, boundary_decisions?}
# Output : ScanCreateResponse {scan_id, project_id, status, build_result,
#          boundary_proposals, available_boundary_actions}
#          build_result includes Track A viewer_load_result / graph projection
#          when status=completed.
#          404 "Project not found" when the project_id was never imported.
#
# A project_id must be imported first, so this script imports the project then
# starts a scan (unless --project-id is supplied).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROJECT_ID=""

usage() {
  cat <<'USAGE'
Trace POST /api/scans

Usage:
  scripts/trace_scans_create.sh [common options] [--project-id ID]

Options:
  --project-id ID         Use an already imported project_id (skip import).
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import when no --project-id is given.
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
  kai_section "準備：先匯入專案取得 project_id"
  PROJECT_ID="$(kai_import_project)"
fi

kai_section "建立掃描：POST /api/scans"
REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" --arg out "$OUTPUT_DIR" \
  '{project_id:$id, scan_depth:"system", output:$out, redact_root_path:true, no_snippets:false}')"
kai_progress "現在要建立 scan（系統掃描）..."
api_call POST "/api/scans" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Scan 摘要"
echo "$LAST_BODY" | jq '{
  scan_id,
  project_id,
  status,
  build_status: .build_result.status,
  build_id: .build_result.lineage.build_id,
  map_json_path: .build_result.map_json_path
}'
kai_section "Build result / graph projection 摘要（Track A）"
BUILD_RESULT_JSON="$(echo "$LAST_BODY" | jq '.build_result')"
kai_summarize_map_build_result "$BUILD_RESULT_JSON"

SCAN_STATUS="$(echo "$LAST_BODY" | jq -r '.status')"
if [[ "$SCAN_STATUS" == "completed" ]]; then
  kai_assert_graph_projection_loaded "$(echo "$BUILD_RESULT_JSON" | jq '{viewer_load_result}')"
fi

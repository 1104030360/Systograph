#!/usr/bin/env bash
# Trace: GET /api/detail-scans/{detail_scan_id}
#
# A detail scan must exist first, so this script imports + scans, creates a
# build-bound detail scan, then reads it back by id. Summary includes lineage
# ids and Track A child graph projection when viewer_load_result is present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

DETAIL_SCAN_ID=""
TARGET_TYPE="component_slot"

usage() {
  cat <<'USAGE'
Trace GET /api/detail-scans/{detail_scan_id}

Usage:
  scripts/trace_detail_scans_get.sh [common options] [--detail-scan-id ID]

Options:
  --detail-scan-id ID     Existing detail scan id. If omitted, one is created.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan when creating a detail scan.
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
    --detail-scan-id)
      i=$((i + 1))
      DETAIL_SCAN_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --detail-scan-id}"
      ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

if [[ -z "$DETAIL_SCAN_ID" ]]; then
  kai_section "準備：匯入 + 掃描 + 建立 detail scan"
  PROJECT_ID="$(kai_import_project)"
  SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
  BUILD_ID="$(echo "$SCAN_JSON" | jq -r '.build_result.lineage.build_id')"
  TARGET="$(echo "$SCAN_JSON" | jq -r '.build_result.ai_system_map.components_by_slot | keys[0]')"
  [[ -n "$BUILD_ID" && "$BUILD_ID" != "null" ]] \
    || kai_die "Scan response missing build_result.lineage.build_id"
  [[ -n "$TARGET" && "$TARGET" != "null" ]] \
    || kai_die "Could not derive a default target slot from the scan"
  kai_progress "現在要建立 detail scan（之後再依 id 讀回）..."
  DETAIL_BODY="$(setup_post "/api/detail-scans" \
    "$(jq -n --arg id "$PROJECT_ID" --arg build "$BUILD_ID" \
      --arg tt "$TARGET_TYPE" --arg t "$TARGET" \
      '{project_id:$id, build_id:$build, target_type:$tt, target:$t,
        scan_depth:"component"}')")"
  DETAIL_SCAN_ID="$(echo "$DETAIL_BODY" | jq -r '.detail_scan.id')"
  [[ -n "$DETAIL_SCAN_ID" && "$DETAIL_SCAN_ID" != "null" ]] \
    || kai_die "Failed to create a detail scan"
  kai_progress "已建立 detail_scan_id=$DETAIL_SCAN_ID"
fi

ENCODED_ID="$(kai_urlencode "$DETAIL_SCAN_ID")"
kai_section "讀取 detail scan：GET /api/detail-scans/{id}"
kai_progress "現在要依 id 讀回 detail scan..."
api_call GET "/api/detail-scans/$ENCODED_ID"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Detail scan 摘要（含 Track A child graph）"
echo "$LAST_BODY" | jq '{
  project_id,
  detail_scan_id: .detail_scan.id,
  target_type: .detail_scan.target_type,
  target: .detail_scan.target,
  status: .detail_scan.status,
  source_build_id,
  build_id,
  scan_id,
  child_graph: (
    if .viewer_load_result == null then null
    else {
      loaded: .viewer_load_result.loaded,
      node_count: (.viewer_load_result.graph_view_model.nodes | length)
    }
    end
  )
}'

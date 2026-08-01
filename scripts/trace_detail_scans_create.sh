#!/usr/bin/env bash
# Trace: POST /api/detail-scans
#
# Input  : {project_id, build_id?, target_type, target, scan_depth}
# Output : DetailScanResponse with child build lineage fields when build-bound,
#          plus optional viewer_load_result (Track A child graph projection).
#
# Phase2 S1: prefer explicit build_id so the detail scan binds to a parent build
# and publishes an immutable child build_id.
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
systograph_parse_common_args "$@"
i=0
while [[ $i -lt ${#SYSTOGRAPH_EXTRA_ARGS[@]} ]]; do
  arg="${SYSTOGRAPH_EXTRA_ARGS[$i]}"
  case "$arg" in
    --target-type)
      i=$((i + 1)); TARGET_TYPE="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --target-type}" ;;
    --target)
      i=$((i + 1)); TARGET="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --target}" ;;
    --scan-depth)
      i=$((i + 1)); SCAN_DEPTH="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --scan-depth}" ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
systograph_bootstrap_server

systograph_section "準備：匯入專案並掃描，取得 build_id"
PROJECT_ID="$(systograph_import_project)"
SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
BUILD_ID="$(echo "$SCAN_JSON" | jq -r '.build_result.lineage.build_id')"
[[ -n "$BUILD_ID" && "$BUILD_ID" != "null" ]] \
  || systograph_die "Scan response missing build_result.lineage.build_id"

if [[ -z "$TARGET" ]]; then
  TARGET="$(echo "$SCAN_JSON" | jq -r '.build_result.ai_system_map.components_by_slot | keys[0]')"
  [[ -n "$TARGET" && "$TARGET" != "null" ]] \
    || systograph_die "Could not derive a default target slot from the scan"
  systograph_progress "預設目標 ($TARGET_TYPE) = $TARGET"
fi

systograph_section "執行 detail scan：POST /api/detail-scans"
REQUEST_BODY="$(jq -n \
  --arg id "$PROJECT_ID" \
  --arg build "$BUILD_ID" \
  --arg tt "$TARGET_TYPE" \
  --arg t "$TARGET" \
  --arg sd "$SCAN_DEPTH" \
  '{project_id:$id, build_id:$build, target_type:$tt, target:$t, scan_depth:$sd}')"
systograph_progress "現在要對指定 build 做 detail scan（target=${TARGET}）..."
api_call POST "/api/detail-scans" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Detail scan 摘要（含 Track A child graph）"
echo "$LAST_BODY" | jq '{
  detail_scan_id: .detail_scan.id,
  target_type: .detail_scan.target_type,
  target: .detail_scan.target,
  scan_depth: .detail_scan.scan_depth,
  status: .detail_scan.status,
  source_build_id,
  build_id,
  scan_id,
  finding_count: (.detail_scan.findings | length),
  evidence_total: (.ai_system_map.evidence | length),
  warnings,
  child_graph: (
    if .viewer_load_result == null then null
    else {
      loaded: .viewer_load_result.loaded,
      node_count: (.viewer_load_result.graph_view_model.nodes | length),
      edge_count: (.viewer_load_result.graph_view_model.edges | length),
      relationship_count: ((.viewer_load_result.graph_view_model.relationships // []) | length)
    }
    end
  )
}'

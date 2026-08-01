#!/usr/bin/env bash
# Trace: POST /api/map/build
#
# Input  : {project_path, output, redact_root_path, no_snippets}
# Output : MapBuildResult {status, project_name, output_run_dir, map_json_path,
#          map_markdown_path, profile_signals_path, viewer_load_result,
#          ai_system_map, warnings, error} — Track A graph projection lives
#          under viewer_load_result.graph_view_model.
#
# This is the all-in-one demo endpoint: it scans a path and stores the latest
# viewer payload in one call (no prior import needed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace POST /api/map/build

Usage:
  scripts/trace_map_build.sh [common options]

Common options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Local project path to scan and build.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
systograph_parse_common_args "$@"
[[ ${#SYSTOGRAPH_EXTRA_ARGS[@]} -eq 0 ]] || systograph_die "Unknown option: ${SYSTOGRAPH_EXTRA_ARGS[*]}"
[[ -d "$PROJECT_PATH" ]] || systograph_die "Project path does not exist: $PROJECT_PATH"
systograph_bootstrap_server

systograph_section "Demo 建圖：POST /api/map/build"
REQUEST_BODY="$(jq -n --arg p "$PROJECT_PATH" --arg out "$OUTPUT_DIR" \
  '{project_path:$p, output:$out, redact_root_path:true, no_snippets:false}')"
systograph_progress "現在要用 path 一次掃描並建圖（demo 流程）..."
api_call POST "/api/map/build" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "結果摘要（含 Track A graph projection）"
systograph_summarize_map_build_result "$LAST_BODY"

BUILD_STATUS="$(echo "$LAST_BODY" | jq -r '.status')"
VIEWER_PRESENT="$(echo "$LAST_BODY" | jq -r '.viewer_load_result != null')"
if [[ "$BUILD_STATUS" == "ok" && "$VIEWER_PRESENT" == "true" ]]; then
  systograph_assert_graph_projection_loaded "$(echo "$LAST_BODY" | jq '{viewer_load_result}')"
fi

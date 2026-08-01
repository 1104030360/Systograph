#!/usr/bin/env bash
# Trace: POST /api/viewer/load
#
# Input  : {map_json_path:"outputs/.../ai_system_map.json"}
# Output : ViewerPayload built by re-validating an existing ai_system_map.json.
#          Includes Track A graph_view_model projection (schema_version, lenses,
#          relationships, reference_assessments). Invalid maps still return
#          HTTP 200 with loaded:false + error_reason.
#
# This endpoint does NOT scan a project. It loads a map file from disk, so the
# script first builds one to obtain a real map_json_path (unless --map-json-path
# is supplied).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

MAP_JSON_PATH=""

usage() {
  cat <<'USAGE'
Trace POST /api/viewer/load

Usage:
  scripts/trace_viewer_load.sh [common options] [--map-json-path PATH]

Options:
  --map-json-path PATH    Existing ai_system_map.json to load. If omitted, a
                          map is built first and its map_json_path is reused.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to build when no --map-json-path is given.
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
    --map-json-path)
      i=$((i + 1))
      MAP_JSON_PATH="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --map-json-path}"
      ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
systograph_bootstrap_server

if [[ -z "$MAP_JSON_PATH" ]]; then
  systograph_section "準備：先建圖取得 map_json_path"
  systograph_progress "現在要先呼叫 map/build 取得地圖檔路徑..."
  BUILD_JSON="$(setup_post "/api/map/build" \
    "$(jq -n --arg p "$PROJECT_PATH" --arg out "$OUTPUT_DIR" \
      '{project_path:$p, output:$out, redact_root_path:true, no_snippets:false}')")"
  MAP_JSON_PATH="$(echo "$BUILD_JSON" | jq -r '.map_json_path')"
  [[ -n "$MAP_JSON_PATH" && "$MAP_JSON_PATH" != "null" ]] \
    || systograph_die "Build did not return a map_json_path"
  systograph_progress "已取得 map_json_path=$MAP_JSON_PATH"
fi

systograph_section "載入 Viewer：POST /api/viewer/load"
REQUEST_BODY="$(jq -n --arg path "$MAP_JSON_PATH" '{map_json_path:$path}')"
systograph_progress "現在要從磁碟載入 ai_system_map.json 到 viewer..."
api_call POST "/api/viewer/load" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Graph projection 摘要（Track A）"
systograph_summarize_viewer_payload "$LAST_BODY"
# map_json_path was resolved above; expect a loaded projection.
systograph_assert_graph_projection_loaded "$LAST_BODY"

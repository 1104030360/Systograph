#!/usr/bin/env bash
# Trace: POST /api/map/build
#
# Input  : {project_path, output, redact_root_path, no_snippets}
# Output : MapBuildResult {status, project_name, output_run_dir, map_json_path,
#          map_markdown_path, viewer_load_result, ai_system_map, warnings, error}
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
kai_parse_common_args "$@"
[[ ${#KAI_EXTRA_ARGS[@]} -eq 0 ]] || kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
[[ -d "$PROJECT_PATH" ]] || kai_die "Project path does not exist: $PROJECT_PATH"
kai_bootstrap_server

kai_section "POST /api/map/build"
REQUEST_BODY="$(jq -n --arg p "$PROJECT_PATH" --arg out "$OUTPUT_DIR" \
  '{project_path:$p, output:$out, redact_root_path:true, no_snippets:false}')"
api_call POST "/api/map/build" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Result summary"
echo "$LAST_BODY" | jq '{
  status,
  project_name,
  output_run_dir,
  map_json_path,
  map_markdown_path,
  node_count: (.ai_system_map.components_by_slot | length),
  unmapped_count: (.ai_system_map.unmapped_components | length),
  warnings
}'

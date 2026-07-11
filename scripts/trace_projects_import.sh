#!/usr/bin/env bash
# Trace: POST /api/projects/import
#
# Input  : {source_type:"local_path", project_path:<abs path>}
# Output : {project_id, source_type, project_name, project_path}
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace POST /api/projects/import

Usage:
  scripts/trace_projects_import.sh [common options]

Common options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Local project path to import.
  --output DIR            Scan output dir (unused here). Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
[[ ${#KAI_EXTRA_ARGS[@]} -eq 0 ]] || kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
[[ -d "$PROJECT_PATH" ]] || kai_die "Project path does not exist: $PROJECT_PATH"
kai_bootstrap_server

kai_section "匯入專案：POST /api/projects/import"
REQUEST_BODY="$(jq -n --arg p "$PROJECT_PATH" \
  '{source_type:"local_path", project_path:$p}')"
kai_progress "現在要匯入專案：$PROJECT_PATH"
api_call POST "/api/projects/import" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
echo "project_id => $(echo "$LAST_BODY" | jq -r '.project_id')"

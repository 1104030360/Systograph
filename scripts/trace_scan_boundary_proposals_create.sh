#!/usr/bin/env bash
# Trace: POST /api/scan-boundary-proposals
#
# Input  : {project_id}
# Output : ScanBoundaryProposalListResponse {project_id, proposals:[...],
#          available_actions:[...]}
#
# By default this script creates a temporary demo project containing `.env` so
# the endpoint returns at least one boundary proposal. Pass --use-project-path
# to scan the common --project-path instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROJECT_ID=""
USE_PROJECT_PATH=0
DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace POST /api/scan-boundary-proposals

Usage:
  scripts/trace_scan_boundary_proposals_create.sh [common options] \
    [--project-id ID] [--use-project-path]

Options:
  --project-id ID         Existing project_id with a loaded map (skip setup).
  --use-project-path      Use --project-path instead of a temporary demo project.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import/scan when --use-project-path is set.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

make_demo_project() {
  DEMO_PROJECT_DIR="$(mktemp -d)"
  mkdir -p "$DEMO_PROJECT_DIR/src"
  printf '%s\n' 'OPENAI_API_KEY=sk-live-secret-value' \
    >"$DEMO_PROJECT_DIR/.env"
  printf '%s\n' 'print("hello")' >"$DEMO_PROJECT_DIR/src/app.py"
  echo "$DEMO_PROJECT_DIR"
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
    --use-project-path)
      USE_PROJECT_PATH=1
      ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

if [[ -z "$PROJECT_ID" ]]; then
  kai_section "Setup: import + scan project"
  if [[ "$USE_PROJECT_PATH" -eq 1 ]]; then
    PROJECT_ID="$(kai_import_project "$PROJECT_PATH")"
  else
    PROJECT_ID="$(kai_import_project "$(make_demo_project)")"
  fi
  kai_run_scan "$PROJECT_ID" >/dev/null
fi

kai_section "POST /api/scan-boundary-proposals"
REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" '{project_id:$id}')"
api_call POST "/api/scan-boundary-proposals" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Scan boundary proposal summary"
echo "$LAST_BODY" | jq '{
  project_id,
  proposal_count: (.proposals | length),
  available_actions,
  proposals: [.proposals[] | {
    proposal_id,
    status,
    path: .target.path,
    risk_type: .target.risk_type,
    fingerprint: .target.fingerprint
  }]
}'

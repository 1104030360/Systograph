#!/usr/bin/env bash
# Trace: POST /api/scan-boundary-proposals/{proposal_id}/decision
#
# Input  : ScanBoundaryDecisionRequest {decision, reason?}
# Output : ScanBoundaryDecisionResult {proposal, decision}
#
# A pending boundary proposal must exist first, so this script creates a
# temporary demo project by default. Pass --proposal-id to decide directly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROPOSAL_ID=""
DECISION="skip_this_run"
REASON="API trace decision."
USE_PROJECT_PATH=0
DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace POST /api/scan-boundary-proposals/{proposal_id}/decision

Usage:
  scripts/trace_scan_boundary_proposals_decision.sh [common options] \
    [--proposal-id ID] \
    [--decision skip_this_run|always_skip|metadata_only|masked_summary_only|scan_normally] \
    [--reason TEXT] [--use-project-path]

Options:
  --proposal-id ID        Existing pending proposal id. If omitted, one is created.
  --decision DECISION     Default: skip_this_run.
  --reason TEXT           Optional reason attached to the decision.
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
    --proposal-id)
      i=$((i + 1)); PROPOSAL_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --proposal-id}" ;;
    --decision)
      i=$((i + 1)); DECISION="${KAI_EXTRA_ARGS[$i]:?missing value for --decision}" ;;
    --reason)
      i=$((i + 1)); REASON="${KAI_EXTRA_ARGS[$i]:?missing value for --reason}" ;;
    --use-project-path)
      USE_PROJECT_PATH=1
      ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done

case "$DECISION" in
  skip_this_run|always_skip|metadata_only|masked_summary_only|scan_normally) ;;
  *) kai_die "Unsupported --decision: $DECISION" ;;
esac
kai_bootstrap_server

if [[ -z "$PROPOSAL_ID" ]]; then
  kai_section "Setup: import + scan + create a pending boundary proposal"
  if [[ "$USE_PROJECT_PATH" -eq 1 ]]; then
    PROJECT_ID="$(kai_import_project "$PROJECT_PATH")"
  else
    PROJECT_ID="$(kai_import_project "$(make_demo_project)")"
  fi
  kai_run_scan "$PROJECT_ID" >/dev/null
  REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" '{project_id:$id}')"
  PROPOSAL_JSON="$(setup_post "/api/scan-boundary-proposals" "$REQUEST_BODY")"
  PROPOSAL_ID="$(echo "$PROPOSAL_JSON" | jq -r '.proposals[0].proposal_id // empty')"
  [[ -n "$PROPOSAL_ID" ]] \
    || kai_die "Failed to create a scan boundary proposal"
  echo "[setup] proposal_id=$PROPOSAL_ID" >&2
fi

kai_section "POST /api/scan-boundary-proposals/{proposal_id}/decision"
REQUEST_BODY="$(jq -n \
  --arg decision "$DECISION" \
  --arg reason "$REASON" \
  '{decision:$decision}
   + (if $reason == "" then {} else {reason:$reason} end)')"
ENCODED_ID="$(kai_urlencode "$PROPOSAL_ID")"
api_call POST "/api/scan-boundary-proposals/$ENCODED_ID/decision" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Scan boundary decision summary"
echo "$LAST_BODY" | jq '{
  proposal_id: .proposal.proposal_id,
  proposal_status: .proposal.status,
  decision_id: .decision.decision_id,
  decision: .decision.decision,
  target_path: .decision.target.path
}'

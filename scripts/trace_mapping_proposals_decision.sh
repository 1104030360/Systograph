#!/usr/bin/env bash
# Trace: POST /api/mapping-proposals/{proposal_id}/decision
#
# Input  : MappingProposalDecisionRequest {decision, candidate_id?, edited_mapping?, reason?}
#          - accept       -> requires candidate_id (no edited_mapping)
#          - reject        -> no candidate_id / edited_mapping
#          - skip_for_now  -> no candidate_id / edited_mapping
#          - edit          -> requires edited_mapping (use --body-file)
# Output : MappingProposalDecisionResult {proposal, manual_mapping?}
#          404 proposal_not_found, 422 on invalid decision payload.
#
# A pending proposal must exist first, so this script imports + scans + creates
# one proposal, then applies a decision (default: accept).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROPOSAL_ID=""
DECISION="accept"
CANDIDATE_ID=""
REASON=""

usage() {
  cat <<'USAGE'
Trace POST /api/mapping-proposals/{proposal_id}/decision

Usage:
  scripts/trace_mapping_proposals_decision.sh [common options] \
    [--proposal-id ID] [--decision accept|reject|skip_for_now] \
    [--candidate-id ID] [--reason TEXT]

Options:
  --proposal-id ID        Existing pending proposal id. If omitted, one is created.
  --decision DECISION     accept | reject | skip_for_now. Default: accept
  --candidate-id ID       Candidate to accept. Auto-selected for accept if omitted.
  --reason TEXT           Optional reason attached to the decision.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import/scan when creating a proposal.
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
    --proposal-id)
      i=$((i + 1)); PROPOSAL_ID="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --proposal-id}" ;;
    --decision)
      i=$((i + 1)); DECISION="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --decision}" ;;
    --candidate-id)
      i=$((i + 1)); CANDIDATE_ID="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --candidate-id}" ;;
    --reason)
      i=$((i + 1)); REASON="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --reason}" ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done

case "$DECISION" in
  accept|reject|skip_for_now) ;;
  edit) systograph_die "edit requires a custom edited_mapping payload; not supported by this trace script" ;;
  *) systograph_die "Unsupported --decision: $DECISION" ;;
esac
systograph_bootstrap_server

if [[ -z "$PROPOSAL_ID" ]]; then
  systograph_section "準備：匯入 + 掃描 + 建立 pending proposal"
  PROJECT_ID="$(systograph_import_project)"
  SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
  UNMAPPED_ID="$(systograph_first_unmapped_id "$SCAN_JSON")"
  [[ -n "$UNMAPPED_ID" ]] \
    || systograph_die "Scan produced no unmapped component; try --project-path with one"
  PROPOSAL_JSON="$(systograph_create_proposal "$PROJECT_ID" "$UNMAPPED_ID")"
  PROPOSAL_ID="$(echo "$PROPOSAL_JSON" | jq -r '.proposal_id')"
  [[ -n "$PROPOSAL_ID" && "$PROPOSAL_ID" != "null" ]] \
    || systograph_die "Failed to create a proposal"
  systograph_progress "已建立 proposal_id=$PROPOSAL_ID"
  if [[ "$DECISION" == "accept" && -z "$CANDIDATE_ID" ]]; then
    CANDIDATE_ID="$(echo "$PROPOSAL_JSON" | jq -r '
      [.candidates[]
       | select(.candidate_id != null)
       | select(.candidate_type == "existing_slot_mapping" or .candidate_type == "non_baseline_capability_candidate")
       | .candidate_id][0] // empty')"
    [[ -n "$CANDIDATE_ID" ]] \
      || systograph_die "No acceptable candidate to auto-select; use --decision skip_for_now or pass --candidate-id"
    systograph_progress "自動選取 candidate_id=$CANDIDATE_ID"
  fi
fi

if [[ "$DECISION" == "accept" && -z "$CANDIDATE_ID" ]]; then
  systograph_die "accept requires --candidate-id"
fi

systograph_section "送出決策：POST /api/mapping-proposals/{id}/decision"
REQUEST_BODY="$(jq -n \
  --arg decision "$DECISION" \
  --arg candidate_id "$CANDIDATE_ID" \
  --arg reason "$REASON" \
  '{decision:$decision}
   + (if $candidate_id == "" then {} else {candidate_id:$candidate_id} end)
   + (if $reason == "" then {} else {reason:$reason} end)')"
ENCODED_ID="$(systograph_urlencode "$PROPOSAL_ID")"
systograph_progress "現在要對 proposal 送出決策（decision=${DECISION}）..."
api_call POST "/api/mapping-proposals/$ENCODED_ID/decision" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Decision summary"
echo "$LAST_BODY" | jq '{
  proposal_id: .proposal.proposal_id,
  proposal_status: .proposal.status,
  manual_mapping_id: (.manual_mapping.mapping_id // null),
  manual_mapping_decision: (.manual_mapping.decision // null)
}'
systograph_progress "已完成 decision=${DECISION} trace；manual mapping / audit 結果如上。"

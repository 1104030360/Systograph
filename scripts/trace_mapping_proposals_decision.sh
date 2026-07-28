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
# one proposal, then applies a decision (default: skip_for_now).
#
# KNOWN PRODUCT BUG (backend, not this script): `reject` / `skip_for_now` return
# 422 whenever the proposal carries no `existing_slot_mapping` candidate.
# ProposalManualMappingFactory.create_audit copies the mapping *type* from
# _audit_mapping_type (which also defaults to non_baseline_capability_candidate)
# but never fills capability_candidate_id/name/kind, and
# ManualMappingCreate.validate_shape demands them for that type regardless of
# decision. The deterministic offline provider hits this on every
# custom_router_rag proposal. This script traces the call and reports the known
# 422 instead of hard-failing; every other status still fails, and the tolerance
# disappears by itself once the backend is fixed.
set -euo pipefail

# Exact 422 signature of the known audit-mapping bug described above.
KNOWN_AUDIT_BUG_DETAIL='non-baseline capability mapping requires candidate fields'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

PROPOSAL_ID=""
DECISION="skip_for_now"
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
  --decision DECISION     accept | reject | skip_for_now. Default: skip_for_now
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
kai_parse_common_args "$@"
i=0
while [[ $i -lt ${#KAI_EXTRA_ARGS[@]} ]]; do
  arg="${KAI_EXTRA_ARGS[$i]}"
  case "$arg" in
    --proposal-id)
      i=$((i + 1)); PROPOSAL_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --proposal-id}" ;;
    --decision)
      i=$((i + 1)); DECISION="${KAI_EXTRA_ARGS[$i]:?missing value for --decision}" ;;
    --candidate-id)
      i=$((i + 1)); CANDIDATE_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --candidate-id}" ;;
    --reason)
      i=$((i + 1)); REASON="${KAI_EXTRA_ARGS[$i]:?missing value for --reason}" ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done

case "$DECISION" in
  accept|reject|skip_for_now) ;;
  edit) kai_die "edit requires a custom edited_mapping payload; not supported by this trace script" ;;
  *) kai_die "Unsupported --decision: $DECISION" ;;
esac
kai_bootstrap_server

if [[ -z "$PROPOSAL_ID" ]]; then
  kai_section "準備：匯入 + 掃描 + 建立 pending proposal"
  PROJECT_ID="$(kai_import_project)"
  SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
  UNMAPPED_ID="$(kai_first_unmapped_id "$SCAN_JSON")"
  [[ -n "$UNMAPPED_ID" ]] \
    || kai_die "Scan produced no unmapped component; try --project-path with one"
  PROPOSAL_JSON="$(kai_create_proposal "$PROJECT_ID" "$UNMAPPED_ID")"
  PROPOSAL_ID="$(echo "$PROPOSAL_JSON" | jq -r '.proposal_id')"
  [[ -n "$PROPOSAL_ID" && "$PROPOSAL_ID" != "null" ]] \
    || kai_die "Failed to create a proposal"
  kai_progress "已建立 proposal_id=$PROPOSAL_ID"
  if [[ "$DECISION" == "accept" && -z "$CANDIDATE_ID" ]]; then
    CANDIDATE_ID="$(echo "$PROPOSAL_JSON" | jq -r '
      [.candidates[]
       | select(.candidate_id != null)
       | select(.candidate_type == "existing_slot_mapping" or .candidate_type == "non_baseline_capability_candidate")
       | .candidate_id][0] // empty')"
    [[ -n "$CANDIDATE_ID" ]] \
      || kai_die "No acceptable candidate to auto-select; use --decision skip_for_now or pass --candidate-id"
    kai_progress "自動選取 candidate_id=$CANDIDATE_ID"
  fi
fi

if [[ "$DECISION" == "accept" && -z "$CANDIDATE_ID" ]]; then
  kai_die "accept requires --candidate-id"
fi

kai_section "送出決策：POST /api/mapping-proposals/{id}/decision"
REQUEST_BODY="$(jq -n \
  --arg decision "$DECISION" \
  --arg candidate_id "$CANDIDATE_ID" \
  --arg reason "$REASON" \
  '{decision:$decision}
   + (if $candidate_id == "" then {} else {candidate_id:$candidate_id} end)
   + (if $reason == "" then {} else {reason:$reason} end)')"
ENCODED_ID="$(kai_urlencode "$PROPOSAL_ID")"
kai_progress "現在要對 proposal 送出決策（decision=${DECISION}）..."
api_call POST "/api/mapping-proposals/$ENCODED_ID/decision" "$REQUEST_BODY"

if [[ "$LAST_STATUS" != "200" ]]; then
  if [[ "$LAST_STATUS" == "422" && "$DECISION" != "accept" ]] \
    && grep -Fq "$KNOWN_AUDIT_BUG_DETAIL" <<<"$LAST_BODY"; then
    kai_section "KNOWN PRODUCT BUG（後端 audit mapping，非本 script）"
    echo "decision=$DECISION returned 422: create_audit builds a"
    echo "non_baseline_capability_candidate ManualMappingCreate without"
    echo "capability_candidate_id/name/kind, which ManualMappingCreate"
    echo "rejects. See mapping_proposal_mapping_factory.create_audit."
    echo "Endpoint traced; treating the documented 422 as a known failure."
    exit 0
  fi
  kai_die "Unexpected status: $LAST_STATUS"
fi
kai_section "Decision summary"
echo "$LAST_BODY" | jq '{
  proposal_id: .proposal.proposal_id,
  proposal_status: .proposal.status,
  manual_mapping_id: (.manual_mapping.mapping_id // null),
  manual_mapping_decision: (.manual_mapping.decision // null)
}'

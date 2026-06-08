#!/usr/bin/env bash
# Trace: POST /api/mapping-proposals
#
# Input  : {project_id, source_unmapped_id, user_description?}
# Output : MappingProposal {proposal_id, status:"pending_user_confirmation",
#          candidates:[...], provider_name, provider_error_reason, ...}
#          404 project_not_found / map_not_loaded / unmapped_not_found.
#
# Requires an unmapped component, so this script imports + scans, then proposes
# a mapping for the first unmapped component. Without NVIDIA_API_KEY the backend
# falls back to a deterministic provider, so this still works offline.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

UNMAPPED_ID=""
USER_DESCRIPTION=""

usage() {
  cat <<'USAGE'
Trace POST /api/mapping-proposals

Usage:
  scripts/trace_mapping_proposals_create.sh [common options] \
    [--unmapped-id ID] [--description TEXT]

Options:
  --unmapped-id ID        Specific unmapped component id. Default: first found.
  --description TEXT       Optional user_description sent with the proposal.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan (must yield unmapped items).
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.

Note:
  Set NVIDIA_API_KEY in .env to exercise the real NVIDIA NIM provider; without
  it the proposal endpoint returns a deterministic fallback candidate set.
USAGE
}

require_tools
kai_parse_common_args "$@"
i=0
while [[ $i -lt ${#KAI_EXTRA_ARGS[@]} ]]; do
  arg="${KAI_EXTRA_ARGS[$i]}"
  case "$arg" in
    --unmapped-id)
      i=$((i + 1)); UNMAPPED_ID="${KAI_EXTRA_ARGS[$i]:?missing value for --unmapped-id}" ;;
    --description)
      i=$((i + 1)); USER_DESCRIPTION="${KAI_EXTRA_ARGS[$i]:?missing value for --description}" ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

kai_section "Setup: import + scan to obtain an unmapped component"
PROJECT_ID="$(kai_import_project)"
SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
if [[ -z "$UNMAPPED_ID" ]]; then
  UNMAPPED_ID="$(kai_first_unmapped_id "$SCAN_JSON")"
  [[ -n "$UNMAPPED_ID" ]] \
    || kai_die "Scan produced no unmapped component; try --project-path with one"
  echo "[setup] unmapped_id=$UNMAPPED_ID" >&2
fi

kai_section "POST /api/mapping-proposals"
if [[ -n "$USER_DESCRIPTION" ]]; then
  REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" --arg u "$UNMAPPED_ID" --arg d "$USER_DESCRIPTION" \
    '{project_id:$id, source_unmapped_id:$u, user_description:$d}')"
else
  REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" --arg u "$UNMAPPED_ID" \
    '{project_id:$id, source_unmapped_id:$u}')"
fi
api_call POST "/api/mapping-proposals" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
kai_section "Proposal summary"
echo "$LAST_BODY" | jq '{
  proposal_id,
  status,
  provider_name,
  provider_error_reason,
  source_unmapped_id,
  candidate_count: (.candidates | length),
  candidates: [.candidates[] | {candidate_id, candidate_type, recommendation_level, target_slot, component_name}]
}'

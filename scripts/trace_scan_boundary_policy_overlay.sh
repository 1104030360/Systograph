#!/usr/bin/env bash
# Trace: scan boundary policy overlay behavior across two scans.
#
# This verifies the Phase 24 safety behavior:
# 1. An unresolved `.env` is held as pending boundary review on the first scan.
# 2. A `scan_normally` decision allows the matching file on the next scan.
# 3. Raw secret values are not returned in scan/proposal responses.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace scan boundary policy overlay behavior.

Usage:
  scripts/trace_scan_boundary_policy_overlay.sh [common options]

Options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
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

jq_get() {
  local json="$1"
  local filter="$2"
  echo "$json" | jq -r "$filter"
}

require_tools
kai_parse_common_args "$@"
if [[ ${#KAI_EXTRA_ARGS[@]} -gt 0 ]]; then
  kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
fi
kai_bootstrap_server

kai_section "Setup: import demo project with .env"
PROJECT_ID="$(kai_import_project "$(make_demo_project)")"

kai_section "First scan: unresolved .env must not enter provider collection"
FIRST_SCAN="$(kai_run_scan "$PROJECT_ID")"
FIRST_SCANNED="$(jq_get "$FIRST_SCAN" '.build_result.ai_system_map.scan_summary.files_scanned')"
FIRST_SKIPPED="$(jq_get "$FIRST_SCAN" '.build_result.ai_system_map.scan_summary.files_skipped')"
[[ "$FIRST_SCANNED" == "1" ]] \
  || kai_die "Expected first scan files_scanned=1, got $FIRST_SCANNED"
[[ "$FIRST_SKIPPED" -ge 1 ]] \
  || kai_die "Expected first scan files_skipped >= 1, got $FIRST_SKIPPED"
if grep -q 'sk-live-secret-value' <<<"$FIRST_SCAN"; then
  kai_die "Raw secret leaked in first scan response"
fi
echo "$FIRST_SCAN" | jq '{
  scan_id,
  files_scanned: .build_result.ai_system_map.scan_summary.files_scanned,
  files_skipped: .build_result.ai_system_map.scan_summary.files_skipped
}'

kai_section "Create scan boundary proposal"
REQUEST_BODY="$(jq -n --arg id "$PROJECT_ID" '{project_id:$id}')"
PROPOSAL_JSON="$(setup_post "/api/scan-boundary-proposals" "$REQUEST_BODY")"
PROPOSAL_ID="$(jq_get "$PROPOSAL_JSON" '.proposals[0].proposal_id // empty')"
TARGET_PATH="$(jq_get "$PROPOSAL_JSON" '.proposals[0].target.path // empty')"
[[ -n "$PROPOSAL_ID" ]] || kai_die "Expected a pending proposal"
[[ "$TARGET_PATH" == ".env" ]] \
  || kai_die "Expected proposal target .env, got $TARGET_PATH"
if grep -q 'sk-live-secret-value' <<<"$PROPOSAL_JSON"; then
  kai_die "Raw secret leaked in proposal response"
fi
echo "$PROPOSAL_JSON" | jq '{
  proposal_count: (.proposals | length),
  proposal_id: .proposals[0].proposal_id,
  status: .proposals[0].status,
  target_path: .proposals[0].target.path,
  risk_type: .proposals[0].target.risk_type,
  raw_file_contents_included: .proposals[0].evidence_packet.context_limits.raw_file_contents_included
}'

kai_section "Decision: scan_normally"
DECISION_BODY="$(jq -n \
  '{decision:"scan_normally", reason:"Approved for trace verification."}')"
ENCODED_ID="$(kai_urlencode "$PROPOSAL_ID")"
api_call POST "/api/scan-boundary-proposals/$ENCODED_ID/decision" "$DECISION_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected decision status: $LAST_STATUS"

kai_section "Second scan: scan_normally allows matching .env"
SECOND_SCAN="$(kai_run_scan "$PROJECT_ID")"
SECOND_SCANNED="$(jq_get "$SECOND_SCAN" '.build_result.ai_system_map.scan_summary.files_scanned')"
[[ "$SECOND_SCANNED" == "2" ]] \
  || kai_die "Expected second scan files_scanned=2, got $SECOND_SCANNED"
if grep -q 'sk-live-secret-value' <<<"$SECOND_SCAN"; then
  kai_die "Raw secret leaked in second scan response"
fi
if ! grep -q 'OPENAI_API_KEY' <<<"$SECOND_SCAN"; then
  kai_die "Expected masked config evidence for OPENAI_API_KEY in second scan"
fi
echo "$SECOND_SCAN" | jq '{
  scan_id,
  files_scanned: .build_result.ai_system_map.scan_summary.files_scanned,
  files_skipped: .build_result.ai_system_map.scan_summary.files_skipped,
  secret_masking_applied: .build_result.ai_system_map.scan_summary.secret_masking_applied
}'

kai_section "PASS"
echo "scan boundary policy overlay behavior is correct"

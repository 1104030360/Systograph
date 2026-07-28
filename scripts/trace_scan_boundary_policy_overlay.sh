#!/usr/bin/env bash
# Trace: scan boundary same-run gate behavior.
#
# This verifies the Phase 24 safety behavior:
# 1. A scan with unresolved `.env` returns requires_boundary_decision.
# 2. Supplying `scan_this_run` decisions lets the current scan complete.
# 3. Decisions are not remembered; the next scan asks again.
# 4. Raw secret values are not returned in scan/proposal responses.
# 5. A completed scan writes a readable ai_system_map.json artifact.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace scan boundary same-run gate behavior.

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

run_scan_body() {
  local project_id="$1"
  local output_dir="$2"
  local boundary_decisions="${3:-[]}"
  jq -n \
    --arg id "$project_id" \
    --arg out "$output_dir" \
    --argjson decisions "$boundary_decisions" \
    '{project_id:$id, scan_depth:"system", output:$out,
      redact_root_path:true, no_snippets:false,
      boundary_decisions:$decisions}'
}

require_tools
kai_parse_common_args "$@"
if [[ ${#KAI_EXTRA_ARGS[@]} -gt 0 ]]; then
  kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
fi
kai_bootstrap_server

kai_section "準備：匯入含 .env 的 demo 專案"
PROJECT_ID="$(kai_import_project "$(make_demo_project)")"

kai_section "第一次掃描：未確認 .env，應要求 boundary decision"
FIRST_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR")"
kai_progress "現在要建立 scan（預期回 requires_boundary_decision）..."
api_call POST "/api/scans" "$FIRST_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected first scan HTTP: $LAST_STATUS"
FIRST_SCAN="$LAST_BODY"
FIRST_STATUS="$(jq_get "$FIRST_SCAN" '.status')"
[[ "$FIRST_STATUS" == "requires_boundary_decision" ]] \
  || kai_die "Expected requires_boundary_decision, got $FIRST_STATUS"
PROPOSAL_ID="$(jq_get "$FIRST_SCAN" '.boundary_proposals[0].proposal_id // empty')"
TARGET_PATH="$(jq_get "$FIRST_SCAN" '.boundary_proposals[0].target.path // empty')"
FINGERPRINT="$(jq_get "$FIRST_SCAN" '.boundary_proposals[0].target.fingerprint // empty')"
[[ -n "$PROPOSAL_ID" && "$TARGET_PATH" == ".env" && -n "$FINGERPRINT" ]] \
  || kai_die "Expected one .env boundary proposal"
if grep -q 'sk-live-secret-value' <<<"$FIRST_SCAN"; then
  kai_die "Raw secret leaked in first scan response"
fi

kai_section "第二次掃描：送出 scan_this_run 完成本次掃描"
DECISIONS="$(jq -n \
  --arg path "$TARGET_PATH" \
  --arg fingerprint "$FINGERPRINT" \
  '[{target_path:$path, fingerprint:$fingerprint, decision:"scan_this_run"}]')"
SECOND_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$DECISIONS")"
kai_progress "接著帶 boundary_decisions 再呼叫 scan..."
api_call POST "/api/scans" "$SECOND_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected second scan HTTP: $LAST_STATUS"
SECOND_SCAN="$LAST_BODY"
SECOND_STATUS="$(jq_get "$SECOND_SCAN" '.status')"
# ai-system-map/v2 dropped scan_summary; per-run file counts now live on the
# scan response as inventory_selection_summary.
SECOND_SCANNED="$(jq_get \
  "$SECOND_SCAN" \
  '.inventory_selection_summary.included_file_count')"
SECOND_MAP_JSON_PATH="$(jq_get "$SECOND_SCAN" '.build_result.map_json_path // empty')"
[[ "$SECOND_STATUS" == "completed" ]] \
  || kai_die "Expected completed second scan, got $SECOND_STATUS"
[[ "$SECOND_SCANNED" == "2" ]] \
  || kai_die "Expected second scan included_file_count=2, got $SECOND_SCANNED"
[[ -f "$SECOND_MAP_JSON_PATH" ]] \
  || kai_die "Expected map_json_path to exist: $SECOND_MAP_JSON_PATH"
# The stored artifact carries the identity pair instead of a count summary.
STORED_MAP="$(cat "$SECOND_MAP_JSON_PATH")"
[[ "$(jq_get "$STORED_MAP" '.scan_id')" == "$(jq_get "$SECOND_SCAN" '.scan_id')" ]] \
  || kai_die "Stored ai_system_map.json scan_id did not match response"
[[ "$(jq_get "$STORED_MAP" '.build_id')" \
   == "$(jq_get "$SECOND_SCAN" '.build_result.lineage.build_id')" ]] \
  || kai_die "Stored ai_system_map.json build_id did not match response"
if grep -q 'sk-live-secret-value' <<<"$SECOND_SCAN"; then
  kai_die "Raw secret leaked in second scan response"
fi
if grep -q 'sk-live-secret-value' "$SECOND_MAP_JSON_PATH"; then
  kai_die "Raw secret leaked in stored ai_system_map.json"
fi

kai_section "第三次掃描：確認 decision 不會被記住"
THIRD_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR")"
kai_progress "再次建立 scan（預期又要求 boundary decision）..."
api_call POST "/api/scans" "$THIRD_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected third scan HTTP: $LAST_STATUS"
THIRD_STATUS="$(jq_get "$LAST_BODY" '.status')"
[[ "$THIRD_STATUS" == "requires_boundary_decision" ]] \
  || kai_die "Expected requires_boundary_decision third scan, got $THIRD_STATUS"

kai_section "PASS"
echo "scan boundary same-run gate behavior is correct"

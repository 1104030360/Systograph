#!/usr/bin/env bash
# Trace: scan boundary same-run gate behavior.
#
# This verifies the safety behavior on the explicit preflight flow:
# 1. The preflight lists `.env` as a required decision, and a scan that carries
#    the preflight_request_id but no decision returns requires_boundary_decision.
# 2. Supplying `scan_this_run` decisions lets the current scan complete.
# 3. Decisions are not remembered; the next preflight/scan asks again.
# 4. Raw secret values are not returned in preflight/scan/proposal responses.
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
  local preflight_id="$3"
  local boundary_decisions="${4:-[]}"
  jq -n \
    --arg id "$project_id" \
    --arg out "$output_dir" \
    --arg preflight_id "$preflight_id" \
    --argjson decisions "$boundary_decisions" \
    '{project_id:$id, scan_depth:"system", output:$out,
      redact_root_path:true, no_snippets:false,
      preflight_request_id:$preflight_id,
      boundary_decisions:$decisions}'
}

open_preflight() {
  local project_id="$1"
  systograph_progress "現在要開 preflight（metadata-only，不建立 scan）..."
  api_call POST "/api/projects/${project_id}/scan-preflights" \
    '{"requested_paths":[]}'
  [[ "$LAST_STATUS" == "200" ]] \
    || systograph_die "Unexpected preflight HTTP: $LAST_STATUS"
}

require_tools
systograph_parse_common_args "$@"
if [[ ${#SYSTOGRAPH_EXTRA_ARGS[@]} -gt 0 ]]; then
  systograph_die "Unknown option: ${SYSTOGRAPH_EXTRA_ARGS[*]}"
fi
systograph_bootstrap_server

systograph_section "準備：匯入含 .env 的 demo 專案"
PROJECT_ID="$(systograph_import_project "$(make_demo_project)")"

systograph_section "Preflight：列出必須決定的 .env"
open_preflight "$PROJECT_ID"
PREFLIGHT="$LAST_BODY"
PREFLIGHT_ID="$(jq_get "$PREFLIGHT" '.preflight_request_id // empty')"
REQUIRED='.required_boundary_proposals[0]'
PROPOSAL_ID="$(jq_get "$PREFLIGHT" "$REQUIRED.proposal_id // empty")"
TARGET_PATH="$(jq_get "$PREFLIGHT" "$REQUIRED.target.path // empty")"
FINGERPRINT="$(jq_get "$PREFLIGHT" "$REQUIRED.target.fingerprint // empty")"
[[ -n "$PREFLIGHT_ID" && -n "$PROPOSAL_ID" && "$TARGET_PATH" == ".env" \
  && -n "$FINGERPRINT" ]] \
  || systograph_die "Expected one required .env boundary proposal"
if grep -q 'sk-live-secret-value' <<<"$PREFLIGHT"; then
  systograph_die "Raw secret leaked in preflight response"
fi

systograph_section "第一次掃描：帶單號但未附決定，應要求 boundary decision"
FIRST_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$PREFLIGHT_ID")"
systograph_progress "現在要建立 scan（預期回 requires_boundary_decision）..."
api_call POST "/api/scans" "$FIRST_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected first scan HTTP: $LAST_STATUS"
FIRST_SCAN="$LAST_BODY"
FIRST_STATUS="$(jq_get "$FIRST_SCAN" '.status')"
[[ "$FIRST_STATUS" == "requires_boundary_decision" ]] \
  || systograph_die "Expected requires_boundary_decision, got $FIRST_STATUS"
[[ "$(jq_get "$FIRST_SCAN" '.boundary_proposals[0].target.path // empty')" \
  == ".env" ]] \
  || systograph_die "Expected the pending proposal to be .env"
if grep -q 'sk-live-secret-value' <<<"$FIRST_SCAN"; then
  systograph_die "Raw secret leaked in first scan response"
fi

systograph_section "第二次掃描：送出 scan_this_run 完成本次掃描"
DECISIONS="$(jq -n \
  --arg path "$TARGET_PATH" \
  --arg fingerprint "$FINGERPRINT" \
  '[{target_path:$path, fingerprint:$fingerprint, decision:"scan_this_run"}]')"
SECOND_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$PREFLIGHT_ID" \
  "$DECISIONS")"
systograph_progress "接著帶 boundary_decisions 再呼叫 scan..."
api_call POST "/api/scans" "$SECOND_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected second scan HTTP: $LAST_STATUS"
SECOND_SCAN="$LAST_BODY"
SECOND_STATUS="$(jq_get "$SECOND_SCAN" '.status')"
SECOND_SCANNED="$(jq_get "$SECOND_SCAN" \
  '.inventory_selection_summary.included_file_count')"
SECOND_SCAN_ID="$(jq_get "$SECOND_SCAN" '.scan_id // empty')"
SECOND_MAP_JSON_PATH="$(jq_get "$SECOND_SCAN" '.build_result.map_json_path // empty')"
[[ "$SECOND_STATUS" == "completed" ]] \
  || systograph_die "Expected completed second scan, got $SECOND_STATUS"
[[ "$SECOND_SCANNED" == "2" ]] \
  || systograph_die "Expected second scan to include 2 files, got $SECOND_SCANNED"
[[ -f "$SECOND_MAP_JSON_PATH" ]] \
  || systograph_die "Expected map_json_path to exist: $SECOND_MAP_JSON_PATH"
STORED_MAP="$(cat "$SECOND_MAP_JSON_PATH")"
[[ "$(jq_get "$STORED_MAP" '.schema_version')" == "ai-system-map/v2" ]] \
  || systograph_die "Stored ai_system_map.json is not ai-system-map/v2"
[[ "$(jq_get "$STORED_MAP" '.scan_id')" == "$SECOND_SCAN_ID" ]] \
  || systograph_die "Stored ai_system_map.json scan_id did not match response"
if grep -q 'sk-live-secret-value' <<<"$SECOND_SCAN"; then
  systograph_die "Raw secret leaked in second scan response"
fi
if grep -q 'sk-live-secret-value' "$SECOND_MAP_JSON_PATH"; then
  systograph_die "Raw secret leaked in stored ai_system_map.json"
fi

systograph_section "第三次掃描：rescan 開新 preflight，decision 不會被記住"
open_preflight "$PROJECT_ID"
THIRD_PREFLIGHT_ID="$(jq_get "$LAST_BODY" '.preflight_request_id // empty')"
[[ "$(jq_get "$LAST_BODY" '.required_boundary_proposals | length')" == "1" ]] \
  || systograph_die "Expected the rescan preflight to ask about .env again"
THIRD_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$THIRD_PREFLIGHT_ID")"
systograph_progress "再次建立 scan（預期又要求 boundary decision）..."
api_call POST "/api/scans" "$THIRD_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected third scan HTTP: $LAST_STATUS"
THIRD_STATUS="$(jq_get "$LAST_BODY" '.status')"
[[ "$THIRD_STATUS" == "requires_boundary_decision" ]] \
  || systograph_die "Expected requires_boundary_decision third scan, got $THIRD_STATUS"

systograph_section "PASS"
echo "scan boundary same-run gate behavior is correct"

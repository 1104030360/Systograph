#!/usr/bin/env bash
# Trace: scan boundary same-run gate with multiple proposals.
#
# This verifies the frontend-facing explicit preflight flow:
# 1. The preflight returns every required boundary proposal at once, and a scan
#    that carries the preflight_request_id but no decision stays pending.
# 2. The pending response does not build artifacts, so the project still has
#    no latest build to read.
# 3. The second scan can submit all boundary decisions in one request.
# 4. Decisions are same-run only and are not remembered.
# 5. The completed scan writes a readable ai_system_map.json artifact.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace scan boundary multi-decision same-run gate behavior.

Usage:
  scripts/trace_scan_boundary_multi_decision_gate.sh [common options]

Options:
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

make_demo_project() {
  DEMO_PROJECT_DIR="$(mktemp -d)"
  mkdir -p "$DEMO_PROJECT_DIR/src" "$DEMO_PROJECT_DIR/vector_store"
  printf '%s\n' 'OPENAI_API_KEY=sk-live-secret-value' \
    >"$DEMO_PROJECT_DIR/.env"
  printf '%s\n' 'print("hello")' >"$DEMO_PROJECT_DIR/src/app.py"
  printf '%s\n' 'local vector persistence metadata' \
    >"$DEMO_PROJECT_DIR/vector_store/data.index"
  echo "$DEMO_PROJECT_DIR"
}

jq_get() {
  local json="$1"
  local filter="$2"
  echo "$json" | jq -r "$filter"
}

# HTTP status of the project's latest build. 404 means nothing was published
# yet, which is what a gated scan must leave behind.
latest_build_status() {
  local project_id="$1"
  curl -sS -o /dev/null -w '%{http_code}' \
    -H 'Accept: application/json' \
    "$API_BASE_URL/api/projects/${project_id}/map-builds/latest"
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

proposal_value() {
  local proposals_json="$1"
  local path="$2"
  local filter="$3"
  jq -r --arg path "$path" \
    ".[] | select(.target.path == \$path) | $filter" \
    <<<"$proposals_json"
}

require_tools
systograph_parse_common_args "$@"
if [[ ${#SYSTOGRAPH_EXTRA_ARGS[@]} -gt 0 ]]; then
  systograph_die "Unknown option: ${SYSTOGRAPH_EXTRA_ARGS[*]}"
fi
systograph_bootstrap_server

systograph_section "準備：匯入含兩個 boundary 目標的 demo 專案"
DEMO_PROJECT_DIR="$(make_demo_project)"
PROJECT_ID="$(systograph_import_project "$DEMO_PROJECT_DIR")"
systograph_progress "先確認這個 project 還沒有任何 build..."
BEFORE_LATEST_STATUS="$(latest_build_status "$PROJECT_ID")"
[[ "$BEFORE_LATEST_STATUS" == "404" ]] \
  || systograph_die "Expected no latest build before scanning, got HTTP $BEFORE_LATEST_STATUS"

systograph_section "Preflight：一次列出所有 required boundary proposals"
open_preflight "$PROJECT_ID"
PREFLIGHT="$LAST_BODY"
PREFLIGHT_ID="$(jq_get "$PREFLIGHT" '.preflight_request_id // empty')"
[[ -n "$PREFLIGHT_ID" ]] || systograph_die "Missing preflight_request_id"
PREFLIGHT_PATHS="$(jq -r '.required_boundary_proposals[].target.path' \
  <<<"$PREFLIGHT" | sort | paste -sd ',' -)"
[[ "$PREFLIGHT_PATHS" == ".env,vector_store/data.index" ]] \
  || systograph_die "Unexpected required preflight paths: $PREFLIGHT_PATHS"
if grep -Fq 'sk-live-secret-value' <<<"$PREFLIGHT"; then
  systograph_die "Raw secret leaked in preflight response"
fi

systograph_section "第一次掃描：帶單號未附決定，一次收回所有 pending proposals"
FIRST_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$PREFLIGHT_ID")"
systograph_progress "現在要建立 scan（預期回 requires_boundary_decision）..."
api_call POST "/api/scans" "$FIRST_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected first scan HTTP: $LAST_STATUS"
FIRST_SCAN="$LAST_BODY"
FIRST_STATUS="$(jq_get "$FIRST_SCAN" '.status')"
[[ "$FIRST_STATUS" == "requires_boundary_decision" ]] \
  || systograph_die "Expected requires_boundary_decision, got $FIRST_STATUS"
[[ "$(jq_get "$FIRST_SCAN" '.build_result == null')" == "true" ]] \
  || systograph_die "Expected build_result=null for pending boundary decision"

PROPOSALS_JSON="$(jq -c '.boundary_proposals' <<<"$FIRST_SCAN")"
PROPOSAL_COUNT="$(jq_get "$FIRST_SCAN" '.boundary_proposals | length')"
PROPOSAL_PATHS="$(jq -r '.boundary_proposals[].target.path' <<<"$FIRST_SCAN" \
  | sort | paste -sd ',' -)"
[[ "$PROPOSAL_COUNT" == "2" ]] \
  || systograph_die "Expected 2 boundary proposals, got $PROPOSAL_COUNT"
[[ "$PROPOSAL_PATHS" == ".env,vector_store/data.index" ]] \
  || systograph_die "Unexpected proposal paths: $PROPOSAL_PATHS"
if grep -Fq 'sk-live-secret-value' <<<"$FIRST_SCAN"; then
  systograph_die "Raw secret leaked in first scan response"
fi
if grep -Fq "$DEMO_PROJECT_DIR" <<<"$FIRST_SCAN"; then
  systograph_die "Local absolute path leaked in first scan response"
fi

systograph_progress "確認 pending 期間沒有發佈任何 build..."
PENDING_LATEST_STATUS="$(latest_build_status "$PROJECT_ID")"
[[ "$PENDING_LATEST_STATUS" == "404" ]] \
  || systograph_die "Pending boundary decision unexpectedly published a build (HTTP $PENDING_LATEST_STATUS)"

systograph_section "第二次掃描：一次送回全部 boundary decisions"
ENV_FINGERPRINT="$(proposal_value "$PROPOSALS_JSON" ".env" '.target.fingerprint')"
VECTOR_FINGERPRINT="$(proposal_value \
  "$PROPOSALS_JSON" \
  "vector_store/data.index" \
  '.target.fingerprint')"
[[ -n "$ENV_FINGERPRINT" && -n "$VECTOR_FINGERPRINT" ]] \
  || systograph_die "Could not derive proposal fingerprints"
DECISIONS="$(jq -n \
  --arg env_fp "$ENV_FINGERPRINT" \
  --arg vector_fp "$VECTOR_FINGERPRINT" \
  '[
    {
      target_path: ".env",
      fingerprint: $env_fp,
      decision: "scan_this_run",
      reason: "User confirmed this config for the current scan."
    },
    {
      target_path: "vector_store/data.index",
      fingerprint: $vector_fp,
      decision: "skip_this_run",
      reason: "User skipped this local persistence file for the current scan."
    }
  ]')"
SECOND_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$PREFLIGHT_ID" \
  "$DECISIONS")"
systograph_progress "接著一次送回全部 boundary_decisions..."
api_call POST "/api/scans" "$SECOND_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected second scan HTTP: $LAST_STATUS"
SECOND_SCAN="$LAST_BODY"
SECOND_STATUS="$(jq_get "$SECOND_SCAN" '.status')"
SECOND_PROPOSALS="$(jq_get "$SECOND_SCAN" '.boundary_proposals | length')"
SECOND_SCANNED="$(jq_get \
  "$SECOND_SCAN" \
  '.inventory_selection_summary.included_file_count')"
SECOND_SKIPPED="$(jq_get \
  "$SECOND_SCAN" \
  '.inventory_selection_summary.skipped_file_count')"
SECOND_SCAN_ID="$(jq_get "$SECOND_SCAN" '.scan_id // empty')"
SECOND_MAP_JSON_PATH="$(jq_get "$SECOND_SCAN" '.build_result.map_json_path // empty')"
[[ "$SECOND_STATUS" == "completed" ]] \
  || systograph_die "Expected completed second scan, got $SECOND_STATUS"
[[ "$SECOND_PROPOSALS" == "0" ]] \
  || systograph_die "Expected no boundary proposals after all decisions"
[[ "$SECOND_SCANNED" == "2" ]] \
  || systograph_die "Expected .env and app.py to be included, got $SECOND_SCANNED"
[[ "$SECOND_SKIPPED" -ge 1 ]] \
  || systograph_die "Expected at least one skipped file after skip_this_run"
[[ -f "$SECOND_MAP_JSON_PATH" ]] \
  || systograph_die "Expected map_json_path to exist: $SECOND_MAP_JSON_PATH"
STORED_MAP="$(cat "$SECOND_MAP_JSON_PATH")"
[[ "$(jq_get "$STORED_MAP" '.schema_version')" == "ai-system-map/v2" ]] \
  || systograph_die "Stored ai_system_map.json is not ai-system-map/v2"
[[ "$(jq_get "$STORED_MAP" '.scan_id')" == "$SECOND_SCAN_ID" ]] \
  || systograph_die "Stored ai_system_map.json scan_id did not match response"
if grep -Fq 'sk-live-secret-value' <<<"$SECOND_SCAN"; then
  systograph_die "Raw secret leaked in second scan response"
fi
if grep -Fq 'sk-live-secret-value' "$SECOND_MAP_JSON_PATH"; then
  systograph_die "Raw secret leaked in stored ai_system_map.json"
fi
if grep -Fq "$DEMO_PROJECT_DIR" "$SECOND_MAP_JSON_PATH"; then
  systograph_die "Local absolute path leaked in stored ai_system_map.json"
fi

systograph_progress "確認完成掃描後該 project 已有可讀的 latest build..."
AFTER_COMPLETED_LATEST="$(setup_get "/api/projects/$PROJECT_ID/map-builds/latest")"
[[ "$(jq_get "$AFTER_COMPLETED_LATEST" '.viewer_load_result.loaded')" == "true" ]] \
  || systograph_die "Completed scan did not publish a readable latest build"

systograph_section "第三次掃描：rescan 開新 preflight，same-run decisions 不會被記住"
open_preflight "$PROJECT_ID"
THIRD_PREFLIGHT_ID="$(jq_get "$LAST_BODY" '.preflight_request_id // empty')"
[[ "$(jq_get "$LAST_BODY" '.required_boundary_proposals | length')" == "2" ]] \
  || systograph_die "Expected the rescan preflight to ask about both targets"
THIRD_BODY="$(run_scan_body "$PROJECT_ID" "$OUTPUT_DIR" "$THIRD_PREFLIGHT_ID")"
systograph_progress "再次建立 scan（預期又要求兩筆 boundary decision）..."
api_call POST "/api/scans" "$THIRD_BODY"
[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected third scan HTTP: $LAST_STATUS"
THIRD_STATUS="$(jq_get "$LAST_BODY" '.status')"
THIRD_COUNT="$(jq_get "$LAST_BODY" '.boundary_proposals | length')"
[[ "$THIRD_STATUS" == "requires_boundary_decision" ]] \
  || systograph_die "Expected requires_boundary_decision third scan, got $THIRD_STATUS"
[[ "$THIRD_COUNT" == "2" ]] \
  || systograph_die "Expected both proposals to be requested again, got $THIRD_COUNT"

systograph_section "PASS"
echo "scan boundary multi-decision same-run gate behavior is correct"

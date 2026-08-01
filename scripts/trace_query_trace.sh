#!/usr/bin/env bash
# Trace: POST /api/trace
#
# Safe default uses endpoint:missing so the smoke test validates the route
# contract without calling a real RAG endpoint. Pass --endpoint-id to opt in to
# a detected endpoint from the loaded map.
#
# Phase2 S1: request must bind a build_id; response includes source_scan_id /
# source_build_id lineage fields.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

ENDPOINT_ID="endpoint:missing"
QUERY="Systograph query trace smoke test"
TIMEOUT_SECONDS="3"

usage() {
  cat <<'USAGE'
Trace POST /api/trace

Usage:
  scripts/trace_query_trace.sh [common options] \
    [--endpoint-id ID] [--query TEXT] [--timeout-seconds SEC]

Options:
  --endpoint-id ID       Endpoint id from ai_system_map.endpoints[].
                         Default: endpoint:missing, which sends no request.
  --query TEXT           Query to send when endpoint exists. Raw value is masked in trace output.
  --timeout-seconds SEC  Endpoint timeout. Default: 3
  --start-server         Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL     Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH    Project to import and scan.
  --output DIR           Scan output dir. Default: outputs
  -h, --help             Show this help.
USAGE
}

require_tools
systograph_parse_common_args "$@"
i=0
while [[ $i -lt ${#SYSTOGRAPH_EXTRA_ARGS[@]} ]]; do
  arg="${SYSTOGRAPH_EXTRA_ARGS[$i]}"
  case "$arg" in
    --endpoint-id)
      i=$((i + 1)); ENDPOINT_ID="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --endpoint-id}" ;;
    --query)
      i=$((i + 1)); QUERY="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --query}" ;;
    --timeout-seconds)
      i=$((i + 1)); TIMEOUT_SECONDS="${SYSTOGRAPH_EXTRA_ARGS[$i]:?missing value for --timeout-seconds}" ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
systograph_bootstrap_server

systograph_section "準備：匯入專案並掃描，取得 build_id"
PROJECT_ID="$(systograph_import_project)"
SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
BUILD_ID="$(echo "$SCAN_JSON" | jq -r '.build_result.lineage.build_id')"
[[ -n "$BUILD_ID" && "$BUILD_ID" != "null" ]] \
  || systograph_die "Scan response missing build_result.lineage.build_id"

systograph_section "執行 query trace：POST /api/trace"
REQUEST_BODY="$(jq -n \
  --arg id "$PROJECT_ID" \
  --arg build "$BUILD_ID" \
  --arg endpoint "$ENDPOINT_ID" \
  --arg query "$QUERY" \
  --arg timeout "$TIMEOUT_SECONDS" \
  '{project_id:$id, build_id:$build, endpoint_id:$endpoint, query:$query,
    timeout_seconds:($timeout|tonumber)}')"
systograph_progress "現在要對 build 執行 query trace（endpoint=${ENDPOINT_ID}）..."
api_call POST "/api/trace" "$REQUEST_BODY"

[[ "$LAST_STATUS" == "200" ]] || systograph_die "Unexpected status: $LAST_STATUS"
systograph_section "Trace 摘要"
echo "$LAST_BODY" | jq '{
  trace_id,
  status,
  query_sent,
  endpoint_id,
  source_scan_id,
  source_build_id,
  event_types: [.events[].event_type],
  warning_count: (.warnings | length),
  error_reason
}'

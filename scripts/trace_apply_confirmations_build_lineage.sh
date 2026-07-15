#!/usr/bin/env bash
# Trace: POST /api/map-builds/{base_build_id}/apply
#         + GET /api/map-builds/{build_id}
#         + GET /api/projects/{id}/map-builds[/latest]
#
# Verifies apply confirmations create an immutable child build with lineage,
# and that latest / history pointers advance correctly.
# Track A: GET map-builds/{id} surfaces viewer_load_result graph projection and
# build_result.profile_signals_available.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

usage() {
  cat <<'USAGE'
Trace Apply confirmations and build lineage

Usage:
  scripts/trace_apply_confirmations_build_lineage.sh [common options]

Common options:
  --start-server          Start a local FastAPI server for this run.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to import and scan.
  --output DIR            Build output directory. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
[[ ${#KAI_EXTRA_ARGS[@]} -eq 0 ]] \
  || kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
kai_bootstrap_server

kai_section "準備：匯入專案並建立初始 scan / build"
PROJECT_ID="$(kai_import_project)"
SCAN_JSON="$(kai_run_scan "$PROJECT_ID")"
SCAN_ID="$(echo "$SCAN_JSON" | jq -r '.scan_id')"
BASE_BUILD_ID="$(echo "$SCAN_JSON" \
  | jq -r '.build_result.lineage.build_id')"
UNMAPPED_COUNT="$(echo "$SCAN_JSON" \
  | jq '.build_result.ai_system_map.unmapped_components | length')"
[[ -n "$BASE_BUILD_ID" && "$BASE_BUILD_ID" != "null" ]] \
  || kai_die "Scan response missing build_result.lineage.build_id"
[[ "$UNMAPPED_COUNT" -ge 2 ]] \
  || kai_die "Need at least two unmapped components; found $UNMAPPED_COUNT"
kai_progress "初始 build_id=${BASE_BUILD_ID}，unmapped=$UNMAPPED_COUNT"

kai_section "準備：建立兩筆 confirmed mapping"
MAPPING_IDS=()
for index in 0 1; do
  UNMAPPED="$(echo "$SCAN_JSON" \
    | jq ".build_result.ai_system_map.unmapped_components[$index]")"
  BODY="$(echo "$UNMAPPED" | jq \
    --arg project "$PROJECT_ID" \
    --arg name "Trace Confirmed Component $((index + 1))" \
    '{project_id:$project, mapping_type:"existing_slot_mapping",
      decision:"confirmed", source_unmapped_id:.id,
      source_file:.source_file, observed_kind:.observed_kind,
      evidence_ids:.evidence_ids, target_slot:"vector_store",
      component_name:$name, component_kind:"manual_trace"}')"
  kai_progress "現在要建立第 $((index + 1)) 筆 mapping..."
  CREATED="$(setup_post "/api/mappings" "$BODY")"
  MAPPING_IDS+=("$(echo "$CREATED" | jq -r '.mapping_id')")
done

kai_section "套用 confirmations：POST /api/map-builds/{B1}/apply"
MAPPING_IDS_JSON="$(printf '%s\n' "${MAPPING_IDS[@]}" | jq -R . | jq -s .)"
REQUEST_BODY="$(jq -n --argjson ids "$MAPPING_IDS_JSON" \
  '{mapping_ids:$ids}')"
kai_progress "現在要套用 mapping 到 build，產生新的 child build..."
api_call POST "/api/map-builds/$BASE_BUILD_ID/apply" "$REQUEST_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"

APPLIED_BUILD_ID="$(echo "$LAST_BODY" | jq -r '.build_id')"
[[ "$(echo "$LAST_BODY" | jq -r '.scan_id')" == "$SCAN_ID" ]] \
  || kai_die "Apply unexpectedly changed scan_id"
[[ "$(echo "$LAST_BODY" | jq -r '.based_on_build_id')" == "$BASE_BUILD_ID" ]] \
  || kai_die "Apply lineage parent mismatch"
kai_progress "套用完成，新 build_id=$APPLIED_BUILD_ID"

kai_section "讀取 build：GET /api/map-builds/{build_id}"
kai_progress "接著依 build_id 讀取剛套用的 build..."
api_call GET "/api/map-builds/$APPLIED_BUILD_ID"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected status: $LAST_STATUS"
[[ "$(echo "$LAST_BODY" | jq -r '.build_id')" == "$APPLIED_BUILD_ID" ]] \
  || kai_die "GET map-builds/{id} returned unexpected build_id"

kai_section "Graph projection 摘要（Track A）"
kai_summarize_viewer_payload "$(echo "$LAST_BODY" | jq '{viewer_load_result}')"
echo "$LAST_BODY" | jq '{
  profile_signals_available: .build_result.profile_signals_available,
  readiness_report_available: .build_result.readiness_report_available
}'

PROFILE_OK="$(echo "$LAST_BODY" | jq -r '.build_result.profile_signals_available')"
[[ "$PROFILE_OK" == "true" ]] \
  || kai_die "Expected build_result.profile_signals_available=true, got: $PROFILE_OK"
VIEWER_PRESENT="$(echo "$LAST_BODY" | jq -r '.viewer_load_result != null')"
if [[ "$VIEWER_PRESENT" == "true" ]]; then
  kai_assert_graph_projection_loaded "$(echo "$LAST_BODY" | jq '{viewer_load_result}')"
fi

kai_section "確認 latest / history 指標"
kai_progress "接著查詢專案最新 build..."
LATEST="$(setup_get "/api/projects/$PROJECT_ID/map-builds/latest")"
kai_progress "接著查詢專案 build 歷史列表..."
HISTORY="$(setup_get "/api/projects/$PROJECT_ID/map-builds")"
[[ "$(echo "$LATEST" | jq -r '.build_id')" == "$APPLIED_BUILD_ID" ]] \
  || kai_die "Latest pointer did not advance to the applied build"

kai_section "Lineage 摘要"
jq -n \
  --arg project_id "$PROJECT_ID" \
  --arg scan_id "$SCAN_ID" \
  --arg base_build_id "$BASE_BUILD_ID" \
  --arg applied_build_id "$APPLIED_BUILD_ID" \
  --argjson mappings "$MAPPING_IDS_JSON" \
  --argjson history "$(echo "$HISTORY" | jq '.builds | map(.build_id)')" \
  '{project_id:$project_id, scan_id:$scan_id, base_build_id:$base_build_id,
    applied_build_id:$applied_build_id, mapping_ids:$mappings,
    history_build_ids:$history}'

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/api_trace_common.sh"

DEMO_PROJECT_DIR=""

usage() {
  cat <<'USAGE'
Trace inventory preflight and one-run directory selection.

Usage:
  scripts/trace_inventory_selection_preflight.sh [common options]

Options:
  --start-server          Start a local FastAPI server for this run.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

make_demo_project() {
  DEMO_PROJECT_DIR="$(mktemp -d)"
  mkdir -p "$DEMO_PROJECT_DIR/ignored"
  printf '%s\n' 'ignored/' >"$DEMO_PROJECT_DIR/.gitignore"
  printf '%s\n' 'print("app")' >"$DEMO_PROJECT_DIR/app.py"
  printf '%s\n' 'MODE=fixture' >"$DEMO_PROJECT_DIR/ignored/.env"
  printf '%s\n' 'print("safe")' >"$DEMO_PROJECT_DIR/ignored/safe.py"
  printf '%s\n' 'print("skip")' >"$DEMO_PROJECT_DIR/ignored/skip.py"
  printf 'prefix\0binary' >"$DEMO_PROJECT_DIR/ignored/blob.dat"
  echo "$DEMO_PROJECT_DIR"
}

tree_digest() {
  local root="$1"
  (
    cd "$root"
    find . -type f -exec cksum {} \; | LC_ALL=C sort
    find . -type l -print | LC_ALL=C sort
  ) | cksum
}

proposal_field() {
  local response="$1"
  local path="$2"
  local field="$3"
  jq -r --arg path "$path" \
    ".requested_target_results[]
     | select(.target_path == \$path)
     | .proposal.${field}" <<<"$response"
}

require_tools
require_cmd cksum
kai_parse_common_args "$@"
if [[ ${#KAI_EXTRA_ARGS[@]} -gt 0 ]]; then
  kai_die "Unknown option: ${KAI_EXTRA_ARGS[*]}"
fi
kai_bootstrap_server

kai_section "準備 metadata-only preflight fixture"
DEMO_PROJECT_DIR="$(make_demo_project)"
BEFORE_DIGEST="$(tree_digest "$DEMO_PROJECT_DIR")"
PROJECT_ID="$(kai_import_project "$DEMO_PROJECT_DIR")"

kai_section "Preflight：非法路徑 fail closed"
api_call POST "/api/projects/${PROJECT_ID}/scan-preflights" \
  '{"requested_paths":["../outside"]}'
[[ "$LAST_STATUS" == "422" ]] \
  || kai_die "Unexpected invalid-path HTTP: $LAST_STATUS"
[[ "$(jq -r '.detail.code' <<<"$LAST_BODY")" == \
  "inventory_selection_path_invalid" ]] \
  || kai_die "Expected typed invalid-path error"
[[ "$(jq -r '.detail | has("scan_id")' <<<"$LAST_BODY")" == "false" ]] \
  || kai_die "Invalid preflight must not return scan_id"

kai_section "Preflight：展開 ignored directory 與 exact child"
PREFLIGHT_BODY="$(jq -n \
  '{requested_paths:["ignored","ignored/skip.py"],
    reviewable_excluded_limit:100}')"
api_call POST "/api/projects/${PROJECT_ID}/scan-preflights" "$PREFLIGHT_BODY"
[[ "$LAST_STATUS" == "200" ]] \
  || kai_die "Unexpected preflight HTTP: $LAST_STATUS"
PREFLIGHT="$LAST_BODY"
PREFLIGHT_ID="$(jq -r '.preflight_request_id // empty' <<<"$PREFLIGHT")"
[[ -n "$PREFLIGHT_ID" ]] || kai_die "Missing preflight_request_id"
[[ "$(jq -r 'has("scan_id")' <<<"$PREFLIGHT")" == "false" ]] \
  || kai_die "Preflight must not return scan_id"
[[ "$(proposal_field "$PREFLIGHT" "ignored" \
  'selection_context.selection_scope')" == "recursive_directory" ]] \
  || kai_die "Expected recursive_directory proposal"
if grep -Fq 'entries' <<<"$(jq -c '.requested_target_results' <<<"$PREFLIGHT")"; then
  kai_die "Directory internal entries leaked through API"
fi

DIR_FINGERPRINT="$(proposal_field "$PREFLIGHT" "ignored" \
  'target.fingerprint')"
FILE_FINGERPRINT="$(proposal_field "$PREFLIGHT" "ignored/skip.py" \
  'target.fingerprint')"
DECISIONS="$(jq -n \
  --arg dir_fingerprint "$DIR_FINGERPRINT" \
  --arg file_fingerprint "$FILE_FINGERPRINT" \
  '[
    {target_path:"ignored", fingerprint:$dir_fingerprint,
     decision:"scan_this_run", selection_scope:"recursive_directory"},
    {target_path:"ignored/skip.py", fingerprint:$file_fingerprint,
     decision:"skip_this_run", selection_scope:"exact_file"}
  ]')"
SCAN_BODY="$(jq -n \
  --arg project_id "$PROJECT_ID" \
  --arg preflight_id "$PREFLIGHT_ID" \
  --arg output "$OUTPUT_DIR" \
  --argjson decisions "$DECISIONS" \
  '{project_id:$project_id, scan_depth:"system", output:$output,
    preflight_request_id:$preflight_id, boundary_decisions:$decisions}')"

kai_section "Scan：directory scan + exact child skip"
api_call POST "/api/scans" "$SCAN_BODY"
[[ "$LAST_STATUS" == "200" ]] || kai_die "Unexpected scan HTTP: $LAST_STATUS"
[[ "$(jq -r '.status' <<<"$LAST_BODY")" == "completed" ]] \
  || kai_die "Expected completed scan"
[[ "$(jq -r '.inventory_selection_summary.directory_scope_results[0].included_file_count' <<<"$LAST_BODY")" == "2" ]] \
  || kai_die "Expected two included directory descendants"
[[ "$(jq -r '.inventory_selection_summary.directory_scope_results[0].post_decision_blocked_file_count' <<<"$LAST_BODY")" == "1" ]] \
  || kai_die "Expected binary child to be post-decision blocked"

AFTER_DIGEST="$(tree_digest "$DEMO_PROJECT_DIR")"
[[ "$AFTER_DIGEST" == "$BEFORE_DIGEST" ]] \
  || kai_die "Target project changed during preflight/scan"

kai_section "PASS"
echo "inventory preflight and one-run directory selection are correct"

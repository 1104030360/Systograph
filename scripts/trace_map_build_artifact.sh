#!/usr/bin/env bash
# Trace: GET /api/map-builds/{build_id}/artifacts/{file_name}
#
# Input  : a build_id the caller already holds, a whitelisted file name,
#          and optionally ?download=true.
# Output : the artifact bytes (text/markdown for ai_system_map.md), with
#          Content-Disposition: attachment only under ?download=true.
#          404 build_not_found for a build id nobody committed.
#
# The endpoint answers per build, so the default run scans a project
# (import -> scans) and reads back the build_id that scan produced. With
# --no-setup it skips the scan entirely and reads a build id that cannot
# exist, pinning the 404 arm without depending on prior server state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

NO_SETUP=0
DOWNLOAD=0
ARTIFACT_NAME="ai_system_map.md"

usage() {
  cat <<'USAGE'
Trace GET /api/map-builds/{build_id}/artifacts/{file_name}

Usage:
  scripts/trace_map_build_artifact.sh [common options] [--download] [--no-setup]

Options:
  --download              Request the attachment variant (?download=true).
  --no-setup              Do not scan. Read an unknown build id instead and
                          expect 404 build_not_found.
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to scan before reading the artifact.
  --output DIR            Scan output dir. Default: outputs
  -h, --help              Show this help.
USAGE
}

require_tools
systograph_parse_common_args "$@"
for arg in ${SYSTOGRAPH_EXTRA_ARGS[@]+"${SYSTOGRAPH_EXTRA_ARGS[@]}"}; do
  case "$arg" in
    --download) DOWNLOAD=1 ;;
    --no-setup) NO_SETUP=1 ;;
    *) systograph_die "Unknown option: $arg" ;;
  esac
done
systograph_bootstrap_server

if [[ "$NO_SETUP" -eq 1 ]]; then
  systograph_section "略過掃描：改讀一個不存在的 build_id"
  # Deliberately unreachable: build ids are minted as build:<uuid4>, so this
  # one is never committed and the 404 arm stays deterministic.
  BUILD_ID="build:trace-no-setup-never-committed"
  EXPECTED_STATUS="404"
else
  systograph_section "準備：先掃描，取得這次 build 的 build_id"
  PROJECT_ID="$(systograph_import_project)"
  SCAN_JSON="$(systograph_run_scan "$PROJECT_ID")"
  BUILD_ID="$(echo "$SCAN_JSON" \
    | jq -r '.build_result.lineage.build_id // empty')"
  [[ -n "$BUILD_ID" ]] \
    || systograph_die "Scan response missing build_result.lineage.build_id"
  EXPECTED_STATUS="200"
fi

ENDPOINT="/api/map-builds/$BUILD_ID/artifacts/$ARTIFACT_NAME"
if [[ "$DOWNLOAD" -eq 1 ]]; then
  ENDPOINT="$ENDPOINT?download=true"
fi

TMP_DIR="$(mktemp -d)"
TMP_HEADERS="$TMP_DIR/headers"
TMP_BODY="$TMP_DIR/body"

# systograph_die after dropping this run's temp files. The shared EXIT trap
# belongs to --start-server, so this script must not install one of its own.
trace_die() {
  rm -rf "$TMP_DIR"
  systograph_die "$@"
}

systograph_section "讀取 build artifact：GET $ENDPOINT"
systograph_progress "現在要讀取這個 build 的 map markdown 報告..."
echo "-------------------- REQUEST --------------------"
echo "GET $API_BASE_URL$ENDPOINT"
echo "-------------------- RESPONSE -------------------"
STATUS="$(curl -sS -D "$TMP_HEADERS" -o "$TMP_BODY" -w '%{http_code}' \
  "$API_BASE_URL$ENDPOINT" -H 'Accept: text/markdown')"
echo "HTTP $STATUS"
echo "Headers:"
grep -iE '^(content-type|content-disposition):' "$TMP_HEADERS" || true
echo "Body (first 40 lines):"
head -n 40 "$TMP_BODY"

[[ "$STATUS" == "$EXPECTED_STATUS" ]] \
  || trace_die "Expected HTTP $EXPECTED_STATUS, got: $STATUS"

if [[ "$EXPECTED_STATUS" == "404" ]]; then
  DETAIL="$(jq -r '.detail // empty' "$TMP_BODY")"
  [[ "$DETAIL" == "build_not_found" ]] \
    || trace_die "Expected detail=build_not_found, got: $DETAIL"
  systograph_progress "未知 build_id 如預期被拒：404 $DETAIL"
  rm -rf "$TMP_DIR"
  exit 0
fi

grep -iq '^content-type: *text/markdown' "$TMP_HEADERS" \
  || trace_die "Expected a text/markdown Content-Type"

if [[ "$DOWNLOAD" -eq 1 ]]; then
  grep -iqF "content-disposition: attachment; filename=\"$ARTIFACT_NAME\"" \
    "$TMP_HEADERS" \
    || trace_die "Expected Content-Disposition attachment for --download"
  systograph_progress "附件標頭如預期：attachment; filename=\"$ARTIFACT_NAME\""
elif grep -iq '^content-disposition:' "$TMP_HEADERS"; then
  # An inline read must not smuggle in a download: the header is set only
  # by ?download=true, and a stray one changes how a browser treats it.
  trace_die "Unexpected Content-Disposition without --download"
else
  systograph_progress "行內讀取如預期：無 Content-Disposition"
fi

rm -rf "$TMP_DIR"
systograph_progress "build_id=$BUILD_ID 的 $ARTIFACT_NAME 讀取成功"

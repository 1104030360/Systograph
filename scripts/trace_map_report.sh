#!/usr/bin/env bash
# Trace: GET /api/map/report
#
# Input  : optional query ?download=true
# Output : text/markdown report body (the latest controlled map markdown).
#          404 map_markdown_not_available when no successful build exists.
#
# A successful build must exist first, so this script builds a map before
# fetching the report (unless --no-setup is passed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

NO_SETUP=0
DOWNLOAD=0

usage() {
  cat <<'USAGE'
Trace GET /api/map/report

Usage:
  scripts/trace_map_report.sh [common options] [--download] [--no-setup]

Options:
  --download              Request the attachment variant (?download=true).
  --no-setup              Do not build a map first (expect 404 if none exists).
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  --project-path PATH     Project to build before reading the report.
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

if [[ "$NO_SETUP" -eq 0 ]]; then
  systograph_section "準備：先建圖，讓 markdown report 存在"
  systograph_progress "現在要先呼叫 map/build 產生報告..."
  setup_post "/api/map/build" \
    "$(jq -n --arg p "$PROJECT_PATH" --arg out "$OUTPUT_DIR" \
      '{project_path:$p, output:$out, redact_root_path:true, no_snippets:false}')" \
    >/dev/null
fi

ENDPOINT="/api/map/report"
[[ "$DOWNLOAD" -eq 1 ]] && ENDPOINT="/api/map/report?download=true"

systograph_section "讀取報告：GET $ENDPOINT"
systograph_progress "現在要下載 / 讀取 map markdown 報告..."
echo "-------------------- REQUEST --------------------"
echo "GET $API_BASE_URL$ENDPOINT"
echo "-------------------- RESPONSE -------------------"
TMP_HEADERS="$(mktemp)"
STATUS="$(curl -sS -D "$TMP_HEADERS" -o /tmp/systograph-report-body.$$ -w '%{http_code}' \
  "$API_BASE_URL$ENDPOINT" -H 'Accept: text/markdown')"
echo "HTTP $STATUS"
echo "Headers:"
grep -iE '^(content-type|content-disposition):' "$TMP_HEADERS" || true
echo "Body (first 40 lines):"
head -n 40 /tmp/systograph-report-body.$$
rm -f "$TMP_HEADERS" /tmp/systograph-report-body.$$

[[ "$STATUS" == "200" || "$NO_SETUP" -eq 1 ]] \
  || systograph_die "Unexpected status: $STATUS"

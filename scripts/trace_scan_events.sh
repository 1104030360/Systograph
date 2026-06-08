#!/usr/bin/env bash
# Trace: GET /api/scan/events  (Server-Sent Events)
#
# Input  : none. Accept: text/event-stream.
# Output : an SSE stream. The current MVP emits one `scan_progress` event with
#          a completed payload, then closes the stream.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/api_trace_common.sh
source "$SCRIPT_DIR/lib/api_trace_common.sh"

MAX_TIME=5

usage() {
  cat <<'USAGE'
Trace GET /api/scan/events (SSE)

Usage:
  scripts/trace_scan_events.sh [common options] [--max-time SEC]

Options:
  --max-time SEC          Seconds to keep the stream open. Default: 5
  --start-server          Start a local FastAPI server for this run, stop on exit.
  --api-base-url URL      Backend base URL. Default: http://127.0.0.1:8000
  -h, --help              Show this help.
USAGE
}

require_tools
kai_parse_common_args "$@"
i=0
while [[ $i -lt ${#KAI_EXTRA_ARGS[@]} ]]; do
  arg="${KAI_EXTRA_ARGS[$i]}"
  case "$arg" in
    --max-time)
      i=$((i + 1))
      MAX_TIME="${KAI_EXTRA_ARGS[$i]:?missing value for --max-time}"
      ;;
    *) kai_die "Unknown option: $arg" ;;
  esac
  i=$((i + 1))
done
kai_bootstrap_server

kai_section "GET /api/scan/events (text/event-stream)"
echo "-------------------- REQUEST --------------------"
echo "GET $API_BASE_URL/api/scan/events"
echo "Accept: text/event-stream"
echo "-------------------- RESPONSE (raw SSE) ---------"
# -N disables buffering; --max-time bounds the wait since the MVP stream is short.
curl -sS -N --max-time "$MAX_TIME" \
  "$API_BASE_URL/api/scan/events" \
  -H 'Accept: text/event-stream' || true
echo
echo "(stream closed)"

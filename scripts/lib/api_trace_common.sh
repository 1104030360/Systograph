#!/usr/bin/env bash
# Shared helpers for the per-endpoint API trace scripts under scripts/.
#
# This file is meant to be sourced, not executed directly. Each endpoint
# script sources it, parses common flags, optionally boots a local FastAPI
# server, prepares any prerequisite session state, then calls exactly one
# target endpoint with full request/response tracing.

# Resolve repo root from this file location (scripts/lib/ -> repo root).
KAI_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Defaults (override via env or common flags).
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
PROJECT_PATH="${PROJECT_PATH:-$KAI_ROOT_DIR/tests/fixtures/rag_projects/custom_router_rag}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs}"
SERVER_LOG="${SERVER_LOG:-$KAI_ROOT_DIR/outputs/api-trace-server.log}"

START_SERVER=0
SERVER_PID=""
KAI_EXTRA_ARGS=()

# Globals populated by api_call / setup_* helpers.
LAST_STATUS=""
LAST_BODY=""

kai_die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    kai_die "Missing required command: $1"
  fi
}

require_tools() {
  require_cmd curl
  require_cmd jq
}

# Parse flags common to every endpoint script. Endpoint-specific flags are
# collected into KAI_EXTRA_ARGS for the caller to handle. Each caller must
# define a usage() function before calling this.
kai_parse_common_args() {
  KAI_EXTRA_ARGS=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --start-server)
        START_SERVER=1
        shift
        ;;
      --api-base-url)
        API_BASE_URL="${2:?missing value for --api-base-url}"
        shift 2
        ;;
      --project-path)
        PROJECT_PATH="${2:?missing value for --project-path}"
        shift 2
        ;;
      --output)
        OUTPUT_DIR="${2:?missing value for --output}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        KAI_EXTRA_ARGS+=("$1")
        shift
        ;;
    esac
  done
}

kai_cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

wait_for_api() {
  local attempt
  for attempt in $(seq 1 60); do
    if curl -fsS "$API_BASE_URL/api/map" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "Backend did not become available at $API_BASE_URL" >&2
  if [[ -f "$SERVER_LOG" ]]; then
    echo "Server log tail ($SERVER_LOG):" >&2
    tail -n 40 "$SERVER_LOG" >&2 || true
  fi
  exit 1
}

# Boot a local server when --start-server was passed, then block until ready.
# When --start-server is not passed, just wait for an already running server.
kai_bootstrap_server() {
  cd "$KAI_ROOT_DIR"
  if [[ "$START_SERVER" -eq 1 ]]; then
    if [[ ! -x ".venv/bin/uvicorn" ]]; then
      kai_die "Cannot find executable .venv/bin/uvicorn (create the venv first)"
    fi
    mkdir -p "$(dirname "$SERVER_LOG")"
    .venv/bin/uvicorn kai_mind.web.app:create_app --factory \
      --host 127.0.0.1 --port 8000 >"$SERVER_LOG" 2>&1 &
    SERVER_PID="$!"
    trap kai_cleanup EXIT
    echo "Started FastAPI PID=$SERVER_PID log=$SERVER_LOG"
  fi
  wait_for_api
}

kai_section() {
  echo
  echo "==================== $* ===================="
}

# Short Traditional Chinese progress line before an API call / phase step.
kai_progress() {
  echo ">> $*"
}

# Full request/response trace for the target endpoint under test.
# Usage: api_call METHOD ENDPOINT [JSON_BODY]
api_call() {
  local method="$1"
  local endpoint="$2"
  local body="${3:-}"
  local url="$API_BASE_URL$endpoint"
  local tmp status

  echo "-------------------- REQUEST --------------------"
  echo "$method $url"
  if [[ -n "$body" ]]; then
    echo "Content-Type: application/json"
    echo "Body:"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
  fi

  tmp="$(mktemp)"
  if [[ -n "$body" ]]; then
    status="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -d "$body")"
  else
    status="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" \
      -H 'Accept: application/json')"
  fi

  echo "-------------------- RESPONSE -------------------"
  echo "HTTP $status"
  jq '.' "$tmp" 2>/dev/null || cat "$tmp"
  echo

  LAST_STATUS="$status"
  LAST_BODY="$(cat "$tmp")"
  rm -f "$tmp"
}

# Quiet helpers used to build prerequisite session state. They fail fast and
# echo the raw response body to stdout for capture with $(...).
setup_post() {
  local endpoint="$1"
  local body="$2"
  curl -fsS -X POST "$API_BASE_URL$endpoint" \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "$body"
}

setup_get() {
  local endpoint="$1"
  curl -fsS "$API_BASE_URL$endpoint" -H 'Accept: application/json'
}

kai_urlencode() {
  jq -rn --arg v "$1" '$v|@uri'
}

# Import PROJECT_PATH and echo the resulting project_id.
kai_import_project() {
  local path="${1:-$PROJECT_PATH}"
  [[ -d "$path" ]] || kai_die "Project path does not exist: $path"
  kai_progress "現在要匯入專案：$path" >&2
  local body project_id
  body="$(jq -n --arg p "$path" \
    '{source_type:"local_path", project_path:$p}')"
  project_id="$(setup_post "/api/projects/import" "$body" | jq -r '.project_id')"
  [[ -n "$project_id" && "$project_id" != "null" ]] \
    || kai_die "Failed to import project: $path"
  kai_progress "匯入完成，project_id=$project_id" >&2
  echo "$project_id"
}

# Run a system scan for a project_id and echo the full scan response JSON.
kai_run_scan() {
  local project_id="$1"
  kai_progress "現在要建立 scan（系統掃描）project_id=$project_id" >&2
  local body scan status build_id
  body="$(jq -n --arg id "$project_id" --arg out "$OUTPUT_DIR" \
    '{project_id:$id, scan_depth:"system", output:$out, redact_root_path:true, no_snippets:false}')"
  scan="$(setup_post "/api/scans" "$body")"
  status="$(echo "$scan" | jq -r '.status')"
  [[ "$status" == "completed" ]] \
    || kai_die "Scan did not complete (status=$status)"
  build_id="$(echo "$scan" | jq -r '.build_result.lineage.build_id // empty')"
  if [[ -n "$build_id" ]]; then
    kai_progress "掃描完成，build_id=$build_id" >&2
  else
    kai_progress "掃描完成（無 lineage.build_id）" >&2
  fi
  echo "$scan"
}

# Create one confirmed existing_slot manual mapping using a real slot key and a
# real evidence id derived from a scan response. Echoes the created mapping JSON.
# Usage: kai_create_demo_mapping PROJECT_ID SCAN_JSON [COMPONENT_NAME]
kai_create_demo_mapping() {
  local project_id="$1"
  local scan_json="$2"
  local component_name="${3:-TraceDemoComponent}"
  local slot evidence_id body

  slot="$(echo "$scan_json" \
    | jq -r '.build_result.ai_system_map.components_by_slot | keys[0]')"
  evidence_id="$(echo "$scan_json" \
    | jq -r '.build_result.ai_system_map.evidence[0].id // empty')"
  [[ -n "$slot" && "$slot" != "null" ]] \
    || kai_die "Could not derive a target slot from the scan"
  [[ -n "$evidence_id" ]] \
    || kai_die "Could not derive an evidence id from the scan"

  kai_progress "現在要建立 manual mapping（slot=$slot）" >&2
  body="$(jq -n \
    --arg id "$project_id" \
    --arg slot "$slot" \
    --arg name "$component_name" \
    --arg ev "$evidence_id" \
    '{project_id:$id, mapping_type:"existing_slot_mapping", decision:"confirmed",
      target_slot:$slot, component_name:$name, evidence_ids:[$ev]}')"
  setup_post "/api/mappings" "$body"
}

# Echo the first unmapped component id from a scan response JSON.
kai_first_unmapped_id() {
  local scan_json="$1"
  echo "$scan_json" \
    | jq -r '.build_result.ai_system_map.unmapped_components[0].id // empty'
}

# Create a pending mapping proposal for an unmapped component and echo the
# proposal JSON. Falls back to a deterministic provider when no NVIDIA key.
# Usage: kai_create_proposal PROJECT_ID UNMAPPED_ID
kai_create_proposal() {
  local project_id="$1"
  local unmapped_id="$2"
  kai_progress "接著呼叫 mapping proposal（unmapped=$unmapped_id）" >&2
  local body
  body="$(jq -n --arg id "$project_id" --arg u "$unmapped_id" \
    '{project_id:$id, source_unmapped_id:$u}')"
  setup_post "/api/mapping-proposals" "$body"
}

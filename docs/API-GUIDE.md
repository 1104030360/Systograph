# KAI-Mind Local API Guide

本機 Python 後端（FastAPI）的前端對接文件。涵蓋所有 endpoint 的輸入、輸出與錯誤。

## 相關文件

- 欄位語意與 contract 邊界：`docs/MODEL-CONTRACT.md`
- UA 整合邊界（2026-07-07）：`ref-opensource/kai-mind-understand-anything-integration-boundary.md`
- JSON payload 範例：`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`（依 Phase2 pipeline step 分資料夾；見根目錄 `README.md`）
- 設計意圖與相容性規則：`docs/work/Timmy/design/EPIC1/Phase1/epic1-local-api-guide.md`
- 可執行的逐 endpoint 範例：`scripts/trace_*.sh`（每支對應一個 API）
- 互動式型別瀏覽：後端啟動後開 `http://127.0.0.1:8000/docs`

## 基本資訊

- **Base URL**：`http://127.0.0.1:8000`（前端可用 `VITE_API_BASE_URL` 覆寫）
- **Auth**：無。Local-only，server 只綁 `127.0.0.1`。
- **CORS allowlist**：`http://127.0.0.1:5173`、`http://localhost:5173`
- **Content-Type**：request/response 皆為 `application/json`（SSE 為 `text/event-stream`，report 為 `text/markdown`）
- **Request size limit**：寫入類 request body 預設上限 1 MB；超過時回 `413` 與 `{ "detail": "request_too_large" }`。

## 約定

- 所有寫入類 endpoint 拒絕未知欄位（`extra="forbid"`）。
- 錯誤回傳統一為 `{ "detail": string }`；request 結構錯誤（422）的 `detail` 為陣列。
- 413 / 500 類安全錯誤回傳 stable error code，不包含 raw secret、Python exception string 或本機絕對路徑。
- 只要 request `Origin` 在 allowlist 中，包含 413 / 500 在內的錯誤回應都會保留 CORS header，讓前端可讀取錯誤內容。
- **Current runtime** 的 session 狀態存在記憶體中，重啟後端會清空，`project_id` 需重新 import。
- **Current runtime 的兩種流程**：
  - **Project session**（`import` → `scans`）：建立 `project_id`，掃描結果綁在該 project 上。`detail-scans`、`mapping-proposals`、`mappings` 都必須走這條。Scan boundary review 內嵌在 `POST /api/scans` 的正式掃描前 gate。
  - **Viewer demo**（`map/build`）：只掃 path、更新 latest viewer payload，**不建立 `project_id`**。適合快速載圖，不能接後續 project-scoped API。
- `graph_view_model` 是前端渲染輸入；它是投影，不是 canonical truth，前端不應回寫。
- **Phase2 target contract**：本文件同時標出 static-trace-plan 目標欄位。若欄位標示為
  Phase2 target，代表前端可先對齊型別與 mock；不代表 current runtime 已可用。
  實際 runtime availability 仍以當前 backend sample / OpenAPI / trace script 為準。
  欄位語意、五態、activation、Mapping Completeness 與 GraphViewModel 邊界以
  `docs/MODEL-CONTRACT.md` 為準。

## Phase2 Static Contract Overlay（2026-07-05）

Phase2 static path 的 input 是 **AI system repo / workflow artifacts**，不是固定 RAG repo。
`rag-core-v1@1.1.0` 只保留為 v1 grounding compatibility template；active target 會經
`00A` compatibility gate、`13` cutover、`14` validation 後走 generic
`ai-system-map/v2`。API 只提供 generic map、profile、readiness findings 與 evidence artifacts。

本節只列 API Guide 需要知道的 endpoint / artifact overlay，不重複完整 Graph Studio 規格。
Graph Studio 的 projection semantics、reference map / repo overlay、五態圖例、lens 與
Evidence Inspector contract 以 `docs/MODEL-CONTRACT.md` 與 frontend handoff 文件為準。

Phase2 P0 output 是多個 independent sibling artifacts，不是一個 aggregate JSON：

```text
ai_system_map.json
evidence_table.json
call_graph.json
dataflow_hints.json
execution_paths.json
profile_signals.json
readiness_report.json
ai_system_map.md
system_map.mmd
execution_map.mmd
```

Frontend 不需要等 manual review 才能顯示第一次 scan 結果。Ambiguous evidence 只應顯示成
optional review queue；confirmed decision 會透過 Apply replay（不重掃、不重跑 UA）或下一次
Rescan 套用，不直接 mutate 當前 artifact。

Phase2 target 中，readiness 只透過 `readiness_report.json.findings[]`、profile/capability
assessment 與 GraphViewModel projection 呈現；frontend 不需要也不應自行判斷 repo 是否
屬於某種 RAG。

## Phase2 Target — UA Scanner Staged Rollout

UA integration 尚未進入 current runtime；目前 Step 3 仍由
`ProjectScanService` 與現有 KAI scan providers 執行。Phase2 分三階段遷移：

- **Phase A — TOML primary（current runtime）**：現有 KAI providers 產生 Step 3
  facts/evidence；`ua-analysis-result` 可以不存在。
- **Phase B — UA primary + TOML parity（target）**：UA structural extraction 成為
  primary；KAI providers 只產 parity report。
- **Phase C — UA only（target）**：Plan 14 parity gate 通過後，由 Plan 18 退役
  transitional KAI provider 主掃描路徑。
- `ua-analysis-result.json` 是 reserved nullable internal sidecar slot，不列 public
  artifact。Phase2 active path 不執行 `file-analyzer` bounded LLM，因此不產生、不消費
  semantic sidecar；Step 6 由純 Python `ProfileInferenceService` 定案五態。
- UA failure 在 Phase B/C 採 fail-closed；Apply 沿用同一 `scan_id`、不重跑 UA，
  並建立新的 `build_id`。Rescan 建立新 `scan_id` 並重跑 UA。
- Plan 17 `AssessmentOrchestrator` / AI semantic candidate flow 已 deferred，不是
  Phase2 acceptance dependency。

UA integration 本身不要求 frontend 讀取 UA 欄位；但 broader Phase2 contract 仍會因
00A、03A、build-scoped API 與 safe artifact refs 改變 response shape。

```json
// 錯誤回傳範例
{ "detail": "project_not_found" }
```

## 快速開始

```bash
# 1. 啟動後端
.venv/bin/uvicorn kai_mind.web.app:create_app --factory --host 127.0.0.1 --port 8000

# 2. 一次性掃描並取得 viewer payload（最簡單的 demo 路徑）
curl -s -X POST http://127.0.0.1:8000/api/map/build \
  -H 'Content-Type: application/json' \
  -d '{"project_path":"/abs/path/to/rag_project"}' | jq '.status'

# 3. 讀取最新地圖
curl -s http://127.0.0.1:8000/api/map | jq '.viewer_load_result.loaded'
```

每個 endpoint 都有對應的可執行範例腳本，例如 `scripts/trace_map_build.sh`、`scripts/trace_all.sh`（一次跑完全部）。

---

## 1. 專案與掃描

**Project session 流程**：`import` 取得 `project_id` → `scans` 觸發掃描 → `scan/events` 看進度。後續 detail scan / mapping 都依賴此 `project_id`。

**Viewer demo 捷徑**：`map/build` 一次掃 path 並更新 `/api/map`，但不建立 project session（見下方說明）。

### POST /api/projects/import

登記本機專案路徑，建立 `project_id` 供後續掃描引用。不支援 upload / zip。

```http
POST /api/projects/import
```

```json
{ "source_type": "local_path", "project_path": "/abs/path/to/project" }
```

Response `200`：

```json
{
  "project_id": "project:<uuid>",
  "source_type": "local_path",
  "project_name": "custom_router_rag",
  "project_path": "/abs/path/to/project"
}
```

### POST /api/scans

用已 import 的 `project_id` 執行 L1 系統掃描（同步）。正式掃描前會先做 scan boundary preflight；若有 `.env`、secret-like config、vector persistence path 等需要使用者確認的 target，response 會先回 `requires_boundary_decision`，不產生 map、不寫 artifact、不更新 `/api/map`。使用者在同一個 endpoint 帶本次 `boundary_decisions` 後，才會正式掃描並更新 `/api/map`。

Current runtime 仍使用現有 KAI scan providers。Phase B/C target 才會在 Step 2
boundary 完成後呼叫 Understand-Anything sidecar 作為 Step 3 primary source；
屆時 UA sidecar 無效會 fail closed 並以 `status:"error"` / build error 呈現。

```http
POST /api/scans
```

```json
{
  "project_id": "project:<uuid>",
  "scan_depth": "system",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false,
  "boundary_decisions": []
}
```

若不需要人工決定，或已提供完整本次 decisions，Response `200`：

```ts
{
  scan_id: string;
  project_id: string;
  status: "completed" | "error";
  build_result: MapBuildResult; // 見 POST /api/map/build
  boundary_proposals: [];
  available_boundary_actions: ["scan_this_run", "skip_this_run"];
}
```

若需要使用者先決定本次掃不掃，Response `200`：

```ts
{
  scan_id: string;
  project_id: string;
  status: "requires_boundary_decision";
  build_result: null;
  boundary_proposals: ScanBoundaryProposal[];
  available_boundary_actions: ["scan_this_run", "skip_this_run"];
}
```

把本次 decision 送回同一個 endpoint：

```json
{
  "project_id": "project:<uuid>",
  "scan_depth": "system",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false,
  "boundary_decisions": [
    {
      "target_path": ".env",
      "fingerprint": "sha256:...",
      "decision": "scan_this_run",
      "reason": "Need this config for the current scan."
    }
  ]
}
```

- `scan_this_run`：只讓該 target 在這一次 scan 進入 Step 3 scan input。
- `skip_this_run`：只在這一次 scan 把該 target 從 Step 3 scan input 排除。API-visible 結果是本次 `files_scanned` 下降、`files_skipped` 上升；內部 inventory reason 為 `skipped_by_policy_overlay`，不會作為前端可依賴的 canonical map 欄位輸出。
- Decision 必須 match `target_path + fingerprint`；檔案內容或 metadata 改變時，舊 decision 不套用，API 會重新回 `requires_boundary_decision`。
- Decision 不會保存成歷史偏好，也不會影響下一次 scan。
- 已由 deterministic scanner hard-skip 的 large/binary/generated/log、dependency/cache、model weights 等 target 只留在 skipped audit trail，不產生使用者 decision proposal。

前端建議流程：

1. 使用者按「開始掃描」後，前端先送一次 `POST /api/scans`。
2. 若 response 是 `requires_boundary_decision`，前端一次列出 `boundary_proposals` 內所有項目，不要逐項呼叫 API。
3. 使用者針對所有項目選完 `scan_this_run` / `skip_this_run` 後，前端用同一個 `POST /api/scans` 一次送回完整 `boundary_decisions`。
4. 第二次 response 是 `completed` 時才顯示正式掃描結果；若再次回 `requires_boundary_decision`，代表 decision 不足或 fingerprint 已 stale，前端應重新顯示新的確認清單。
5. UI 文案應使用「確認本次掃描範圍」與「確認並繼續掃描」，不要說「重新上傳」或「下一次才生效」。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `Project not found` | 404 | `project_id` 未 import 或後端已重啟 |
| 驗證失敗 | 422 | `boundary_decisions` action/path/fingerprint payload 不合法 |

### GET /api/scan/events

掃描進度 SSE。現階段送出一筆 `scan_progress`（completed）後關閉串流。

```http
GET /api/scan/events
Accept: text/event-stream
```

```text
event: scan_progress
data: {"event":"scan_progress","status":"completed","stage":"validate","message":"Scan completed.","percent":100,"scan_depth":"system","timestamp":"...Z"}
```

後端現階段固定送 `event: scan_progress`（payload 內 `event` 欄位同值）。前端 parser 可相容 `message` 別名，但不必期待後端送未命名 event。

前端依序解析 `node_id` → `edge_id` → `component_id` → `source_id` → `slot` 找出要 highlight 的目標。

### POST /api/map/build

All-in-one viewer / demo build：送入 path 觸發 L1 build，寫出 artifact，更新 current
runtime 的 process-wide latest `/api/map`。

Current runtime 的 Step 3 仍由現有 KAI scan providers 執行。Phase B/C target 才改由
UA structural sidecar 主導，並在 UA 失敗時 fail closed。

> **不建立 project session**——沒有 `project_id`，build result 也不會存到 project-scoped store。若要接 `detail-scans` 或 `mapping-proposals`，請改走 `import` → `scans`。

```http
POST /api/map/build
```

```json
{
  "project_path": "/abs/path/to/project",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false
}
```

Current runtime response `200`（`MapBuildResult`）：

```ts
{
  status: "ok" | "error";
  project_name: string;
  output_run_dir: string;
  map_json_path: string | null;
  map_markdown_path: string | null;
  map_error_path: string | null;
  viewer_load_result: ViewerLoadResult; // 見 GET /api/map
  ai_system_map: object;                // canonical 掃描事實；Phase2 target: ai-system-map/v2
  warnings: string[];
  error: string | null;
}
```

> Current runtime 的 `output_run_dir` 與 `*_path` 可能是 server-local absolute path，
> 僅屬 compatibility contract。Phase2 target response 不得新增或延續 absolute-path 欄位。

Phase2 target 以兩層 identity 與 safe artifact refs 回傳：

```ts
type ArtifactRef = {
  artifact_id: string;
  artifact_type: string;
  file_name: string; // basename only
  media_type: string;
  sha256: string;
  size_bytes: number;
};

type Phase2MapBuildResult = {
  status: "ok" | "error";
  scan_id: string;  // immutable read-only scan snapshot
  build_id: string; // one materialization from that scan
  environment_id: string;
  artifacts: ArtifactRef[];
  viewer_load_result: ViewerLoadResult | null;
  ai_system_map: object | null;
  warnings: string[];
  error: string | null;
};
```

Phase2 active target 不另設 `snapshot_id`；同一 `scan_id` 可產生 initial、Apply 或
Detail Scan 等多個 immutable `build_id`。

---

## 2. 地圖讀取（Viewer）

### Current runtime 與 Phase2 target

| Contract | Current runtime | Phase2 target |
|---|---|---|
| Read surface | process-wide `GET /api/map` | project latest 或指定 `build_id` |
| Response wrapper | `ViewerPayload` | build-scoped `ViewerLoadResult` |
| Persistence | `InMemorySessionStore` latest only | project/scan/build local JSON repositories |
| Identity | 無持久化 build identity | `scan_id` + `build_id` |
| Artifacts | server-local `*_path` compatibility fields | safe `artifact_refs` |

Phase2 primary endpoints：

```http
GET /api/projects/{project_id}/map-builds/latest
GET /api/map-builds/{build_id}
POST /api/map-builds/{base_build_id}/apply
```

這三支 endpoint 都是 Phase2 target，尚未存在於 current OpenAPI。`GET /api/map`
與 `GET /map` 在 Phase2 僅保留為單專案 demo / legacy compatibility path。

### GET /api/map

Current runtime 回傳目前 process session 最新的 viewer payload。它是現行前端 API mode
入口，但不是 Phase2 build history 的正式讀取入口。

```http
GET /api/map
```

Response `200`（`ViewerPayload`）：

```ts
{
  viewer_load_result: {
    loaded: boolean;
    error_reason: string | null;
    map_json: string | null;
    ai_system_map: object;
    graph_view_model: {
      schema_version: string;            // "graph-view-model/v1"
      source_schema_version: string | null;
      summary: object | null;
      nodes: GraphNode[];
      edges: GraphEdge[];
      details: {
        evidence_by_id: Record<string, object>;
        risk_hints_by_id: Record<string, object>;
      };
      filters: { available: GraphFilter[]; behavior?: string };
    };
  };
}
```

尚未 build 前仍回傳 contract-compatible payload：`loaded:false`、`error_reason:"no_map_loaded"`、空 `nodes`/`edges`。

### GET /map

`GET /api/map` 的 legacy fallback，回傳完全相同的 `ViewerPayload`。前端會先試 `/api/map`，失敗再退回 `/map`。

### GET /api/projects/{project_id}/map-builds/latest（Phase2 target）

取得指定 project 的 latest immutable build，不讀 process-wide latest。

### GET /api/map-builds/{build_id}（Phase2 target）

取得指定歷史 build。Response 直接包含 build-scoped `ViewerLoadResult`：

```ts
type ViewerLoadResult = {
  loaded: boolean;
  error_reason: string | null;
  warnings: string[];
  scan_id: string;
  build_id: string;
  environment_id: string;
  artifact_refs: ArtifactRef[];
  ai_system_map: object;
  profile_inference_result: object | null;
  readiness_report: object | null;
  graph_view_model: GraphViewModel;
};
```

`artifact_refs` 不包含 server-local absolute path；frontend 只能依 stable artifact id/type
與受控下載／讀取 API 使用 artifact。

### POST /api/map-builds/{base_build_id}/apply（Phase2 target）

套用已確認 manual mappings，沿用 base build 的同一 `scan_id`，跳過 Step 3 並重跑
Step 4～7，建立新的 `build_id`。Apply 不重新掃描 repo；Phase B/C 也不重跑 UA。

```json
{ "mapping_ids": ["mapping:abc", "mapping:def"] }
```

```ts
{
  project_id: string;
  scan_id: string;
  build_id: string;
  based_on_build_id: string;
  build_reason: "apply_confirmations";
  applied_mapping_ids: string[];
  build_result: Phase2MapBuildResult;
  viewer_load_result: ViewerLoadResult;
}
```

### POST /api/viewer/load

載入磁碟上既有的 `ai_system_map.json`，重新 validate 後成為最新 viewer payload。**不掃描專案、不呼叫 scanner。**
這支 current compatibility endpoint 接受 server-local `map_json_path`；Phase2 target
build-scoped workflow 改用 safe `artifact_refs`，不接受 frontend 傳入任意 absolute path。
若同一 run directory 有 `profile_signals.json`、`readiness_report.json` 或 static execution
artifacts，Phase2 target viewer 可讀取它們作為 enrichment；缺失時應回 warnings，不阻塞
base graph 載入。

```http
POST /api/viewer/load
```

```json
{ "map_json_path": "outputs/<run>/ai_system_map.json" }
```

Response `200`：`ViewerPayload`。
map 無效時仍回 `200`，但 `loaded:false` 並帶 `error_reason`，讓前端渲染明確的 broken-map 狀態而非崩潰。

### GET /api/map/report

回傳目前 session 最新的 Markdown report（讀 `map_build` 寫出的 `map_markdown_path`，不接受任意路徑）。

```http
GET /api/map/report            # 行內檢視
GET /api/map/report?download=true   # 觸發附件下載
```

Response `200`：`Content-Type: text/markdown; charset=utf-8`（純文字）。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `map_markdown_not_available` | 404 | 尚無成功的 build，或檔案不存在 |

---

## 3. Detail Scan（L2 / L3 漸進式掃描）

對單一目標做有界的深掃，結果以 append-only 方式追加到 canonical map 後再回傳。**需先完成 project session**（`import` → `scans`）；只用 `map/build` 不足以滿足 `map_not_loaded` 檢查。

### POST /api/detail-scans

```http
POST /api/detail-scans
```

```json
{
  "project_id": "project:<uuid>",
  "target_type": "component_slot",
  "target": "app_api_or_orchestrator",
  "scan_depth": "component"
}
```

- `target_type`：`component_slot` | `component_instance` | `unmapped_component` |
  `capability_candidate` | `profile` | `edge` | `evidence`
  （另接受別名 `slot` / `component` / `unmapped`）
- `extension` 僅屬 legacy v1 compatibility；active v2 UI 不應把 extension 當作 detail target。
- `scan_depth`：`component`（L2）| `code_path`（L3）

Response `200`：

```ts
{
  project_id: string;
  detail_scan: DetailScanResult; // id, target_type, target, scan_depth, status, findings[], code_path[], warnings[]
  ai_system_map: object;          // 已追加新 evidence 並通過 validation 的整份 map
}
```

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `project_not_found` | 404 | `project_id` 不存在 |
| `map_not_loaded` | 404 | 該專案尚未有掃描結果 |
| `target_not_found` | 422 | `target` 在 map 中不存在 |

### GET /api/detail-scans/{detail_scan_id}

依 id 讀回已完成的 detail scan 與更新後的 map。

```http
GET /api/detail-scans/{detail_scan_id}
```

Response `200`：與 `POST /api/detail-scans` 相同。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `detail_scan_not_found` | 404 | 找不到該 detail scan id |

---

## 4. Query Trace（Runtime opt-in）

對已載入 project map 的某個 endpoint id 執行一次黑箱 query trace。這是明確 opt-in 的 runtime 路徑；`POST /api/scans`、`POST /api/map/build`、`GET /api/map` 不會自動呼叫任何 endpoint。

Trace 只回傳 transient `TraceRunResult`，不寫回 `ai_system_map.query_trace_events`，也不會把 observed unmapped component 自動升級成 confirmed mapping 或 baseline edge。

Static execution artifacts（`call_graph.json`、`dataflow_hints.json`、`execution_paths.json`）
不是 runtime trace。Frontend 不可把 static inferred path 轉成 `trace_steps`，也不可用它宣稱
某次 query 實際執行該路徑。

Query Trace 會從該 project session 的 `project_path/pyproject.toml` 讀取 optional tool config。沒有設定時使用預設 retrieved chunk keys：`retrieved_chunks`、`chunks`、`documents`。

```toml
# 被掃描專案的 pyproject.toml
[tool.kai-mind.trace]
retrieved_chunks_keys = [
  "retrieved_chunks",
  "chunks",
  "documents",
  "docs",
  "retrieved_docs",
  "context",
]
```

CLI 使用同一套設定 loader，但需要顯式傳入 project root，避免從 map artifact 猜測來源：

```bash
kai-mind trace outputs/run/ai_system_map.json \
  --endpoint-id endpoint:chat \
  --query "hello" \
  --project-root /abs/path/to/scanned-project
```

### POST /api/trace

```http
POST /api/trace
```

```json
{
  "project_id": "project:<uuid>",
  "endpoint_id": "endpoint:<id>",
  "query": "raw query sent once to the endpoint",
  "timeout_seconds": 30
}
```

Response `200`：

```ts
{
  trace_id: string;
  status: "completed" | "partial" | "endpoint_not_found" | "error";
  query_sent: boolean;
  endpoint_id: string;
  events: QueryTraceEvent[]; // request_sent / response_received / error / endpoint_not_found
  warnings: string[];
  error_reason: string | null;
}
```

資料安全約定：

- `query`、response output、`retrieved_chunks` 進入 event 前會被遮蔽/摘要化；response 不回傳 raw query 或 raw answer。
- `endpoint_id` 必須存在於該 project 的 `ai_system_map.endpoints[]`；找不到時回 `status:"endpoint_not_found"`、`query_sent:false`，不送任何 HTTP request。
- endpoint URL 視為不可信輸入。預設 safe mode 會在 request 前解析 hostname/DNS，並阻擋 metadata、loopback、private、link-local、unspecified、multicast、reserved 與其他 non-global 位址。
- egress policy 阻擋時回 `status:"partial"`、`query_sent:false`、`error_reason:"egress_policy_blocked"`，events 只包含一個 `status:"blocked"` 的 `error` event，不會先產生 `request_sent`。
- Query Trace 不跟隨 HTTP redirect，預設 HTTP client 也不讀取 `HTTP_PROXY`、`HTTPS_PROXY` 或 `ALL_PROXY` 等環境 proxy 設定。
- `retrieved_chunks_keys` 必須是非空字串陣列；設定錯誤會讓 route 回 `invalid_trace_config`，不會 fallback 成看似成功但漏資料的 trace。
- 被掃描專案的 `[tool.kai-mind.trace]` 只控制 retrieved chunk keys，不能自行開啟 localhost/private egress。Local-dev 例外必須由 KAI-Mind operator 在 app startup 注入明確 host + port allowlist；CLI 目前固定使用 safe mode。
- timeout / transport error 回 `status:"partial"`，保留 `request_sent` 與 `error` events，讓前端可以 replay 到失敗點。
- 若 response metadata 暗示已知 `unmapped_component_id`，event 只標示 `step_type:"unknown"` 與 `needs_mapping_confirmation`，確認與持久化仍交給 mapping / proposal 流程。

完整安全邊界、local-dev 注入範例與 DNS rebinding 剩餘限制，請見
[`docs/security/query-trace-egress-policy.md`](security/query-trace-egress-policy.md)。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `project_not_found` | 404 | `project_id` 不存在 |
| `map_not_loaded` | 404 | 該專案尚未有掃描結果 |
| `invalid_trace_config: ...` | 400 | `pyproject.toml` 的 `[tool.kai-mind.trace]` 格式錯誤 |
| `egress_policy_blocked` | 200 / `partial` | endpoint 在送出 request 前被 SSRF egress policy 阻擋 |

---

## 5. Manual Mappings

保存使用者對 `unmapped / needs_confirmation` 元件做出的 project-level 決定。只寫入 mapping store，不直接 mutate map artifact。
Phase2 UI 語意是 **optional ambiguous evidence review**：第一次 scan 結果應先顯示；
review decision 透過 Apply replay（同 scan snapshot、不重跑 UA）或下一次 Rescan 改善後續 map。

### GET /api/mappings

```http
GET /api/mappings?project_id=project:<uuid>
```

Response `200`：

```ts
{
  project_id: string;
  mappings: ManualMapping[];
  available_actions: ["confirm", "edit", "reject", "skip_for_now", "mark_not_applicable"];
}
```

### POST /api/mappings

建立一筆 mapping 決定。`evidence_ids` 必填。`decision: "confirmed"` 時依 `mapping_type` 補齊欄位：

| `mapping_type` | `confirmed` 必填欄位 |
| --- | --- |
| `existing_slot_mapping` | `target_slot`（已知 grounding slot / dimension）、`component_name` |
| `non_baseline_capability_candidate` | `capability_candidate_id`、`capability_candidate_name`、`capability_candidate_kind` |
| `new_extension_component` | legacy compatibility only；active v2 UI 不應建立新的 extension |

```http
POST /api/mappings
```

```json
{
  "project_id": "project:<uuid>",
  "mapping_type": "non_baseline_capability_candidate",
  "decision": "confirmed",
  "source_unmapped_id": "unmapped:reranker",
  "capability_candidate_id": "capability-candidate:reranker",
  "capability_candidate_name": "Reranker",
  "capability_candidate_kind": "reranker",
  "evidence_ids": ["evidence:<id>"]
}
```

- `mapping_type`：`existing_slot_mapping` | `non_baseline_capability_candidate` |
  `new_extension_component`（legacy compatibility）
- `decision`：`confirmed` | `rejected` | `skip_for_now` | `not_applicable`

Response `200`：`ManualMapping`（含 `mapping_id`、`mapping_digest`、`created_at`、`updated_at`）。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| 驗證失敗 | 422 | 缺 evidence、未知 slot、含未遮蔽 secret 等 |

### PATCH /api/mappings/{mapping_id}

部分更新一筆 mapping（會重新 validate 並產生新的 `mapping_digest`）。

```http
PATCH /api/mappings/{mapping_id}
```

```json
{ "reason": "Confirmed after reviewing config.yaml" }
```

可更新欄位：`decision`、`reason`、`target_slot`、`component_name`、`component_kind`、
`provider`、`capability_candidate_id`、`capability_candidate_name`、
`capability_candidate_kind`、`audit_metadata`。Extension 欄位只屬 legacy compatibility。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `mapping_not_found` | 404 | id 不存在 |
| 驗證失敗 | 422 | 更新後的結果不符合規則 |

---

## 6. Mapping Proposals（AI 建議）

針對 unmapped 元件向 LLM 取得 mapping 候選，使用者再做決定。**需先完成 project session**（`import` → `scans`）。

**Provider 啟用條件**（兩者缺一不可，否則走 deterministic fallback，仍可離線使用）：

```bash
KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true
NVIDIA_API_KEY=<your-key>
```

僅有 `NVIDIA_API_KEY` 而沒有 explicit flag 時，後端仍用 deterministic provider（`provider_name: "deterministic"`）。

### GET /api/mapping-proposals

```http
GET /api/mapping-proposals?project_id=project:<uuid>
```

Response `200`：

```ts
{
  project_id: string;
  proposals: MappingProposal[];
  available_actions: ["accept", "edit", "reject", "skip_for_now"];
}
```

### POST /api/mapping-proposals

對某個 unmapped 元件建立一筆 pending proposal。

```http
POST /api/mapping-proposals
```

```json
{
  "project_id": "project:<uuid>",
  "source_unmapped_id": "unmapped:<id>",
  "user_description": "optional hint"
}
```

Response `200`（`MappingProposal`）：

```ts
{
  proposal_id: string;
  project_id: string;
  source_unmapped_id: string;
  status: "pending_user_confirmation";
  candidates: MappingCandidate[];   // candidate_type: existing_slot_mapping / non_baseline_capability_candidate / needs_more_information / skip_for_now
  evidence_packet: object;          // 送給 provider 的 masked evidence 摘要
  provider_name: string;            // "deterministic" | "nvidia-nim"
  provider_error_reason: string | null; // fallback 時如 "provider_unavailable"
  user_description: string | null;
  available_actions: ["accept", "edit", "reject", "skip_for_now"];
  created_at: string;
  updated_at: string;
}
```

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `project_not_found` | 404 | `project_id` 不存在 |
| `map_not_loaded` | 404 | 該專案尚未有掃描結果 |
| `unmapped_not_found` | 404 | `source_unmapped_id` 不存在 |

### POST /api/mapping-proposals/{proposal_id}/decision

對 pending proposal 套用決定。

```http
POST /api/mapping-proposals/{proposal_id}/decision
```

```json
{ "decision": "accept", "candidate_id": "candidate:1" }
```

- `accept`：需 `candidate_id`，不可帶 `edited_mapping`
- `edit`：需 `edited_mapping`（`ManualMappingCreate` 形狀），不可帶 `candidate_id`
- `reject` / `skip_for_now`：兩者皆不帶

Response `200`：

```ts
{
  proposal: MappingProposal;          // status 變為 accepted / edited / rejected / skipped
  manual_mapping: ManualMapping | null; // accept / edit 時必有
}
```

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `proposal_not_found` | 404 | `proposal_id` 不存在 |
| 驗證失敗 | 422 | decision payload 不合法（如 accept 缺 candidate_id） |

---

## 7. Scan Boundary Same-Run Gate（掃描邊界審查）

Scan boundary review 已整合進 `POST /api/scans`，沒有獨立的 `/api/scan-boundary-proposals` endpoints。這個 gate 的目的，是在正式 Step 3 scan 前先攔住 `.env`、secret-like config、vector persistence path 等需要人工確認的 target，避免第一次 scan 就深入讀取敏感或 local-only 檔案。

核心規則：

- 使用者只選本次 scan 要不要掃該 target，不保存歷史偏好。
- 只有 `scan_this_run` / `skip_this_run` 兩個 action。
- `target_path + fingerprint` 必須 match 才套用 decision。
- 若 decision 不足或已 stale，`POST /api/scans` 會回 `requires_boundary_decision`，且不更新 `/api/map`。
- `POST /api/map/build` viewer demo flow 不走這個 gate。

可用以下 trace script 端到端驗證 same-run gate 行為：

```bash
scripts/trace_scan_boundary_policy_overlay.sh --start-server
scripts/trace_scan_boundary_multi_decision_gate.sh --start-server
```

它會建立含 `.env` 的暫時專案，驗證第一次 scan 回 `requires_boundary_decision`，第二次帶 `scan_this_run` 後完成正式掃描，第三次不帶 decision 會再次要求決策，並讀取完成後的 `map_json_path` 確認 `ai_system_map.json` 可被 `jq` 解析且未包含 raw secret。
第二支 script 會建立含 `.env` 與 `vector_store/data.index` 的暫時專案，驗證第一次 response 一次回傳所有 pending proposals、pending 時不更新 `/api/map`、第二次可一次送回所有 `boundary_decisions` 後完成正式掃描，並確認存下來的 `ai_system_map.json` 與 response 的 `scan_summary.files_scanned/files_skipped` 一致。

---

## 錯誤對照表

| 狀態 | 意義 | 常見 `detail` |
| --- | --- | --- |
| 200 | 成功（含「map 無效」這類明確的 loaded:false 狀態） | — |
| 404 | 目標不存在 | `project_not_found`、`map_not_loaded`、`unmapped_not_found`、`proposal_not_found`、`detail_scan_not_found`、`mapping_not_found`、`map_markdown_not_available` |
| 413 | request body 超過本機 API resource limit | `request_too_large` |
| 422 | 輸入不合法 / 驗證失敗 | `target_not_found`、validation 陣列 |
| 500 | 未預期後端錯誤，回應會遮蔽 raw path / secret | `internal_server_error` |

> 後端重啟會清空記憶體 session。出現 404 `project_not_found` / `map_not_loaded` 時，請重新 `import` 並 `scan`。

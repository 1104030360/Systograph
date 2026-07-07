# KAI-Mind Local API Guide

本機 FastAPI 後端的 **HTTP 契約**：endpoint、request/response、錯誤碼。欄位語意、五態、activation、GraphViewModel 規則見 [`MODEL-CONTRACT.md`](MODEL-CONTRACT.md)。

## 相關文件

| 用途 | 文件 |
|------|------|
| 欄位語意 / artifact lifecycle | `docs/MODEL-CONTRACT.md` |
| Phase2 設計意圖 | `docs/design/epic1-phase2.md` |
| 執行計畫與 gate | `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md` |
| JSON 範例 | `docs/work/Timmy/design/EPIC1/frontend-json-handoff/` |
| 可執行 trace | `scripts/trace_*.sh` |
| OpenAPI | `http://127.0.0.1:8000/docs` |

## 全域約定

| 項目 | 規則 |
|------|------|
| Base URL | `http://127.0.0.1:8000`（`VITE_API_BASE_URL` 可覆寫） |
| Auth | 無；local-only，綁 `127.0.0.1` |
| CORS | `http://127.0.0.1:5173`、`http://localhost:5173` |
| Content-Type | JSON；SSE 為 `text/event-stream`；report 為 `text/markdown` |
| Body 上限 | 1 MB；超限 `413` + `{ "detail": "request_too_large" }` |
| 未知欄位 | 寫入類 endpoint `extra="forbid"` |
| 錯誤格式 | `{ "detail": string }`；422 時 `detail` 為陣列 |
| 安全錯誤 | 413/500 不回 raw secret、exception string、absolute path |
| Session | **Current runtime** 狀態在記憶體；重啟後需重新 `import` |

### 兩種流程

| 流程 | 路徑 | 用途 |
|------|------|------|
| **Project session** | `import` → `scans` → … | 正式 workflow；detail scan / mapping / proposals 必走此路 |
| **Viewer demo** | `map/build` → `GET /api/map` | 快速載圖；**無** `project_id`，不能接 project-scoped API |

> **Phase2 標記：** 標 `[phase2]` 的 endpoint / 欄位為 target contract，current runtime 可能尚未實作。Pipeline、UA rollout、artifact 清單見 MODEL-CONTRACT；架構分層見 `epic1-phase2.md` §6。

### Phase2 重點（API 視角）

- Identity：`scan_id`（immutable snapshot）+ `build_id`（一次 materialization）；**無** `snapshot_id`
- `environment_id` 固定 `environment:default-static`
- Apply：跳 Step 3 / UA；先 **4-1 bridge replay**，再 **4-2 confirmed mappings**，重跑 Step 4～7
- Response 用 `viewer_load_result`（非 `viewer_payload`）；型別見 MODEL-CONTRACT
- **10** public sibling artifacts（7 JSON + 3 render）一次 atomic publish；另 **+1** ephemeral
  `graph_view_model`（API inline，非磁碟 sibling）。詳見 MODEL-CONTRACT §3 artifact 計數、§7、§9

## Endpoint 總覽

| Method | Path | 流程 | Runtime | § |
|--------|------|------|---------|---|
| POST | `/api/projects/import` | project | current | 1 |
| POST | `/api/scans` | project | current | 1 |
| GET | `/api/scan/events` | project | current | 1 |
| POST | `/api/map/build` | demo | current | 1 |
| GET | `/api/map` | demo | current | 2 |
| GET | `/map` | demo | current | 2 |
| POST | `/api/viewer/load` | demo | current | 2 |
| GET | `/api/map/report` | demo | current | 2 |
| POST | `/api/detail-scans` | project | current | 3 |
| GET | `/api/detail-scans/{id}` | project | current | 3 |
| POST | `/api/trace` | project | current | 4 |
| GET/POST/PATCH | `/api/mappings`… | project | current | 5 |
| GET/POST | `/api/mapping-proposals`… | project | current | 6 |
| GET | `/api/projects/{id}/map-builds` | build | **[phase2]** | 2 |
| GET | `/api/projects/{id}/map-builds/latest` | build | **[phase2]** | 2 |
| GET | `/api/map-builds/{build_id}` | build | **[phase2]** | 2 |
| POST | `/api/map-builds/{base_build_id}/apply` | build | **[phase2]** | 2 |
| POST | `/api/map-builds/{build_id}/detail-scans` | build | **[phase2]** | 2 |
| POST | `/api/map-builds/{build_id}/trace` | build | **[phase2]** | 2 |

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

`project_path` 是 current runtime compatibility 欄位，可能包含 server-local absolute path。
Phase2 target response **不得**回傳 raw absolute path；project identity 應只暴露
`project_id`、safe display metadata，以及可用於重用 project 的 `canonical_path_digest`。

Phase2 target response：

```ts
{
  project_id: string;
  source_type: "local_path";
  project_name: string;
  canonical_path_digest: string;
}
```

### POST /api/scans

用已 import 的 `project_id` 執行 L1 系統掃描（同步）。正式掃描前會先做 scan boundary preflight；若有 `.env`、secret-like config、vector persistence path 等需要使用者確認的 target，response 會先回 `requires_boundary_decision`，不產生 map、不寫 artifact、不更新 `/api/map`。使用者在同一個 endpoint 帶本次 `boundary_decisions` 後，才會正式掃描並更新 `/api/map`。

> **Phase2 target：** project-scoped scan/build 應產生持久化 `scan_id` + `build_id`，並透過
> `GET /api/projects/{project_id}/map-builds/latest` 或 `GET /api/map-builds/{build_id}` 讀取；
> **不得**再依賴更新 process-wide `/api/map` 作為正式讀取入口。Boundary preflight
> 尚未完成時不得建立 domain `scan_id`、Build 或 artifacts；若 transport 需要追蹤 id，
> 應使用 `preflight_request_id`，不得冒充 scan identity。

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

上方是 current compatibility shape。Phase2 target pending response 不含 `scan_id`：

```ts
{
  preflight_request_id?: string;
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
5. UI 文案：「確認本次掃描範圍」／「確認並繼續掃描」（非「重新上傳」）。

Trace scripts：`scripts/trace_scan_boundary_policy_overlay.sh`、`scripts/trace_scan_boundary_multi_decision_gate.sh`。

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
  generated_from_build_id: string; // equals build_id for same-build publish
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

Phase2 primary endpoints（完整 surface，對齊 `epic1-phase2.md` §16）：

```http
POST /api/projects/import
POST /api/scans
GET  /api/projects/{project_id}/map-builds
GET  /api/projects/{project_id}/map-builds/latest
GET  /api/map-builds/{build_id}
POST /api/map-builds/{base_build_id}/apply
POST /api/map-builds/{build_id}/detail-scans
POST /api/map-builds/{build_id}/trace
```

下列 build-scoped endpoint **尚未存在於 current OpenAPI**；`GET /api/map` 與 `GET /map`
在 Phase2 僅保留 demo / legacy compatibility。Current runtime 仍使用
`POST /api/detail-scans`（`project_id`）與 `POST /api/trace`（`project_id`）；Phase2 遷移後
改為上表 build-scoped 路徑，且 detail scan 產生 **immutable child `build_id`**，不 overwrite parent。

### GET /api/projects/{project_id}/map-builds（Phase2 target）

列出 project 的 immutable build history。預設排序：`generated_at DESC`，tie-break `build_id DESC`。

```ts
type MapBuildListItem = {
  project_id: string;
  scan_id: string;
  build_id: string;
  environment_id: string; // Phase2 fixed: "environment:default-static"
  generated_from_build_id: string;
  build_reason: "initial_scan" | "apply_confirmations" | "detail_scan";
  based_on_build_id?: string | null;
  generated_at: string;
  is_latest: boolean;
};
```

### GET /api/projects/{project_id}/map-builds/latest（Phase2 target）

取得指定 project 的 latest immutable build，不讀 process-wide latest。

### GET /api/map-builds/{build_id}（Phase2 target）

取得指定歷史 build。Response 直接包含 build-scoped `ViewerLoadResult`（對齊
`MODEL-CONTRACT.md` `ViewerLoadResult`）：

```ts
type ViewerLoadResult = {
  loaded: boolean;
  error_reason?: string | null;
  warnings: string[];
  project_id: string;
  scan_id: string;
  build_id: string;
  environment_id: string; // Phase2 fixed: "environment:default-static"
  generated_from_build_id: string;
  based_on_build_id?: string | null;
  applied_mapping_ids: string[];
  artifact_refs: ArtifactRef[];
  ai_system_map: object;
  profile_inference_result: ProfileInferenceResult | null; // ≡ validated profile_signals.json
  readiness_report: ReadinessReport | null;
  graph_view_model: GraphViewModel; // ephemeral projection; not a persisted sibling JSON file
};
```

`profile_inference_result` 缺失或 invalid 時：`profile_inference_result: null`，`warnings`
含 `profile_signals_missing` 或 `profile_signals_invalid`；canonical map 仍可 load（degraded mode）。

`artifact_refs` 不包含 server-local absolute path；frontend 只能依 stable artifact id/type
與受控下載／讀取 API 使用 artifact。

#### ViewerLoadResult 載入策略

| 來源 artifact | API 欄位 | 載入 |
|---------------|----------|------|
| `ai_system_map.json` | `ai_system_map` | inline |
| `profile_signals.json` | `profile_inference_result` | inline |
| `readiness_report.json` | `readiness_report` | inline |
| Step 7 投影 | `graph_view_model` | inline（ephemeral；**非**磁碟 sibling） |
| static execution 三件套 | — | `artifact_refs[]` lazy load |
| `evidence_table.json` | — | `artifact_refs[]` lazy load |
| `*.md` / `*.mmd` render | — | `artifact_refs[]` lazy load |

**主畫布 ≠ merge 六份 Step 6 JSON**；只有 6-1 Profile Inference 經 Step 7 進 canvas。
Build 磁碟上 atomic publish **10** public siblings（7 JSON + 3 render）；`snapshot.json`、
manual mapping 屬 project state，**不**計入 7 JSON。見 MODEL-CONTRACT §3、§7.0、§9.1。

Frontend **不得**重算五態、activation、Mapping Completeness。Sidecar 缺失 → degraded load + warnings。完整型別與 enum 見 [`MODEL-CONTRACT.md`](MODEL-CONTRACT.md) § `ViewerLoadResult`、`GraphViewModel`、`readiness-report/v1`；handoff 見 `frontend-json-handoff/step-08-viewer/`。

### POST /api/map-builds/{base_build_id}/apply（Phase2 target）

套用已確認 manual mappings，沿用 base build 的同一 `scan_id`，跳過 Step 3 並從
**Step 4-1 bridge replay + Step 4-2 confirmed-mapping replay** 重跑 Step 4～7，建立新的
`build_id`。Apply 不重新掃描 repo；Phase B/C 也不重跑 UA。

**Request 驗證（fail-closed）：**

- `base_build_id` 必須是該 project 的 **latest** build；否則 `409` + `{ "detail": "base_build_not_latest" }`
- `mapping_ids` 必須 **non-empty、unique**、皆為 **confirmed** 且屬同一 `project_id`；否則 `422`
- 相同 `base_build_id` + 相同 sorted `mapping_ids` + 相同 mapping digests → **idempotent**（回同一 child build）

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

Apply publish 失敗時：**不得**切換 `latest_build_id`；pending confirmations 保留。

### POST /api/map-builds/{build_id}/detail-scans（Phase2 target）

對指定 immutable build 執行 detail scan，產生 **child build**（新 `build_id`、同一 `scan_id`），
不 overwrite parent map artifact。Current runtime 等價路徑為 `POST /api/detail-scans`（`project_id`）。

### POST /api/map-builds/{build_id}/trace（Phase2 target）

對指定 build 執行 opt-in query trace overlay。Current runtime 等價路徑為 `POST /api/trace`（`project_id`）。
Trace overlay 不得寫回 canonical map / profile artifacts。

### GET /api/map（legacy / demo）

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

Current runtime 對單一目標做有界深掃，結果會以 append-only 方式追加到目前
in-memory canonical map 後再回傳。Phase2 target 改由 build-scoped
`POST /api/map-builds/{build_id}/detail-scans` 產生 immutable child `build_id`；
不得 overwrite parent build。**需先完成 project session**（`import` → `scans`）；
只用 `map/build` 不足以滿足 `map_not_loaded` 檢查。

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

資料安全（摘要）：

- `query`、response、chunks 進 event 前遮蔽/摘要化
- `endpoint_id` 須存在於 map；否則 `endpoint_not_found`，不送 HTTP
- 預設阻擋 non-global / private / metadata 位址；egress 被擋 → `partial` + `egress_policy_blocked`
- 不跟隨 redirect；預設不讀 proxy env
- `[tool.kai-mind.trace]` 只控制 chunk keys；local-dev allowlist 由 operator 注入
- timeout / transport error → `status:"partial"`，保留 events 供 replay
- 完整 egress 政策見 [`docs/security/query-trace-egress-policy.md`](security/query-trace-egress-policy.md)

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

針對 unmapped 元件取得 mapping 候選，使用者再做決定。**需先完成 project session**（`import` → `scans`）。

> **與 deferred semantic 的差別：** 本節屬 **Phase2 active** Step 9（`proposal` 青綠底 + `py` 紫底）。
> optional NVIDIA NIM 為 **active-optional**（`runtimeConfig` 靛紫底）。**Deferred** 僅
> Step 3 semantic / Plan 17（`ai` 灰底紅框虛線）。

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

## 錯誤對照表

| 狀態 | 意義 | 常見 `detail` |
| --- | --- | --- |
| 200 | 成功（含「map 無效」這類明確的 loaded:false 狀態） | — |
| 404 | 目標不存在 | `project_not_found`、`map_not_loaded`、`unmapped_not_found`、`proposal_not_found`、`detail_scan_not_found`、`mapping_not_found`、`map_markdown_not_available` |
| 409 | 狀態衝突（Phase2 target） | `base_build_not_latest`（Apply stale base build） |
| 413 | request body 超過本機 API resource limit | `request_too_large` |
| 422 | 輸入不合法 / 驗證失敗 | `target_not_found`、`profile_sidecar_contract_invalid`（strict mode）、Apply 跨 project / unconfirmed / duplicate `mapping_ids`、validation 陣列 |
| 500 | 未預期後端錯誤，回應會遮蔽 raw path / secret | `internal_server_error` |

> 後端重啟會清空記憶體 session。出現 404 `project_not_found` / `map_not_loaded` 時，請重新 `import` 並 `scan`。

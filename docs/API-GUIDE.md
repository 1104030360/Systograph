# Systograph Local API Guide

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
| State | Project workflow 使用 `${SYSTOGRAPH_STATE_DIR:-~/.systograph}` local JSON；project、scan、build、mapping 與 latest 可跨重啟恢復。Demo `/api/map` 仍保留 process-latest compatibility（deprecated，即將移除） |

### 兩種流程

| 流程 | 路徑 | 用途 |
|------|------|------|
| **Project session** | `import` → `scans` → … | 正式 workflow；detail scan / mapping / proposals 必走此路 |
| **Viewer demo**（**deprecated，即將移除**） | `map/build` → `GET /api/map` | 快速載圖；**無** `project_id`，不能接 project-scoped API。已決定退役，勿建立新依賴；退役後讀圖一律需要 `project_id` |

> **標記：** `current` 是目前 OpenAPI 已實作；`[phase2-later]` 是後續 target。Pipeline、UA rollout、artifact 清單見 MODEL-CONTRACT；架構分層見 `epic1-phase2.md` §6。

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
| POST | `/api/map/build` | demo | **deprecated** | 1 |
| GET | `/api/map` | demo | **deprecated** | 2 |
| GET | `/map` | demo | **deprecated** | 2 |
| GET | `/api/map/report` | demo | current | 2 |
| POST | `/api/detail-scans` | project | current | 3 |
| GET | `/api/detail-scans/{id}` | project | current | 3 |
| POST | `/api/trace` | project | current | 4 |
| GET/POST/PATCH | `/api/mappings`… | project | current | 5 |
| GET/POST | `/api/mapping-proposals`… | project | current | 6 |
| GET | `/api/projects/{id}/map-builds` | build | current | 2 |
| GET | `/api/projects/{id}/map-builds/latest` | build | current | 2 |
| GET | `/api/map-builds/{build_id}` | build | current | 2 |
| POST | `/api/map-builds/{base_build_id}/apply` | build | current | 2 |
| POST | `/api/map-builds/{build_id}/detail-scans` | build | **[phase2-later]** | 2 |
| POST | `/api/map-builds/{build_id}/trace` | build | **[phase2-later]** | 2 |

## 快速開始

```bash
# 1. 啟動後端
.venv/bin/uvicorn systograph.web.app:create_app --factory --host 127.0.0.1 --port 8000

# 2. 匯入專案取得 project_id
curl -s -X POST http://127.0.0.1:8000/api/projects/import \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"local_path","project_path":"/abs/path/to/rag_project"}' | jq -r '.project_id'

# 3. 開 preflight 取得 preflight_request_id（path 中的 ":" 需 URL-encode 為 "%3A"）
curl -s -X POST "http://127.0.0.1:8000/api/projects/project%3A<uuid>/scan-preflights" \
  -H 'Content-Type: application/json' \
  -d '{}' | jq -r '.preflight_request_id'

# 4. 掃描（必帶 preflight_request_id；若回 requires_boundary_decision，
#    補上 boundary_decisions 用同一張單號再送一次）
curl -s -X POST http://127.0.0.1:8000/api/scans \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"project:<uuid>","preflight_request_id":"preflight:<digest>"}' \
  | jq '.status'

# 5. 讀取該 project 的最新地圖（path 中的 ":" 需 URL-encode 為 "%3A"）
curl -s "http://127.0.0.1:8000/api/projects/project%3A<uuid>/map-builds/latest" \
  | jq '.viewer_load_result.loaded'
```

> **舊的 demo 捷徑（`POST /api/map/build` → `GET /api/map`）已 deprecated**，
> 請改用上面的 project session 流程。

每個 endpoint 都有對應的可執行範例腳本，例如 `scripts/trace_map_build.sh`、`scripts/trace_all.sh`（一次跑完全部）。

---

## 1. 專案與掃描

**Project session 流程**：`import` 取得 `project_id` → `scans` 觸發掃描 → `scan/events` 看進度。後續 detail scan / mapping 都依賴此 `project_id`。

**Viewer demo 捷徑（deprecated，即將移除）**：`map/build` 一次掃 path 並更新 `/api/map`，但不建立 project session（見下方說明）。勿建立新依賴。

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
  "project_path": "/abs/path/to/project",
  "reused": false
}
```

`project_path` 是 current runtime compatibility 欄位，可能包含 server-local absolute path。
相同 canonical path 再 import 會回相同 `project_id` 與 `reused:true`。Project metadata
持久化於 local JSON state；後端重啟不需要重新建立 identity。後續 safe-response target
不得回傳 raw absolute path，project identity 應只暴露 `project_id` 與 safe display metadata。

後續 safe-response target：

```ts
{
  project_id: string;
  source_type: "local_path";
  project_name: string;
  reused: boolean;
}
```

### POST /api/projects/{project_id}/scan-preflights

建立可重試、無持久化副作用的 metadata-only inventory preflight。它會先套用
`scan_inventory_rules.toml`、Git／`.gitignore` 與不可覆寫的 filesystem safety，再回傳 Systograph
建議預設、必要敏感檔確認、可單次覆寫的 soft exclusions，以及 exact path 查詢結果。
Preflight 不讀候選檔內容、不產 snippet，也不建立 `scan_id`、snapshot、build 或 output。

```json
{
  "scan_depth": "system",
  "requested_paths": ["ignored/custom.py", "node_modules/local-package"],
  "reviewable_excluded_cursor": null,
  "reviewable_excluded_limit": 100
}
```

- Path 一律是 project-relative POSIX；root 只能寫 `.`，不接受 absolute、traversal 或 glob。
- Regular file 產生 `exact_file` proposal；directory 產生 bounded
  `recursive_directory` manifest。單一 scope 最多 5,000 個 observed regular files、
  500,000,000 selectable bytes、64 層；每次 request 最多 20 個 directory scopes。
- Directory payload 只回 summary 與 manifest fingerprint，不回 internal `entries[]`。
- `preflight_request_id` 綁定 project、candidate set、policy digest 與 safety version；它是 stale
  token，不是 authorization token。
- Git index仍列出但worktree已刪除的tracked path會計入`missing_count`，並以
  `tracked_missing_candidate_observed` warning呈現；不會讓其他安全檔案停止scan。

Response 主要欄位：

```ts
{
  preflight_request_id: string;
  project_id: string;
  source_mode: "git" | "recursive" | "fallback_after_git_error";
  inventory_policy_schema_version: string;
  inventory_policy_digest: string;
  candidate_set_digest: string;
  filesystem_safety_version: string;
  summary: {
    default_included_file_count: number;
    required_review_count: number;
    reviewable_excluded_count: number;
    hard_blocked_count: number;
    missing_count: number;
    collapsed_directory_count: number;
  };
  required_boundary_proposals: ScanBoundaryProposal[];
  reviewable_excluded_page: {
    items: ScanBoundaryProposal[];
    next_cursor: string | null;
    total: number;
  };
  requested_target_results: InventoryRequestedTargetView[];
  blocked_summaries: Array<{path: string; reason_code: string; can_expand: boolean}>;
  warnings: string[];
}
```

### POST /api/scans

必須帶 `preflight_request_id` 與本次 delta decisions 開始正式 scan。Backend 會重新 enumeration、
驗證 file metadata／directory manifest、套用 `hard safety > exact file > deepest directory >
ancestor directory > default policy`，通過 post-decision safe-open／binary probe 後才建立唯一的
final `FileInventory`。所有 current providers 只收到這份 final allowlist；此 runtime 不呼叫 UA。
Safe-open會以directory handle逐層使用no-follow lookup，open後以`fstat`重驗type／size／mtime／
identity，並在同一file handle建立content SHA-256；snapshot保存前會用相同adapter重驗，禁止退回
一般path-based second read。平台沒有必要primitive時fail closed。

```json
{
  "project_id": "project:<uuid>",
  "scan_depth": "system",
  "output": "outputs",
  "preflight_request_id": "preflight:<digest>",
  "boundary_decisions": [
    {
      "target_path": "node_modules/local-package",
      "fingerprint": "sha256:<manifest>",
      "decision": "scan_this_run",
      "selection_scope": "recursive_directory"
    },
    {
      "target_path": "node_modules/local-package/private.py",
      "fingerprint": "sha256:<metadata>",
      "decision": "skip_this_run",
      "selection_scope": "exact_file"
    }
  ]
}
```

`preflight_request_id` 是必填欄位：沒帶就回 422 `preflight_request_id_required`，不做任何
enumeration、snapshot 或 build。Client 一律先呼叫 `POST /api/projects/{project_id}/scan-preflights`
取得單號再掃描。

`scan_this_run`／`skip_this_run` 只作用於這次 scan，不改 `.gitignore`、TOML 或 Manual Mapping。
Directory decision涵蓋所有 selectable descendants；hard-blocked child仍保持 blocked，exact child
decision優先。沒有 optional decision 時維持 Systograph default；缺 required sensitive decision 時回
`requires_boundary_decision`。

Pending response 不含 `scan_id`，也沒有 snapshot/build/latest pointer：

```ts
{
  project_id: string;
  status: "requires_boundary_decision";
  preflight_request_id: string;
  build_result: null;
  boundary_proposals: ScanBoundaryProposal[];
  available_boundary_actions: ["scan_this_run", "skip_this_run"];
}
```

Completed response會回真實 `scan_id`、build與由 final audit投影的 summary：

```ts
{
  scan_id: string;
  project_id: string;
  status: "completed" | "error";
  preflight_request_id: string;
  build_result: MapBuildResult;
  inventory_selection_summary?: {
    included_file_count: number;
    skipped_file_count: number;
    directory_scope_results: Array<{
      target_path: string;
      decision: "scan_this_run" | "skip_this_run";
      observed_file_count: number;
      included_file_count: number;
      hard_blocked_file_count: number;
      post_decision_blocked_file_count: number;
    }>;
  };
}
```

Pending 階段同樣是 metadata-only，且只能決定 current required sensitive targets，不能藉此覆寫 soft
exclusions。Apply 重用保存的 snapshot，不重新 preflight或讀 repo；Rescan必須建立新 preflight，
不自動沿用上次 decisions。

Typed error body固定為 `{detail:{code,message,retryable,context}}`。主要 code：

| HTTP | code | 意義 |
| ---: | --- | --- |
| 404 | `project_not_found` | project不存在 |
| 422 | `preflight_request_id_required` | `POST /api/scans` 未帶 `preflight_request_id` |
| 409 | `inventory_preflight_stale` | candidate set已變；刷新 preflight |
| 409 | `inventory_selection_target_missing` | target已刪除；刷新 preflight |
| 409 | `inventory_selection_target_changed` | file metadata或directory manifest已變 |
| 422 | `inventory_selection_path_invalid` | absolute／traversal／glob／blank path |
| 422 | `inventory_selection_scope_invalid` | path type與scope不符 |
| 422 | `inventory_selection_duplicate_decision` | 同一 path/scope重複 |
| 422 | `inventory_selection_conflicting_decision` | 同一 path/scope決策衝突 |
| 422 | `inventory_selection_override_not_allowed` | hard/missing/未展開 target不可覆寫 |
| 422 | `inventory_selection_directory_limit_exceeded` | directory hard bound超限 |
| 422 | `inventory_selection_directory_no_scannable_files` | directory最後無安全child |
| 422 | `inventory_selection_post_decision_blocked` | exact file未通過內容安全 |
| 422 | `inventory_preflight_review_limit_exceeded` | required review超過200 |
| 422 | `inventory_rules_unavailable`／`inventory_rules_invalid` | policy catalog fail closed |
| 422 | `inventory_enumeration_failed` | candidate enumeration fail closed |

Trace scripts：`scripts/trace_scan_boundary_policy_overlay.sh`、
`scripts/trace_scan_boundary_multi_decision_gate.sh`、
`scripts/trace_inventory_selection_preflight.sh`。

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

> **Deprecated，即將移除。** 與 `GET /api/map`、`GET /map` 一同退役；請改用
> `POST /api/projects/import` → `POST /api/scans` → `GET /api/projects/{project_id}/map-builds/latest`。

All-in-one viewer / demo build：送入 path 觸發 L1 build，寫出 artifact，更新 current
runtime 的 process-wide latest `/api/map`。

Current runtime 的 Step 3 仍由現有 Systograph scan providers 執行。Phase B/C target 才改由
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

`system_map_schema_version` 是 Plan 15 前保留的 deprecated input。省略或指定
`ai-system-map/v2` 才能正常建置；public request 指定 v1 會回 `422` +
`legacy_output_not_selectable`。v1 rollback 不透過 request，而由 process 啟動前的 operator
setting 控制。

Current runtime response `200`（`MapBuildResult`）：

```ts
{
  status: "ok" | "error";
  project_name: string;
  output_run_dir: string;
  map_json_path: string | null;
  map_markdown_path: string | null;
  map_error_path: string | null;
  profile_signals_path: string | null;
  readiness_report_path: string | null;
  call_graph_path: string | null;
  dataflow_hints_path: string | null;
  execution_paths_path: string | null;
  evidence_table_path: string | null;
  system_map_mermaid_path: string | null;
  execution_map_mermaid_path: string | null;
  viewer_load_result: ViewerLoadResult; // 見 GET /api/map
  ai_system_map: object;                // 唯一 normalized v2 canonical truth
  profile_inference_result: ProfileInferenceResult;
  readiness_report: ReadinessReport;
  active_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
  requested_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
  source_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
  operator_rollback_active: boolean;
  migration_warnings: string[];
  warnings: string[];
  error: object | null;
}
```

> Current runtime 的 `output_run_dir` 與 `*_path` 可能是 server-local absolute path，
> 僅屬 compatibility contract。Phase2 target response 不得新增或延續 absolute-path 欄位。

> `ai_system_map` 帶 deterministic `recommended_next_checks[]`（scan-fact checks，欄位語意
> 見 MODEL-CONTRACT §5.3）。此欄位為 additive，缺此欄位的舊 artifact 仍可載入；但 pin 舊
> v2 schema copy 的 strict validator 需先更新 schema copy 才能驗證新 artifact。

正式 project workflow 不使用這個 demo response 當 history contract；它透過下節的
`MapBuildScopedResponse` 回傳 scan/build lineage，且不暴露上述 absolute paths。
Plan 06 後續才加入 safe lazy artifact refs：

```ts
type ArtifactRef = {
  artifact_id: string;
  artifact_type: string;
  file_name: string; // basename only
  media_type: string;
  sha256: string;
  size_bytes: number;
};

```

Phase2 active contract 不另設 `snapshot_id`；同一 `scan_id` 可產生 initial、Apply 或
Detail Scan 等多個 immutable `build_id`。

---

## 2. 地圖讀取（Viewer）

### Current runtime 與 later target

| Contract | Current S1 | Later target |
|---|---|---|
| Read surface | project latest / 指定 `build_id`；另保留 demo `/api/map` | 同左 |
| Response wrapper | `MapBuildScopedResponse` + legacy `ViewerLoadResult` | richer Graph projection + safe refs |
| Persistence | project/scan/build/mapping local JSON repositories | 可替換 database adapter |
| Identity | persisted `scan_id` + `build_id` | 同左 |
| Artifacts | build-scoped response 不回 path；demo 保留 `*_path` | safe `artifact_refs` |

Phase2 primary endpoints（完整 surface，對齊 `epic1-phase2.md` §16）：

```http
POST /api/projects/import
POST /api/scans
GET  /api/projects/{project_id}/map-builds
GET  /api/projects/{project_id}/map-builds/latest
GET  /api/map-builds/{build_id}
POST /api/map-builds/{base_build_id}/apply
POST /api/detail-scans  // optional build_id in body
POST /api/trace         // optional build_id in body
```

`GET /api/map` 與 `GET /map` 僅保留 demo / legacy compatibility。Current detail scan
與 trace 使用 request body 的 optional `build_id`；省略時採 latest fallback 並回 warning。
Path-scoped `/api/map-builds/{build_id}/detail-scans|trace` 是 later alias target，尚未存在。

### GET /api/projects/{project_id}/map-builds（current）

列出 project 的 immutable build history。排序為 `generated_at ASC`，tie-break `build_id ASC`，
讓 lineage 依建立順序呈現。

```ts
{
  project_id: string;
  builds: Array<{
    project_id: string;
    scan_id: string;
    build_id: string;
    based_on_build_id: string | null;
    build_reason: "initial_scan" | "apply_confirmations" | "detail_scan";
    applied_mapping_ids: string[];
    generated_at: string;
  }>;
};
```

### GET /api/projects/{project_id}/map-builds/latest（current）

取得指定 project 的 latest immutable build，不讀 process-wide latest。

### GET /api/map-builds/{build_id}（current）

取得指定歷史 build。Response 的 lineage 在外層，validated profile/readiness 在
`build_result`，legacy base graph 在 `viewer_load_result`：

```ts
type MapBuildScopedResponse = {
  project_id: string;
  scan_id: string;
  build_id: string;
  based_on_build_id: string | null;
  build_reason: "initial_scan" | "apply_confirmations" | "detail_scan";
  applied_mapping_ids: string[];
  build_result: {
    status: "ok" | "error";
    project_name: string;
    active_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    requested_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    source_schema_version: "ai-system-map/v1" | "ai-system-map/v2";
    operator_rollback_active: boolean;
    migration_warnings: string[];
    warnings: string[];
    profile_signals_available: boolean;
    readiness_report_available: boolean;
    profile_inference_result: ProfileInferenceResult | null;
    readiness_report: ReadinessReport | null;
  };
  viewer_load_result: ViewerLoadResult;
};
```

`profile_inference_result` 缺失或 invalid 時：`build_result.profile_inference_result:null`，
`build_result.warnings` 含 `profile_signals_missing_or_invalid`；canonical map 仍可 load。
Readiness 對應 warning 為 `readiness_report_missing_or_invalid`。
Manifest 會保存 `active_schema_version`、`requested_schema_version`、
`source_schema_version`、`operator_rollback_active`、`artifact_set_version` 與
`migration_warnings`；同一 `build_id` 在 restart 前後不得改寫這些欄位。

Current build-scoped response 不包含 server-local absolute path，也尚未包含
`artifact_refs`。Plan 06 加入 refs 後，frontend 只能依 stable artifact id/type 與受控 API
讀取 artifact。

#### ViewerLoadResult 載入策略

| 來源 artifact | API 欄位 | 載入 |
|---------------|----------|------|
| `ai_system_map.json` | `ai_system_map` | inline |
| `profile_signals.json` | `build_result.profile_inference_result` | inline |
| `readiness_report.json` | `build_result.readiness_report` | inline |
| current base projection | `viewer_load_result.graph_view_model` | inline（ephemeral） |
| static execution 四件套 | — | current 不 inline；Plan 06 `artifact_refs[]` lazy load |
| `*.md` / `*.mmd` render | — | current 不 inline；Plan 06 `artifact_refs[]` lazy load |

**主畫布 ≠ merge 六份 Step 6 JSON**。Current canvas 由 backend 將 normalized v2 與
6-1 Profile Inference 透過 `GraphProjectionService` 投影，不由 frontend 重建。
Build 磁碟上 atomic publish **10** public siblings（7 JSON + 3 render）；`snapshot.json`、
manual mapping 屬 project state，**不**計入 7 JSON。見 MODEL-CONTRACT §3、§7.0、§9.1。

Frontend **不得**重算五態、activation、Mapping Completeness。Sidecar 缺失 → degraded load + warnings。完整型別與 enum 見 [`MODEL-CONTRACT.md`](MODEL-CONTRACT.md) § `ViewerLoadResult`、`GraphViewModel`、`readiness-report/v1`；handoff 見 `frontend-json-handoff/step-08-viewer/`。

### POST /api/map-builds/{base_build_id}/apply（current）

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
成功的 public child build 維持 v2 request provenance；Apply 不會自行切成 v1。Operator
rollback 若啟用，則只由 process-level setting 決定實際 artifact version並留下稽核欄位。

### POST /api/map-builds/{build_id}/detail-scans（later alias，未實作）

對指定 immutable build 執行 detail scan，產生 **child build**（新 `build_id`、同一 `scan_id`），
不 overwrite parent map artifact。Current runtime 等價路徑為 `POST /api/detail-scans`（`project_id`）。

### POST /api/map-builds/{build_id}/trace（later alias，未實作）

對指定 build 執行 opt-in query trace overlay。Current runtime 等價路徑為 `POST /api/trace`（`project_id`）。
Trace overlay 不得寫回 canonical map / profile artifacts。

### GET /api/map（legacy / demo，**deprecated**）

> **即將移除。** 正式讀圖入口是 `GET /api/projects/{project_id}/map-builds/latest`
> （指定版本用 `GET /api/map-builds/{build_id}`）。退役後讀圖一律需要 `project_id`。

Current runtime 回傳目前 process session 最新的 viewer payload。現行前端仍保留它作為
build-scoped 讀取失敗時的 fallback，但它不是 Phase2 build history 的正式讀取入口。

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

### GET /map（**deprecated**）

`GET /api/map` 的 legacy fallback，回傳完全相同的 `ViewerPayload`。前端會先試 `/api/map`，失敗再退回 `/map`。與 `/api/map`、`POST /api/map/build` 一同退役。

### GET /api/map/report

回傳目前 session 最新的 Markdown report（讀 `map_build` 寫出的 `map_markdown_path`，不接受任意路徑）。

```http
GET /api/map/report            # 行內檢視
GET /api/map/report?download=true   # 觸發附件下載
```

Response `200`：`Content-Type: text/markdown; charset=utf-8`（純文字）。

Report 的 `## Recommended Next Checks` 底下**並列兩段**：`### Scan-fact checks`（map 的
`recommended_next_checks[]`）與 `### Capability review checks`（profile 評估的 per-node
checks）。兩段各自去重、互不遮蔽；任一段為空時仍保留標題並標示 no checks（見
MODEL-CONTRACT §5.3）。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `map_markdown_not_available` | 404 | 尚無成功的 build，或檔案不存在 |

---

## 3. Detail Scan（L2 / L3 漸進式掃描）

Current runtime 對單一目標做有界深掃，綁定指定 build，並產生同 `scan_id` 的
immutable child `build_id`；不得 overwrite parent。**需先完成 project session**
（`import` → `scans`）；只用 `map/build` 不足以滿足 `map_not_loaded` 檢查。
若省略 `build_id`，後端使用該 project latest 並回 `latest_build_fallback` warning。

### POST /api/detail-scans

```http
POST /api/detail-scans
```

```json
{
  "project_id": "project:<uuid>",
  "build_id": "build:<uuid>",
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
  ai_system_map: object;          // child build 的 validated canonical map
  source_build_id: string;
  build_id: string;               // immutable child build
  scan_id: string;
  viewer_load_result: ViewerLoadResult;
  warnings: string[];
}
```

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `project_not_found` | 404 | `project_id` 不存在 |
| `map_not_loaded` | 404 | 該專案尚未有掃描結果 |
| `target_not_found` | 422 | `target` 在 map 中不存在 |
| `base_build_not_latest` | 409 | 指定 build 已不是 latest，避免 lineage fork |
| `scan_snapshot_stale` | 409 | 目標檔案 fingerprint 已變更，需 explicit rescan |
| `profile_sidecar_unavailable` | 409 | parent profile sidecar 缺失或 invalid；base graph 仍可讀，但不得發布語意不完整的 child build |
| `legacy_rollback_not_representable` | 422 | 僅 operator rollback 模式；preflight 判定該 map 無法以 v1 表示。詳見〈Operator rollback 專用 error code〉 |
| `legacy_rollback_detail_scan_unsupported` | 422 | 僅 operator rollback 模式；rollback writer 不支援 enriched map。詳見〈Operator rollback 專用 error code〉 |

> **兩者的優先順序（rollback 模式下）：** preflight 先跑，因此 map 若不可表示，回的是較具體的
> `legacy_rollback_not_representable`；只有通過 preflight 的 map 才會走到
> `legacy_rollback_detail_scan_unsupported`。normal v2 模式下兩者都不會出現。

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
[tool.systograph.trace]
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
systograph trace outputs/run/ai_system_map.json \
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
  "build_id": "build:<uuid>",
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
  source_scan_id: string | null;
  source_build_id: string | null;
  events: QueryTraceEvent[]; // request_sent / response_received / error / endpoint_not_found
  warnings: string[];
  error_reason: string | null;
}
```

資料安全（摘要）：

- `query`、response、chunks 進 event 前遮蔽/摘要化
- `endpoint_id` 須存在於 map；否則 `endpoint_not_found`，不送 HTTP
- `build_id` 指定 trace source；省略時使用 latest 並回 `latest_build_fallback` warning
- 預設阻擋 non-global / private / metadata 位址；egress 被擋 → `partial` + `egress_policy_blocked`
- 不跟隨 redirect；預設不讀 proxy env
- `[tool.systograph.trace]` 只控制 chunk keys；舊 `[tool.systograph.trace]` 仍為相容 alias；
  local-dev allowlist 由 operator 注入
- timeout / transport error → `status:"partial"`，保留 events 供 replay
- 完整 egress 政策見 [`docs/security/query-trace-egress-policy.md`](security/query-trace-egress-policy.md)

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `project_not_found` | 404 | `project_id` 不存在 |
| `map_not_loaded` | 404 | 該專案尚未有掃描結果 |
| `invalid_trace_config: ...` | 400 | `pyproject.toml` 的 `[tool.systograph.trace]`（或 legacy `[tool.systograph.trace]`）格式錯誤 |
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
SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS=true
NVIDIA_API_KEY=<your-key>
```

僅有 `NVIDIA_API_KEY` 而沒有 explicit flag 時，後端仍用 deterministic provider（`provider_name: "deterministic"`）。

**Runtime 設定（非敏感預設值）**：預設值由 bundled TOML
`src/systograph/core/configs/llm_proposal.toml` 提供（模型 `google/gemma-4-31b-it`、
endpoint `https://integrate.api.nvidia.com/v1/chat/completions`）。本機測試可經
`.env` / 環境變數暫時覆寫（`.env` 已被 gitignore，API key 不得 commit）：

```bash
NVIDIA_NIM_MODEL=google/gemma-4-31b-it
NVIDIA_NIM_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions
NVIDIA_NIM_TIMEOUT_SECONDS=8.0
NVIDIA_NIM_MAX_TOKENS=16384
NVIDIA_NIM_TEMPERATURE=1.0
NVIDIA_NIM_TOP_P=0.95
NVIDIA_NIM_STREAM=false
NVIDIA_NIM_ENABLE_THINKING=true
```

只有 runtime/provider 預設值屬於 TOML／`.env`。Mapping proposal 的輸出上限
（候選數、label/rationale 長度、evidence id 數、suggested edge 數、
`provider_error_reason` 長度）是 `src/systograph/core/models/mapping.py` 的
Pydantic schema limits，屬 API 與安全契約的一部分，**刻意不開放 TOML 設定**。
Provider 只接收 masked packet 與 schema summary；request 採 NVIDIA Platform
non-streaming chat completion 形狀。測試一律用 mock HTTP transport，不打真實
NVIDIA endpoint。

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
- `reject` / `skip_for_now`：兩者皆不帶 candidate payload；後端仍建立 durable audit mapping

Response `200`：

```ts
{
  proposal: MappingProposal;          // status 變為 accepted / edited / rejected / skipped
  manual_mapping: ManualMapping;      // 四種 decision 都持久化；reject/skip 不會 materialize
}
```

`reject` 會寫 `decision:"rejected"`；`skip_for_now` 會寫
`decision:"skip_for_now"`。兩者都保存 `proposal_id`、evidence 與 audit metadata，但不會
進入 Apply 的 `applied_mapping_ids`。

| 錯誤 | 狀態 | 說明 |
| --- | --- | --- |
| `proposal_not_found` | 404 | `proposal_id` 不存在 |
| 驗證失敗 | 422 | decision payload 不合法（如 accept 缺 candidate_id） |

---

## 錯誤對照表

| 狀態 | 意義 | 常見 `detail` |
| --- | --- | --- |
| 200 | 成功（含「map 無效」這類明確的 loaded:false 狀態） | — |
| 404 | 目標不存在 | `resource_not_found`（malformed typed state id）、`project_not_found`、`map_not_loaded`、`unmapped_not_found`、`proposal_not_found`、`detail_scan_not_found`、`mapping_not_found`、`map_markdown_not_available` |
| 409 | 狀態衝突 | `base_build_not_latest`、`latest_build_changed`、`scan_snapshot_stale`、`profile_sidecar_unavailable` |
| 413 | request body 超過本機 API resource limit | `request_too_large` |
| 422 | 輸入不合法 / 驗證失敗 | `legacy_output_not_selectable`、`legacy_mapping_type_read_only`、`target_not_found`、`profile_sidecar_contract_invalid`（strict mode）、Apply 跨 project / unconfirmed / duplicate `mapping_ids`、operator rollback 的 `legacy_rollback_*`（見下表）、validation 陣列 |
| 500 | 未預期後端錯誤，回應會遮蔽 raw path / secret | `internal_server_error` |
| 503 | project state lock timeout | `project_state_busy` |

> Project workflow 會跨重啟恢復。若重啟後出現 404，先確認啟動前後使用相同
> `SYSTOGRAPH_STATE_DIR`；只有 state record 不存在時才需要重新 import / scan。

### Operator rollback 專用 error code

下列 code 只在 process 啟動前設定
`SYSTOGRAPH_CANONICAL_OUTPUT_VERSION=ai-system-map/v1` 的 operator rollback 模式出現；
normal `ai-system-map/v2` 模式不會產生。失敗時都不寫任何 artifact。

| `detail` | 意義 |
| --- | --- |
| `legacy_rollback_not_representable` | map 無法以 v1 無損表示：不是 v1-sourced map，或含 legacy contract 表達不了的 component（`semantic_kind` 超出 `repo_component` / `slot_placeholder` / `legacy_extension`）。preflight fail closed，不靜默丟資料 |
| `legacy_rollback_detail_scan_unsupported` | map 本身可以 v1 表示，但 rollback writer 只能從 raw scan 重建；enriched map（detail scan 子 build）這條路徑在 rollback 模式沒有 writer |
| `legacy_rollback_writer_unavailable` | process 設成 rollback 模式，但該 build pipeline 沒有被注入 rollback writer（`MapBuildPipeline` 的 `legacy_rollback` 為 `None`）。屬 wiring/組態錯誤，不是使用者輸入問題 |

- 前兩者由 `POST /api/detail-scans`（enriched map 路徑）以 `422` 回傳。
  同一 endpoint 上 preflight 先跑，因此 `legacy_rollback_not_representable` 優先於
  `legacy_rollback_detail_scan_unsupported`。
- `legacy_rollback_writer_unavailable` **不限** detail-scan：normal build 路徑
  （`MapBuildPipeline.materialize`）在 rollback 模式下同樣會拋，因此 `POST /api/scans`、
  `POST /api/map/build` 與 CLI `map` 都可能遇到。它代表 wiring／組態問題（pipeline 沒被注入
  rollback writer），不是使用者輸入問題，重送相同請求不會改變結果。
  HTTP 呈現依 endpoint 而異：`POST /api/detail-scans` 與 `POST /api/scans` 走各自的 broad
  `ValueError` handler，以 `422` + 同名 code 回傳；`POST /api/map/build` 目前只攔
  `CanonicalOutputConfigurationError`，因此會落到 middleware 的
  `500 internal_server_error`。

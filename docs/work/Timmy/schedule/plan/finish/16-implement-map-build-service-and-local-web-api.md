# Task 16: Implement MapBuildService and Local Web API

## 目標
串起 `MapBuildService` 與 local web API，讓 GUI/local web UI 可以從畫面觸發 L1 system scan，產生 validated canonical `ai_system_map.json`，並回傳前端 API mode 可消費的 typed response wrapper。

這是 Epic 1 backend 第一個完整 end-to-end milestone。它的重點是把「project folder -> canonical JSON -> local API response」打通，同時守住 backend 架構邊界：route 只做 adapter，scanner 邏輯只在 core service，`ai-system-map/v1` 仍是唯一 canonical truth。

## 為什麼要先做這個
設計文件與 2026-06-05 meeting review 都指向同一個缺口：

```text
目前已完成：

ProjectScanService
  ↓
ComponentDetectionService
  ↓
Endpoint / Risk / Flow
  ↓
SystemMapNormalizeService
  ↓
RagSystemMap ai-system-map/v1

前端 API mode 需要：

GET /api/map
  ↓
viewer_load_result
  ↓
graph_view_model
```

因此 Task 16 不能只寫出 raw `ai_system_map.json`。它必須至少提供 local API wrapper 與最小 viewer payload contract，讓前端不必從 canonical map 自行推 graph truth。

完整 `GraphViewModel` projection 仍屬 Task 18；Task 16 只負責最小可用 API shell、typed schema、session/build result、以及避免前端 API mode 直接拿 raw map 失敗。

## 查證與架構校正（2026-06-05）

### 已讀文件
- `docs/work/Timmy/meeting/backend-architecture-visual-review-2026-06-05.md`
- `docs/work/Timmy/meeting/frontend-backend-architecture-visual-review-2026-06-05.md`
- `frontend/API_CONTRACT.md`
- `frontend/src/types.ts`
- `docs/work/Timmy/schedule/plan/unfinish/18-implement-viewer-session-graph-projection.md`
- `docs/work/Timmy/schedule/plan/unfinish/21-implement-progressive-detail-scan.md`
- `docs/work/Timmy/schedule/plan/unfinish/22-implement-query-trace-mvp.md`

### 外部查證來源
- FastAPI features: FastAPI 基於 OpenAPI / JSON Schema，並使用 Pydantic 做資料驗證與文件化，適合 typed local API contract。
  https://fastapi.tiangolo.com/features/
- FastAPI response model: `response_model` 會用於文件、validation、serialization/filtering，因此 route 應宣告 typed response model，不要直接回任意 dict。
  https://fastapi.tiangolo.com/tutorial/response-model/
- FastAPI bigger applications: `APIRouter` 適合拆分多檔 route，避免 route 全塞在 app entrypoint。
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI testing: 官方建議使用 `TestClient` 以 pytest 方式測試 API route。
  https://fastapi.tiangolo.com/tutorial/testing/
- FastAPI CORS: `CORSMiddleware` 預設限制，local frontend/backend 開發若跨 origin，必須明確列出允許 origin。
  https://fastapi.tiangolo.com/tutorial/cors/
- FastAPI SSE: FastAPI 官方 SSE 使用 `EventSourceResponse` 與 `text/event-stream`，瀏覽器原生 `EventSource` 可消費；目前 `uv.lock` FastAPI 為 `0.136.3`，可用官方 SSE 路線，但版本下限 `fastapi>=0.115,<1` 仍需在 API guide 標註。
  https://fastapi.tiangolo.com/tutorial/server-sent-events/
- FastAPI SSE version boundary: `EventSourceResponse` 是 FastAPI `0.135.0` 新增；若 Task 16 實作用它，`pyproject.toml` 應把 FastAPI 下限調整為 `>=0.135,<1`，避免 lock 重解時退回不支援 SSE 的版本。
  https://fastapi.tiangolo.com/tutorial/server-sent-events/
- WHATWG / MDN SSE format: SSE response 必須是 `text/event-stream`；event stream 以 UTF-8 文字傳輸，message 由空白行分隔，`data:` 欄位可被瀏覽器 `EventSource` 消費。`Cache-Control: no-cache` 與 `X-Accel-Buffering: no` 屬於實務上的 buffering 防護，特別是日後若經過 proxy。
  https://html.spec.whatwg.org/multipage/server-sent-events.html
  https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- OWASP API Security Top 10 2023: API4 unrestricted resource consumption、API8 security misconfiguration 直接對應 local scan API 的資源限制與 local-only policy。
  https://owasp.org/API-Security/editions/2023/en/0x00-header/
- React single source of truth / Thinking in React: 前端 state 應只保存互動狀態，canonical facts 與 graph projection 不應在前端重複推導。
  https://react.dev/learn/sharing-state-between-components
  https://react.dev/learn/thinking-in-react
- Langflow 1.9.x: 官方文件顯示 Langflow 由 React/TypeScript frontend 與 Python/FastAPI backend 組成，開發時 frontend/backend 分 port 執行，API 文件也列出 `/api/v1/...` endpoint。它適合參考 route 分層、typed API 與 graph/backend state 轉前端 payload 的模式；但資料庫、權限、自訂程式碼、public build endpoint 與 file upload 不是 Task 16 範圍，且 Langflow 曾有 public build endpoint RCE，因此只能借鑑邊界設計，不可照抄其執行/上傳/公開 build 行為。
  https://docs.langflow.org/contributing-how-to-contribute
  https://docs.langflow.org/api
  https://github.com/langflow-ai/langflow/security/advisories/GHSA-vwmf-pq79-vjvx
- Microsoft Promptflow: `promptflow` 已拆成 `promptflow-core`、`promptflow-devkit` 等套件；官方 changelog 顯示 local serve 已加入 FastAPI engine，且 devkit 負責啟動本地 serving、解析 flow path 與處理 host/port。可參考其 core serving 與 devkit serving helper 的分層，但 Systograph Task 16 不應引入 Promptflow 的 flow execution、連線管理或瀏覽器開啟行為。
  https://microsoft.github.io/promptflow/reference/changelog/promptflow.html

### Research 校正結論
- 你的 research 大方向正確：Task 16 應用 FastAPI typed route、`response_model`、`APIRouter`、local-only CORS allowlist、core/web 解耦、minimal projection 與 SSE contract。
- 需要修正的地方是 SSE 參考來源：不要把 LangGraph 生態圈當主要依據；本任務以 FastAPI 官方 SSE、WHATWG SSE 規範、MDN EventSource 文件為主要依據。Langflow 可作為實務參考，因它目前仍大量使用 FastAPI `APIRouter` 與 `StreamingResponse`。
- 若採 FastAPI 官方 `EventSourceResponse`，實作必須同步更新 dependency lower bound 到 `fastapi>=0.135,<1`；否則未來重新解 lock 可能破壞 SSE import。
- CORS `allow_origins=["*"]` 不是本地 scanner API 的合理預設。Task 16 預設只能 allowlist `http://127.0.0.1:5173` 與 `http://localhost:5173`；server bind guide 預設 `127.0.0.1`。
- `graph_view_model` 是 API/viewer projection，不是 `RagSystemMap` canonical truth；`ai_system_map.json` 不得寫入 `viewer_load_result` 或 `graph_view_model`。

## 前置需求
- Task 6 已完成 precondition/output policy。
- Task 12 已完成 `ProjectScanService`。
- Task 13 已完成 component detection。
- Task 14 已完成 endpoint/risk/flow derivation。
- Task 15 已完成 normalize/validate。
- Task 3 已完成 template service。
- Task 1 已建立 `web/` adapter skeleton。
- 已完成 local web backend framework 選擇：FastAPI。
- 前端已完成 API mode contract：`GET /api/map`、fallback `GET /map`、`viewer_load_result.graph_view_model`、`GET /api/scan/events` target priority。

## 實作範圍
- 建立 `MapBuildService`，串接 precondition、template、scan、component detection、endpoint/risk/flow、normalize、validate、artifact write。
- 補強 `OutputArtifactProvider`，支援 JSON artifact writer；fatal precondition error 寫出 `map-error.md`。
- 建立 typed core build models，例如 `MapBuildRequest` / `MapBuildResult` / artifact path model；core model 不依賴 FastAPI。
- 建立 local web schemas，例如 `ProjectImportRequest`、`ScanCreateRequest`、`MapBuildApiRequest`、`ViewerLoadResult`、`GraphViewModel` minimal schema、`ScanProgressEvent`。
- 建立 FastAPI app scaffold 與 route modules，使用 `APIRouter`，route handler 只做 request/response 轉換與 service 呼叫。
- 建立 `POST /api/map/build`，支援一次性 demo / development flow：送 `project_path` 後觸發 build，回傳 build result 或 viewer wrapper。
- 建立 `GET /api/map` 與 `GET /map` fallback，兩者共用同一 service/handler，回傳前端 `viewerPayloadSchema` 可 parse 的 `viewer_load_result` wrapper。
- 建立最小 `GraphViewModel` placeholder/projection shell：
  - 必須有 `nodes`、`edges`、`details.evidence_by_id`、`details.risk_hints_by_id`、`filters.available`。
  - 可以先只做 L1 minimal projection，完整 components/extensions/unmapped/flows projection 留 Task 18。
  - 不得把 `graph_view_model` 寫進 canonical `RagSystemMap`。
- 建立 local path project import/session shell：
  - `POST /api/projects/import`：MVP 僅支援 `source_type="local_path"`。
  - `POST /api/scans`：以 `project_id` 啟動 L1 scan，回傳 `scan_id` 與 status。
  - 若實作時為了 MVP 採 in-memory session store，API guide 必須明確標註 non-persistent。
- 建立 `GET /api/scan/events` basic SSE endpoint 或 deterministic placeholder：
  - 若本任務不做真進度串流，仍需提供 contract-compatible basic event / completed event。
  - event payload 必須保留前端 target priority：`node_id`、`edge_id`、`component_id`、`source_id`、`slot`。
- 建立 Epic 1 local API guide，作為前端、desktop app、CLI adapter 共用的 API contract 文件。
- 在 local web API 完成後，補上 `systograph map` thin adapter；CLI 只能呼叫同一個 `MapBuildService`。

## 不包含範圍
- 不產生 Markdown，留給 Task 17。
- 不實作完整 `ViewerSessionService` graph projection；完整 projection 留 Task 18。
- 不做 viewer command。
- 不做 CLI 專屬 scanner logic；CLI 是次要入口，只能 thin-wrap core service。
- 不做 query trace；runtime endpoint 呼叫留 Task 22。
- 不做 progressive detail scan；L2/L3 lazy loading 留 Task 21。
- 不做 manual mapping / AI mapping proposal。
- 不做 frontend GUI 畫面。
- 不做 project zip upload / multipart upload；MVP 僅 local path import。
- 不做 persistent multi-user session store；若需要歷史紀錄，後續另開 task。

## 延後功能落點

Task 16 是 L1 map build + local API shell。凡是會引入第二層產品語意、使用者決策、runtime side effect、archive attack surface、或長期狀態管理的功能，都不應在本任務順手做掉。

| 本任務不做的功能 | 未來落點 | 是否已有 plan | 補充說明 |
| --- | --- | --- | --- |
| Markdown artifact / readable report | Task 17: `17-implement-markdown-summary-artifact.md` | 已有 | 從 validated `RagSystemMap` 產生 `ai_system_map.md`；不重新掃 project files，也不成為第二份 truth。 |
| 完整 `ViewerSessionService` / `GraphViewModel` projection | Task 18: `18-implement-viewer-session-graph-projection.md` | 已有 | Task 16 只提供 minimal viewer wrapper；components、extensions、unmapped、flows、risk hints 的完整 nodes/edges/details projection 留 Task 18。 |
| viewer command / map validate CLI UX | Task 18 | 已有 | 若要補 CLI viewer 或 validate command，只能 thin-wrap `ViewerSessionService`；不能在 CLI 重新實作 projection。 |
| manual mapping / user-confirmed mapping store | Task 19: `19-implement-manual-mapping-store.md` | 已有 | 使用者確認 unmapped component 後，寫入 Systograph-managed store；不寫入被掃描 repo。 |
| AI / rule-assisted mapping proposal | Task 20: `20-implement-ai-mapping-proposal-flow.md` | 已有 | 只產生 pending proposal；accept/edit/reject 後才交給 Task 19 的 manual mapping store。 |
| progressive detail scan / L2-L3 lazy loading | Task 21: `21-implement-progressive-detail-scan.md` | 已有 | 針對 component、extension、unmapped、edge、evidence 做 bounded scan；不做 whole-repo call graph。 |
| query trace / runtime endpoint 呼叫 | Task 22: `22-implement-query-trace-mvp.md` | 已有 | 會真的呼叫 RAG endpoint，必須 opt-in；不得由 `systograph map` 或 Task 16 預設觸發。 |
| cross-platform path、logging、snapshot safety hardening | Task 23: `23-hardening-cross-platform-logging-and-snapshot-safety.md` | 已有 | Task 16 先提供 end-to-end baseline；大範圍 hardening 在功能完成後集中收斂。 |
| AI-assisted scan boundary review / local template import | Task 24: `24-final-ai-scan-boundary-review-and-template-import.md` | 已有 | 這是 Epic 1 final milestone；依賴 baseline scanner、policy store、masking、validation 穩定後再做。 |
| project zip upload / multipart upload | Task 25: `25-implement-project-upload-ingestion.md` | 新增 | 這不是 Task 24 的 template import。它是把使用者專案 archive 當 scan input，必須獨立處理 size limit、archive extraction safety、path traversal、binary/model/dependency skip policy。 |
| persistent multi-user session store / scan history | Task 26: `26-implement-persistent-session-store-and-scan-history.md` | 新增 | Task 16 只允許 in-memory session shell。若要 scan history、多使用者、重啟後保留 session，需獨立設計 storage、retention、masking、migration。 |
| frontend GUI 畫面 | frontend / Hardy plan，不放 Timmy backend plan | 需由 frontend 排程承接 | Timmy backend 只提供 API contract、schemas、SSE event shape 與 guide；React 畫面、layout、interaction state 不在本資料夾的 backend plan 執行。 |
| CLI 專屬 scanner logic | 永久不開獨立實作計劃 | 不需要 | CLI 可以有 command UX，但不得擁有獨立 scanner pipeline；所有 scanner 行為都要呼叫 core service。 |

## API contract 決策

### 1. Canonical map build
```http
POST /api/map/build
Content-Type: application/json
```

最小 request：

```json
{
  "project_path": "/absolute/or/local/project/path",
  "output": "outputs",
  "redact_root_path": true,
  "no_snippets": false
}
```

最小 response：

```text
MapBuildResult
├─ status: ok | error
├─ project_name
├─ output_run_dir
├─ map_json_path
├─ map_error_path
├─ viewer_load_result
└─ warnings[]
```

### 2. Frontend map loading
```http
GET /api/map
Accept: application/json
```

Temporary fallback：

```http
GET /map
Accept: application/json
```

回傳必須符合 `frontend/src/types.ts` 的 `viewerPayloadSchema`：

```text
viewer_load_result
├─ loaded
├─ error_reason
├─ map_json
├─ ai_system_map
└─ graph_view_model
   ├─ nodes[]
   ├─ edges[]
   ├─ details
   │  ├─ evidence_by_id
   │  └─ risk_hints_by_id
   └─ filters.available[]
```

### 3. Local path import / scan session shell
```http
POST /api/projects/import
Content-Type: application/json
```

```json
{
  "source_type": "local_path",
  "project_path": "/Users/example/rag-project"
}
```

```http
POST /api/scans
Content-Type: application/json
```

```json
{
  "project_id": "project:...",
  "scan_depth": "system"
}
```

Task 16 可用 in-memory session shell；API guide 必須寫清楚這不是 production session store。

### 4. Scan progress SSE
```http
GET /api/scan/events?scan_id=...
Accept: text/event-stream
```

最小 event shape：

```json
{
  "event": "scan_progress",
  "status": "running|completed|error",
  "stage": "project_scan|component_detection|normalize|validate",
  "message": "Human-readable progress message",
  "percent": 0,
  "node_id": null,
  "edge_id": null,
  "component_id": null,
  "source_id": null,
  "slot": null,
  "timestamp": "2026-06-05T..."
}
```

## 建議實作步驟
1. 建立 `src/systograph/core/services/map_build_service.py`。
2. 建立 core build request/result models；可放 `src/systograph/core/models/map_build.py`，避免 web framework 型別滲進 core。
3. 將 precondition、template、scan、detection、endpoint/risk/flow、normalize、validate 串起來。
4. 確保 `MapBuildService` 寫出 artifact 前一定使用 Task 15 的 normalize result；若上游 detection/risk/trace 沒有資料，仍由 normalize result 輸出 canonical 空陣列，不可直接 serialize 半成品 dict。
5. 補強 `OutputArtifactProvider.write_json()`，使用 validated `RagSystemMap.model_dump(mode="json")`。
6. 建立 minimal viewer payload builder；可先命名 `ViewerPayloadService` 或 `MinimalViewerProjectionService`，但完整 `ViewerSessionService` 留 Task 18。
7. Minimal graph projection 至少輸出：
   - detected component slots as nodes。
   - flow edges as edges。
   - `evidence_by_id` 與 `risk_hints_by_id` index。
   - empty/default filters。
   - stable `source_id`，對應 canonical component/edge/slot id。
8. 建立 FastAPI app scaffold：`src/systograph/web/app.py`。
9. 建立 route modules：
   - `src/systograph/web/routes/map_routes.py`
   - `src/systograph/web/routes/project_routes.py`
   - `src/systograph/web/routes/scan_routes.py`
10. 建立 `src/systograph/web/schemas.py`，用 Pydantic 定義 request/response model，route decorator 使用 `response_model`。
11. 設定 local-only app policy：
    - 預設文件建議只 bind `127.0.0.1`。
    - CORS 只允許明確 local frontend origins，例如 `http://127.0.0.1:5173`、`http://localhost:5173`。
    - 不使用 wildcard CORS 作為預設。
12. 建立 `POST /api/map/build`，觸發 map build 並回傳 structured result。
13. 建立 `GET /api/map` 與 `GET /map` fallback，兩者共用同一 handler / service；正式 contract 以 `/api/map` 為主。
14. 建立 `POST /api/projects/import` 與 `POST /api/scans` 的 MVP in-memory shell；若不落地完整 session，至少 API guide 要定義形狀與未來擴充規則。
15. 建立 `GET /api/scan/events` basic SSE；若只回 completed event，也要符合 `ScanProgressEvent` schema。
16. 建立 `docs/work/Timmy/design/epic1-local-api-guide.md`，記錄：
    - local-only 原則。
    - `POST /api/map/build`。
    - `GET /api/map` / `GET /map`。
    - `POST /api/projects/import`。
    - `POST /api/scans`。
    - `GET /api/scan/events`。
    - `viewer_load_result` / `graph_view_model` schema。
    - common error format。
    - API version / compatibility rule。
    - Task 18/21/22 的後續 API 邊界。
17. 在 API guide 註明：任何 task 若新增、移除或改動 endpoint / request / response / error code，都必須同步更新本文件。
18. 用 FastAPI `TestClient` 或 HTTPX 寫 web API integration tests。
19. 寫 map build service integration tests：basic fixture 產生 valid JSON，且 JSON 不含完整 secret。
20. 寫 frontend contract compatibility test：API response shape 必須能對齊 `frontend/API_CONTRACT.md` 與 `frontend/src/types.ts` 欄位。
21. 寫 missing project test：API 回傳 error result，且只產生 error report。
22. 寫 existing output test：outputs 已存在時產生 timestamped directory。
23. 寫 local-only/CORS config test：app 設定不使用 wildcard origin 作為預設。
24. 建立 `src/systograph/cli/map_command.py`，讓 CLI 呼叫同一個 `MapBuildService` method。
25. 寫 CLI thin adapter test：確認 CLI 產生的 artifact contract 與 local API 相同，且 CLI 不直接呼叫 providers。

## 預期輸出
- `src/systograph/core/models/map_build.py`
- `src/systograph/core/services/map_build_service.py`
- `src/systograph/core/services/minimal_viewer_projection_service.py` 或等價 minimal projection helper
- `src/systograph/web/app.py`
- `src/systograph/web/routes/map_routes.py`
- `src/systograph/web/routes/project_routes.py`
- `src/systograph/web/routes/scan_routes.py`
- `src/systograph/web/schemas.py`
- `src/systograph/cli/map_command.py`
- `src/systograph/cli/main.py`
- `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/web/test_map_routes.py`
- `tests/web/test_project_scan_routes.py`
- `tests/cli/test_map_command.py`
- `tests/integration/test_map_build_service.py`
- `tests/unit/core/test_minimal_viewer_projection_service.py`

## 驗收標準
- `MapBuildService` 能從 fixture project 產生 validated `ai_system_map.json`。
- 產出的 `ai_system_map.json` 具備完整 canonical top-level shape；沒有資料的 collections 必須是 `[]`，不是缺欄位。
- `ai_system_map.json` 不包含 `viewer_load_result` 或 `graph_view_model`；viewer wrapper 只能存在 API response / viewer projection output。
- `POST /api/map/build` 能觸發 build，並回傳 structured `MapBuildResult`。
- `GET /api/map` 與 `GET /map` 回傳同一 typed payload shape，且包含 `viewer_load_result.graph_view_model`。
- `viewer_load_result.graph_view_model` 至少包含 `nodes`、`edges`、`details.evidence_by_id`、`details.risk_hints_by_id`、`filters.available`。
- Web API response shape 對齊 `frontend/API_CONTRACT.md` 與 `frontend/src/types.ts`。
- missing project 產生 `map-error.md` 且不產生 normal map。
- outputs 已存在時產生 timestamped directory。
- Web adapter 不直接掃描檔案，只呼叫 core service。
- Route handler 不包含 provider/detection/normalization/projection 內部邏輯。
- `POST /api/projects/import` MVP 僅接受 `source_type="local_path"`；不支援 upload。
- `POST /api/scans` 回傳 `scan_id` 與 status，且 API guide 清楚說明 session 是否 in-memory。
- `GET /api/scan/events` basic SSE response 符合 `ScanProgressEvent` 欄位與 target priority。
- `systograph map ./fixture --output outputs` 作為 thin adapter 產生同 contract 的 valid JSON。
- `epic1-local-api-guide.md` 已記錄 map build API、viewer load wrapper、request/response schema、error format、local-only policy、CORS policy、SSE event schema、Task 18/21/22 後續邊界。
- PR / task 完成前若 API contract 有變更，必須同步更新 API guide。

## 可能風險與注意事項
- Web adapter 不應承擔 scanner logic，避免與 CLI adapter 重複。
- request/response schema 要貼近 core model，但不要讓 FastAPI 型別滲進 core services。
- `GraphViewModel` 不能變成第二份 truth；所有 node/edge/detail 都要能追回 canonical `RagSystemMap` source id。
- Task 16 的 graph projection 是 minimal shell；完整 graph semantics、invalid map viewer state、filter metadata、extension/unmapped projection 留 Task 18。
- SSE 在 `uv.lock` 的 FastAPI `0.136.3` 可走官方 `EventSourceResponse`，但 dependency range 仍是 `fastapi>=0.115,<1`；若未來 lock 降版，需改用 Starlette/StreamingResponse 或調整 dependency lower bound。
- Local API 仍要注意 OWASP API4 unrestricted resource consumption：project scan 應沿用 `FilesystemProvider` skip policy，不可讓 API request 任意讀大檔、binary、model weights、dependency dirs。
- Local API 仍要注意 OWASP API8 security misconfiguration：預設 local-only、CORS allowlist，不要在 MVP 暴露成 public network service。
- API guide 是 frontend / desktop app / CLI adapter 的協作契約，不是自動產生文件的替代品；FastAPI OpenAPI 可以輔助，但 Markdown guide 必須保留設計意圖與使用規則。

## 新手提示
`MapBuildService` 是總指揮。local web API 只是把 GUI 送來的資料轉給它，然後把結果路徑、狀態、以及前端能讀的 viewer wrapper 回傳給畫面。

不要把 `RagSystemMap`、`GraphViewModel`、frontend state 混在一起：

```text
RagSystemMap      = canonical scanner truth
GraphViewModel   = backend rendering projection
Frontend state   = user interaction state
```

## 視覺化說明
```text
┌──────────────┐
│ GUI / Web UI │
└──────┬───────┘
       ↓
┌──────────────────────────────┐
│ Local API Adapter             │
│ POST /api/map/build           │
│ GET /api/map                  │
│ GET /map fallback             │
└──────┬───────────────────────┘
       ↓
┌──────────────────────┐
│ MapBuildService       │
└──────┬──────┬────────┘
       │      │
       ↓      ↓
┌──────────────┐ ┌──────────────────────┐
│ Precondition │ │ ProjectScanService    │
└──────┬───────┘ └──────────┬───────────┘
       │                    ↓
       │          ┌──────────────────────┐
       │          │ Detection/Risk/Flow   │
       │          └──────────┬───────────┘
       └────────────┬───────┘
                    ↓
┌──────────────────────┐
│ Normalize / Validate  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ai_system_map.json    │
│ canonical truth       │
└──────────┬───────────┘
           ↓
┌──────────────────────────────┐
│ Minimal Viewer Projection     │
│ viewer_load_result            │
│ graph_view_model shell        │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ React frontend API mode       │
└──────────────────────────────┘
```

## Task 邊界圖
```text
Task 16
  Build canonical map
  Provide local API shell
  Return minimal viewer wrapper
        ↓
Task 17
  Render Markdown summary from validated map
        ↓
Task 18
  Full ViewerSessionService / GraphViewModel projection
        ↓
Task 19
  Persist user-confirmed manual mappings
        ↓
Task 20
  Produce pending AI/rule-assisted mapping proposals
        ↓
Task 21
  Progressive L2/L3 detail scan
        ↓
Task 22
  Opt-in runtime query trace
        ↓
Task 23
  Cross-platform/logging/snapshot hardening
        ↓
Task 24
  Final scan boundary review + local template import

Independent future tracks
  Task 25: project upload ingestion
  Task 26: persistent session store / scan history
  Frontend plan: actual GUI screens and interactions
```

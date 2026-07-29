# Audit B — `src/kai_mind/web/routes/` 現況稽核（重構前，READ-ONLY）

- 稽核範圍：9 個 route 檔（1,150 行）+ `dependencies.py`（參考）
- 已讀完的契約文件：`docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`、`frontend/API_CONTRACT.md`、`CLAUDE.md`
- 已讀完 `docs/work/Timmy/schedule/plan/unfinish/phase2.5/1.md`；凡屬 `create_app()` → `AppServices` / `dependencies.py` 的 17 個 `cast()` 一律標 `[已被 Plan 1 涵蓋]`，不重複展開
- 本報告未修改任何檔案

---

## 0. 全部已註冊 route 一覽表（客觀證據）

以下表格由實際跑 `create_app()` 後列舉 `app.routes` 產生（`APIRoute` only，過濾 HEAD/OPTIONS）：

```
KAI_MIND_STATE_DIR=<tmp> uv run python -c "
from kai_mind.web.app import create_app
from fastapi.routing import APIRoute
import inspect
a = create_app()
for r in a.app.routes: ...  # methods/path/status_code/response_model/response_class/tags/async/deps
"
```

| # | Method | Path | 檔案:行 | 函式 | `status_code=` | `response_model` | `response_class` | tags | def/async | route-level deps |
|---|--------|------|---------|------|----------------|------------------|------------------|------|-----------|------------------|
| 1 | POST | `/api/map/build` | `map_routes.py:22` | `build_map` | None(→200) | `MapBuildResult`（**core model**） | JSONResponse | `map` | `def` | — |
| 2 | GET | `/api/map` | `map_routes.py:37` | `get_api_map` | None(→200) | `ViewerPayload`（core） | JSONResponse | `map` | `def` | — |
| 3 | GET | `/api/map/report` | `map_routes.py:45` | `get_map_report` | None(→200) | **無** | JSONResponse（**實際回 text/markdown**） | `map` | `def` | — |
| 4 | GET | `/map` | `map_routes.py:75` | `get_map_fallback` | None(→200) | `ViewerPayload`（core） | JSONResponse | `map` | `def` | — |
| 5 | POST | `/api/map-builds/{base_build_id}/apply` | `map_build_routes.py:38` | `apply_confirmations` | None(→200) | `ApplyConfirmationsResponse`（web） | JSONResponse | `map-builds` | `def` | — |
| 6 | GET | `/api/map-builds/{build_id}` | `map_build_routes.py:79` | `get_build` | None(→200) | `MapBuildScopedResponse`（web） | JSONResponse | `map-builds` | `def` | — |
| 7 | GET | `/api/projects/{project_id}/map-builds/latest` | `map_build_routes.py:94` | `get_latest_build` | None(→200) | `MapBuildScopedResponse`（web） | JSONResponse | `map-builds` | `def` | — |
| 8 | GET | `/api/projects/{project_id}/map-builds` | `map_build_routes.py:109` | `list_builds` | None(→200) | `MapBuildHistoryResponse`（web） | JSONResponse | `map-builds` | `def` | — |
| 9 | POST | `/api/detail-scans` | `detail_scan_routes.py:39` | `create_detail_scan` | None(→200) | `DetailScanResponse`（web） | JSONResponse | `detail-scans` | `def` | — |
| 10 | GET | `/api/detail-scans/{detail_scan_id}` | `detail_scan_routes.py:127` | `get_detail_scan` | None(→200) | `DetailScanResponse`（web） | JSONResponse | `detail-scans` | `def` | — |
| 11 | GET | `/api/mapping-proposals` | `mapping_proposal_routes.py:37` | `list_mapping_proposals` | None(→200) | `MappingProposalListResponse`（web） | JSONResponse | `mapping-proposals` | `def` | — |
| 12 | POST | `/api/mapping-proposals` | `mapping_proposal_routes.py:55` | `create_mapping_proposal` | None(→200) | `MappingProposal`（**core model**） | JSONResponse | `mapping-proposals` | `def` | — |
| 13 | POST | `/api/mapping-proposals/{proposal_id}/decision` | `mapping_proposal_routes.py:97` | `decide_mapping_proposal` | None(→200) | `MappingProposalDecisionResult`（**core**） | JSONResponse | `mapping-proposals` | `def` | `reject_legacy_mapping_type` |
| 14 | GET | `/api/mappings` | `mapping_routes.py:24` | `list_mappings` | None(→200) | `ManualMappingListResponse`（web） | JSONResponse | `mappings` | `def` | — |
| 15 | POST | `/api/mappings` | `mapping_routes.py:39` | `create_mapping` | None(→200) | `ManualMapping`（**core model**） | JSONResponse | `mappings` | `def` | `reject_legacy_mapping_type` |
| 16 | PATCH | `/api/mappings/{mapping_id}` | `mapping_routes.py:58` | `update_mapping` | None(→200) | `ManualMapping`（**core**） | JSONResponse | `mappings` | `def` | **無**（見 §「確認沒問題」） |
| 17 | GET | `/api/projects/{project_id}` | `project_routes.py:21` | `get_project` | None(→200) | `ProjectResponse`（web） | JSONResponse | `projects` | `def` | — |
| 18 | POST | `/api/projects/import` | `project_routes.py:36` | `import_project` | None(→200) | `ProjectImportResponse`（web） | JSONResponse | `projects` | `def` | — |
| 19 | POST | `/api/projects/{project_id}/scan-preflights` | `scan_routes.py:79` | `create_scan_preflight` | None(→200) | `InventoryPreflightResponse`（web） | JSONResponse | **`scans`** | `def` | — |
| 20 | POST | `/api/scans` | `scan_routes.py:127` | `create_scan` | None(→200) | `ScanCreateResponse`（web） | JSONResponse | `scans` | `def` | — |
| 21 | GET | `/api/scan/events` | `scan_routes.py:354` | `scan_events` | None(→200) | **無** | `EventSourceResponse` | `scans` | **`async`** | — |
| 22 | POST | `/api/trace` | `trace_routes.py:27` | `create_query_trace` | None(→200) | `TraceRunResult`（**core**） | JSONResponse | `trace` | `def` | — |
| 23 | POST | `/api/viewer/load` | `viewer_routes.py:19` | `load_viewer_map` | None(→200) | `ViewerPayload`（core） | JSONResponse | `viewer` | `def` | — |

### 表格直接讀出來的不一致

1. **`status_code=` 欄位 23/23 都是 `None`** — 沒有任何 route 在 decorator 宣告 status code；POST 建立資源一律 200。
2. **`responses={...}` 0/23** — 實測 `grep -c "responses=" src/kai_mind/web/routes/*.py` → `0`。所以 OpenAPI 只有 `200` 與 FastAPI 自動加的 `422`：

```
GET    /api/map/report              codes=['200','422']  200content=['application/json']   ← 實際是 text/markdown
POST   /api/scans                   codes=['200','422']  ← 文件寫了 404/409/422，OpenAPI 沒有
GET    /api/detail-scans/{id}       codes=['200','422']  ← 文件寫了 404，OpenAPI 沒有
```

3. **`response_model` 兩種流派**：7 條直接回 core domain model（`MapBuildResult`/`ViewerPayload`/`ManualMapping`/`MappingProposal`/`MappingProposalDecisionResult`/`TraceRunResult`），16 條回 `web/schemas.py` 的 `WebSchema` 投影。
4. **`prefix=` 0/9** — 9 個 router 全部是 `APIRouter(tags=[...])`，`/api` 在 23 條 path 各寫一次。
5. **tag 命名混用**：`scans`/`detail-scans`/`map-builds`/`mapping-proposals`/`mappings`/`projects`（複數）vs `map`/`trace`/`viewer`（單數）。
6. **路徑歸屬與 router 檔不對齊**：`/api/projects/...` 出現在 3 個檔（`project_routes` #17-18、`scan_routes` #19、`map_build_routes` #7-8），且 #19 被打上 `scans` tag。

---

## 逐條發現

### B-1. 同一個 `project_not_found` 有兩種 response body shape，且前端只認得其中一種

- **位置（全部出現點）**
  - dict 形（`{"detail": {code, message, retryable, context}}`）：`src/kai_mind/web/routes/scan_routes.py:98-101`、`src/kai_mind/web/routes/scan_routes.py:163-166`
  - 純字串形（`{"detail": "project_not_found"}`）：`src/kai_mind/web/routes/project_routes.py:28`、`src/kai_mind/web/routes/detail_scan_routes.py:56`、`src/kai_mind/web/routes/map_build_routes.py:119`、`src/kai_mind/web/routes/mapping_proposal_routes.py:69`、`src/kai_mind/web/routes/trace_routes.py:40`
  - 產生 dict 形的來源：`src/kai_mind/web/inventory_error_response.py:65-70`

- **現況**（兩種寫法並列）

```python
# scan_routes.py:98-101（唯一用 inventory_error_response 的檔）
raise HTTPException(
    status_code=404,
    detail=project_not_found_detail(),   # -> {"code":..., "message":..., "retryable":...}
)

# trace_routes.py:40 / project_routes.py:28 / detail_scan_routes.py:56 / …
raise HTTPException(status_code=404, detail="project_not_found")
```

  `inventory_error_response.py` 只被 `scan_routes.py:50-54` import，全 repo 沒有第二個使用者。它之所以特殊，是因為 `docs/API-GUIDE.md:274` 為 inventory selection 家族單獨定義了 typed error body：「Typed error body固定為 `{detail:{code,message,retryable,context}}`」，而 `docs/API-GUIDE.md:26` 的全域規則是 `{ "detail": string }`。也就是說 **契約文件本身就承認有兩種格式**，但 `project_not_found` 這個 code **同時出現在兩邊**（`API-GUIDE.md:278` 的 typed 表 + `API-GUIDE.md:985` 的全域 404 表）——這是文件與實作一起漂移的結果，不是刻意設計。

- **為什麼是問題**
  1. 同一語意的錯誤在不同 endpoint 回不同型別，客戶端必須寫兩套解析。
  2. **前端實測會壞**：`frontend/src/services/http.ts:61-68`

```ts
async function errorMessage(response: Response) {
  try {
    const payload = apiErrorSchema.parse(await response.json());
    if (typeof payload.detail === "string") return payload.detail;   // ← 只認 string
  } catch { /* … */ }
  return `${response.status} ${response.statusText}`;                 // ← dict 落到這裡
}
```

  `frontend/src/types.ts:142-146` 的 `apiErrorSchema` 雖然 union 了 `z.record(z.unknown())`，但 `http.ts:64` 只在 `typeof === "string"` 時取用。所以 `inventory_error_response.py:11-51` 那 13 條精心寫給人看的 `ERROR_MESSAGES`（例如 `"Scan selection changed. Refresh the file review."`）**永遠不會顯示給使用者**，UI 只會看到 `"404 Not Found"` / `"409 Conflict"`。而 `frontend/src/services/projectScanApi.ts:28` 呼叫的 `/api/scans` 正是走 dict 形的那條。

- **建議改法**：統一成 **structured detail**（`{code, message, retryable, context}`），不是統一成字串。理由：(a) typed 形是 superset，字串形可無損升級成 `{code: "project_not_found", message: ..., retryable: false}`；(b) `ERROR_MESSAGES` 這種 i18n-ready 的人類訊息只有 typed 形放得下；(c) 反向（把 inventory 降級成字串）會直接違反 `docs/API-GUIDE.md:274`。
  作法是把 `inventory_error_response.py` 升格成 `web/error_response.py`，加一個通用工廠：

```python
def api_error_detail(
    code: str,
    *,
    message: str,
    retryable: bool = False,
    context: dict[str, str | int] | None = None,
) -> dict[str, object]: ...

def api_error(status_code: int, code: str, ...) -> HTTPException: ...
```

  然後 route 一律寫 `raise api_error(404, "project_not_found")`。過渡期建議先改 `http.ts:64` 支援 dict（`if (typeof d === "object" && typeof d.message === "string") return d.message`），再逐檔搬後端。

- **影響面（已實查）**：**會破壞前端契約，必須明講**。
  - `frontend/src/services/http.ts:64` — 需要改成同時支援 string 與 `{code,message}`。
  - `frontend/src/types.ts:142-146` — `apiErrorSchema` 型別已能容納，不必改。
  - `frontend/API_CONTRACT.md:259` — 目前只寫「A stale/changed selection uses `{detail:{code,message,retryable,context}}`」，統一後這句要改成全域規則。
  - `docs/API-GUIDE.md:26`（全域錯誤格式）與 `docs/API-GUIDE.md:980-990`（錯誤對照表）都要改寫。

- **相關測試**
  - 修改：`tests/web/test_mapping_proposal_routes.py::test_proposal_route_requires_existing_project`（`:327` 斷言 `detail == "project_not_found"`）、`::test_proposal_route_requires_loaded_map`（`:351`）
  - 修改：`tests/web/test_trace_routes.py::test_trace_route_requires_loaded_project_map`（`:193`、`:195`）
  - 修改：`tests/web/test_detail_scan_routes.py::test_detail_scan_route_rejects_invalid_target_without_writing`（`:67`）
  - 修改：`tests/web/test_detail_scan_build_binding.py`（`:143`、`:206`、`:244`、`:275` 四處字串斷言）
  - 修改：`tests/web/test_map_build_apply_routes.py::test_apply_route_is_idempotent_and_rejects_stale_base`（`:178`）
  - 修改：`tests/web/test_map_routes.py`（`:107`、`:117`）
  - 修改：`tests/web/test_legacy_mapping_write_rejection.py`（`:50`、`:119`）
  - 修改：`tests/web/test_trace_build_binding.py::test_query_trace_rejects_unknown_requested_build`（`:51`）
  - 不動（已是 dict 形）：`tests/web/test_inventory_preflight_routes.py`（`:223`、`:234`、`:269`、`:339`）、`tests/web/test_project_scan_routes.py`（`:104`、`:155`、`:201`）、`tests/e2e/test_inventory_selection_scan_flow.py:190`
  - 新增：一支 contract 測試，掃過所有 route 的錯誤路徑，斷言 `detail` 一律是 `{code, message, retryable}`

- **嚴重度**：**P1**（跨層契約分裂 + 前端已被實質影響）
- **風險**：**中** — 改動點多（8 個測試檔 + 前端 1 檔 + 2 份文件），但每一處都是機械式替換，且有測試覆蓋。

---

### B-2. `trace_routes` 把原始 exception 字串（含**絕對路徑**）回給 HTTP client

- **位置**：`src/kai_mind/web/routes/trace_routes.py:58-66`

- **現況**

```python
try:
    trace_config = QueryTraceConfigLoader().load_project_config(
        project.project_path
    )
except QueryTraceConfigError as exc:
    raise HTTPException(
        status_code=400,
        detail=f"invalid_trace_config: {exc}",     # ← exc 由 OSError 包起來
    ) from exc
```

  上游 `src/kai_mind/core/services/query_trace_config_loader.py:45-48`：

```python
except OSError as exc:
    raise QueryTraceConfigError(
        f"Failed to read pyproject.toml: {exc}"
    ) from exc
```

  **實測**（我實際跑過，把目標 `pyproject.toml` chmod 000）：

```
DETAIL WOULD BE: invalid_trace_config: Failed to read pyproject.toml:
  [Errno 13] Permission denied: '/var/folders/0g/.../kai_secret_project_tx_0mjb0/pyproject.toml'
```

  被掃描專案的**完整絕對路徑**直接進了 HTTP response body。

- **為什麼是問題**
  - `CLAUDE.md` 核心原則：「**Local-first privacy** — never log or display full secret values, only masked previews」；`docs/API-GUIDE.md:27`「安全錯誤 | 413/500 不回 raw secret、exception string、absolute path」。這裡是 400，但洩漏的內容正是那條規則要擋的東西（raw exception string + absolute path）。
  - `AGENTS.md` 把 secret exposure 列為 PR review 重點。
  - 對照組：`tests/web/test_scan_boundary_routes.py:106` 已經有 `assert str(tmp_path) not in str(pending)` 這種「不得洩漏絕對路徑」的斷言，證明這是本 repo 認可的規範；trace 路徑只是漏了。
  - 附帶：**400 是全 API 唯一一個 400**（見 §0 表 + `grep status_code=` 結果）。`docs/API-GUIDE.md:783` 在 §4 endpoint 表裡有寫，但全域錯誤對照表 `docs/API-GUIDE.md:982-990` 沒有 400 這一列。

- **建議改法**
  1. 把 detail 收斂成穩定 code，不帶 exception 內容：`raise api_error(422, "invalid_trace_config")`（順帶把 400 併入既有的 422「輸入不合法」語意，消掉唯一的 400）。
  2. 若要保留診斷資訊，走 `safe_log_event`（`core/services/logging_service.py`，`web/middleware.py:106-112` 已在用）記到 server log，不進 response。
  3. `QueryTraceConfigLoader` 應改成注入（見 B-8），才能在測試裡驗證 fail-closed 行為。
  4. 建議簽名：`def create_query_trace(..., trace_config_loader: Annotated[QueryTraceConfigLoader, Depends(query_trace_config_loader)]) -> TraceRunResult:`

- **影響面**：前端 `frontend/src/services/http.ts:64` 只是把 detail 當文字顯示，沒有解析 `invalid_trace_config:` 前綴；`frontend/src/types.ts` 沒有 trace endpoint 的 schema；`frontend/API_CONTRACT.md:311-319` 明說 query replay 目前是從 `viewer_load_result.ai_system_map.query_trace_events` 渲染，**尚未呼叫 `/api/trace`**。→ **前端零影響**。要改 `docs/API-GUIDE.md:783` 的 400→422。
- **相關測試**
  - 新增：`tests/web/test_trace_routes.py::test_trace_invalid_config_does_not_leak_absolute_path`（斷言 `str(project_root) not in response.text`）
  - 檢查/可能修改：`tests/web/test_trace_routes.py::test_trace_route_uses_project_pyproject_chunk_keys`（`:133`，目前只測 happy path，沒測 malformed config）
- **嚴重度**：**P1**（privacy / secret-boundary 迴歸，契約文件明列）
- **風險**：**低** — 單檔單處，前端無依賴。

---

### B-3. `detail=str(exc)` 有 8 處，把不可列舉的自由文字當成 API 錯誤契約

- **位置（全部）**
  - `src/kai_mind/web/routes/scan_routes.py:265`、`src/kai_mind/web/routes/scan_routes.py:337`
  - `src/kai_mind/web/routes/detail_scan_routes.py:90-97`（`detail = str(exc)`）、`:99-100`、`:102`
  - `src/kai_mind/web/routes/map_build_routes.py:57`、`:64`
  - `src/kai_mind/web/routes/mapping_routes.py:55`、`:76`
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:94`、`:119`

- **現況**（三種寫法並列，全在同一層）

```python
# (a) 穩定 code —— 正確做法
raise HTTPException(status_code=422, detail=exc.code)          # map_routes.py:32
raise HTTPException(status_code=status_code, detail=exc.code)  # scan_routes.py:325

# (b) 硬編字面 code —— 也 OK，但與 (a) 來源不同
raise HTTPException(status_code=404, detail="build_not_found") # map_build_routes.py:90

# (c) 原始 exception 訊息 —— 不可列舉
raise HTTPException(status_code=422, detail=str(exc))          # mapping_routes.py:55
```

  這些 `str(exc)` 實際會產生什麼？我追到上游：
  - `core/services/manual_mapping_service.py:174` → `f"Unknown target slot: {target_slot}"`（**含使用者輸入**）
  - `core/services/manual_mapping_service.py:151` → `"Manual mapping must reference evidence"`
  - `core/services/apply_confirmations_service.py:162-170` → `"mapping belongs to another project"`、`"mapping must be confirmed"`、`"mapping evidence is not present in source snapshot"`
  - `core/models/mapping_proposals.py:75-132` → `"candidate_id is required for accept"` 等 10 種
  - `web/schemas.py:151-153`（`MapBuildScopedResponse.from_core`）→ `"build response requires lineage and viewer result"`

  而**測試已經在依賴這些自由文字**：
  - `tests/web/test_mapping_routes.py:68` → `assert "Unknown target slot" in response.json()["detail"]`
  - `tests/web/test_mapping_proposal_routes.py:285` → `assert "Proposal is not pending" in second_response.json()["detail"]`

- **為什麼是問題**
  - `docs/API-GUIDE.md:980-990` 的錯誤對照表把 detail 定義成**可列舉的穩定 code 集合**。`str(exc)` 讓這張表在 8 個 route 失效——任何人改一句 core 的錯誤訊息就是一次未察覺的 API breaking change，而 pre-commit 不會擋。
  - 錯誤訊息含使用者輸入（`Unknown target slot: {target_slot}`）→ reflected content，雖然這裡是本機 API，但同一模式套到 path/secret 就會變成 B-2。
  - `str(exc)` 也讓 `except` 與 status code 的對應變得脆弱：`detail_scan_routes.py:89-97` 就是靠字串比對決定 409 還是 404：

```python
except DetailScanBuildError as exc:
    detail = str(exc)
    status = (
        409
        if detail in {"base_build_not_latest", "profile_sidecar_unavailable"}
        else 404
    )
```

  也就是說 **exception 的 `str()` 被當成 error code enum 在用**，但型別上完全沒有保證。`scan_routes.py:315-325`（`BuildCommitError`）用的是 `exc.code`，是同一件事的正確版本。

- **建議改法**
  1. Core 的 domain error 一律加 `code: str` 屬性（`BuildCommitError` 已經有，`core/services/build_commit_service.py:24`），route 只讀 `exc.code`。
  2. Route 端把 exception→(status, code) 的對應抽成一張宣告式表，放 `web/error_mapping.py`：

```python
ERROR_STATUS: Final[Mapping[type[Exception], int]] = {
    BuildNotFoundError: 404,
    MappingNotFoundError: 404,
    BaseBuildNotLatestError: 409,
    ApplyValidationError: 422,
    ProjectStateBusyError: 503,
}

def http_error_from(exc: Exception) -> HTTPException: ...
```
  3. 移除 `detail_scan_routes.py:91-96` 的字串比對分支，改成 `DetailScanBuildError` 帶 `code` + 上表查詢。

- **影響面**：`frontend/src/services/http.ts:64` 只是原樣顯示 detail 文字，不解析內容；`frontend/src/types.ts` 沒有任何 mapping / apply / detail-scan 的 error 型別；`frontend/API_CONTRACT.md` 完全沒提這些 endpoint 的錯誤字串。→ **前端無依賴，可安全收斂**（唯一例外是 B-1 的 shape 變更）。
- **相關測試**
  - 修改：`tests/web/test_mapping_routes.py::test_mapping_route_rejects_invalid_slot`（`:68` 的子字串斷言改成 code 斷言）
  - 修改：`tests/web/test_mapping_proposal_routes.py::test_proposal_decision_second_request_returns_422`（`:285`）
  - 修改：`tests/web/test_map_build_apply_routes.py::test_apply_route_validates_request_and_unknown_ids`（`:181`）
  - 修改：`tests/web/test_detail_scan_build_binding.py::test_detail_scan_rejects_build_owned_by_another_project`（`:206`，目前斷言 `"project_build_mismatch"`——這個 code **未出現在 `docs/API-GUIDE.md:677-684` 的 detail-scan 錯誤表**）
  - 新增：一支測試斷言所有 route 的 detail code 都在 `docs/API-GUIDE.md` 列舉的集合內
- **嚴重度**：**P1**（API 契約沒有被型別或測試鎖住，且已在 core 與 web 之間形成隱性耦合）
- **風險**：**中** — 需要動 core 的 exception 類別，範圍溢出 routes 層；建議拆成獨立 plan 分兩步（先加 `code`，再改 route）。

---

### B-4. `ScanCreateResponse` 把三種結果壓成一個 model，且前端 zod schema 與它不相容（boundary flow 必然 parse 失敗）

- **位置**
  - 定義：`src/kai_mind/web/schemas.py:236-257`
  - 四個回傳點：`src/kai_mind/web/routes/scan_routes.py:193-201`、`:236-240`、`:243-248`、`:268-273`、`:344-351`
  - 前端 schema：`frontend/src/types.ts:210-217`
  - 前端呼叫點：`frontend/src/services/projectScanApi.ts:27-37`

- **現況**

```python
# schemas.py:236-257
class ScanCreateResponse(WebSchema):
    scan_id: str | None = Field(default=None, exclude_if=lambda v: v is None)   # 動態消失
    project_id: str
    status: Literal["completed", "error", "requires_boundary_decision"]
    build_result: MapBuildResult | None = None
    boundary_proposals: list[ScanBoundaryProposal] = Field(default_factory=list)
    available_boundary_actions: list[ScanBoundaryDecisionAction] = Field(
        default_factory=lambda: [SCAN_THIS_RUN, SKIP_THIS_RUN]                  # 永遠輸出
    )
    preflight_request_id: str | None = Field(default=None, exclude_if=lambda v: v is None)
    inventory_selection_summary: InventorySelectionSummary | None = None
```

  我實際序列化驗證：

```
BOUNDARY:  {"project_id":"p","status":"requires_boundary_decision","build_result":null,
            "boundary_proposals":[],"available_boundary_actions":[...],"inventory_selection_summary":null}
            ← 沒有 scan_id
COMPLETED: {"scan_id":"scan:1","project_id":"p","status":"completed", ... }
```

  後端測試也明文鎖住這個行為：`tests/web/test_scan_boundary_routes.py:92` → `assert "scan_id" not in pending`。
  `frontend/API_CONTRACT.md:256` 也寫「When `requires_boundary_decision` is returned, `scan_id` is absent.」

  但前端 zod：

```ts
// frontend/src/types.ts:210-217
export const scanCreateResponseSchema = z.object({
  scan_id: z.string(),                                  // ← 必填，沒有 .optional()
  project_id: z.string(),
  status: z.enum(["completed", "error", "requires_boundary_decision"]),
  build_result: z.record(z.unknown()).nullable().optional(),
  boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
  available_boundary_actions: z.array(scanBoundaryActionSchema).default([...]),
});
```

  `frontend/src/services/projectScanApi.ts:36` 直接 `scanCreateResponseSchema.parse(payload)` → **凡是回 `requires_boundary_decision`，前端一定丟 ZodError**。而 `status` enum 裡明明列了 `requires_boundary_decision`，代表這條路徑是預期會發生的。

- **為什麼是問題**
  - 這是 **route 層契約設計問題**的直接後果：一個 `response_model` 承載三種互斥結果（completed / error / requires_boundary_decision），靠 `exclude_if` 讓欄位動態出現或消失，OpenAPI 無法表達，前端自然對不齊。
  - `docs/MODEL-CONTRACT.md` 的五態評估原則（明確狀態、不用單一模糊訊號）在 HTTP 層沒有被貫徹。
  - 附帶：`available_boundary_actions` 有 `default_factory`，所以連 `completed` 回應也會帶 `["scan_this_run","skip_this_run"]`，但 `frontend/API_CONTRACT.md:213` 只在 boundary review response 定義它。這是純雜訊欄位。

- **建議改法**
  1. 短期（不動 wire format）：把前端 `frontend/src/types.ts:211` 改成 `scan_id: z.string().optional()`，並用 discriminated union 表達：

```ts
export const scanCreateResponseSchema = z.discriminatedUnion("status", [
  z.object({ status: z.literal("requires_boundary_decision"), project_id: z.string(),
             preflight_request_id: z.string().optional(),
             boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
             available_boundary_actions: z.array(scanBoundaryActionSchema).default([...]) }),
  z.object({ status: z.enum(["completed", "error"]), scan_id: z.string(), project_id: z.string(),
             build_result: z.record(z.unknown()).nullable().optional(),
             inventory_selection_summary: z.unknown().optional() }),
]);
```
  2. 中期（後端）：後端也拆成 `ScanCompletedResponse | ScanBoundaryReviewResponse`，用 `response_model=Union[...]` + `Field(discriminator="status")`，讓 OpenAPI 能表達，並把 `available_boundary_actions` 移到只有 boundary 那一支才有。
  3. `exclude_if` 這種「欄位有時在有時不在」的技巧，改成兩個明確 model 之後就不需要了。

- **影響面**：**這一條本身就是前端已經破掉的契約**。必須改 `frontend/src/types.ts:210-217`；`frontend/src/services/projectScanApi.ts:36` 的呼叫寫法可不動。`frontend/API_CONTRACT.md:182-254` 已經正確描述了兩種 shape，文件不用改（實作對不上文件）。
- **相關測試**
  - 前端新增：`frontend/src/services/` 下針對 `scanCreateResponseSchema` 的 vitest（目前只有 `http.test.ts`，沒有 `projectScanApi.test.ts`）
  - 後端不動（`tests/web/test_scan_boundary_routes.py::test_scan_requires_boundary_decision_before_building_map` 已鎖住行為）
  - 若採建議 2：修改 `tests/web/test_scan_boundary_routes.py`（`:92`-`:99`）與 `tests/web/test_inventory_preflight_routes.py::test_preflight_selection_scan_uses_final_inventory_and_returns_summary`（`:136`）
- **嚴重度**：**P1**（前端 boundary-decision flow 目前應是壞的）
- **風險**：短期修法 **低**（只動前端 zod）；中期後端拆 model **中**（OpenAPI + 測試連動）。

---

### B-5. `create_scan` 在 route 裡塞了 ~190 行編排邏輯，包含 build_id 生成與樂觀鎖參數計算

- **位置**：`src/kai_mind/web/routes/scan_routes.py:131-351`（單一函式 221 行，其中函式體 190 行）

- **現況**（節錄關鍵段落）

```python
# scan_routes.py:174-208 —— 「隱式 preflight」的完整決策流程
implicit_state = preflight_service.create(payload.project_id, project.project_path,
    InventoryPreflightRequest(requested_paths=tuple(
        item.target_path for item in payload.boundary_decisions)))
required_paths = {item.path for item in implicit_state.candidate_set.candidates
                  if item.decision_required}
if not payload.boundary_decisions and required_paths:
    implicit_proposals = boundary_service.create_selection_proposals(implicit_state)
    return ScanCreateResponse(..., boundary_proposals=[
        item for item in implicit_proposals if item.target.path in required_paths])
if any(item.target_path not in required_paths for item in payload.boundary_decisions):
    raise InventorySelectionError(InventorySelectionErrorCode.OVERRIDE_NOT_ALLOWED)

# scan_routes.py:217-241 —— stale/changed 自動重試策略
except InventorySelectionError as exc:
    if not explicit_preflight and exc.code in {PREFLIGHT_STALE, TARGET_CHANGED}:
        refreshed = preflight_service.create(...)
        proposals = [item for item in boundary_service.create_selection_proposals(refreshed)
                     if item.selection_context is not None
                     and item.selection_context.decision_required]

# scan_routes.py:284-288 —— ID 生成 + 樂觀鎖參數
build_id = f"build:{uuid4()}"
output_dir = Path(payload.output) / build_id.replace(":", "_")
pointer = repository.get_latest_pointer(payload.project_id)
expected_id = pointer.latest_build_id if pointer else None
expected_revision = pointer.revision if pointer else 0
```

  對照其他 8 個檔的 route 函式體：`viewer_routes.py:20-34`（15 行）、`project_routes.py:36-53`（18 行）、`mapping_routes.py:44-55`（12 行）、`map_build_routes.py:83-91`（9 行）。`create_scan` 比它們大一個數量級。

  同一檔還注入了 **8 個服務**（`scan_routes.py:133-158`），是全 repo 最多的；其中 `state_repository`（`LocalJsonStateProvider`）是**唯一一個被 route 直接注入的 provider**，其他 route 都只碰 service。

- **為什麼是問題**
  - `CLAUDE.md`：「**Core engine is platform-independent** — CLI, Web API, and launchers must not duplicate core scanner logic.」這段編排是 scan boundary 的核心政策，CLI 走 `MapBuildService` 完全拿不到它 → 同樣的 boundary 決策規則在 CLI 路徑不存在。
  - `CLAUDE.md` 的分層宣告是 `Web / CLI adapters -> Core services -> Providers / Models`。route 直接拿 `LocalJsonStateProvider` 讀 `get_latest_pointer` 是 **adapter 跳過 service 直接呼叫 provider**，違反宣告的依賴方向。
  - 本 repo 已經有一支測試在強制「route 必須是薄 adapter」：`tests/web/test_viewer_routes.py:59` `test_viewer_route_is_thin_adapter_without_project_scan_logic`，用 `inspect.getsource` 檢查 route 原始碼不得出現 `ProjectScanService` 等字樣。**這條標準只套在 viewer_routes，沒套到 scan_routes。**
  - `f"build:{uuid4()}"` 的 ID 慣例在 core 已有三處（`core/services/map_build_service.py:213`、`:253`、`:293`），web 這裡是第四份複製（詳見 B-14）。

- **建議改法**
  新增 `core/services/scan_orchestration_service.py`（或擴充既有 `inventory_selection_service` / `scan_boundary_review_service`），把 `scan_routes.py:168-337` 整段搬進去，route 只剩下「呼叫 + 把結果 map 成 HTTP」：

```python
# core/services/scan_orchestration_service.py
@dataclass(frozen=True)
class ScanOutcome:
    kind: Literal["completed", "requires_boundary_decision"]
    scan_id: str | None
    preflight_request_id: str | None
    boundary_proposals: tuple[ScanBoundaryProposal, ...]
    build_result: MapBuildResult | None
    inventory_selection_summary: InventorySelectionSummary | None

class ScanOrchestrationService:
    def run(
        self,
        *,
        project_id: str,
        project_root: Path,
        output: Path,
        boundary_decisions: Sequence[ScanBoundaryDecisionRequest],
        preflight_request_id: str | None,
        build_options: MapBuildRequest,
    ) -> ScanOutcome: ...
```

```python
# scan_routes.py 之後長這樣（~30 行）
@router.post("/api/scans", response_model=ScanCreateResponse)
def create_scan(
    payload: ScanCreateRequest,
    orchestration: Annotated[ScanOrchestrationService, Depends(scan_orchestration_service)],
    store: Annotated[SessionStore, Depends(session_store)],
) -> ScanCreateResponse:
    project = store.project(payload.project_id)
    if project is None:
        raise api_error(404, "project_not_found")
    try:
        outcome = orchestration.run(...)
    except InventorySelectionError as exc:
        raise api_error(exc.http_status, exc.code.value, ...) from exc
    return ScanCreateResponse.from_outcome(outcome)
```

  選這種切法的理由：`build`（`scan_routes.py:290-305`）目前是定義在 route 裡的 closure，它捕捉了 `snapshot`/`project`/`payload` 三個 route-local 變數——這正是「編排屬於 core」的最直接證據，搬進 service 後這個 closure 變成 service 的私有方法。

- **影響面**：純內部重構，wire format 不變 → `frontend/src/services/projectScanApi.ts:27-37`、`frontend/src/types.ts:210-217`、`frontend/API_CONTRACT.md:159-262` **全部不受影響**（前提是 `ScanCreateResponse` 欄位不動；若同時做 B-4 則另計）。
- **相關測試**
  - 修改（改成打 service 而非 HTTP）：`tests/web/test_scan_boundary_routes.py` 的 5 支測試（`:45`、`:76`、`:114`、`:152`、`:189`）——建議保留 HTTP 層 smoke，把細節斷言下沉
  - 新增：`tests/unit/core/services/test_scan_orchestration_service.py`（隱式 preflight、OVERRIDE_NOT_ALLOWED、stale 重試三條分支）
  - 不動：`tests/e2e/test_inventory_selection_scan_flow.py` 三支（`:49`、`:156`、`:198`）應原樣通過，可當回歸閘門
  - 新增：把 `tests/web/test_viewer_routes.py:59` 的 thin-adapter 檢查推廣成參數化測試，覆蓋 9 個 route 模組
- **嚴重度**：**P1**（違反 `CLAUDE.md` 明列的架構原則，且 CLI 拿不到同一套 boundary 規則）
- **風險**：**高** — 這是全 repo 最複雜的 route，牽涉 scan boundary（安全邊界）與樂觀鎖；必須先確保 e2e 三支綠燈才動，建議獨立成一個 plan。

---

### B-6. `scan_routes.py:267-273` 是死碼，`inventory_policy = None` 是廢變數

- **位置**：`src/kai_mind/web/routes/scan_routes.py:226`、`:253`、`:267-273`、`:276`

- **現況**

```python
        if selection.inventory is None:
            raise ValueError("Inventory selection was not materialized")
        inventory = selection.inventory
        selection_summary = selection.summary
        proposals = []                                   # :253 —— 無條件清空
    except InventorySelectionError as exc:
        ...
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if proposals:                                        # :267 —— 永遠 False
        return ScanCreateResponse(
            project_id=payload.project_id,
            status="requires_boundary_decision",
            boundary_proposals=proposals,
            preflight_request_id=payload.preflight_request_id,
        )

    try:
        inventory_policy = None                          # :276 —— 賦值後只被讀一次
        snapshot = snapshot_service.scan_and_save(
            ...,
            inventory_policy=inventory_policy,           # :280
        )
```

- **為什麼是問題**
  - `proposals` 全檔只有兩個綁定點：`:226`（在 inner `except` 內）與 `:253`。窮舉所有控制流：
    - `:226` 賦值後若非空 → `:236` return；若為空 → `:241` `raise` → 被 `:254` 的 outer except 接住 → 一定 raise `HTTPException`，函式結束。
    - 成功路徑一定經過 `:253`，`proposals = []`。
    → 抵達 `:267` 時 `proposals` **恆為 `[]`**，`:267-273` 這 7 行**不可能執行**。
  - `inventory_policy = None` 是把 literal 繞一個變數再傳，等價於 `inventory_policy=None`。這種寫法通常是「以前這裡有計算邏輯、後來被拿掉」的殘留。
  - 額外問題：`:250` 的 `raise ValueError("Inventory selection was not materialized")` 是**內部不變式違反**，卻被 `:264` 的 `except ValueError` 接住變成 **422 使用者輸入錯誤**，而且訊息原樣回給 client（同 B-3）。這種情況應該是 500（讓 `SafeUnhandledExceptionMiddleware` 遮蔽），不是 422。

- **建議改法**
  1. 刪掉 `:267-273`。
  2. `:276` 直接寫 `inventory_policy=None`，或若真的不需要就從 `scan_and_save` 呼叫中拿掉。
  3. `:249-250` 改成專用的內部錯誤型別（例如 `AssertionError` 或自訂 `InventoryMaterializationError`），不被 `except ValueError` 捕捉，讓它走 500。
  4. `:209` 的 `assert selection_request_id is not None` 在 `python -O` 下會被移除；改成明確的 `if ... is None: raise`。

- **影響面**：死碼與內部變數，前端零影響。`:250` 改成 500 會改變一個目前是 422 的行為，但這條路徑理論上不可達（`selection.pending_proposals` 為空且 `selection.inventory` 為 None 的組合），前端沒有對應處理。
- **相關測試**
  - 現有測試無一覆蓋 `:267-273`（`tests/web/test_scan_boundary_routes.py` 的 boundary 路徑走的是 `:243-248` 或 `:193-201`）。刪除後 **coverage 分母下降 → 85% branch gate 只會變好**
  - 新增：非必要；若要防迴歸，可加一支 `tests/web/test_project_scan_routes.py::test_scan_internal_invariant_failure_returns_500`
- **嚴重度**：**P2**（死碼會誤導後續 refactor，且掩蓋 `:250` 的錯誤分類問題）
- **風險**：**低** — 刪除不可達分支。建議先跑 `uv run pytest --cov` 確認該行 coverage 為 0 再刪。

---

### B-7. `_legacy_detail_scan`（46 行）在 production 佈線下不可達，只有 `InMemorySessionStore` 測試打得到

- **位置**：`src/kai_mind/web/routes/detail_scan_routes.py:58-71`（進入條件）、`:163-208`（函式本體）

- **現況**

```python
# detail_scan_routes.py:58-71
build_result = store.build_result(payload.project_id)
if (
    payload.build_id is None
    and build_result is not None
    and build_result.lineage is None          # ← 關鍵條件
):
    return _legacy_detail_scan(...)
```

  但 production 用的是 `PersistentSessionStore`（`web/app.py:233-237`），它的 `build_result()`（`web/session_store.py:216-228`）一定走 `self._manifest_service.load(manifest)`，而 `BuildManifestService.load` 在 `src/kai_mind/core/services/build_manifest_service.py:179` 無條件設 `lineage=manifest.lineage`（`MapBuildManifest.lineage` 非 Optional）。
  → **`build_result.lineage` 在 production 永遠不是 `None`**，legacy 分支不可達。

  唯一打得到的入口：`tests/web/test_detail_scan_routes.py:73-94`

```python
store = InMemorySessionStore()
store.save_build_result(
    MapBuildResult(status="ok", project_name=..., ai_system_map=base_map()),   # lineage 預設 None
    project_id=project.project_id,
)
return TestClient(create_app(session_store=store)), ...
```

  此外 `_legacy_detail_scan:201` 呼叫 `store.save_build_result(updated, project_id=payload.project_id)`，但 `PersistentSessionStore.save_build_result`（`web/session_store.py:179-189`）**收下 `project_id` 後完全不使用**——所以就算這條路徑真的被觸發，寫入也不會被 `GET /api/detail-scans/{id}`（`detail_scan_routes.py:131` → `store.build_results()` → `web/session_store.py:230-236` 從 manifest 重載）讀到。

- **為什麼是問題**
  - `_legacy_detail_scan` 內含業務編排（`viewer_service.build_canonical`、`build_result.model_copy(update={...})`、append `detail_scan_results`），全部在 adapter 層 —— 同 B-5 的違規，但這次是為了維持一條不會發生的相容性。
  - `tests/web/test_detail_scan_routes.py` 的兩支測試（`:16`、`:50`）**只驗證了 production 不會走的路徑**，等於 `POST /api/detail-scans` 的主線（`build_service.run`）在 `tests/web/` 沒有直接的 route-level 覆蓋（主線覆蓋在 `tests/web/test_detail_scan_build_binding.py`）。
  - `warnings=["legacy_latest_build_fallback"]`（`:207`）這個字串沒有出現在任何契約文件；`docs/API-GUIDE.md:638` 記載的是 `latest_build_fallback`（無 `legacy_` 前綴），而那是 `build_service.run` 路徑的 warning。兩個近似字串，只有一個被文件化。

- **建議改法**
  1. 確認 `MapBuildResult.lineage is None` 是否真的還可能從任何 `SessionStore` 實作產生。若否 → **刪除 `detail_scan_routes.py:58-71` 與 `:163-208`**，並移除 `DetailScanService`、`ViewerSessionService`、`Path` 三個只為 legacy 存在的 import（`:5`、`:16-19`、`:23`）與對應的兩個 `Depends`（`:42`、`:47-50`）。
  2. 把 `tests/web/test_detail_scan_routes.py` 的兩支測試改用 `PersistentSessionStore` + 真實 build（可複用 `tests/web/test_detail_scan_build_binding.py:45` 的 fixture 手法），變成有意義的 route-level 覆蓋。
  3. 順手修 `web/session_store.py:179-189` 把未使用的 `project_id` 參數處理掉（或明確標注 Persistent 的 per-project 讀取來源是 manifest）。

- **影響面**：`frontend/API_CONTRACT.md:321-336` 明說 detail scan 目前前端渲染的是 sample（`detail_scan_result_sample`），**尚未呼叫 `/api/detail-scans`**；`frontend/src/services/` 沒有 detail-scan client。→ **前端零影響**。
- **相關測試**
  - 修改：`tests/web/test_detail_scan_routes.py::test_detail_scan_route_appends_result_to_project_map`（`:16`）、`::test_detail_scan_route_rejects_invalid_target_without_writing`（`:50`）、helper `create_detail_scan_test_client`（`:73`）
  - 刪除：若 legacy 路徑移除，`InMemorySessionStore` 的 import（`tests/web/test_detail_scan_routes.py:13`）一併移除
  - 不動：`tests/web/test_detail_scan_build_binding.py` 全部 7 支（主線覆蓋）
- **嚴重度**：**P2**（46 行 dead legacy + 測試覆蓋錯位；不是使用者可見缺陷）
- **風險**：**中** — 「不可達」的結論依賴「沒有第三方 `SessionStore` 實作會產生 `lineage=None`」。刪除前應先 grep `SessionStore` 的所有實作（目前只有 `InMemorySessionStore`、`PersistentSessionStore`），並跑一輪完整 e2e。

---

### B-8. Route 內直接 `new` 服務物件 + 內嵌 domain 規則（DI 破口 + 業務邏輯外洩）

- **位置**
  - `src/kai_mind/web/routes/trace_routes.py:59` — `QueryTraceConfigLoader()`
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:74` — `SystemMapIndex.from_map(normalized)`
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:78-82` — `semantic_kind == "repo_component"` 的 domain 規則
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:83-90` — `MappingEvidencePacketBuilder()` + `template_slots()`
  - `src/kai_mind/web/routes/detail_scan_routes.py:187-200` —（legacy 路徑內）`viewer_service.build_canonical` + `model_copy`

- **現況**（三種取得服務的方式並列）

```python
# (a) 標準做法 —— 22 個服務全都這樣拿
service: Annotated[MappingProposalService, Depends(mapping_proposal_service)]

# (b) 直接 new，繞過 DI —— trace_routes.py:59
trace_config = QueryTraceConfigLoader().load_project_config(project.project_path)

# (c) 直接 new + 在 route 裡組 domain 物件 —— mapping_proposal_routes.py:74-90
index = SystemMapIndex.from_map(normalized)
if index.unmapped_by_id(payload.source_unmapped_id) is None:
    raise HTTPException(status_code=404, detail="unmapped_not_found")

confirmed_component_ids = [
    component.component_id
    for component in normalized.components
    if component.metadata.get("semantic_kind") == "repo_component"   # ← domain 規則
]
packet = MappingEvidencePacketBuilder().build(
    project_id=payload.project_id,
    index=index,
    unmapped_id=payload.source_unmapped_id,
    available_slots=sorted(template_slots()),                        # ← rag-core-v1 template 知識
    confirmed_component_ids=confirmed_component_ids,
    user_description=payload.user_description,
)
```

- **為什麼是問題**
  - `"semantic_kind" == "repo_component"` 是 `ai-system-map/v2` 的 metadata 語意規則，屬於 `docs/MODEL-CONTRACT.md` 管轄；把它寫在 HTTP adapter 裡，代表 CLI 或未來任何非 HTTP 入口要重做一次。
  - `template_slots()` 是 `rag-core-v1` legacy template 的知識（`CLAUDE.md`：「`rag-core-v1` 是 legacy template only」）；讓 route 直接引用它，等於在 web 層釘死一個 legacy 依賴。
  - 直接 `new` 導致這些元件在測試中無法替換：`tests/web/test_trace_routes.py::test_trace_route_uses_project_pyproject_chunk_keys`（`:133`）只能靠在 tmp 目錄寫真的 `pyproject.toml` 來測 —— 而 malformed config（B-2 那條）根本沒有測試，因為沒有注入點。
  - 違反 `CLAUDE.md` 分層宣告與 `tests/web/test_viewer_routes.py:59` 已建立的 thin-adapter 標準。

- **建議改法**
  1. `MappingProposalService.create_proposal` 改成接受 `(project_id, system_map, unmapped_id, user_description)`，把 `SystemMapIndex` 建構、`repo_component` 篩選、`template_slots()`、`MappingEvidencePacketBuilder` 全部收進 service：

```python
class MappingProposalService:
    def propose_for_unmapped(
        self,
        *,
        project_id: str,
        system_map: AiSystemMapV2,
        unmapped_id: str,
        user_description: str | None,
    ) -> MappingProposal:
        """Raises UnmappedNotFoundError when unmapped_id is absent."""
```
    route 縮到 12 行：查 project → 查 map → 呼叫 → map 錯誤。
  2. `QueryTraceConfigLoader` 加進 `AppServices`（Plan 1 的容器）並在 `dependencies.py` 開一個 `query_trace_config_loader(request)`。**注意：這是 Plan 1 之外的新增欄位，屬本 plan 範圍。**
  3. 把 `tests/web/test_viewer_routes.py:59` 的 `inspect.getsource` 檢查參數化到 9 個 route 模組，禁止 `Builder(` / `Loader(` / `Index.from_` 這類直接建構。

- **影響面**：純內部重構，`POST /api/mapping-proposals`、`POST /api/trace` 的 request/response 不變。`frontend/src/types.ts:330` 只註記「shapes already match the real /api/mapping-proposals contract」，實際沒有 client 程式碼呼叫它（`grep` 全 `frontend/src` 只有註解提到）。→ **前端零影響**。
- **相關測試**
  - 修改：`tests/web/test_mapping_proposal_routes.py::test_proposal_routes_create_and_list_pending_proposal`（`:77`）、`::test_proposal_create_uses_requested_project_build_result`（`:115`）、`::test_proposal_route_falls_back_when_provider_is_unavailable`（`:288`）
  - 新增：`tests/unit/core/services/test_mapping_proposal_service.py` 針對 `repo_component` 篩選與 `unmapped_not_found` 的直接測試
  - 新增：`tests/web/test_trace_routes.py::test_trace_invalid_config_returns_stable_code`（需要 loader 可注入才寫得出來，與 B-2 合併做）
- **嚴重度**：**P2**（架構原則違反，但目前無使用者可見缺陷）
- **風險**：**低-中** — `MappingProposalService` 的簽名變更會影響 `mapping_proposal_service` 的所有呼叫端（僅 1 個 route + 測試）。

---

### B-9. project 存在性檢查政策不一致：兩個 endpoint 對不存在的 project 回 200 + 空陣列

- **位置**
  - **有檢查**：`src/kai_mind/web/routes/project_routes.py:26-28`、`src/kai_mind/web/routes/detail_scan_routes.py:54-56`、`src/kai_mind/web/routes/map_build_routes.py:118-119`、`src/kai_mind/web/routes/mapping_proposal_routes.py:68-69`、`src/kai_mind/web/routes/trace_routes.py:38-40`、`src/kai_mind/web/routes/scan_routes.py:96-101`、`:161-166`
  - **沒檢查**：`src/kai_mind/web/routes/mapping_routes.py:25-36`（`GET /api/mappings`）、`src/kai_mind/web/routes/mapping_proposal_routes.py:41-52`（`GET /api/mapping-proposals`）

- **現況**

```python
# map_build_routes.py:113-126 —— list 類，有檢查
def list_builds(project_id: str, service: ..., store: ...) -> MapBuildHistoryResponse:
    if store.project(project_id) is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return MapBuildHistoryResponse(project_id=project_id, builds=[...])

# mapping_routes.py:25-36 —— 同樣是 list 類，沒檢查
def list_mappings(project_id: str, service: ...) -> ManualMappingListResponse:
    return ManualMappingListResponse(
        project_id=project_id,                      # ← 原樣回傳未驗證的 id
        mappings=service.list_for_project(project_id),   # ← 不存在時回 []
    )

# mapping_proposal_routes.py:41-52 —— 同上，沒檢查
```

  更奇怪的是同一個檔內就不一致：`mapping_proposal_routes.py` 的 `POST`（`:68-69`）檢查了，`GET`（`:41-52`）沒檢查。

- **為什麼是問題**
  - `GET /api/mappings?project_id=typo` 回 `200 {"project_id":"typo","mappings":[],"available_actions":[...]}`，前端無法分辨「這個 project 沒有 mapping」與「這個 project 根本不存在」。
  - `docs/API-GUIDE.md:985` 把 `project_not_found` 列為 404 的標準 detail，隱含「project 不存在就該 404」。
  - `mapping_routes.py:34` 把未驗證的 `project_id` 直接回填進 response，是一種弱 echo。

- **建議改法**：抽一個 dependency，讓「project 必須存在」變成宣告式：

```python
# web/dependencies.py
def required_project(
    project_id: str,
    store: Annotated[SessionStore, Depends(session_store)],
) -> ProjectRecord:
    record = store.project(project_id)
    if record is None:
        raise api_error(404, "project_not_found")
    return record
```

  route 變成 `project: Annotated[ProjectRecord, Depends(required_project)]`，同時消掉 7 處重複的 404 組裝（見 B-13）。對 path param 版本可用 `Depends` 直接吃 `project_id`；query param 版本（B-10 若一併改成 path param）自然統一。

- **影響面**：`GET /api/mappings` 與 `GET /api/mapping-proposals` 從 200 變 404 是**行為變更**。實查前端：`frontend/src/services/` 三個檔（`viewerApi.ts`、`projectScanApi.ts`、`scanTemplateApi.ts`）**沒有任何一處呼叫 `/api/mappings` 或 `/api/mapping-proposals`**（`grep -rn "api/mapping" frontend/src` 只命中註解：`frontend/src/types.ts:330`、`frontend/src/components/proposal/ProposalModal.tsx:7`、`frontend/src/data/scanTemplate.mock.ts:9`）。→ **前端零影響**。要更新 `docs/API-GUIDE.md:794`（`GET /api/mappings`）與 `:887`（`GET /api/mapping-proposals`）的錯誤表，補 `project_not_found | 404`。
- **相關測試**
  - 修改：`tests/web/test_mapping_routes.py::test_mapping_routes_create_and_list_confirmed_mapping`（`:10`）——若測試中用了未 import 的 project_id 會開始 404
  - 修改：`tests/web/test_mapping_proposal_routes.py::test_proposal_routes_create_and_list_pending_proposal`（`:77`）
  - 新增：`tests/web/test_mapping_routes.py::test_list_mappings_unknown_project_returns_404`、`tests/web/test_mapping_proposal_routes.py::test_list_proposals_unknown_project_returns_404`
- **嚴重度**：**P2**
- **風險**：**低** — 前端無依賴，測試改動小。

---

### B-10. project-scoped 資源定址三種寫法，且散落在 3 個 router 檔

- **位置**
  - path param 巢狀：`map_build_routes.py:94`（`/api/projects/{project_id}/map-builds/latest`）、`map_build_routes.py:109`（`/api/projects/{project_id}/map-builds`）、`scan_routes.py:79-80`（`/api/projects/{project_id}/scan-preflights`）、`project_routes.py:21`（`/api/projects/{project_id}`）
  - query param：`mapping_routes.py:24-25`（`GET /api/mappings?project_id=`）、`mapping_proposal_routes.py:37-42`（`GET /api/mapping-proposals?project_id=`）
  - body 欄位：`scan_routes.py:132`（`ScanCreateRequest.project_id`）、`detail_scan_routes.py:41`、`trace_routes.py:29`、`mapping_proposal_routes.py:60`

- **現況**

```python
# (a) path param
@router.get("/api/projects/{project_id}/map-builds", response_model=MapBuildHistoryResponse)
def list_builds(project_id: str, ...)

# (b) query param（沒有 Query() 標註，靠型別推斷）
@router.get("/api/mappings", response_model=ManualMappingListResponse)
def list_mappings(project_id: str, ...)

# (c) body 欄位
@router.post("/api/scans", response_model=ScanCreateResponse)
def create_scan(payload: ScanCreateRequest, ...)     # payload.project_id
```

  同時 router 檔的切分是按「被建立的資源」而非 URL 前綴，導致 `/api/projects/...` 這個前綴橫跨 `project_routes.py`、`scan_routes.py`、`map_build_routes.py` 三個檔，而 `scan_routes.py:79` 的 `/api/projects/{project_id}/scan-preflights` 被打上 `tags=["scans"]`（`scan_routes.py:70`），在 `/docs` 裡跟 `projects` 分組是分開的。

- **為什麼是問題**
  - (c) 對 POST 是合理的；(a) 與 (b) 對同樣是 list 語意的 GET 卻分歧，客戶端要記兩套規則。
  - 這種散落是 **B-11（無 `prefix=`）無法簡單修好的直接原因**：想加 `prefix="/api/projects"` 就得先把 route 依 URL 重新分檔。
  - `docs/API-GUIDE.md:50-70` 的 endpoint 總覽把它們分成 `project` / `build` 兩種「流程」，但這個分類與 router 檔、與 URL 形狀都對不上。

- **建議改法**（分兩步，第二步可延後）
  1. **先統一 GET 的定址**：`GET /api/mappings?project_id=` → `GET /api/projects/{project_id}/mappings`；`GET /api/mapping-proposals?project_id=` → `GET /api/projects/{project_id}/mapping-proposals`。理由：這兩個資源本來就是 project-scoped（`service.list_for_project(project_id)`），path param 讓 `required_project` dependency（B-9）能直接套用，也讓 404 語意自然。
  2. **再重切 router 檔**：`project_routes.py` 收下所有 `/api/projects/**`，其餘各檔用 `APIRouter(prefix="/api/<resource>")`。
  3. POST 的 body `project_id` 保持不變（RESTful 上 `POST /api/scans` + body 是可接受的，且動它會破前端）。

- **影響面**：**`GET /api/mappings` / `GET /api/mapping-proposals` 改路徑是 breaking change**，但如 B-9 所查，`frontend/src/` 沒有任何呼叫端 → **前端零影響**。`frontend/API_CONTRACT.md` 完全沒提這兩個 endpoint，不用改。
  **但 trace 腳本有依賴，必須一併改**（已實查）：`scripts/trace_mappings_list.sh:2`、`:19`、`:58`、`:60`（`api_call GET "/api/mappings?project_id=$ENCODED_ID"`）、`scripts/trace_mapping_proposals_list.sh:2`、`:19`、`:61`、`:63`。POST 路徑（`scripts/lib/api_trace_common.sh:247`、`:267`）不受影響。
  文件需同步改 `docs/API-GUIDE.md:63-64`（總覽表）、`:794`、`:887`（endpoint 章節）。
- **相關測試**
  - 修改：`tests/web/test_mapping_routes.py`（`:10`、`:71`、`:93` 三支會用到 `GET /api/mappings`）
  - 修改：`tests/web/test_mapping_proposal_routes.py::test_proposal_routes_create_and_list_pending_proposal`（`:77`）
  - 新增：`tests/contracts/` 下一支「所有 project-scoped GET 都用 path param」的結構測試
- **嚴重度**：**P2**
- **風險**：**中** — 是公開 URL 變更。消費者已完整盤點：前端 0 處、trace 腳本 2 支（上列）、測試 4 支。本機 API 無外部消費者，建議直接改而非保留 deprecated 別名。

---

### B-11. 9 個 `APIRouter` 全部沒有 `prefix=`，`/api` 硬寫 23 次；tag 命名單複數混用

- **位置**：`detail_scan_routes.py:36`、`map_build_routes.py:35`、`map_routes.py:19`、`mapping_proposal_routes.py:34`、`mapping_routes.py:21`、`project_routes.py:18`、`scan_routes.py:70`、`trace_routes.py:24`、`viewer_routes.py:16`

- **現況**（9 個全長一樣）

```python
router = APIRouter(tags=["scans"])            # scan_routes.py:70
router = APIRouter(tags=["map"])              # map_routes.py:19
router = APIRouter(tags=["detail-scans"])     # detail_scan_routes.py:36
```

  然後每條 path 各自帶 `/api`：

```python
@router.post("/api/projects/{project_id}/scan-preflights", ...)
@router.post("/api/scans", ...)
@router.get("/api/scan/events", ...)
```

  唯一例外：`map_routes.py:75` 的 `@router.get("/map", ...)` 沒有 `/api`（legacy fallback）。

  tag 值：複數 `scans` / `detail-scans` / `map-builds` / `mapping-proposals` / `mappings` / `projects`；單數 `map` / `trace` / `viewer`。

- **為什麼是問題**
  - `/api` 重複 23 次，改 base path 要動 23 個地方。
  - tag 是 `/docs`（`docs/API-GUIDE.md:14` 指定的官方介面）的分組依據，單複數混用讓側欄看起來像兩套命名法。
  - `scan_routes.py:79` 的 preflight 掛在 `scans` tag 下，但 URL 在 `/api/projects/**`（見 B-10）。

- **建議改法**
  1. 每個 router 改成 `APIRouter(prefix="/api", tags=["..."])`，path 去掉 `/api`。`map_routes.py:75` 的 `/map` 需要一個獨立的 `legacy_router = APIRouter(tags=["map"])`（無 prefix）或在 `app.py:244` 用 `include_router(map_routes.legacy_router)`。
  2. 進一步（配合 B-10 重切檔）可用 `prefix="/api/mappings"` 這種資源級 prefix。
  3. tag 一律用複數 kebab-case 資源名：`map` → `maps`（或 `viewer-map`）、`trace` → `traces`、`viewer` → `viewer-sessions`。
  4. 建議在 `app.py` 統一：`app.include_router(r, prefix="/api")`，讓 route 檔完全不知道 base path —— 這是最徹底的作法，但 `/map` 例外要另外處理。

- **影響面**：**URL 完全不變**（prefix + path 拼起來一樣）→ 前端零影響。tag 改名只影響 `/docs` 顯示與 OpenAPI `tags`，`frontend/` 不消費 OpenAPI（無 codegen，`frontend/src/types.ts` 是手寫 zod）。
- **相關測試**：無測試斷言 router prefix 或 tag。若改 tag，`tests/` 全域 grep `tags=` 無命中 → **不用改任何測試**。
- **嚴重度**：**P3**
- **風險**：**低** — 純機械式；改完用 §0 的 route 列舉腳本 diff 一次即可驗證 URL 集合不變。

---

### B-12. 零個 route 宣告 `responses={}`，OpenAPI 完全沒有錯誤碼；`/api/map/report` 的 content-type 在 OpenAPI 是錯的

- **位置**：全 9 檔（`grep -c "responses=" src/kai_mind/web/routes/*.py` → `0`）；`map_routes.py:45-72`

- **現況**（實跑 `app.openapi()` 的結果）

```
POST   /api/map/build                        codes=['200','422']
GET    /api/map/report                       codes=['200','422']  200content=['application/json']
POST   /api/map-builds/{base_build_id}/apply codes=['200','422']
POST   /api/detail-scans                     codes=['200','422']
POST   /api/scans                            codes=['200','422']
GET    /api/scan/events                      codes=['200']        200content=['text/event-stream']
```

  對照 `docs/API-GUIDE.md:980-990` 記載的實際狀態碼：`404` / `409` / `413` / `422` / `500` / `503`（外加 `trace` 的 `400`）—— **一個都沒進 OpenAPI**。那個 `422` 還只是 FastAPI 為 request validation 自動補的，不是文件裡那些業務 422。

  `/api/map/report` 的 handler：

```python
@router.get("/api/map/report")                 # map_routes.py:45 —— 沒有 response_class
def get_map_report(...) -> Response:
    ...
    return Response(
        content=result.map_markdown_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",     # ← 實際
        headers=headers,
    )
```

  `docs/API-GUIDE.md:625` 寫「Response `200`：`Content-Type: text/markdown; charset=utf-8`」，但 OpenAPI 說 `application/json`。對照組：`scan_routes.py:354` 有正確宣告 `response_class=EventSourceResponse`，OpenAPI 就對了（`text/event-stream`）。

- **為什麼是問題**
  - `docs/API-GUIDE.md:14` 把 `http://127.0.0.1:8000/docs` 列為官方介面之一；目前它對錯誤處理完全沉默，讀 `/docs` 的人會以為這些 endpoint 不會失敗。
  - 沒有 `responses={}` 就沒有機制強制「route 實際 raise 的 status code」與「文件記載的」一致 —— B-16 那些未文件化的 code（`detail_build_incomplete`、`project_build_mismatch`）就是這樣漏出來的。

- **建議改法**
  1. 定義共用常數，避免 23 條 route 各寫一份：

```python
# web/openapi_responses.py
ERROR_RESPONSE: Final = {"model": ApiErrorResponse}
NOT_FOUND: Final = {404: {**ERROR_RESPONSE, "description": "project_not_found | build_not_found | map_not_loaded"}}
CONFLICT: Final = {409: {**ERROR_RESPONSE, "description": "base_build_not_latest | scan_snapshot_stale"}}
UNPROCESSABLE: Final = {422: ERROR_RESPONSE}
BUSY: Final = {503: ERROR_RESPONSE}
```
     route 寫 `@router.post(..., responses={**NOT_FOUND, **CONFLICT, **UNPROCESSABLE})`。
  2. `map_routes.py:45` 補 `response_class=Response` 與 `responses={200: {"content": {"text/markdown": {}}}}`。
  3. 新增 contract 測試：把 `docs/API-GUIDE.md:982-990` 的表格解析出來，與 `app.openapi()` 的 `responses` 交叉比對。

- **影響面**：純 metadata，wire format 不變 → 前端零影響。`frontend/` 沒有 OpenAPI codegen（`frontend/src/types.ts` 是手寫 zod schema）。
- **相關測試**
  - 新增：`tests/contracts/test_openapi_error_responses.py`（斷言每條 route 至少宣告了它會 raise 的 status code）
  - 新增：`tests/web/test_map_routes.py::test_map_report_openapi_declares_markdown`
  - 不動：`tests/web/test_map_routes.py::test_map_report_route_returns_latest_markdown_report`（`:36`）已驗證實際 content-type
- **嚴重度**：**P2**（`/docs` 是文件明列的介面，目前對錯誤處理誤導）
- **風險**：**低**

---

### B-13. 跨檔重複：`project_not_found` × 7、`build_not_found` × 5、`map_not_loaded` × 4 的 404 組裝

- **位置**
  - `project_not_found`（7）：`project_routes.py:28`、`detail_scan_routes.py:56`、`map_build_routes.py:119`、`mapping_proposal_routes.py:69`、`trace_routes.py:40`、`scan_routes.py:98-101`、`scan_routes.py:163-166`
  - `build_not_found`（5）：`detail_scan_routes.py:83`、`map_build_routes.py:90`、`map_build_routes.py:105`、`trace_routes.py:49`、`trace_routes.py:56`
  - `map_not_loaded`（4）：`detail_scan_routes.py:141`、`detail_scan_routes.py:173`、`mapping_proposal_routes.py:72`、`trace_routes.py:51`
  - build_id 解析重複：`trace_routes.py:42-56` vs `map_build_routes.py:87-91` vs `detail_scan_routes.py:82-83`

- **現況**（同一件事的三種寫法）

```python
# map_build_routes.py:87-91 —— service.get + KeyError
try:
    result = service.get(build_id)
except KeyError as exc:
    raise HTTPException(status_code=404, detail="build_not_found") from exc

# trace_routes.py:42-56 —— 同樣的事 + 額外的 project 歸屬檢查
try:
    build_result = (
        build_query.get(payload.build_id)
        if payload.build_id is not None
        else store.build_result(payload.project_id)
    )
except KeyError as exc:
    raise HTTPException(status_code=404, detail="build_not_found") from exc
if build_result is None or build_result.ai_system_map is None:
    raise HTTPException(status_code=404, detail="map_not_loaded")
if (build_result.lineage is not None
        and build_result.lineage.project_id != payload.project_id):
    raise HTTPException(status_code=404, detail="build_not_found")   # ← 跨 project 也回 build_not_found

# detail_scan_routes.py:82-83 —— 同樣的 KeyError，但走 build_service.run
except KeyError as exc:
    raise HTTPException(status_code=404, detail="build_not_found") from exc
```

  注意 `trace_routes.py:52-56` 的「build 屬於別的 project」檢查，`map_build_routes.py:83-91`（`GET /api/map-builds/{build_id}`）**沒有做** —— 也就是 `GET /api/map-builds/{build_id}` 可以讀到任意 project 的 build。這在 local-only single-user API 下不是漏洞，但兩條 route 對同一件事的政策不一致。而 `detail_scan_routes` 走的是 core 的 `project_build_mismatch`（`tests/web/test_detail_scan_build_binding.py:206`），第三種政策。

- **為什麼是問題**
  - 三種 build 解析政策（不檢查 / route 內檢查回 `build_not_found` / core 檢查回 `project_build_mismatch`），錯誤語意對客戶端不一致。
  - 16 處重複的 404 組裝讓 B-1 的格式統一工作變成 16 次機械修改。

- **建議改法**
  1. 抽 dependency（同 B-9）：

```python
# web/dependencies.py
def required_project(project_id: str, store: ...) -> ProjectRecord: ...
def required_build(
    build_id: str,
    project: Annotated[ProjectRecord, Depends(required_project)],
    query: Annotated[MapBuildQueryService, Depends(map_build_query_service)],
) -> MapBuildResult:
    """404 build_not_found；跨 project 一律 404 project_build_mismatch。"""
```
  2. 統一跨 project 政策：一律用 core 已有的 `project_build_mismatch`（`tests/web/test_detail_scan_build_binding.py:206` 已鎖住），把 `trace_routes.py:56` 從 `build_not_found` 改過去，並補進 `docs/API-GUIDE.md:781-786` 的 trace 錯誤表。
  3. `map_not_loaded` 的判斷（`build_result is None or build_result.ai_system_map is None`）也收進 dependency。

- **影響面**：`trace_routes.py:56` 從 `build_not_found` → `project_build_mismatch` 是 detail 字串變更。前端：`frontend/API_CONTRACT.md:311-319` 明說 query replay 尚未呼叫 `/api/trace`，`frontend/src/services/` 無 trace client → **零影響**。需更新 `docs/API-GUIDE.md:781-786`。
- **相關測試**
  - 修改：`tests/web/test_trace_build_binding.py::test_query_trace_rejects_unknown_requested_build`（`:36`、斷言在 `:51`）
  - 修改：`tests/web/test_trace_routes.py::test_trace_route_requires_loaded_project_map`（`:167`，斷言在 `:193`、`:195`）
  - 新增：`tests/web/test_map_build_apply_routes.py::test_get_build_rejects_cross_project_build_id`（補上目前缺的檢查）
  - 新增：`tests/web/` 下 `required_project` / `required_build` dependency 的單元測試
- **嚴重度**：**P2**
- **風險**：**低-中** — 補上 `GET /api/map-builds/{build_id}` 的跨 project 檢查是行為變更（從 200 變 404），需確認 `tests/web/test_map_build_apply_routes.py::test_apply_route_creates_build_and_read_routes`（`:71`）不依賴跨 project 讀取。

---

### B-14. `f"build:{uuid4()}"` 的 ID 慣例在 web 層重複實作

- **位置**：`src/kai_mind/web/routes/scan_routes.py:284`；core 既有三處 `src/kai_mind/core/services/map_build_service.py:213`、`:253`、`:293`；另有 `core/services/scan_snapshot_service.py:50`（`scan_id_factory`）、`core/services/apply_confirmations_service.py:97`（`self._build_id_factory()`）

- **現況**

```python
# scan_routes.py:284-285 —— web 層自己造 build_id
build_id = f"build:{uuid4()}"
output_dir = Path(payload.output) / build_id.replace(":", "_")
```

```python
# core/services/map_build_service.py:253 —— core 的版本
active_build_id = build_id or f"build:{uuid4()}"
```

```python
# core/services/apply_confirmations_service.py:97 —— 正確做法：注入 factory
build_id = self._build_id_factory()
```

```python
# core/services/scan_snapshot_service.py:50 —— 正確做法
self._scan_id_factory = scan_id_factory or (lambda: f"scan:{uuid4()}")
```

- **為什麼是問題**
  - `docs/MODEL-CONTRACT.md` 把 `scan_id` / `build_id` 定義成核心身分契約（`CLAUDE.md`：「Identity = `scan_id`（immutable snapshot）+ `build_id`（one materialization）」）。ID 的字面格式屬於 core 的 model 契約，web adapter 不該複製。
  - `build_id.replace(":", "_")`（`:285`）也是一段跨平台檔名轉換規則（`CLAUDE.md`：「Cross-platform (macOS/Windows) compatibility matters」），同樣落在 web 層；core 的 `BuildCommitService`（`core/services/build_commit_service.py:88`）自己也在算 `final_dir` / `staging_dir`。兩層各自處理路徑命名。
  - 不可注入 → 測試無法產生確定性 build_id（對照 `ApplyConfirmationsService` 有 `_build_id_factory`，可注入）。

- **建議改法**
  1. 在 core 開一個單一來源：`core/models/identifiers.py` 的 `new_build_id() -> str` / `new_scan_id() -> str` / `build_id_to_dirname(build_id) -> str`，四處呼叫端全改用它。
  2. `scan_routes.py:284-285` 的兩行連同整段編排一起搬進 B-5 的 `ScanOrchestrationService`（這樣這條就會被 B-5 順帶解掉）。
  3. 新增 contract 測試：`tests/contracts/` 斷言 repo 內只有一個地方產生 `build:` / `scan:` 前綴。

- **影響面**：ID 格式不變 → 前端零影響（`frontend/src/types.ts:211` 只要求 `scan_id: z.string()`）。
- **相關測試**
  - 新增：`tests/contracts/test_identifier_single_source.py`
  - 不動：現有測試不依賴 ID 產生位置
- **嚴重度**：**P2**（契約規則複製，屬 `CLAUDE.md` 明列的 P1 review 焦點「core engine platform-independent」的邊緣案例）
- **風險**：**低**

---

### B-15. `response_model` 兩種流派：core domain model 直出 vs web schema 投影

- **位置**
  - **core model 直出**（7 條）：`map_routes.py:22`（`MapBuildResult`）、`map_routes.py:37`、`map_routes.py:75`、`viewer_routes.py:19`（`ViewerPayload`）、`mapping_routes.py:39`、`:58`（`ManualMapping`）、`mapping_proposal_routes.py:55`（`MappingProposal`）、`:97`（`MappingProposalDecisionResult`）、`trace_routes.py:27`（`TraceRunResult`）
  - **web schema 投影**：`map_build_routes.py:38`、`:79`、`:94`、`:109`、`detail_scan_routes.py:39`、`:127`、`scan_routes.py:79`、`:127`、`project_routes.py:21`、`:36`、`mapping_routes.py:24`、`mapping_proposal_routes.py:37`

- **現況**（同一份資料，兩種對外形狀）

```python
# map_routes.py:22 —— 直接把 core model 當 HTTP 契約
@router.post("/api/map/build", response_model=MapBuildResult)
def build_map(...) -> MapBuildResult:
    result = service.build(payload.to_core_request())
    store.save_build_result(result)
    return result
```

```python
# map_build_routes.py:79 —— 同樣的 MapBuildResult，但投影成 Phase2MapBuildResult
@router.get("/api/map-builds/{build_id}", response_model=MapBuildScopedResponse)
def get_build(...) -> MapBuildScopedResponse:
    return MapBuildScopedResponse.from_core(result)   # schemas.py:146-163
```

  `MapBuildResult`（`core/models/map_build.py:70-97`）有 **11 個 `Path` 欄位**（`output_run_dir`、`map_json_path`、`map_markdown_path`、`map_error_path`、`profile_signals_path`、`readiness_report_path`、`call_graph_path`、`dataflow_hints_path`、`execution_paths_path`、`evidence_table_path`、`system_map_mermaid_path`、`execution_map_mermaid_path`）。走 `Phase2MapBuildResult`（`schemas.py:92-123`）的路徑**全部濾掉**，走 `MapBuildResult` 直出的路徑**全部輸出**。

  而 `ScanCreateResponse.build_result`（`schemas.py:243`）的型別是 `MapBuildResult | None` —— 所以 `POST /api/scans` 的 completed 回應**也是原始 `MapBuildResult`**，帶著 11 個絕對路徑。

- **為什麼是問題**
  - 兩種流派意味著「HTTP 契約」沒有一個明確的邊界層：core model 一改欄位，7 條 route 的 wire format 立刻跟著變，且 `web/schemas.py:43-46` 的 `WebSchema(extra="forbid")` 保護（「Base schema that rejects silent API contract drift」）對它們不適用。
  - `Phase2MapBuildResult` 存在本身就證明團隊認為 `MapBuildResult` 不適合直接對外（它顯式挑了 11 個欄位、加了 `profile_signals_available` / `readiness_report_available` 兩個衍生 flag），但這個判斷只套用在一半的 route。
  - 絕對路徑輸出：`docs/API-GUIDE.md:344-372` 確實把這些 path 欄位記載為 `POST /api/map/build` 的回應內容，所以**不是未文件化的洩漏**；但它與 `tests/web/test_scan_boundary_routes.py:106` 的 `assert str(tmp_path) not in str(pending)` 精神相反 —— 同一個 `/api/scans` 的 boundary 回應禁止絕對路徑，completed 回應卻夾帶 11 個。

- **建議改法**
  1. 定調：**所有 route 的 `response_model` 一律是 `web/schemas.py` 的 `WebSchema` 子類**，core model 只能出現在 `WebSchema` 的欄位內部且必須是刻意選擇的。
  2. 為目前直出的 7 條各補一個投影：`MapBuildResponse`（複用 `Phase2MapBuildResult`）、`ManualMappingResponse`、`MappingProposalResponse`、`TraceRunResponse`、`ViewerPayloadResponse`。
  3. `ScanCreateResponse.build_result` 從 `MapBuildResult` 改成 `Phase2MapBuildResult`（與 `MapBuildScopedResponse` 一致）。
  4. 加一支 contract 測試：斷言每條 route 的 `response_model` 都是 `WebSchema` 的子類。

- **影響面**：**這是 breaking change，必須明講。**
  - `POST /api/scans` 的 `build_result` 從完整 `MapBuildResult` 縮成 `Phase2MapBuildResult` → 前端 `frontend/src/types.ts:214` 是 `build_result: z.record(z.unknown()).nullable().optional()`（完全鬆散，不驗證內容），且 `frontend/API_CONTRACT.md:188` 寫 `build_result?: unknown`。**已實查**：`grep -rn "build_result" frontend/src` 全 repo **只有 `frontend/src/types.ts:214` 這一行**，沒有任何 component 讀它的內部欄位 → **zod 不會壞、UI 也不會壞**。
  - `POST /api/map/build`：`frontend/API_CONTRACT.md:61` 明說「It does not call `/api/map/build` for this interactive flow」，`frontend/src/services/` 也沒有呼叫端 → 零影響。
  - `docs/API-GUIDE.md:344-372`（`MapBuildResult` 回應形狀）與 `:246-254`（`/api/scans` 回應）都要改。
- **相關測試**
  - 修改：`tests/web/test_map_routes.py::test_map_build_route_updates_api_map_payload`（`:11`）、`::test_map_build_route_rejects_public_v1_selection`（`:89`）
  - 修改：`tests/web/test_project_scan_routes.py::test_scan_create_builds_imported_project`（`:63`）
  - 修改：`tests/web/test_mapping_routes.py`（`:10`、`:93`）、`tests/web/test_mapping_proposal_routes.py`（`:144`、`:181`、`:218`）
  - 新增：`tests/contracts/test_response_models_are_web_schemas.py`
  - 新增：`tests/web/test_project_scan_routes.py::test_completed_scan_response_has_no_absolute_paths`
- **嚴重度**：**P2**（架構一致性 + 潛在路徑輸出；不是立即缺陷因為已文件化）
- **風險**：**中** — 觸及 7 條 route 的 wire format。前端消費面已盤點完畢（只有一個鬆散的 `z.record(z.unknown())`），實際風險集中在 8 支後端測試的斷言更新，不在前端。建議仍分兩步：先加 contract 測試 + 補投影 model，再切換 `ScanCreateResponse.build_result`。

---

### B-16. 三個未文件化 / 不一致的字串：`detail_build_incomplete`、`project_build_mismatch`、`legacy_latest_build_fallback`

- **位置**
  - `src/kai_mind/web/routes/detail_scan_routes.py:106` — `raise HTTPException(status_code=500, detail="detail_build_incomplete")`
  - `src/kai_mind/web/routes/detail_scan_routes.py:89-97` — `project_build_mismatch` 由 `str(exc)` 產生（測試斷言在 `tests/web/test_detail_scan_build_binding.py:206`）
  - `src/kai_mind/web/routes/detail_scan_routes.py:207` — `warnings=["legacy_latest_build_fallback"]`

- **現況**

```python
# detail_scan_routes.py:104-106
child = result.build_result
if child.ai_system_map is None or child.viewer_load_result is None:
    raise HTTPException(status_code=500, detail="detail_build_incomplete")
```

  但 `docs/API-GUIDE.md:989` 對 500 的規定是：

```
| 500 | 未預期後端錯誤，回應會遮蔽 raw path / secret | `internal_server_error` |
```

  `docs/API-GUIDE.md:677-684` 的 detail-scan 錯誤表列出 5 個 code，**沒有 `detail_build_incomplete`、也沒有 `project_build_mismatch`**。

  warning 字串：`detail_scan_routes.py:207` 是 `legacy_latest_build_fallback`，`docs/API-GUIDE.md:638` 記載的是 `latest_build_fallback`（`trace_routes.py:78` 用的正是後者）。兩個相近字串，只有一個進了文件。

- **為什麼是問題**
  - 500 帶自訂 detail 打破了「500 一律 `internal_server_error`」的約定 —— 這個約定是有理由的：`web/middleware.py:105-121` 的 `SafeUnhandledExceptionMiddleware` 就是靠它保證 500 不洩漏內部狀態。route 自己 raise 的 500 繞過了那層保護（雖然這個特定字串無害）。
  - `detail_build_incomplete` 語意上是「core 回了不完整的結果」→ 這是 internal invariant 違反，應該讓它冒泡到 middleware（同 B-6 的 `:250`）。
  - warning 字串不一致讓前端無法用單一常數判斷「這是 latest fallback」。

- **建議改法**
  1. `detail_scan_routes.py:104-106` 改成 raise 一個 core 的內部錯誤（例如 `DetailScanBuildError("detail_build_incomplete")` 由 `DetailScanBuildService` 自己檢查並拋），讓 route 不需要做完整性判斷；或至少讓它冒泡到 `SafeUnhandledExceptionMiddleware`。
  2. 補文件：`docs/API-GUIDE.md:677-684` 加入 `project_build_mismatch | 404`。
  3. warning 統一成 `latest_build_fallback`（若 legacy 路徑照 B-7 刪掉，這條自動消失）。

- **影響面**：`frontend/API_CONTRACT.md:321-336` 說 detail scan 目前渲染 sample，未呼叫 API → 前端零影響。
- **相關測試**
  - 修改：`tests/web/test_detail_scan_build_binding.py::test_detail_scan_rejects_build_owned_by_another_project`（`:174`，斷言在 `:206`）
  - 新增：`tests/contracts/` 下一支「route 的 detail code 必須出現在 `docs/API-GUIDE.md`」的測試（與 B-3 共用）
- **嚴重度**：**P3**
- **風險**：**低**

---

### B-17. docstring 與註解風格不一致（module docstring 缺 1、route docstring 缺 6、中英混用）

- **位置**
  - **缺 module docstring**：`src/kai_mind/web/routes/map_build_routes.py:1`（第 1 行直接是 `from __future__ import annotations`）。另外 8 個檔都有（`detail_scan_routes.py:1`、`map_routes.py:1`、`mapping_proposal_routes.py:1`、`mapping_routes.py:1`、`project_routes.py:1`、`scan_routes.py:1`、`trace_routes.py:1`、`viewer_routes.py:1`）
  - **缺 route docstring（6 條）**：`map_build_routes.py:42`（`apply_confirmations`）、`:83`（`get_build`）、`:98`（`get_latest_build`）、`:113`（`list_builds`）、`project_routes.py:22`（`get_project`）、`scan_routes.py:83`（`create_scan_preflight`）
  - **中文 docstring（5 條）**：`scan_routes.py:160`、`scan_routes.py:356`、`map_routes.py:28`、`map_routes.py:41`、`map_routes.py:79`、`project_routes.py:41`
  - **英文 docstring（其餘 12 條）**

- **現況**

```python
# scan_routes.py:160 —— 中文
"""用已匯入的 project_id 執行掃描，並回傳這次掃描的建置結果。"""

# detail_scan_routes.py:53 —— 英文
"""Run a bounded target-scoped detail scan for the loaded project map."""

# map_build_routes.py:42-50 —— 無 docstring
def apply_confirmations(
    base_build_id: str,
    payload: ApplyConfirmationsRequest,
    ...
) -> ApplyConfirmationsResponse:
    try:
```

- **為什麼是問題**
  - FastAPI 把 docstring 當成 OpenAPI 的 `description`（`docs/API-GUIDE.md:14` 把 `/docs` 列為官方介面）。6 條沒有 description，5 條是中文、12 條是英文 → `/docs` 讀起來是三種語言狀態。
  - `CLAUDE.md` 提到 core 的 service 檔「carry structured header comments（責任 / 呼叫鏈）」，routes 層沒有對等規範。
  - 附帶：中文 docstring 的**顯示寬度**超過 79 欄（`scan_routes.py:160` 是 91 bytes / 大量 CJK；ruff 的 E501 按 Unicode code point 計數所以放行，`uv run ruff check src/kai_mind/web/routes/` 是 `All checks passed!`）。這不是 lint 違規，但在 79 欄的編輯器裡會折行，與其他檔的視覺一致性不同。

- **建議改法**
  1. 定調語言（依 repo 現況多數 → 英文），把 5 條中文 docstring 翻成英文；或反過來全中文。**必須二選一並寫進 `CLAUDE.md`。**
  2. 補齊 6 條缺的 docstring，格式統一為一行祈使句（現有英文 docstring 的風格）。
  3. `map_build_routes.py` 補 module docstring：`"""Build-scoped map read and apply-confirmations routes."""`
  4. 可考慮開 ruff 的 `D` rule（`pyproject.toml:69` 目前 `select = ["E","F","I","UP","B"]`）強制 `D100`/`D103`，但這會波及整個 repo，建議另開。

- **影響面**：只影響 `/docs` 的 description 文字，wire format 完全不變 → 前端零影響。
- **相關測試**：無測試斷言 docstring → **不用改任何測試**。
- **嚴重度**：**P3**
- **風險**：**低**

---

### B-18. 隱式 preflight 流程不回傳 `preflight_request_id`，客戶端無法沿用

- **位置**：`src/kai_mind/web/routes/scan_routes.py:174-183`、`:193-201`、`:222-240`、`:243-248`

- **現況**

```python
# :174-183 —— 伺服器端建了一個 preflight
implicit_state = preflight_service.create(payload.project_id, project.project_path, ...)
selection_request_id = implicit_state.preflight_request_id     # ← 有 id
...
# :193-201 —— 但回應不帶它
return ScanCreateResponse(
    project_id=payload.project_id,
    status="requires_boundary_decision",
    boundary_proposals=[...],
    # ← 沒有 preflight_request_id
)

# :222-240 —— stale 重試路徑，同樣建了 refreshed 卻不回傳它的 id
refreshed = preflight_service.create(payload.project_id, project.project_path,
                                     InventoryPreflightRequest())
...
return ScanCreateResponse(..., boundary_proposals=proposals)   # ← 也沒有

# :243-248 —— 只有這條回傳，而且回的是 *client 送來的* id（隱式流程下恆為 None）
return ScanCreateResponse(
    ...,
    preflight_request_id=payload.preflight_request_id,
)
```

- **為什麼是問題**
  - `frontend/API_CONTRACT.md:211` 把 `preflight_request_id?: string` 列在 boundary review response 裡，隱含客戶端可以拿到它；實作在隱式流程下永遠不給。
  - 結果是：client 拿到 proposals 後只能不帶 `preflight_request_id` 再 POST 一次，伺服器 `:174` 又建一個新的 implicit preflight（而且這次 `requested_paths` 只含 decision 的 target path，與第一次的 candidate set 不同）。這條路徑在 `tests/web/test_scan_boundary_routes.py:114-152`（`test_scan_this_run_decision_builds_map_for_current_scan_only`）確實跑得通，但代價是**每次 boundary 決策都重跑一次 preflight 列舉**，而且 stale 檢測（`InventorySelectionErrorCode.PREFLIGHT_STALE`）在隱式流程下形同虛設（因為每次都是新的）。
  - `frontend/API_CONTRACT.md:259` 說「A stale/changed selection uses `{detail:{code,message,retryable,context}}`; refresh preflight rather than silently reusing decisions」—— 隱式流程沒有 id 可 refresh。

- **建議改法**
  三個 boundary 回傳點都帶上伺服器實際使用的 id：

```python
return ScanCreateResponse(
    project_id=payload.project_id,
    status="requires_boundary_decision",
    preflight_request_id=selection_request_id,   # 或 refreshed.preflight_request_id
    boundary_proposals=[...],
)
```

  這是純新增欄位（`exclude_if` 會讓它在有值時才出現），不移除任何東西。搬進 B-5 的 `ScanOrchestrationService` 後，`ScanOutcome.preflight_request_id` 應該是必填欄位，型別上就不會漏。

- **影響面**：純新增欄位。`frontend/src/types.ts:210-217` 的 `scanCreateResponseSchema` 沒有 `preflight_request_id`，zod `z.object` 預設會**忽略**未宣告的多餘欄位（非 `.strict()`）→ **不會壞**。`frontend/API_CONTRACT.md:211` 已經預期它存在，實作補上反而是對齊文件。
- **相關測試**
  - 修改：`tests/web/test_scan_boundary_routes.py::test_scan_requires_boundary_decision_before_building_map`（`:76`）加斷言 `"preflight_request_id" in pending`
  - 修改：`tests/web/test_inventory_preflight_routes.py::test_stale_preflight_scan_returns_409_without_snapshot`（`:242`）
  - 新增：`tests/e2e/test_inventory_selection_scan_flow.py` 加一支「用回傳的 preflight_request_id 提交決策，不觸發第二次列舉」
- **嚴重度**：**P2**（讓 stale 檢測在主流程失效）
- **風險**：**低**（純新增），但要驗證伺服器不會因此把 stale 檢查從「always fresh」變成「真的會 stale」而讓既有測試轉紅 —— `tests/web/test_scan_boundary_routes.py::test_scan_rejects_stale_or_removed_boundary_decisions`（`:189`）需重跑確認。

---

### B-19.（附註）`PersistentSessionStore.save_build_result` 收下 `project_id` 但完全不使用

- **位置**：`src/kai_mind/web/session_store.py:179-189`；呼叫端 `src/kai_mind/web/routes/detail_scan_routes.py:201`、`src/kai_mind/web/routes/map_routes.py:33`、`src/kai_mind/web/session_store.py:53-67`（`save_committed_build_projection`）

- **現況**

```python
# session_store.py:179-189 —— Persistent 版
def save_build_result(
    self,
    result: MapBuildResult,
    *,
    project_id: str | None = None,     # ← 收下
) -> None:
    self._latest_build_result = result
    if result.viewer_load_result is not None:
        self.save_viewer_payload(ViewerPayload(viewer_load_result=result.viewer_load_result))
    # project_id 從頭到尾沒被用到

# session_store.py:104-116 —— InMemory 版，有用
    if project_id is not None:
        self._build_results_by_project[project_id] = result
```

  兩個呼叫慣例也不一致：

```python
map_routes.py:33          store.save_build_result(result)                      # 不給 project_id
detail_scan_routes.py:201 store.save_build_result(updated, project_id=...)     # 給了但無效
```

- **為什麼是問題**：route 傳了參數卻沒有效果，是一個 silent no-op。Persistent 的 per-project 讀取實際來自 manifest/pointer（`session_store.py:216-228`），所以正常流程沒事；但 B-7 的 legacy 路徑就是因此讓寫入消失。這也讓 `SessionStore` protocol（`session_store.py:38-40`）的語意在兩個實作間不同。
- **建議改法**：要嘛 `PersistentSessionStore` 真的用 `project_id` 做 in-process 快取，要嘛把 protocol 的語意寫清楚（「Persistent 的 per-project 讀取由 manifest 決定，`project_id` 僅供 in-memory 實作使用」），並在 `map_routes.py:33` / `detail_scan_routes.py:201` 統一傳法。
- **影響面**：前端零影響。
- **相關測試**：新增 `tests/web/test_session_store_contract.py`，用同一組斷言跑兩個實作。
- **嚴重度**：**P3**
- **風險**：**低**

---

### B-20. async/sync 標準未成文（現況正確但沒有規則）

- **位置**：`src/kai_mind/web/routes/scan_routes.py:355`（唯一的 `async def`）；其餘 22 條全是 `def`

- **現況**（實測 `inspect.iscoroutinefunction` / `isasyncgenfunction`）

```
22 條 def（sync，FastAPI 丟 threadpool）
 1 條 async def：scan_routes.py:355  scan_events  →  AsyncIterator[ServerSentEvent]
```

  另有 `src/kai_mind/web/legacy_mapping_guards.py:28` 的 `async def reject_legacy_mapping_type`（需要 `await request.json()`）。

- **為什麼（目前）不是缺陷**：所有做阻塞 I/O 的 handler 都是 `def` —— `map_routes.py:69` 的 `result.map_markdown_path.read_text(...)`、`scan_routes.py:277` 的 `snapshot_service.scan_and_save(...)`（整個檔案系統掃描）、`trace_routes.py:59` 的 `load_project_config(...)` 全部在 threadpool 執行，**不會卡住 event loop**。`scan_events` 是 async generator 但只 yield 一個常數事件，不做 I/O。所以現況是對的。
- **為什麼還是要記一筆**：這個「對」是巧合而非規則。`CLAUDE.md` 與 `docs/API-GUIDE.md` 都沒有寫「route handler 一律用 `def`，除非需要 async 原生 I/O 或 streaming」。任何人把 `create_scan` 改成 `async def` 求「看起來比較快」，就會讓一次完整 repo 掃描（可能數十秒）卡死整個 event loop —— 而且不會有測試抓到（`TestClient` 是同步的）。
  次要風險：sync route 佔用 Starlette 的 threadpool（預設 40 個 worker）。`create_scan` 長時間持有一個 worker，理論上 40 個並行掃描會讓所有其他 endpoint 排隊。本機單使用者 API 不構成實際問題。
- **建議改法**：在 `CLAUDE.md` 的 Backend Architecture 一節加一句規則，並加一支結構測試：

```python
# tests/contracts/test_route_sync_convention.py
def test_only_streaming_routes_are_async() -> None:
    """Blocking route handlers must stay sync so they run in the threadpool."""
    allowed_async = {"scan_events"}
    for route in create_app().app.routes: ...
```

- **影響面**：無程式碼變更 → 前端零影響。
- **相關測試**：新增 `tests/contracts/test_route_sync_convention.py`
- **嚴重度**：**P3**
- **風險**：**低**

---

## 建議處理順序

| 順序 | 條目 | 理由 |
|------|------|------|
| 1 | B-4（前端 zod）、B-2 | 使用者可見缺陷 / 安全，改動小、風險低 |
| 2 | B-6、B-16、B-17、B-11 | 純清理，無行為變更，先把噪音降下來 |
| 3 | B-1 + B-13 + B-9 | 錯誤格式與 404 組裝一起做（共用 `api_error` + `required_project` dependency） |
| 4 | B-12、B-20、B-14 | 補 OpenAPI `responses` 與 contract 測試，鎖住 3 的成果 |
| 5 | B-7、B-8、B-10、B-19 | 中型重構，逐檔進行 |
| 6 | B-3、B-15 | 需要動 core exception / response model，建議各自獨立 plan |
| 7 | **B-5** | 最高風險，最後做，前面的 contract 測試會是它的安全網 |

---

## 我確認沒問題的部分

以下是我逐行讀完 9 個 route 檔後**實際查證為一致 / 正確**的部分，重構時不要「順手改」：

1. **依賴注入 100% 統一**。9 個檔、23 條 route、全部服務都走 `Annotated[X, Depends(dependencies.y)]`。`grep -rn "app.state\|request\." src/kai_mind/web/routes/` → **0 命中**。沒有任何 route 直接摸 `request.app.state`。（`dependencies.py` 內部的 17 個 `cast()` **[已被 Plan 1 涵蓋]**。）

2. **`raise ... from exc` 的 exception chaining 一致**。我逐一核對了 `grep -rn "status_code=" src/kai_mind/web/routes/` 的 48 個命中點：所有在 `except` 區塊內的 `raise HTTPException` 都有 `from exc`；所有沒有 `from exc` 的都不在 `except` 內（是主動的前置檢查）。零例外。

3. **沒有 TODO / FIXME / HACK / 被註解掉的死碼**。`grep -rniE "todo|fixme|xxx|hack|暫時|temporar|deprecat"` 在 9 個 `.py` 檔只命中 `legacy_mapping_guards` 的 import 與 `_legacy_detail_scan`（已在 B-7 處理）。`grep -rn "^\s*#" src/kai_mind/web/routes/` → 零行被註解掉的程式碼。

4. **POST 一律回 200（不是 201），且與文件一致**。23/23 route 都沒宣告 `status_code=`。`docs/API-GUIDE.md:109`、`:344`、`:565`、`:662`、`:752`、`:800`、`:841`、`:960` 全部寫 `Response 200`。**不建議改成 201** —— 內部一致、文件一致、前端 `frontend/src/services/http.ts:41` 只檢查 `response.ok`，改了只有壞處。

5. **async/sync 沒有 event-loop 阻塞問題**（見 B-20 —— 記的是「規則沒寫下來」，不是「現在是錯的」）。

6. **`reject_legacy_mapping_type` 的覆蓋範圍是正確的，不是漏掛**。它掛在 `POST /api/mappings`（`mapping_routes.py:42`）與 `POST /api/mapping-proposals/{id}/decision`（`mapping_proposal_routes.py:100`），沒掛在 `PATCH /api/mappings/{mapping_id}`。我查證了原因：`ManualMappingUpdate`（`core/models/mapping_base.py:82-92`）**沒有 `mapping_type` 欄位**，且 `MappingModel` 是 `ConfigDict(extra="forbid")`（`core/models/mapping_base.py:9-10`），所以 PATCH 送 `mapping_type` 會直接被 Pydantic 擋成 422。掛與不掛的判斷是對的。

7. **所有 web request/response schema 都繼承 `WebSchema`（`extra="forbid"`）**（`web/schemas.py:43-46`），符合 `docs/API-GUIDE.md:25`「未知欄位 | 寫入類 endpoint `extra="forbid"`」。

8. **`uv run ruff check src/kai_mind/web/routes/` → `All checks passed!`**。79 欄限制沒有違規（中文 docstring 的視覺寬度問題見 B-17，那不是 lint 違規）。

9. **測試不會寫到真實 state dir**。我一度懷疑 `tests/` 裡 29 處 `create_app()`（無 `state_dir`）會寫到 `~/.kai-mind`，查證後 `tests/conftest.py:21` 已全域設 `os.environ["KAI_MIND_STATE_DIR"]`，`tests/conftest.py:40` 另有 per-test monkeypatch。符合 `CLAUDE.md`「Tests inject a temp state dir」。**不是問題。**

10. **CORS、request size limit、unhandled-exception 遮蔽全在 `app.py` / `middleware.py`，routes 完全乾淨**。沒有任何 route 自己加 CORS header 或 try/except-everything。`web/middleware.py:105-121` 的 500 遮蔽是集中的（B-16 的 `detail_scan_routes.py:106` 是唯一繞過它的地方）。

11. **`/map`（無 `/api` 前綴）是刻意保留的，不要刪**。`map_routes.py:75-80`；`frontend/src/services/viewerApi.ts:5` 的 `const mapEndpoints = ["/api/map", "/map"];` 會依序 fallback（`viewerApi.ts:15-26`），`frontend/API_CONTRACT.md:19-24` 標為「Temporary fallback endpoint」，`docs/API-GUIDE.md:57` 標為 `demo / current`。**前端目前仍會呼叫它**。

12. **SSE 的 header 處理正確**。`scan_routes.py:72-76` 的 `SSE_HEADERS`（`Cache-Control: no-cache` / `Connection: keep-alive` / `X-Accel-Buffering: no`）+ `response_class=EventSourceResponse` 讓 OpenAPI 正確標示 `text/event-stream`（實測確認）。`frontend/src/services/viewerApi.ts:31-33` 的 `EventSource` 用法對應無誤。

13. **`GET /api/map/report` 的 path 安全性沒問題**。`map_routes.py:57` 用的是 `store.latest_build_result().map_markdown_path`（伺服器端狀態），不接受任意路徑；`docs/API-GUIDE.md:618` 明說「不接受任意路徑」，`tests/web/test_map_routes.py::test_map_report_route_ignores_arbitrary_path_query`（`:120`）已鎖住。（OpenAPI 的 content-type 標錯是另一回事，見 B-12。）

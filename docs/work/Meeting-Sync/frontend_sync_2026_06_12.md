# KAI-Mind 前後端進度同步 (2026-06-12)

這份是接續 `frontend_sync_2026_06_01.md` 的前端同步版。重點不是列完整後端 phase log，而是讓前端知道：現在可以接哪些 API、畫面要處理哪些狀態、哪些事情不要在前端自己做。

## 一、目前一句話

6/1 時後端還在打底掃描引擎；現在已經推進到可對接的 local API flow：

```text
選本機專案
  -> POST /api/projects/import
  -> POST /api/scans
     -> completed：產生 map artifact，更新 /api/map
     -> requires_boundary_decision：先讓使用者確認本次掃描範圍
  -> GET /api/map 顯示 graph_view_model
  -> optional：detail scan / mapping proposal / query trace
```

## 二、6/1 到現在完成了什麼

| 區塊 | 後端進度 | 前端價值 |
| --- | --- | --- |
| 安全掃描輸入 | precondition、timestamped output、filesystem inventory、secret masking | 不會直接把使用者本機 secret 或無關大型目錄丟到 UI |
| 事實抽取 | config、Docker Compose、dependency manifest、code pattern providers | 後端可從專案推導 endpoint、provider、RAG pattern、evidence |
| 系統地圖 | component detection、risk hints、flows、normalize/validation | `ai_system_map.json` 成為 canonical artifact |
| Viewer payload | `ViewerSessionService`、`graph-view-model/v1`、`/api/map`、`/api/viewer/load` | 前端直接 render nodes / edges / details / filters，layout 仍由前端處理 |
| 互動能力 | manual mappings、mapping proposals、detail scans、query trace | 前端可以做未對應元件確認、懶載入細節、runtime trace replay |
| API 穩定性 | CORS、request size limit、masked 500、path safety、snapshot safety | 前端能可靠處理 413 / 500 / 404 / 422，不會看到 raw path 或 secret |
| 最新變更 | scan boundary review 內嵌在 `POST /api/scans` | 掃描前若有敏感 target，先確認本次要不要掃 |

## 三、前端優先接的主流程

正式 API mode 請走 project session，不要用 demo shortcut：

```text
1. POST /api/projects/import
   取得 project_id

2. POST /api/scans
   status = completed
     -> 使用 build_result / GET /api/map 更新畫面

   status = requires_boundary_decision
     -> 顯示「確認本次掃描範圍」
     -> 使用者對每個 proposal 選 scan_this_run / skip_this_run
     -> 前端自動再 POST /api/scans，帶 boundary_decisions[]

3. GET /api/map
   使用 viewer_load_result.graph_view_model render graph
```

`POST /api/map/build` 仍可做快速 demo，但它不建立 `project_id`，所以不能接 detail scan、mapping proposal、manual mapping、query trace。

## 四、掃描安全確認流程

當後端發現 `.env`、secret-like config、vector persistence path 等 target，第一次 `POST /api/scans` 會先回：

```text
status = "requires_boundary_decision"
build_result = null
boundary_proposals = [...]
available_boundary_actions = ["scan_this_run", "skip_this_run"]
```

這代表正式掃描還沒開始，不會寫 artifact，也不會更新 `/api/map`。前端要一次列出所有 proposal，讓使用者完成所有選擇後，再用同一個 endpoint 送回 `boundary_decisions[]`。

```text
開始掃描
  -> 需要確認
  -> 確認本次掃描範圍
  -> 繼續掃描
  -> 完成
```

UI 文案不要說「重新上傳」、「下次生效」、「永遠跳過」。這次 decision 只對本次 scan request 生效，下一次掃描仍會重新確認。

## 五、前端要處理的狀態

| 狀態 | 前端行為 |
| --- | --- |
| `no_map_loaded` | 顯示尚未載入地圖的 empty state |
| `completed` | 顯示 `graph_view_model`，並更新結果區 |
| `requires_boundary_decision` | 顯示安全確認 modal / drawer，不更新 graph |
| `error` | 顯示掃描失敗狀態，可讓使用者重試 |
| `project_not_found` / `map_not_loaded` | 後端 session 可能重啟，請重新 import + scan |
| `request_too_large` | request body 超過 1 MB，顯示可理解的錯誤 |
| trace `endpoint_not_found` / `partial` | trace timeline 仍要能 replay 到已知步驟 |

## 六、功能對接備註

- **Detail Scan**：`POST /api/detail-scans`，必須先有 project session + map。結果會回更新後的完整 `ai_system_map`。
- **Mapping Proposal**：`POST /api/mapping-proposals` 只針對 `unmapped`。`accept/edit` 會產生 manual mapping；canonical map 仍等下一次 scan 套用。
- **Manual Mapping**：`GET/POST/PATCH /api/mappings` 管 project-level 使用者決策，不直接修改目前畫面上的 map artifact。
- **Query Trace**：`POST /api/trace` 是明確 opt-in runtime call。前端不要直接 call 使用者專案 endpoint。
- **Viewer Payload**：請 render `viewer_load_result.graph_view_model`。`ai_system_map` 是 canonical truth，不要在前端自行改寫。

## 七、前端不要做的事

- 不要自己讀本機專案檔案。
- 不要顯示 raw secret、完整檔案內容或本機絕對路徑。
- 不要把 `graph_view_model` 當成可以回寫的資料來源。
- 不要用 `/api/map/build` 來接需要 `project_id` 的互動功能。
- 不要實作舊版 scan boundary 選項：`always_skip`、`metadata_only`、`masked_summary_only`、下次跳過、永遠跳過。

## 八、這份同步查過的來源

- `docs/work/Meeting-Sync/frontend_sync_2026_06_01.md`
- `docs/API-GUIDE.md`
- `src/kai_mind/web/routes/project_routes.py`
- `src/kai_mind/web/routes/scan_routes.py`
- `src/kai_mind/web/routes/map_routes.py`
- `src/kai_mind/web/routes/detail_scan_routes.py`
- `src/kai_mind/web/routes/mapping_routes.py`
- `src/kai_mind/web/routes/mapping_proposal_routes.py`
- `src/kai_mind/web/routes/trace_routes.py`
- `src/kai_mind/web/schemas.py`
- `src/kai_mind/core/services/scan_boundary_review_service.py`
- `src/kai_mind/core/services/map_build_service.py`
- `docs/work/Timmy/schedule/report/2026-06-01-*` 到 `2026-06-11-phase24-*`
- `docs/work/Bo-han/schedule/report/*` 與 `docs/work/Bo-han/schedule/plan/unfinish/*`

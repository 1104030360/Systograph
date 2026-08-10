# 2026-08-10 Build-scoped Markdown Report 下載 — TODO

對應計畫：
- 後端主計畫：`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/download.md`
- 前端計畫：`docs/work/Meeting-Sync/meeting_sync_2026_08_10/frontend-build-scoped-report-download.md`
- 驅動 prompt：`docs/work/Timmy/schedule/dev-prompt/phase2/phase11.md`

## 目標一句話

新增 build-scoped 下載端點 `GET /api/map-builds/{build_id}/artifacts/{file_name}`（白名單只開 `ai_system_map.md`），前端接上「下載此 build 的報告」，同一輪硬退役 process-wide 的 `GET /api/map/report`——選哪個 build 就下載哪個 build 的檔，路徑永不過牆。

## 實作邏輯

1. **路徑不過牆**：前端只持有 `build_id` 與白名單檔名；`build_id → manifest → map_markdown_path` 的解析全在 server 端，回應只有內容與 headers。
2. **零新儲存**：複用 `MapBuildQueryService.get(build_id)` 與 manifest 還原，不新增服務、不新增 DB。
3. **硬退役**：`/api/map/report`（process-wide「全域最新」語意，會跨 build 甚至跨 project 給錯檔）依 #277 前例直接移除，不留 deprecated 過渡；front-end 從未接上，風險受控。
4. **TDD + BDD**：每項功能先寫行為導向的失敗測試（紅），再實作到綠；退役部分以 `test_retired_endpoints.py` 斷言 404 鎖定。

## 階段劃分與步驟

### 階段 1：計畫查核與更新（plan-audit）
- [x] 以 2026-08-10 程式碼實況查核兩份計畫，回填缺口：
  - boundary test `test_query_trace_boundaries.py` import `map_routes`（刪檔會爆）
  - `MODEL-CONTRACT.md:165` 仍引用舊端點
  - session_store 死快取欄位範圍（兩個 store 都有）
  - `test_retired_endpoints.py` 需補退役 404 斷言
  - `test_map_routes.py` 內含無關的 CORS/SSE 測試需搬家
  - trace script 更名決策

### 階段 2：後端（backend）
- [x] Task 1+2：新端點 + 測試（build 隔離、404 三態、header、無 path 洩漏、temp state dir）
- [x] Task 3：刪 `map_routes.py`、清 `latest_build_result` 與死快取、修 boundary test、搬 CORS/SSE 測試、trace scripts 改打新端點
- [x] Task 4：`API-GUIDE.md`、`frontend/API_CONTRACT.md`、`MODEL-CONTRACT.md` 同步

### 階段 3：前端（frontend）→ 已退回、轉交前端 owner
- [x] Task 1：`fetchText`（沿用 fetchJson 的 timeout/AbortSignal/錯誤形狀）
- [x] Task 2：`mapReportApi.loadMapBuildReport` + 錯誤碼分類 + Blob 下載
- [x] Task 3：ReadinessPanel 下載入口（effective build id = `activeBuildId ?? viewer_load_result.build_id`；Sample mode 隱藏）
- [x] Task 4：API_CONTRACT 核對

> **2026-08-10 追記：** 分工調整（本 repo 這輪由後端 owner 負責），
> 上列前端改動已全數自 working tree 退回；勾選代表參考實作曾完成並
> 通過 review 與全部 gate。完整交接（計畫交接版 + reference patch）
> 見 `docs/work/Meeting-Sync/meeting_sync_2026_08_10/`。

### 階段 4：收尾（wrap-up）
- [x] scripts/ 全面清點（trace_all 清單、其他引用）
- [x] `docs/work/Timmy/learn/architecture.md` ASCII 全景圖更新
- [x] 全量驗證：`uv run pytest` / `ruff check` / `mypy` / `pnpm lint|test|build`
- [x] 兩份計畫 checkbox 打勾、Status 更新；各階段 REP 寫入 `report/2026-08-10/`

## 驗收（來自計畫 §6）

1. 選歷史 build A 下載到的就是 A 的檔（byte 一致）
2. 所有回應不含 absolute path
3. 404 三態碼正確（`build_not_found` / `artifact_not_found` / `artifact_not_available`）
4. `GET /api/map/report` 回 404，repo 內無殘留引用
5. 後端三件套 + `trace_all.sh` 可跑通；前端三件套全綠
6. 契約文件與實作一致

## 執行模式備註

- 依 phase11 指示由 subagent（Opus）逐任務實作、每任務過 spec+quality review，最後由主 agent 親自逐一複核。
- 本輪**不 commit、不 push**，所有改動留在 working tree 由使用者驗收。

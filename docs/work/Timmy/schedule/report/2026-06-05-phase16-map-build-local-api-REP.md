# 2026-06-05 Phase 16 Map Build Service and Local API REP

## 目標

完成 Task 16 的 L1 map build + local API shell：讓 local path project 能經由 `MapBuildService` 產生 validated `ai_system_map.json`，並讓 web API / CLI 都 thin-wrap 同一個 core service。

## 實作邏輯

1. `MapBuildService` 是 scanner orchestration 唯一路徑，串接 template、project scan、component detection、endpoint/risk/flow derivation、normalize、validate、artifact write。
2. `MinimalViewerProjectionService` 只把 canonical `RagSystemMap` 投射成 frontend `GraphViewModel`；不修改 canonical map，也不把 `graph_view_model` 寫進 `ai_system_map.json`。
3. Web route 只做 request/response 轉換與 session state 更新，不直接 import providers。
4. `kai-mind map` CLI 只建立 `MapBuildRequest` 並呼叫 `MapBuildService`。
5. SSE 採 FastAPI 官方 `EventSourceResponse` marker 模式，並將 FastAPI dependency lower bound 調整為 `>=0.135,<1`。

## 步驟

1. 依最新官方文件與一手來源校正 Task 16 plan 的 research 區塊。
2. 建立 phase16 TODO。
3. 先新增 core / web / CLI 測試，確認 RED 狀態為缺少 Task 16 模組。
4. 實作 core models、JSON artifact writer、`MapBuildService` 與 minimal viewer projection。
5. 實作 FastAPI app factory、schemas、in-memory session store、map/project/scan routes 與 SSE endpoint。
6. 實作 `kai-mind map` CLI thin adapter。
7. 建立 `docs/work/Timmy/design/epic1-local-api-guide.md`。
8. 跑新增測試、全量 pytest、Ruff、mypy，修正格式與型別問題。

## 測試方式

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_output_artifact_provider.py tests/unit/core/test_minimal_viewer_projection_service.py tests/integration/test_map_build_service.py tests/web/test_map_routes.py tests/web/test_project_scan_routes.py tests/cli/test_map_command.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider`
- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check .`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src tests`

## 測試結果

- Phase16 新增測試：17 passed。
- 全量測試：272 passed。
- Ruff check：All checks passed。
- Ruff format check：97 files already formatted。
- Mypy：Success, no issues found in 83 source files。

## 遇到的問題與解法

1. Sandbox 內 pytest / Ruff 無法建立 temporary/cache file。解法：使用可寫 temp/cache 環境重跑；這不是程式 regression。
2. FastAPI `EventSourceResponse` 不能直接回傳 `EventSourceResponse(ServerSentEvent...)` 再讓 Starlette streaming 自行處理。解法：採官方 marker 模式，route 宣告 `response_class=EventSourceResponse` 並 yield `ServerSentEvent`。
3. Projection 一開始沒有把 endpoint risk 對應回 component slot。解法：用 `system_map.endpoints` 建索引，將 endpoint risk 透過 `component_instance_id` 回掛到 node。
4. Ruff B008 要求 Typer / FastAPI dependency 使用 `Annotated`。解法：CLI 與 routes 改成 `Annotated[..., typer.Option/Depends(...)]`。
5. `GraphEdgeModel` 的 `from` 欄位與 Python keyword / mypy 衝突。解法：內部欄位用 `from_id`，Pydantic serialization alias 輸出為 `from`。

## 驗收回核

- `MapBuildService` 能從 fixture project 產生 validated `ai_system_map.json`：已完成。
- Canonical top-level shape 完整，空集合維持 `[]`：沿用 Task 15 normalizer / validator，已由全量測試覆蓋。
- `ai_system_map.json` 不包含 `viewer_load_result` 或 `graph_view_model`：已由 integration test 覆蓋。
- `POST /api/map/build` 回傳 structured `MapBuildResult`：已完成。
- `GET /api/map` 與 `GET /map` 回傳同一 typed payload shape：已完成。
- Minimal `graph_view_model` 包含 `nodes`、`edges`、`details.evidence_by_id`、`details.risk_hints_by_id`、`filters.available`：已完成。
- Response shape 對齊 frontend `viewerPayloadSchema`：已用 schema-compatible 欄位與 web tests 覆蓋。
- Missing project 產生 `map-error.md` 且不產生 normal map：已完成。
- Existing output 產生 timestamped directory：已完成。
- Web adapter 不直接掃描檔案，只呼叫 core service：已完成。
- Route handler 不包含 provider/detection/normalization/projection 內部邏輯：已完成。
- `POST /api/projects/import` MVP 僅接受 `source_type="local_path"`：已完成。
- `POST /api/scans` 回傳 `scan_id` 與 status，session 為 in-memory：已完成並寫入 API guide。
- `GET /api/scan/events` basic SSE 符合 `ScanProgressEvent` 欄位與 target priority：已完成並寫入 API guide。
- `kai-mind map ./fixture --output outputs` 產生同 contract valid JSON，CLI 不直接呼叫 providers：已完成。
- `epic1-local-api-guide.md` 已記錄 local API contract、error format、CORS / SSE policy 與後續 Task 18/21/22 邊界：已完成。

## 結論

Task 16 的實作範圍已完成，並已通過本輪新增測試、全量 pytest、Ruff 與 mypy。完整 `ViewerSessionService`、progressive detail scan、runtime query trace、project upload 與 persistent session store 仍依 plan 留給後續任務。

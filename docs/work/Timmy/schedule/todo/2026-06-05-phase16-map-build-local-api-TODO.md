# 2026-06-05 Phase 16 Map Build Service and Local API TODO

## 目標

依照 `plan/unfinish/16-implement-map-build-service-and-local-web-api.md`，完成 L1 map build end-to-end baseline：local path project 進入 core scanner pipeline，產生 validated `ai_system_map.json`，並提供 frontend API mode 可讀的 `viewer_load_result.graph_view_model` minimal wrapper、local API routes、basic SSE contract 與 CLI thin adapter。

## 實作邏輯

1. 先寫測試，再寫功能程式碼，維持 TDD + BDD。
2. `MapBuildService` 是唯一 scanner orchestration；web route 與 CLI 只能 thin-wrap core service。
3. `RagSystemMap` 是 canonical truth；`GraphViewModel` 只存在於 API/viewer payload，不寫進 `ai_system_map.json`。
4. Local API 預設 local-only：CORS allowlist、文件建議 bind `127.0.0.1`，不使用 wildcard origin。
5. SSE 使用 FastAPI 官方 `EventSourceResponse`，並把 FastAPI dependency lower bound 對齊 `>=0.135`。

## 步驟

1. 查證並修正 Task 16 plan 的外部 research 結論。
2. 新增 core service / projection / artifact writer 測試，先看測試因缺功能而失敗。
3. 實作 `MapBuildRequest`、`MapBuildResult`、`MapBuildService`、JSON artifact writer。
4. 實作 `MinimalViewerProjectionService`，輸出最小 `GraphViewModel` shell 並索引 evidence / risk hints。
5. 新增 web schema、FastAPI app 與 `map/project/scan` route modules，route 使用 `response_model`。
6. 實作 `POST /api/map/build`、`GET /api/map`、`GET /map`、`POST /api/projects/import`、`POST /api/scans`、`GET /api/scan/events`。
7. 實作 `systograph map` CLI thin adapter，確認 CLI 不直接呼叫 providers。
8. 建立 `docs/work/Timmy/design/epic1-local-api-guide.md`，記錄 local API contract、error format、SSE 與後續 Task 18/21/22 邊界。
9. 執行相關測試與全量驗證，修正與本次改動相關的失敗。
10. 完成 phase16 report，逐項回核 plan 驗收條件。

## 驗證

- `.venv/bin/python -m pytest tests/unit/core/test_output_artifact_provider.py`
- `.venv/bin/python -m pytest tests/unit/core/test_minimal_viewer_projection_service.py`
- `.venv/bin/python -m pytest tests/integration/test_map_build_service.py`
- `.venv/bin/python -m pytest tests/web/test_map_routes.py tests/web/test_project_scan_routes.py`
- `.venv/bin/python -m pytest tests/cli/test_map_command.py`
- `.venv/bin/python -m pytest`

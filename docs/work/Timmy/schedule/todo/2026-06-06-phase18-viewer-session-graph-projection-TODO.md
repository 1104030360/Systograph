# 2026-06-06 Phase 18 Viewer Session Graph Projection TODO

## 目標

完成 Task 18：建立 `ViewerSessionService`，將 validated `ai_system_map.json` 投影成前端可直接消費的 `viewer_load_result.graph_view_model`，並補上 local web viewer API、CLI validate thin adapter、API guide 與測試。

## 實作邏輯

- `ai_system_map.json` 維持 canonical scanner truth，不寫入 viewer projection。
- `ViewerSessionService.load_map(path)` 負責讀取 map JSON、再次 validate、回傳 `ViewerPayload`。
- `project_to_graph(canonical_map)` 保持純 projection：不 import FastAPI、不呼叫 providers、不重新掃 project folder。
- `GraphViewModel` 只輸出 nodes、edges、details、filters，不輸出 `x`、`y`、`position`。
- invalid map 回傳 `viewer_load_result.loaded=false` 與 `error_reason`，不是把狀態放進 `graph_view_model`。
- node/edge/detail 都保留 canonical `source_id` / `evidence_ids` / `risk_hint_ids`，讓前端 progress、trace、detail panel 可追溯。

## 步驟

1. 查證 research 與前端 contract
   - 讀 `frontend/src/types.ts`、`frontend/src/services/viewerApi.ts`、`frontend/src/utils/graph.ts`。
   - 讀 `docs/work/Timmy/meeting/frontend-backend-architecture-visual-review-2026-06-05.md`。
   - 上網查 React Flow、Prefect、LangGraph、Marquez、FastAPI 相關文件。
   - 將修正寫入 Phase 18 plan。

2. RED：先寫測試
   - `tests/unit/core/test_viewer_session_service.py`
   - `tests/web/test_viewer_routes.py`
   - `tests/cli/test_viewer_command.py`
   - 驗證 valid map、invalid map、unmapped island node、source_id、filters、no layout fields、API 不掃 project folder、CLI thin adapter。

3. GREEN：實作 core projection
   - 新增 `src/systograph/core/models/graph_view.py` 相容 re-export。
   - 新增 `src/systograph/core/services/viewer_session_service.py`。
   - 將 Phase 16 minimal projection 測試併入 `ViewerSessionService`，並移除舊 service。
   - 更新 `MapBuildService` 使用完整 projection。

4. GREEN：實作 local web API
   - 新增 `src/systograph/web/routes/viewer_routes.py`。
   - 新增 web schema `ViewerLoadMapRequest`。
   - 更新 app/dependencies/session store，讓 `/api/viewer/load` 可更新 latest `/api/map` payload。

5. GREEN：實作 CLI thin adapter
   - 新增 `src/systograph/cli/viewer_command.py` 或等價 validate command。
   - 更新 CLI entrypoint。
   - CLI 只呼叫 `ViewerSessionService`，不直接 import scanner providers。

6. 文件與驗收
   - 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
   - 跑相關測試、全測試、ruff、mypy。
   - 完成 report。
   - 逐項核對 Phase 18 plan 驗收標準。

## 測試方式

- RED targeted tests：先確認新測試會因缺少 service/API/CLI 而失敗。
- GREEN targeted tests：修正後重跑 Phase 18 新測試。
- Regression tests：跑 web、CLI、map build、minimal projection 既有測試。
- Quality gates：跑 ruff、mypy、完整 pytest。

## 狀態

- [x] 已完成 research / frontend contract 查證與 plan 修正。
- [x] 已完成 RED 測試。
- [x] 已完成 core projection。
- [x] 已完成 web API。
- [x] 已完成 CLI validate adapter。
- [x] 已完成 API guide。
- [x] 已完成 verification 與 report。

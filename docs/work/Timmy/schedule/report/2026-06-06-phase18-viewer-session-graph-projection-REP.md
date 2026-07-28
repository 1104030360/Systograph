# 2026-06-06 Phase 18 Viewer Session Graph Projection REP

## 完成範圍

- 已查核目前前端架構：
  - `frontend/src/types.ts`
  - `frontend/src/services/viewerApi.ts`
  - `frontend/src/utils/graph.ts`
  - `frontend/API_CONTRACT.md`
  - `docs/work/Timmy/meeting/frontend-backend-architecture-visual-review-2026-06-05.md`
- 已上網查證並修正 Phase 18 plan research：
  - Prefect graph schema 可作為 topology/state graph response 參考，但 invalid map 200 並非 Prefect 直接規範。
  - LangGraph 可作為 node/edge/state wiring 概念參考，不引入 agent runtime。
  - Marquez 可作為 provenance id 概念參考，但 Systograph 使用 canonical `source_id` / `evidence_ids` / `risk_hint_ids`。
  - React Flow + ELK layout 屬 frontend，因此 backend 不輸出 `x` / `y` / `position`。
  - FastAPI route 維持 `response_model` typed payload。
- 已實作完整 `ViewerSessionService`：
  - `load_map(path)`：讀取、validate、回傳 `ViewerLoadResult`。
  - `project_to_graph(canonical_map)`：純 projection，不依賴 FastAPI、不呼叫 providers、不重新掃 project folder。
  - valid map 產生 component、extension、unmapped island nodes。
  - flow edges 保留 canonical edge `source_id`。
  - details 建立 `evidence_by_id` / `risk_hints_by_id`。
  - filters 建立 highlight metadata。
  - invalid map 回傳 `viewer_load_result.loaded=false` 與 `error_reason`。
- 已補 local web API：
  - `POST /api/viewer/load`
  - valid/invalid load 都會更新 latest `/api/map` payload。
- 已補 CLI thin adapter：
  - `validate-map <ai_system_map.json>`
  - 只呼叫 `ViewerSessionService`，不直接 import scanner providers。
- 已移除舊版 `MinimalViewerProjectionService`：
  - Phase 16 minimal projection 驗收已併入 `tests/unit/core/test_viewer_session_service.py`。
  - code/test 已確認沒有 production caller 依賴舊 service。
- 已修正 Codex Review 指出的 slot-only edge projection：
  - 合法 `ai-system-map/v1` edge 可省略 `from_component_id` / `to_component_id`。
  - Projection 現在會先用 component id，缺少 component id 時用 slot 找 deterministic existing component node。
  - 若 slot 沒有任何 node，才 fallback 到 `node:slot:<slot>`。
- 已更新 API guide：
  - `ViewerSessionService`
  - `graph-view-model/v1`
  - `/api/viewer/load`
  - invalid map response
  - graph source_id / no-layout / filter rules。

## 實作邏輯

`ai_system_map.json` 仍是唯一 canonical truth。Phase 18 只新增 viewer projection：

```text
ai_system_map.json
        ↓ validate
RagSystemMap
        ↓ project_to_graph()
GraphViewModel
        ↓
ViewerPayload / GET /api/map
```

`GraphViewModel` 不寫回 `ai_system_map.json`，也不包含前端座標。前端用 `source_id` 把 graph nodes/edges 對回 canonical component、edge、extension、unmapped component，detail panel 用 evidence/risk lookup table 取資料。

## 步驟

1. 先寫 RED tests：
   - `tests/unit/core/test_viewer_session_service.py`
   - `tests/web/test_viewer_routes.py`
   - `tests/cli/test_viewer_command.py`
2. 確認 RED：
   - 初次在 sandbox 內因 temp dir 不可用無法 collection。
   - 改用正常環境重跑後，測試因缺少 `viewer_session_service`、`viewer_routes`、`viewer_command` 失敗，符合預期 RED。
3. 實作 GREEN：
   - 新增 core service/model exports。
   - 更新 MapBuildService / session store / FastAPI app / dependencies / schemas。
   - 新增 viewer route 與 CLI command。
4. 移除舊版 minimal projection：
   - 將 Phase 16 minimal projection 測試合併到 `tests/unit/core/test_viewer_session_service.py`。
   - 將 `RiskHintIndex` 內移到 `ViewerSessionService`。
   - 移除 `src/systograph/core/services/minimal_viewer_projection_service.py`。
   - 移除 `tests/unit/core/test_minimal_viewer_projection_service.py`。
   - 用 `rg` 確認 `src` / `tests` 已沒有 `MinimalViewerProjectionService` 或 `minimal_viewer_projection_service` caller。
5. 更新文件：
   - Phase 18 plan research correction。
   - Epic 1 local API guide。
   - Phase 18 TODO / report。
6. 跑 targeted、regression、quality gates、frontend build。

## 測試方式

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_viewer_session_service.py tests/web/test_viewer_routes.py tests/cli/test_viewer_command.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_viewer_session_service.py tests/integration/test_map_build_service.py tests/web/test_map_routes.py tests/web/test_project_scan_routes.py tests/cli/test_map_command.py tests/web/test_viewer_routes.py tests/cli/test_viewer_command.py`
- `rg -n "MinimalViewerProjectionService|minimal_viewer_projection_service|test_minimal_viewer_projection_service" src tests`
- `npx --yes pyright src/systograph/core/services/viewer_session_service.py`
- `.venv/bin/ruff check src tests`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src tests`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider`
- `pnpm --dir frontend build`

## 測試結果

- Phase 18 targeted tests：10 passed。
- ViewerSessionService + map/web/CLI regression：24 passed。
- Minimal viewer caller 搜尋：`src` / `tests` 無命中。
- Pyright / Pylance equivalent：0 errors, 0 warnings, 0 informations。
- Ruff：All checks passed。
- Mypy：Success, no issues found in 90 source files。
- Full pytest：293 passed。
- Frontend build：通過。

## 遇到的問題與處理

- 問題：第一次 RED pytest 在受限 sandbox 中找不到可用 temporary directory，未進入 collection。
  - 處理：在正常環境重跑同一組 tests，取得真正 RED：缺少 Phase 18 modules/routes/CLI。
- 問題：使用者 research 將 `loaded` / `error_reason` 放入 `GraphViewModel`。
  - 處理：依 `frontend/src/types.ts` 與 `frontend/API_CONTRACT.md` 修正為 `viewer_load_result.loaded` / `viewer_load_result.error_reason`。
- 問題：frontend build 出現 Vite chunk size warning 與 `web-worker` external warning。
  - 處理：build exit code 0，這不是 Phase 18 改動造成的阻塞；記錄為既有 frontend bundling warning。
- 問題：Phase 18 完成後 `MinimalViewerProjectionService` 已不再是主路徑，但仍保留舊 service 與舊測試會增加雙軌維護成本。
  - 處理：確認 production code 沒有外部 caller 後，將 Phase 16 minimal projection 驗收併入 `ViewerSessionService` 測試，刪除舊 service / 舊測試，並重跑 ruff、mypy、完整 pytest。
- 問題：Codex Review 指出合法 slot-only edge 可能指到不存在的 `node:slot:<slot>`。
  - 處理：新增 regression test `test_slot_only_edges_route_to_existing_component_nodes`，並讓 projection 在缺少 component id 時用 slot 對應到 deterministic existing component node，避免 React Flow / ELK 收到 dangling edge。

## 驗收對照

- valid JSON 產生 graph nodes/edges/details：已完成。
- invalid JSON 回傳 `loaded=false` 與 `error_reason`：已完成。
- unmapped component 顯示 `needs_confirmation`：已完成。
- filter metadata 可支援 highlight，不移除 graph elements：已完成。
- local web viewer API 不直接讀 project folder，只讀 map JSON / validated map input：已完成。
- API guide 已同步記錄 viewer graph API、invalid map error state、response 欄位用途：已完成。
- 舊版 `MinimalViewerProjectionService` 已移除，所有 viewer projection 驗收集中到 `ViewerSessionService`：已完成。
- slot-only edge 不會產生 dangling graph edge：已完成。

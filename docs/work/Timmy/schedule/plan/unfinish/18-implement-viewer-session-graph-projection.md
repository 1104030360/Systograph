# Task 18: Implement Viewer Session Graph Projection

## 目標
實作 `ViewerSessionService` 與 local web viewer API，將 canonical `ai_system_map.json` 轉成 GUI 可消費的 `GraphViewModel`。Graph projection 只表達 backend domain semantics，不做前端 layout。

## 為什麼要先做這個
設計文件明確決定 `GraphViewModel` 由 backend 轉，frontend 只渲染。因為 Epic 1 優先 GUI/local web UI，本任務要直接提供 viewer API，避免前端自行讀 JSON 後重做 backend 判斷。

## 承接 Task 16 延後功能
- 承接 Task 16 「不實作完整 `ViewerSessionService` graph projection」與「不做 viewer command」的延後範圍。
- Task 16 的 `GraphViewModel` 只允許是 minimal shell；本任務要把它升級成完整 projection。
- 若 Task 16 已建立 `GET /api/map` / `GET /map` minimal wrapper，本任務要保留 endpoint 相容性，只替換內部 projection service，不破壞 `frontend/src/types.ts`。
- viewer command / map validate CLI 若在本任務補上，只能呼叫 `ViewerSessionService`，不得直接讀 raw JSON 後自行推 graph。

## 前置需求
- Task 15 已完成 map validation。
- Task 16 已能產生 map JSON。
- Task 17 已確認 artifact output 流程。

## 實作範圍
- 建立 `GraphViewModel` models。
- 建立 `ViewerSessionService.load_map()`。
- 使用 FastAPI 建立 local web viewer route / handler。
- 更新 Epic 1 local API guide，加入 viewer graph endpoint、request/response、invalid map error state。
- 載入 map 後再次 validate。
- 將 components、extensions、unmapped、flows、risk hints 轉成 nodes/edges/details。
- 確保每個 node/edge/detail 都能追回 canonical `source_id` / evidence id。
- invalid map 回傳 error state。
- Local web API 完成後，可補 CLI `viewer` / map validate thin adapter；CLI 只能呼叫同一個 `ViewerSessionService`。

## 不包含範圍
- 不做實際 GUI。
- 不做 zoom/pan/drag。
- 不重新掃描 project folder。
- 不做 filter UI，只提供可 highlight 的 metadata。
- 不做 CLI viewer command 的完整 UX；若補 CLI，只做 validate/load result。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/graph_view.py`。
2. 建立 `src/kai_mind/core/services/viewer_session_service.py`。
3. 實作 map JSON load + validation。
4. 實作 standard slot component nodes。
5. 實作 extension/unmapped nodes。
6. 實作 flow edges 與 details lookup。
7. 建立 FastAPI viewer route，回傳 graph view model 或 invalid map error state。
8. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補上 viewer graph API 與 invalid map response 範例。
9. 可選補上 CLI viewer/map validate thin adapter，輸出 loaded/error status。
10. 寫測試：valid map loaded、invalid map error、viewer 不呼叫 providers、API 不掃 project folder。

## 預期輸出
- `src/kai_mind/core/models/graph_view.py`
- `src/kai_mind/core/services/viewer_session_service.py`
- `src/kai_mind/web/routes/viewer_routes.py`
- `src/kai_mind/cli/viewer_command.py` 或等價 validate command
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_viewer_session_service.py`
- `tests/web/test_viewer_routes.py`
- `tests/cli/test_viewer_command.py` 或等價 CLI validate test

## 驗收標準
- valid JSON 產生 graph nodes/edges/details。
- invalid JSON 回傳 `loaded=false` 與 error_reason。
- unmapped component 顯示 `needs_confirmation`。
- filter metadata 可支援 highlight，不移除 graph elements。
- local web viewer API 不直接讀 project folder，只讀 map JSON / validated map input。
- API guide 已同步記錄 viewer graph API、invalid map error state、response 欄位用途。

## 可能風險與注意事項
- GraphViewModel 不能變第二份 truth；所有欄位都要可追回 canonical JSON。
- 不要把 frontend layout 決策放進 backend。
- Viewer load invalid JSON 時不應顯示空白 graph。
- 若 `GraphViewModel` response 欄位變更，必須同步更新 API guide，避免 frontend / desktop app 用錯 contract。

## 新手提示
Graph projection 是把 JSON 排成前端好畫的形狀，不是重新理解專案。

## 視覺化說明
```text
┌──────────────────────┐
│ ai_system_map.json    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Validate again        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ViewerSessionService  │
└──────┬────────┬──────┘
       │        │
       ↓        ↓
┌──────────────┐ ┌──────────────┐
│ Graph nodes  │ │ Graph edges  │
└──────────────┘ └──────┬───────┘
                        ↓
┌──────────────────────┐
│ Details evidence/risk │
└──────────────────────┘
```

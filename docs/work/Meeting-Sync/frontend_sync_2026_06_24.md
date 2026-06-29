# KAI-Mind Frontend 交接：Query Trace Replay（2026-06-24）

## 1. PR 範圍

- Base branch：`main`
- Head branch：`codex/query-trace-ui-flow`
- 完成 issues：#78、#79、#80
- Parent issue：#54
- Backend dependency：#44（已完成並 merge）

本 branch 已 rebase 到包含 PR #196 的最新 `main`，同時保留 project import、
scan、boundary decision 與 Query Trace flow。

## 2. API wiring

Frontend 只在使用者明確按下 Run 後呼叫：

```http
POST /api/trace
```

Request 包含 `project_id`、`endpoint_id`、`query` 與 bounded timeout。
Response 由 Zod schema 驗證，支援 completed、partial、endpoint-not-found 與 error。

## 3. UI 行為

- 顯示 detected endpoint selector、query input、timeout 與 explicit runtime-probe 提示。
- 沒有 endpoint、project ID 或 query 時 Run disabled，不送 request。
- Events 依 `sequence_index` deterministic 排序。
- 支援 play、pause、previous、next 與 reset。
- Active trace event 同步傳入 graph，依 node/component/edge target 高亮。
- failed、timeout、blocked 或 error step 有明確狀態。
- API request 失敗時不清空既有 replay；partial response 仍保留可播放 events。
- 切換 API base、data source 或 map 時清除舊 runtime trace，避免跨 project 汙染。

## 4. 資料安全與限制

- Query Trace 是 explicit opt-in runtime action，不在 Viewer load 或 scan 時自動執行。
- UI 不直接呈現 raw query output、retrieved chunks 或完整 secret。
- Backend egress policy、masking 與 endpoint validation 仍是正式安全邊界。
- 本 branch 沒有新增 frontend automated tests；測試工具與 interaction tests 仍由
  #90、#91 負責。

## 5. 主要修改檔案

- `frontend/src/components/QueryReplayPanel.tsx`
- `frontend/src/components/ReplayTimeline.tsx`
- `frontend/src/components/SystemGraph.tsx`
- `frontend/src/hooks/useQueryTrace.ts`
- `frontend/src/services/traceApi.ts`
- `frontend/src/utils/trace.ts`
- `frontend/src/utils/graph.ts`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/styles.css`

## 6. 驗證結果

```powershell
pnpm --dir frontend run lint
pnpm --dir frontend run build
uv run pytest tests/web/test_trace_routes.py
```

結果：

- ESLint：0 errors；1 個既有 Fast Refresh warning。
- TypeScript / Vite production build：通過。
- Trace route tests：`5 passed`。
- `git diff --check`：通過。
- 既有 build warnings：`web-worker` external dependency、bundle chunk 超過 500 kB。

## 7. Review / handoff notes

1. 人工確認 endpoint missing 時 Run disabled。
2. 人工確認 partial/error trace 不會清空已完成 steps。
3. 人工確認 play/pause/step/reset 與 graph highlight 同步。
4. 人工確認切換 project/data source 後不保留舊 runtime trace。
5. Merge 時關閉 #78、#79、#80，並在三項都關閉後檢查 parent #54。


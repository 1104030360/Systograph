# KAI-Mind Frontend 交接：Viewer Artifact Actions（2026-06-30）

## 1. 本次範圍

- Base：`main`
- Branch：`feature/219-viewer-artifact-actions`
- Issues：#219、#74
- Backend dependencies：#39、#40（已完成並 merge）

本 branch 串接兩個既有 backend artifact endpoints：

- `POST /api/viewer/load`
- `GET /api/map/report`

## 2. 使用者流程

API mode 的 Source menu 新增：

1. 輸入 backend 可存取的 `ai_system_map.json` 路徑。
2. Load existing map，成功後以 backend validated `ViewerPayload` 更新 graph。
3. Preview latest report，以純文字方式檢視 controlled Markdown artifact。
4. Download latest report，使用 backend attachment response。

Invalid map、404、timeout 或 network error 不會清空目前 graph。

## 3. 安全邊界

- Browser 不直接讀本機 map/report 檔案。
- Frontend 不接受任意 report path。
- Markdown 以 `<pre>` 純文字顯示，不注入 HTML。
- Scanner、canonical map 與 report masking policy均未修改。
- 本 branch 不接 `/api/mappings`，等待 #208 contract 穩定後由 #86/#123 承接。
- `/api/scan/events` 目前仍是 placeholder completed event，不在此 branch 宣稱真實進度。

## 4. 主要檔案

- `frontend/src/services/viewerArtifactApi.ts`
- `frontend/src/services/http.ts`
- `frontend/src/components/DataSourceControl.tsx`
- `frontend/src/components/ReportPreviewModal.tsx`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/styles.css`
- `frontend/API_CONTRACT.md`

## 5. 最小驗證

```powershell
pnpm --dir frontend run lint
pnpm --dir frontend run build
uv run pytest tests/web/test_viewer_routes.py tests/web/test_map_routes.py
```

結果：

- ESLint：0 errors；1 個既有 Fast Refresh warning。
- TypeScript / Vite production build：通過。
- Viewer / map route tests：`11 passed`。
- 既有 build warnings：`web-worker` external dependency、bundle chunk 超過 500 kB。

Browser 人工確認：

- valid map 取代 Viewer payload。
- invalid map 顯示錯誤並保留原 graph。
- report unavailable 顯示可讀錯誤。
- report unavailable 時既有 graph 仍保留。

Report preview/download成功 response 已由 backend route tests覆蓋；本次瀏覽器環境未建立新的
臨時 scan artifact，因此仍建議 PR review 時以現有 build result 做一次 preview/download
smoke check。

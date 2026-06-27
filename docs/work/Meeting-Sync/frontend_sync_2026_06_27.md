# KAI-Mind Frontend 交接：Detail Scan UI（2026-06-27）

## 1. 本次交付

- Base branch：`main`
- Head branch：`feature/detail-scan-ui-flow`
- GitHub issues：#81、#82、#83
- 後端依賴：#43（已完成）
- Project session 依賴：#122 / PR #196（已完成並 merge）

本 branch 完成 Viewer 的 progressive Detail Scan 流程：

1. 從 node、edge 或 trace step 建立合法的 backend detail-scan target。
2. L2 使用 `scan_depth: "component"`。
3. L3 使用 `scan_depth: "code_path"`。
4. 成功後重新讀取 `/api/map`，使用 backend validated projection 更新 Viewer。
5. Detail Scan loading、empty、error 或 refresh failure 都不會由 frontend 改寫 canonical map。

## 2. 明確不在本 branch 的範圍

- #85 Mapping Proposal confirm / reject。
- Mapping Proposal、Manual Mapping 的 API wiring。
- Project import、system scan、boundary decision；這些沿用 PR #196。
- Frontend AST parsing 或自行推導 code path。
- 固定顯示「上下五行」的 source context。

#85 應在本 branch merge 後，從最新 `main` 建立獨立 feature branch。

## 3. API contract

### 建立 Detail Scan

```http
POST /api/detail-scans
Content-Type: application/json
```

```json
{
  "project_id": "project:<uuid>",
  "target_type": "component_slot | component_instance | extension | unmapped_component | edge | evidence",
  "target": "canonical-source-id",
  "scan_depth": "component | code_path"
}
```

Detail Scan 必須使用 `POST /api/projects/import` 建立的 `project_id`。沒有有效
project session 時，UI 會停用 action 並顯示說明，不會送出猜測 request。

### 讀取 Detail Scan

```http
GET /api/detail-scans/{detail_scan_id}
```

Frontend 已提供 typed API helper；目前互動流程直接使用 POST response，並在成功後
重新取得 `/api/map`。

## 4. UI 行為

### L2 Component

- 顯示 request loading、success、empty、error 與 retry。
- 顯示 findings、evidence references、warnings、best-effort 與 backend context limits。
- Evidence reference 可作為下一步 L3 target。
- 結果只作為補充資訊，不覆蓋 base graph facts。

### L3 Code Path

- 顯示 project-owned file、symbol 與 backend 提供的 `line_start` / `line_end`。
- 顯示 best-effort hops 與 bounded uncertainty。
- 不呈現 framework/runtime internals。
- 不由 frontend 擴張固定行數 context。

### Sample / API mode

- Sample mode 保持 read-only，仍可顯示 sample/canonical detail scan results。
- API mode 使用真實 backend request。
- 切換 target、project 或 scan depth 時，不會誤用其他 request 的結果。

### Sidebar follow-up polish

- 尚未載入 map 時，Scan Summary 顯示單一 `Waiting for map` empty state，不再排列
  `unknown detected / missing / risk hints / unmapped`。
- View Filters 依 `Status`、`Component type`、`Flow`、`Review signals` 分組。
- 群組內移除重複的 `Status:` / `Type:` 前綴。

## 5. 資料安全

- UI 不顯示 raw evidence value 或完整 source blob。
- L3 只顯示 project-relative path、symbol 與 backend contract 的 line range。
- Error state 不記錄或顯示完整 secret。
- Detail Scan response 仍以 backend validation 與 masking contract 為準。

## 6. 主要修改檔案

- `frontend/src/App.tsx`
- `frontend/src/components/DetailPanel.tsx`
- `frontend/src/components/ReplayTimeline.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/hooks/useDetailScan.ts`
- `frontend/src/services/detailScanApi.ts`
- `frontend/src/styles.css`
- `frontend/src/types.ts`
- `frontend/API_CONTRACT.md`

## 7. 驗證結果

### Frontend

```powershell
pnpm --dir frontend run lint
pnpm --dir frontend run build
```

結果：

- ESLint：0 errors。
- 既有 warning：`BoundaryDecisionModal.tsx` 同時 export component 與 helper，觸發
  `react-refresh/only-export-components`。
- TypeScript：通過。
- Vite production build：通過。
- 既有 build warnings：`web-worker` external dependency、bundle chunk 超過 500 kB。

### Backend contract

```powershell
uv run pytest tests/web/test_detail_scan_routes.py
```

結果：`2 passed`。

### 已完成的 desktop interaction checks

- 真實 API L2 loading / success。
- L2 顯示 6 筆 findings。
- L2 evidence 進入 L3。
- L3 顯示 3 個 bounded code-path hops。
- API 中斷時顯示 error / retry，既有 graph 保留。

依開發過程中的決定，完整 Playwright responsive pass 暫停；mobile 仍需人工確認。

## 8. Merge 前人工確認

使用 fixture：

```text
tests/fixtures/rag_projects/basic_qdrant_ollama_rag
```

建議流程：

1. API mode 輸入 fixture 絕對路徑並完成 Project Scan。
2. 選擇 Qdrant node，開啟 `L2 Component` 並執行 scan。
3. 確認 loading、findings、evidence 與 `Run again`。
4. 點擊一筆 evidence，確認切換至 `L3 Code Path`。
5. 執行 L3，確認 file、symbol、line range 與 best-effort 呈現。
6. 暫停 API 後重試，確認 graph 不消失且 error 可讀。
7. 切換 Sample / API mode，確認原有 Viewer 功能正常。
8. 在 390 px 左右寬度確認 Summary、filter groups、Detail Panel tabs、長路徑與按鈕
   沒有重疊或水平溢出。

## 9. 後續工作

1. 完成本 PR 的 mobile / narrow viewport review。
2. Merge 後從最新 `main` 建立獨立 branch 實作 #85。
3. #85 不應因 #81–#83 完成而提前關閉。
4. Bundle / `web-worker` warnings 應由獨立 build-performance task 處理。

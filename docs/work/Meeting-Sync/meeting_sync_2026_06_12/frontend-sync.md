# KAI-Mind 前端交接文件（2026-06-12）

這份文件是給前端工程師開工用的版本。

先不用理解全部後端 phase，只要先抓住一件事：

```text
前端現在要把「看 demo map」推進成「真的選專案、掃描、看結果」。
```

## 1. 現在後端已經可以做什麼

後端目前已經有一條正式 API flow：

```text
輸入本機專案路徑
  -> 建立 project_id
  -> 開始 scan
  -> 如果需要安全確認，先讓使用者選這次要不要掃
  -> scan 完成
  -> 讀取 /api/map
  -> 前端顯示 graph
```

前端不要再只停在 sample/demo map。接下來要先把這條 flow 接起來。

## 2. 前端第一優先：接正式掃描流程

對應計畫：

`docs/work/Timmy/schedule/plan/unfinish/24b-implement-project-scan-and-boundary-decision-frontend-flow.md`

### UI 要做

前端要新增或補齊：

1. 一個輸入本機專案路徑的地方。
2. 一個「開始掃描」按鈕。
3. 掃描中 / 成功 / 失敗狀態。
4. 如果後端要求安全確認，要跳出 modal 或 drawer。
5. scan 完成後，自動重新讀 `/api/map` 並更新 graph。

### API 順序

第一步：建立 project。

```http
POST /api/projects/import
```

request:

```json
{
  "source_type": "local_path",
  "project_path": "/Users/example/my-rag-project"
}
```

response 會拿到：

```json
{
  "project_id": "project:..."
}
```

第二步：開始掃描。

```http
POST /api/scans
```

request:

```json
{
  "project_id": "project:..."
}
```

後端會回兩種主要狀態。

### 情況 A：掃描完成

```json
{
  "status": "completed",
  "build_result": {}
}
```

前端接著呼叫：

```http
GET /api/map
```

然後用：

```text
viewer_load_result.graph_view_model
```

更新畫面上的 nodes / edges / details。

### 情況 B：需要安全確認

```json
{
  "status": "requires_boundary_decision",
  "build_result": null,
  "boundary_proposals": [],
  "available_boundary_actions": ["scan_this_run", "skip_this_run"]
}
```

這代表掃描還沒有真的完成。

前端要做：

1. 不要更新 graph。
2. 顯示安全確認 modal / drawer。
3. 把 `boundary_proposals` 全部列出來。
4. 每一項讓使用者選：
   - `scan_this_run`：這次掃。
   - `skip_this_run`：這次跳過。
5. 使用者全部選完後，再呼叫一次 `POST /api/scans`，這次帶 `boundary_decisions`。

範例：

```json
{
  "project_id": "project:...",
  "boundary_decisions": [
    {
      "proposal_id": "boundary:...",
      "action": "scan_this_run"
    }
  ]
}
```

重要文案：

- 可以說：「這次掃描要不要包含這個範圍？」
- 不要說：「永遠跳過」。
- 不要說：「下次也套用」。
- 這個 decision 只影響這一次 scan。

## 3. 第二優先：Mapping Proposal

對應計畫：

`docs/work/Timmy/schedule/plan/unfinish/20a-implement-ai-mapping-proposal-frontend-flow.md`

使用者看到 `unmapped` 元件時，前端要讓他可以請後端產生 mapping proposal。

要做的事：

1. 在 unmapped node / detail panel 放一個「產生 mapping proposal」入口。
2. 呼叫 `POST /api/mapping-proposals`。
3. 顯示後端建議它應該對應到哪個 component / slot。
4. 讓使用者選：
   - accept
   - edit
   - reject
   - skip_for_now

注意：

```text
前端不要自己改 ai_system_map。
```

使用者的 decision 會變成 manual mapping。正式 map 要等下一次 scan 套用。

## 4. 第三優先：Detail Scan

對應計畫：

`docs/work/Timmy/schedule/plan/unfinish/21a-implement-detail-scan-frontend-flow.md`

目前 Detail Panel 還偏 sample-only。接下來要改成真的呼叫後端。

要做的事：

1. 使用者點 node / edge。
2. 使用者切到 L2 Component 或 L3 Code Path。
3. 前端呼叫：

```http
POST /api/detail-scans
```

4. 顯示 loading。
5. 顯示後端回來的 detail scan result。
6. 如果失敗，顯示錯誤，不要讓畫面看起來像已完成。

## 5. Task 24a：Project Mapping Profile Page

對應計畫：

`docs/work/Timmy/schedule/plan/unfinish/24a-implement-project-mapping-profile-page.md`

這個要做，但不是第一個做。

建議放在 EPIC2 / 產品化階段，原因是它需要前面的功能先完成：

1. `24b` project scan flow。
2. `20a` mapping proposal。
3. `21a` detail scan。

Profile page 要解決的是：

```text
這個 project 目前有哪些 manual mappings？
哪些 proposal 被接受？
哪些被跳過？
哪些被拒絕？
使用者能不能回頭修改？
```

它比較像「管理頁」，不是第一條 scan flow 的必要條件。

## 6. 前端還要補的品質工作

### API 文件同步

請同步更新：

`frontend/API_CONTRACT.md`

至少要補：

- `POST /api/projects/import`
- `POST /api/scans`
- `requires_boundary_decision`
- `POST /api/detail-scans`
- `POST /api/mapping-proposals`

### 測試

建議補 frontend tests，至少覆蓋：

1. scan completed 後會重新載入 map。
2. `requires_boundary_decision` 會顯示 modal，不會更新 graph。
3. 使用者送出 boundary decisions 後會再次呼叫 scan。
4. detail scan loading / error / success。
5. mapping proposal accept / reject / skip flow。

### OpenAPI SDK

對應計畫：

`docs/work/Timmy/schedule/plan/unfinish/phase3-platform-foundation/28-introduce-openapi-generated-frontend-sdk.md`

這是收尾品質工作。等 API shape 穩定後，再導入 OpenAPI 產生 TypeScript 型別 / client，避免前端一直手寫 endpoint 和 response type。

## 7. 目前頁面上的 AI 面板

目前前端頁面上有 `ChatPanel`，但它只是前端 UI 殼。

後端目前還沒有：

- assistant API。
- RAG retrieval。
- page context collector。
- 產品操作 action flow。

所以這個不是本輪前端交接要做的主線。

未來如果要把它做成 page-aware RAG assistant，計畫先放在：

`docs/work/Timmy/schedule/plan/future/page-aware-rag-product-assistant.md`

現在前端可以先保留這個入口，但不要為了它阻塞 `24b`、`20a`、`21a`。

## 8. 前端不要做的事

這些事情請不要在前端做：

1. 不要自己讀本機專案檔案。
2. 不要顯示 raw secret。
3. 不要顯示完整本機絕對路徑。
4. 不要把 `graph_view_model` 當成可以回寫的資料。
5. 不要用 `/api/map/build` 來做正式互動流程。
6. 不要自己發明 scan boundary action。

正式互動流程都要走 project session：

```text
POST /api/projects/import
POST /api/scans
GET /api/map
```

## 9. 一句話排程建議

建議前端照這個順序做：

```text
1. 24b：project import + scan + boundary decision
2. 20a：mapping proposal UI
3. 21a：detail scan UI
4. 更新 frontend/API_CONTRACT.md
5. 補 frontend tests
6. 28：OpenAPI generated client
7. 24a：Project Mapping Profile Page
```

## 10. 參考來源

- `frontend/API_CONTRACT.md`
- `docs/API-GUIDE.md`
- `src/kai_mind/web/routes/project_routes.py`
- `src/kai_mind/web/routes/scan_routes.py`
- `src/kai_mind/web/routes/map_routes.py`
- `src/kai_mind/web/routes/detail_scan_routes.py`
- `src/kai_mind/web/routes/mapping_proposal_routes.py`
- `src/kai_mind/web/routes/mapping_routes.py`
- `src/kai_mind/web/routes/trace_routes.py`
- `src/kai_mind/web/schemas.py`
- `frontend/src/components/ChatPanel.tsx`

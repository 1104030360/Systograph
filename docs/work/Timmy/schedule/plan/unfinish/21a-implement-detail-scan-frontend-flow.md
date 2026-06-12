# Task 21a: Implement Detail Scan Frontend Flow

## 目標

在 frontend viewer 中接上 Task 21 的 progressive detail scan backend API，讓使用者可以從 graph detail panel 針對 selected node / edge / evidence 觸發 L2 `component` scan 或 L3 `code_path` scan，並在完成後看到真實 `detail_scans[]`、新增 evidence、best-effort / truncated 狀態，而不是只看 sample payload。

本任務只做前端接線與 UI，不實作 backend scanner，不修改 canonical map validation，也不讓前端自行讀 project files。

## 最新狀態校正（2026-06-12）

後端 Task 21 已完成 `POST /api/detail-scans` / `GET /api/detail-scans/{detail_scan_id}` 與 detail scan evidence append；本任務仍未完成，且仍應留在 EPIC1 收尾 scope。

已再次檢查目前前端：

- `frontend/src/services/viewerApi.ts` 目前沒有 `createDetailScan()` 或 `getDetailScan()`。
- `frontend/src/components/DetailPanel.tsx` 的 L2/L3 tabs 仍只讀 `payload.detail_scan_result_sample`。
- `DetailPanel` 沒有 `Run component detail scan` / `Run code path scan` button。
- `frontend/src/types.ts` 對 `ai_system_map` 採寬鬆 record/passthrough，沒有 typed `detail_scans[]` selector。
- `frontend/package.json` 目前沒有 frontend test runner。

結論：

```text
後端/API：完成
前端 UI/API helper/state/tests：未完成
EPIC1 判斷：仍是 minimum viable frontend scope
```

## 為什麼要拆成 21a

Task 21 的核心是 backend progressive detail scan：target validation、bounded AST / call-like extraction、secret masking、evidence append、`detail_scans[]` append、整份 map validation。

Frontend detail scan flow 是另一個獨立交付面：

- 從 `DetailPanel` 觸發 `POST /api/detail-scans`。
- 顯示 L2/L3 running / error / empty / completed states。
- 從更新後的 viewer payload 顯示真實 `detail_scans[]` 與 evidence。
- 避免 sample mode 和 API mode 混淆。

若把 Task 21 backend 和 frontend 串接混在一起，會讓 scanner correctness、API contract、UX state machine、frontend tests 全部互相卡住。因此拆成 21a。

## 已檢查的目前前端狀態（2026-06-08）

已實際檢查：

- `frontend/src/types.ts`
- `frontend/src/services/viewerApi.ts`
- `frontend/src/store/viewerStore.ts`
- `frontend/src/components/DetailPanel.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/API_CONTRACT.md`
- `docs/work/Bo-han/schedule/plan/finish/04-refine-graph-interaction-and-detail-modal.md`
- `docs/work/Timmy/schedule/plan/unfinish/20a-implement-ai-mapping-proposal-frontend-flow.md`
- `docs/work/Timmy/schedule/plan/unfinish/21-implement-progressive-detail-scan.md`

目前觀察：

- `DetailPanel.tsx` 已有 `Overview` / `L2 Component` / `L3 Code Path` tabs。
- `viewerStore.ts` 已有 `detailMode: "overview" | "component" | "code_path"`。
- `Sidebar.tsx` 已有 L1 / L2 / L3 scan depth indicator。
- `types.ts` 的 `viewerPayloadSchema` 目前只把 `detail_scan_result_sample` 當 `z.record(z.unknown())`，沒有真實 `DetailScanResult` schema。
- `types.ts` 的 `ai_system_map` schema 沒有宣告 `detail_scans`，所以 API mode 即使 backend 回傳 `detail_scans[]`，前端也沒有 typed access。
- `viewerApi.ts` 目前只支援 `loadApiViewerPayload()`、sample payload、scan SSE；沒有 `createDetailScan()` 或 `getDetailScanResult()`。
- `DetailPanel.tsx` 的 L2/L3 目前只讀 `payload.detail_scan_result_sample`，不是 backend `ai_system_map.detail_scans[]`。
- `DetailPanel.tsx` 目前沒有 `Run L2 scan` / `Run L3 scan` button，也沒有 loading/error state。
- `frontend/API_CONTRACT.md` 只有 future detail scan request shape，尚未記錄真實 endpoint、response shape、refetch rule。

## 與 Task 20a 的分工

Task 20a 負責 mapping proposal frontend flow：

- `GET /api/mapping-proposals`
- `POST /api/mapping-proposals`
- `POST /api/mapping-proposals/{proposal_id}/decision`
- candidate cards
- accept/edit/reject/skip

Task 21a 負責 progressive detail scan frontend flow：

- `POST /api/detail-scans`
- `GET /api/detail-scans/{detail_scan_id}`
- L2/L3 tab trigger
- detail scan progress / error / completed states
- refetch viewer payload so new evidence appears in `DetailPanel`

兩者的交會點是 evidence lifecycle：

```text
Task 21 / 21a:
  detail scan → backend append evidence[] + detail_scans[] + unmapped.evidence_ids
  frontend refetch viewer payload

Task 20 / 20a:
  create proposal → backend MappingEvidencePacketBuilder reads updated evidence ids
  frontend renders proposal candidates
```

前端不需要自己把 detail scan result 轉成 proposal input；這是 backend `MappingEvidencePacketBuilder` 的責任。

## 後端 API contract（Task 21 提供）

Task 21 預計提供：

```text
POST /api/detail-scans
GET  /api/detail-scans/{detail_scan_id}
```

Create detail scan request：

```json
{
  "project_id": "project:...",
  "target_type": "component_slot | component | extension | unmapped_component | edge | evidence",
  "target": "slot-or-component-or-edge-or-evidence-id",
  "scan_depth": "component | code_path"
}
```

建議 response shape：

```json
{
  "project_id": "project:...",
  "detail_scan": {
    "id": "detail_scan:...",
    "target_type": "unmapped_component",
    "target": "unmapped:...",
    "scan_depth": "component",
    "status": "completed",
    "findings": [
      {
        "kind": "import_signal",
        "summary": "Found retriever import near target component.",
        "evidence_ids": ["evidence:detail:..."]
      }
    ],
    "code_path": [],
    "warnings": ["best_effort_static_analysis"]
  },
  "ai_system_map": {
    "...": "updated map after evidence/detail scan append"
  }
}
```

若 backend 不直接回傳整份 updated map，frontend mutation success 後必須呼叫 `loadApiViewerPayload()` 重新取得最新 viewer payload。

## 掃描層次 UX

Frontend 應明確表達 L1 / L2 / L3 不是平行功能，而是從粗到細：

```text
L1 System
  已由 base map 顯示整體 graph。

L2 Component
  使用者點 component / slot / unmapped node 後觸發。
  目的：找 target-related files、imports、class/function signatures、decorators、bounded snippets。

L3 Code Path
  使用者在 L2 結果、edge、evidence 或 call-like hint 上繼續觸發。
  目的：找更細的 call-like hints，例如 self.retriever.invoke(...)。
  UI 必須標示 static observation / best_effort，不可暗示已證明 runtime path。
```

## 實作範圍

- 擴充 `frontend/src/types.ts`：
  - `detailScanFindingSchema`
  - `codePathStepSchema`
  - `detailScanResultSchema`
  - `detailScanCreateRequestSchema`
  - `detailScanCreateResponseSchema`
  - 在 `viewerPayloadSchema.viewer_load_result.ai_system_map` 加入 `detail_scans`
- 擴充 `frontend/src/services/viewerApi.ts`：
  - `createDetailScan(baseUrl, request)`
  - `getDetailScan(baseUrl, detailScanId)`
- 建立 hook：
  - `useDetailScansFromPayload(payload, selected)`
  - 或 `useDetailScanMutation()`，依現有 frontend query pattern 決定。
- 在 `DetailPanel.tsx` 的 L2 tab：
  - 若 selected target 可做 component scan，顯示 `Run component detail scan`。
  - 顯示該 target 已存在的 `scan_depth = "component"` detail scan results。
  - 顯示 findings、evidence ids、warnings、best-effort / truncated message。
- 在 `DetailPanel.tsx` 的 L3 tab：
  - 若 selected target 可做 code path scan，顯示 `Run code path scan`。
  - 若尚未有 L2 result，提示「先跑 L2 component detail scan 會讓 L3 更準」。
  - 顯示 `code_path[]` 與 call-like findings。
- mutation 成功後 refetch viewer payload，讓新增 evidence 出現在 Overview evidence list 與後續 Task 20a proposal flow。
- 明確區分 sample mode / API mode：
  - sample mode 可繼續展示 `detail_scan_result_sample`。
  - API mode 必須讀真實 `ai_system_map.detail_scans[]` 與 detail scan endpoints。
- 更新 `frontend/API_CONTRACT.md`，記錄 endpoint、request、response、refetch rule、sample/API mode 差異。
- 補 frontend tests。若尚未有 test runner，需引入 Vitest + React Testing Library 或與 Task 20a 共用同一套 frontend test setup。

## 不包含範圍

- 不實作 backend `DetailScanService`、`ComponentDetailScanService`、`CodePathScanService`。
- 不讓前端讀 project folder、source file、repo root。
- 不讓前端自行抽 AST、call graph、dependency graph。
- 不在前端保存 raw source、raw prompt、unmasked evidence、API key。
- 不讓前端直接修改 `ai_system_map.json` artifact。
- 不把 detail scan result 渲染成已確認 canonical component / extension / flow edge。
- 不做 query trace runtime execution；Task 22 / Bo-han Task 6 才處理 opt-in trace UI。
- 不做 mapping proposal candidate decision flow；那是 Task 20a。

## 建議實作步驟

1. RED：引入或復用 frontend test runner，新增 detail scan schema 與 API helper 測試。
2. 實作 `frontend/src/types.ts` 的 detail scan schemas，確認 sample payload 與 API payload 都能 parse。
3. 在 `viewerPayloadSchema.viewer_load_result.ai_system_map` 加入 `detail_scans: z.array(detailScanResultSchema).optional()`。
4. 實作 `frontend/src/services/viewerApi.ts` 的 `createDetailScan()` 與 `getDetailScan()`。
5. 建立 helper：從 selected node / edge 推導 detail scan target request。
   - node 優先用 `source_id`，fallback 用 `id`
   - edge 優先用 `source_id`，fallback 用 `id`
   - L2 使用 `scan_depth: "component"`
   - L3 使用 `scan_depth: "code_path"`
6. 建立 `useDetailScansForTarget(payload, selected)` 或等價 selector，從 `ai_system_map.detail_scans[]` 找出 target match。
7. 修改 `DetailPanel.tsx` 的 `ComponentDetails`：
   - API mode 讀 real detail scans
   - sample mode 才讀 `detail_scan_result_sample`
   - 加入 `Run component detail scan` / `Run code path scan` buttons
8. 加入 loading / error states：
   - request in progress
   - invalid target
   - backend validation error
   - scanner unavailable / best-effort warning
9. mutation success 後呼叫 viewer payload refetch，並保留目前 selected target 與 active tab。
10. 讓 Overview evidence list 能自然顯示 detail scan 新增的 evidence；不需要特別複製 detail evidence UI。
11. 更新 `frontend/API_CONTRACT.md` 的 Detail Scan section，移除「future request」語氣，改成正式 frontend contract。
12. 加測試：
   - API mode 不讀 `detail_scan_result_sample`
   - sample mode 不呼叫 backend
   - L2 button 送出 `scan_depth: "component"`
   - L3 button 送出 `scan_depth: "code_path"`
   - mutation success 會 refetch viewer payload
   - backend error 顯示可讀錯誤
13. 跑 `cd frontend && pnpm build` 與 frontend tests。

## 預期輸出

- 更新 `frontend/src/types.ts`
- 更新 `frontend/src/services/viewerApi.ts`
- 更新 `frontend/src/components/DetailPanel.tsx`
- 視需要更新 `frontend/src/store/viewerStore.ts`
- 視需要新增 `frontend/src/hooks/useDetailScans.ts`
- 更新 `frontend/API_CONTRACT.md`
- 新增或更新 frontend tests：
  - detail scan schema tests
  - viewer API helper tests
  - DetailPanel L2/L3 interaction tests

## 驗收標準

- API mode 中，L2/L3 tabs 不再把 `payload.detail_scan_result_sample` 當成真實結果。
- 使用者選到可掃描 target 時，可以從 L2 tab 觸發 component detail scan。
- 使用者選到 edge / evidence / call-like target 時，可以從 L3 tab 觸發 code path scan。
- L3 UI 明確標示 `best_effort` / static observation，不暗示 runtime path 已確認。
- mutation 成功後 viewer payload 會刷新，新增 evidence 可在 Overview evidence list 看見。
- 已存在的 `ai_system_map.detail_scans[]` 會依 selected target 顯示，不需要重新掃描才看得到。
- sample mode 不呼叫 backend detail scan API。
- API mode 顯示 backend loading / error / validation failure state。
- frontend 不讀 project folder，不顯示 raw source，不保存 unmasked secret。
- `pnpm build` 與 frontend tests 通過。

## 可能風險與注意事項

- L2/L3 scan 可能較慢，前端必須提供 running state，避免使用者連點重送。
- L3 是比 L2 更細的 static code path scan，不應在 UI 上和 L2 畫成平行等級的「另一種詳情」。
- Backend 追加 evidence 後，graph projection 是否立即包含新 evidence detail 取決於 viewer payload refetch；前端不要嘗試自己 merge partial map。
- 若 backend response 不包含 updated viewer payload，frontend 必須 refetch `/api/map`，不要只用 mutation response 更新局部 state。
- 若 Task 20a 和 Task 21a 同時修改 `DetailPanel.tsx`，應先抽出小 component，例如 `ProposalPanel` 與 `DetailScanPanel`，避免同一檔案過度膨脹。
- L3 scan 不等於 Task 22 query trace。若使用者要 runtime evidence，UI 應引導到 future query trace flow，而不是把 static call-like hints 包裝成 runtime truth。

## 前端工程師白話版

現在畫面已經有 L2 / L3 tab，但內容是假資料。Task 21a 要把它變成真的互動：使用者點一個 node，可以按「掃這個 component」；如果想看更細的 function/call path，可以跑 L3。Backend 會把掃到的新 evidence 寫回 map，前端只要重新載入 viewer payload，Overview 和 proposal flow 就會自然看到新 evidence。

## 視覺化說明

```text
使用者點 graph node / edge
        ↓
DetailPanel
  ├─ Overview: 顯示目前 evidence / risk hints
  ├─ L2 Component
  │    ├─ Run component detail scan
  │    ├─ POST /api/detail-scans scan_depth=component
  │    └─ 顯示 target-level findings
  └─ L3 Code Path
       ├─ Run code path scan
       ├─ POST /api/detail-scans scan_depth=code_path
       └─ 顯示 call-like hints / code_path[]

scan success
        ↓
refetch /api/map
        ↓
viewer payload 更新
        ↓
Overview evidence list + L2/L3 tabs + Task 20a proposal flow 都看到新 evidence
```

# Phase 1 Find-Error — UI/UX 與前端工程 詳細發現

- 日期：2026-06-12 ／ 性質：只檢查與記錄，未修改功能程式碼
- 範圍：`frontend/src/` 全部元件、hooks、services、store、utils、types、build 設定
- 說明：前端部分由主審查者逐檔閱讀並 grep 全 `frontend/src` 確認注入面，再由前端 subagent 複核 `frontend/src`、`frontend/package.json`、build/lint 設定、Hardy 設計/plan 與後端 schema。每項標注「repo 實際觀察」。
- 編號延續總覽報告（M-16/M-17 已在後端檔列出 fetch timeout 與 bundle，這裡聚焦 UI/UX 與前端工程其餘項）。

---

## A. UI/UX

### A-1：API mode 連線失敗只顯示底層錯誤字串，缺乏可操作指引（repo 實際觀察）
- 嚴重程度：Low 偏 Medium
- 來源：`frontend/src/components/StateOverlay.tsx:35-57`（error 卡片顯示 `message ?? "GET .../api/map failed"`）、`frontend/src/services/viewerApi.ts:43`（錯誤訊息 `Unable to load viewer payload from ... Tried /api/map: 404 ...; /map: ...`）
- 問題說明：錯誤卡片把後端 HTTP 狀態字串直接丟給使用者（如 `404 Not Found`、`Failed to fetch`），對 release-readiness 工具使用者而言不易判讀「是後端沒起、port 錯、還是還沒掃描」。`StateOverlay` 設計本身良好（提供 Retry / Use sample data，且不偷偷 fallback），只是訊息可更具引導性。
- 為什麼需要改進：使用者第一次接 API 模式最常見的就是後端沒啟動 / port 不對，現況訊息無法引導他檢查 `127.0.0.1:8000` 是否在跑。
- 具體改善建議：依錯誤類型（網路層 `Failed to fetch` vs HTTP 404 vs schema parse 失敗）給不同文案；網路層失敗時提示「確認本機 Python API 是否已啟動於 {apiBaseUrl}」。
- 重現方式：API mode 指向未啟動的 `http://127.0.0.1:8000` 或錯誤 port，觀察 error 卡片與 toolbar 顯示 raw fetch / HTTP error。
- 建議測試方式：Vitest mock `fetch` 回 network error、404、schema parse error，斷言 UI 顯示可操作文案而非只有 raw error。
- 預期效果：降低 API 模式上手摩擦。
- 影響範圍：`StateOverlay`、`viewerApi`。

### A-2：`loaded=false` / `error_reason` 未充分呈現，invalid map 會像一般未掃描（repo 實際觀察）
- 嚴重程度：Low
- 來源：`frontend/src/App.tsx:37-48`（state matrix）、`StateOverlay.tsx:59-79`（pending 卡片）
- 問題說明：`pending` = API 有回應但 `viewer_load_result.loaded === false`，可能代表「後端尚未產出 map」，也可能代表 `invalid_map` / `map_read_failed` / `invalid_json` 等 `error_reason`。目前 `App.tsx` 只把這些狀態壓成 `pending`，`StateOverlay` 顯示 `No map loaded yet`，不會把 `error_reason` 呈現給使用者，因此 invalid map 看起來像一般未掃描。
- 建議：`pending` 卡片根據 `viewer_load_result.error_reason` 分類：`no_map_loaded` 顯示「請先執行掃描」；`invalid_map` / `map_read_failed` 顯示「map 讀取或驗證失敗」與下一步（重新掃描 / 檢查 API log）。
- 重現方式：讓 API 回 `viewer_load_result.loaded=false,error_reason="invalid_map"`，觀察前端仍顯示一般 `No map loaded yet`。
- 建議測試方式：新增 `StateOverlay` 或 `App` render test，餵 `loaded=false` 的不同 `error_reason`，斷言文案不同。
- 影響範圍：`StateOverlay`、`App.tsx`。

### A-3：Sample / API 模式區分清楚，但 sample 模式無常駐標示（repo 實際觀察，偏正面）
- 嚴重程度：Low
- 來源：`frontend/src/components/DataSourceControl.tsx:16-34`（Sample/API segment 切換）、`App.tsx:50`（sample 時用 `sampleViewerPayload`）
- 問題說明：切到 sample 模式後，toolbar segment 有 active 樣式，但 graph 區域沒有常駐浮水印/標籤提示「目前是範例資料」。demo 時若使用者沒注意 segment，可能誤把 sample 14 nodes 當成真實掃描結果。`StateOverlay` 已避免「API 失敗偷偷 fallback sample」(好)，但「使用者主動切 sample 後忘記」仍可能誤認。
- 建議：sample 模式在 graph 角落加常駐 "Sample data" badge。
- 重現方式：切到 sample mode 後關注 graph 區域，只有 toolbar segment 顯示 mode，graph canvas 本身沒有常駐 sample 標示。
- 建議測試方式：render `App` sample mode，斷言 graph 區有 sample badge；API mode 則不顯示。
- 影響範圍：`App.tsx`、`SystemGraph`。

### A-4：Project-scoped scan / boundary decision flow 尚未接線，安全確認 UX 無法從前端完成（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`frontend/src/services/viewerApi.ts` 目前只讀 `GET /api/map` / fallback `GET /map`；`frontend/src/store/viewerStore.ts` 無 `project_id`、`scan_id`、boundary proposals / decisions state；`frontend/API_CONTRACT.md` 尚未完整記錄 `POST /api/projects/import` -> `POST /api/scans` -> boundary decision flow。
- 問題說明：後端已支援 `POST /api/scans` 回 `requires_boundary_decision` 與 `available_boundary_actions`，但前端 API mode 還只是 viewer payload loader。使用者不能只靠前端完成「輸入 project path -> import -> scan -> boundary decision -> refresh graph」閉環，也看不到「只影響本次 scan」的安全文案。
- 為什麼需要改進：scan boundary 是安全確認點；沒有前端 decision UI 時，local API 的安全設計難以被一般使用者正確使用。
- 具體改善建議：在既有 `24b-implement-project-scan-and-boundary-decision-frontend-flow.md` 中補 typed API helper、decision drawer/modal、proposal state、decision submit + rescan lifecycle，並明確標示 decision 只影響本次 scan。
- 重現方式：目前前端 API mode 只能 reload `/api/map`，沒有 UI 可呼叫 `POST /api/projects/import` 或處理 `requires_boundary_decision`。
- 建議測試方式：導入 Vitest/RTL 後 mock `requires_boundary_decision` response，斷言 proposal 列表、`scan_this_run` / `skip_this_run` action、rescan request shape。
- 影響範圍：`viewerApi.ts`、`viewerStore.ts`、`App.tsx`、未來 scan flow components、`frontend/API_CONTRACT.md`。

### A-5：Floating inspector / progress meter 的 accessibility hardening 尚未完成（repo 實際觀察）
- 嚴重程度：Low
- 來源：`frontend/src/components/DetailPanel.tsx` 有 Escape close，但未設定 `role="dialog"`、`aria-modal`、focus trap；`frontend/src/components/ProgressStrip.tsx` 的 progress meter 只有 `aria-label="scan progress"`，未使用 `role="progressbar"` / `aria-valuenow`。
- 問題說明：目前已有基本 aria-label 與 Escape close，但 inspector 作為 floating panel 時，鍵盤焦點管理與螢幕閱讀器語意還不完整；progress 狀態也缺標準 progressbar semantics。
- 具體改善建議：Hardy Task 8 中補 focus trap / return focus、dialog semantics 或改為非 modal region 的明確語意、progressbar ARIA value；保留現有 Escape close。
- 重現方式：鍵盤打開 DetailPanel 後，用 Tab 導覽可離開 panel；螢幕閱讀器無法把它視為 dialog/progressbar。
- 建議測試方式：RTL + `@testing-library/jest-dom` 檢查 role/name/aria value；必要時用 Playwright 做鍵盤焦點 smoke。
- 影響範圍：`DetailPanel.tsx`、`ProgressStrip.tsx`、responsive inspector。

### A-6：前端沒有 no-secret display regression，會照實顯示後端傳來的 raw evidence value（repo 實際觀察）
- 嚴重程度：Medium（後端為主責，前端為最後一道顯示防線）
- 來源：`frontend/src/components/DetailPanel.tsx` 的 `EvidenceItem` 直接顯示 `evidence.value`；全 frontend 無 test runner（B-3），也沒有 no-secret fixture。
- 問題說明：React escape 可防 DOM XSS，但不能防止 raw secret 以文字形式出現在 UI。這主要應由後端 C-1/M-8 修補，但前端應有 fixture/test 防止 sample/API payload 把 `sk-...`、DSN userinfo 等直接顯示。
- 具體改善建議：前端測試加入 no-secret fixture；若接到疑似 secret 字串，至少在 dev/test 觸發 fail 或顯示安全警告。不建議前端自行重做主要 masking policy，避免與後端 source of truth 分裂。
- 重現方式：在 viewer payload fixture 的 `graph_view_model.details.evidence_by_id[*].value` 放 raw `DATABASE_URL=postgres://u:p@h/db`，UI 會照文字顯示。
- 建議測試方式：RTL render `DetailPanel`，餵 raw secret evidence，先以 failing test 鎖定；後續修補時確認顯示端不出現明文。
- 影響範圍：`DetailPanel.tsx`、sample/API payload fixture、C-1/M-8 修補驗收。

---

## B. 前端工程

### B-1：`fetch` 無 timeout / AbortController（= M-16，repo 實際觀察）
- 嚴重程度：Medium
- 來源：`frontend/src/services/viewerApi.ts:10-22`
- 詳見後端檔 M-16。補充：`useViewerPayload`（`hooks/useViewerPayload.ts:6-11`）設 `retry:false`（好，不會無限重試），但 fetch 本身無逾時，連到 hang 住的 server 時 query 永遠 `isFetching`，UI 停在 loading overlay。
- 建議：`AbortController` + 逾時（10-15s）。
- 重現方式：API mode 指向接受連線但不回應的 endpoint，query 會一直 loading。
- 建議測試方式：Vitest fake timers + mock `fetch` never resolve，斷言逾時後 abort 並進入 error state。

### B-2：互動 lifecycle typed coverage 不足（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`frontend/src/types.ts:98-107`（`ai_system_map: z.record(z.unknown()).and(...)`）、`:110-113`（`trace_result_samples`/`detail_scan_result_sample`/`mapping_proposal_result_sample`/`invalid_map_error_sample` 皆 `z.record(z.unknown())`）
- 問題說明：前端並非完全無型別；`viewer_load_result`、`graph_view_model` 等 viewer subset 有 Zod schema。真正缺口是對 `detail_scans[]`、mapping proposal lifecycle、project/scan lifecycle 與 sample result 區塊仍使用 loose record。一旦要接真實互動 API（unfinish 20a/21a/24b），缺 typed schema 容易出錯。
- 為什麼需要改進：目前 L2/L3 tab、proposal buttons 是 sample placeholder（符合現況），但接真實 API 前需先補 typed contract，否則 runtime 才會發現 shape 不符。
- 建議：為要接線的互動 lifecycle 補 zod schema（對應後端 `web/schemas.py`），並在 `App.tsx`/`DetailPanel` 用 typed access。
- 重現方式：把 detail/proposal sample payload 欄位拼錯，TypeScript 不會在編譯期提醒，Zod 也只把它當 unknown record。
- 建議測試方式：為 detail scan / mapping proposal / project scan response schema 寫 Zod parse success/failure test。
- 影響範圍：`types.ts`、`DetailPanel.tsx`、未來互動 API helper。

### B-3：前端完全無 test runner（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`frontend/package.json` scripts 只有 `dev`/`build`/`lint`，無 `test`
- 問題說明：與 `AGENTS.md`/check1 第 109、110 點一致——前端互動 issue 缺 regression 防線。任何 graph render、filter highlight、API error、boundary decision、proposal/detail scan 互動都無自動測試。
- 建議：導入 Vitest + React Testing Library，最小測試：graph render smoke、detail modal open/close、filter highlight 不隱藏 graph、API error 不 crash、`viewerApi` schema parse。對應 Hardy Task 7 與 Timmy 20a/21a/24b。
- 重現方式：`frontend/package.json` scripts 只有 `dev` / `build` / `preview` / `lint`，執行 `pnpm test` 會找不到 script。
- 建議測試方式：新增 `pnpm test`，至少跑上述 smoke/schema tests，CI（H-6）落地後納入。
- 影響範圍：整個 frontend；CI（H-6）落地後納入。

### B-4：`scanProgressEvent` 解析失敗時靜默轉成 warning 事件（repo 實際觀察，偏正面）
- 嚴重程度：Low
- 來源：`frontend/src/services/viewerApi.ts:50-62`（`parseScanProgressEvent` 失敗回 `{event:"invalid_event", status:"warning", ...}`）、`hooks/useScanProgress.ts:27-30`（`onerror` close + mock 警告）
- 問題說明：SSE 解析失敗不會 crash（好），但會被當成一個 progress 事件吞掉，開發時不易發現後端送了非預期格式。屬可接受的容錯設計，記錄備查。
- 建議：開發模式下對 `invalid_event` 額外 `console.warn` 原始資料以利除錯。
- 重現方式：呼叫 `parseScanProgressEvent("{not-json")` 會回 warning event，而不是在 dev console 保留原始錯誤。
- 建議測試方式：schema parse test 鎖定 warning event；dev mode 額外測 console.warn（若實作）。

### B-5：EventSource / interval 生命週期管理正確（repo 實際觀察，正面記錄）
- 來源：`hooks/useScanProgress.ts:14-35`（`useEffect` 回傳 `eventSource.close()`）、`App.tsx:123-144`（兩個 `setInterval` 都在 cleanup `clearInterval`，且用 `useViewerStore.getState()` 讀最新 index 避免 stale closure，interval 只在 run 切換時重建）。`handleScanEvent`/`handleScanError` 用 `useCallback` 包住（`App.tsx:100-112`），避免 `useScanProgress` 的 effect 因 function identity 改變而反覆重連。
- 結論：無 memory leak、無多重 interval。此為良好實作。

### B-6：無前端程式碼注入面（repo 實際觀察，正面記錄）
- 來源：對整個 `frontend/src` 進行注入面 grep（涵蓋危險 HTML 注入屬性、動態程式碼執行 API、外部連結屬性等樣式）**皆無命中**。所有後端資料（label、evidence value、rationale）都透過 React 文字節點或 `formatValue()`（`utils/format.ts:5-15`，`JSON.stringify`）渲染，由 React 自動 escape。
- 結論：DOM-based 跨站腳本注入風險低。唯一需注意的是 B-2 提到的 LLM rationale 顯示（內容真實性，非注入），已在後端 M-15 記錄。

---

## 已檢查、未發現明顯問題的區塊（前端）

- **狀態管理**：`store/viewerStore.ts` 用 zustand，state 切片清楚；`setSelected` 連帶 reset `detailMode`、`setDataSourceMode` 連帶清 `liveProgressEvent`、`resetFocus` 一次重置多個互動狀態——狀態轉換一致。目前無 project/scan/boundary/proposal lifecycle state（符合現況，前端互動 API 尚未接線）。
- **資料來源誠實性**：`App.tsx:37-48` state matrix 明確區分 loaded/loading/error/pending；`StateOverlay` 在 API 失敗時**不偷偷顯示 sample**，需使用者明確點 "Use sample data"（`StateOverlay.tsx:14-16` 註解與實作一致）—— 避免 demo 誤認，是正確的產品決策。
- **React Query 設定**：`useViewerPayload` `retry:false`、sample 模式 `staleTime: Infinity`、api 模式 `5_000`，queryKey 含 mode + apiBaseUrl（切換會重新查詢）——合理。
- **filter 語意**：`viewerStore.toggleFilter`/`clearFilters` 與 `Sidebar` 是 highlight 而非 hide（符合 check1 第 92 點 release-readiness 需保留完整脈絡）。
- **ErrorBoundary / 入口**：`main.tsx` 用 `React.StrictMode` + `ErrorBoundary` + `QueryClientProvider` 包住 App，render crash 進 ErrorBoundary 不致空白頁。
- **TypeScript / ESLint**：`tsconfig.json` strict、`eslint.config.js` 含 react-hooks 規則；`pnpm run lint` 通過、`pnpm run build` 的 `tsc -b` 通過——無 `any` 濫用跡象（types 用 zod infer）。
- **build 設定**：`vite.config.ts` 已分 react/graph/icons manual chunks；主 chunk 偏大（M-17）但 graph chunk 281KB（reactflow+elkjs）屬預期。
- **format helper**：`utils/format.ts` 的 `compactId`/`formatValue`/`titleCase` 純顯示用，不改 canonical id、不判斷 backend truth（符合 check1 第 124 點）。

---

## 與既有 unfinish issue 的對應（提醒，非本次修補範圍）

前端「真實互動 lifecycle 尚未接線」是**已知且符合現況**的狀態，不是本次新發現的缺陷；相關工作已在既有 plan：
- `unfinish/24b-implement-project-scan-and-boundary-decision-frontend-flow.md`
- `unfinish/21a-implement-detail-scan-frontend-flow.md`
- `unfinish/20a-implement-ai-mapping-proposal-frontend-flow.md`
- Hardy `unfinish/07-add-viewer-regression-tests.md`、`08-hardening-responsive-accessibility-performance.md`

本次前端發現中，B-2（typed schema）、B-3（test runner）、A-1/A-2（錯誤狀態文案）、A-4（project scan / boundary flow）、A-5（accessibility hardening）、A-6（no-secret display regression）、M-16（fetch timeout）建議在執行上述 issue 時一併處理，而非另開獨立修補。

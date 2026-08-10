# 2026-08-10 前端 build-scoped 下載接線（Stage 3）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-10-build-scoped-report-download-TODO.md`
- 分支：`main`（不 commit，改動留在 working tree）
- 對應計畫：`docs/work/Meeting-Sync/meeting_sync_2026_08_10/frontend-build-scoped-report-download.md`

> **2026-08-10 追記（同日稍晚）：本階段的前端改動已全數退回。**
> 分工調整——本 repo 這輪由後端 owner 負責，前端另有 owner。退回範圍：
> `frontend/src` 全部改動（8 檔）與 `API_CONTRACT.md` 的兩段前端視角
> 敘述（該檔後端所寫的契約章節保留）；退回後 `pnpm lint/test/build`
> 全綠回到基線 160/160。本 REP 以下記載的實作與測試結論**仍然有效**，
> 完整保存為交接資料：計畫檔改寫為交接版（含已驗證設計決策與陷阱），
> 參考實作以 `frontend-build-scoped-report-download-reference.patch`
> 保留（擷取自 182/182 全綠狀態，`git apply --check` 驗證可乾淨套用）。

## 實作邏輯

使用者在 Viewer 點「下載」時，拿到的必須是**畫面上那個 build** 的
`ai_system_map.md`。effective build id = `activeBuildId ??
viewer_load_result.build_id`——pin 歷史 build 就下載歷史 build，跟隨
latest 就下載 latest，FE-3 時代的「歷史 build 停用/警示」邏輯整組不需要。
錯誤處理收斂在 service 邊界：三個契約 404 碼對應明確狀態文案，其餘一律
`unknown`，原始網路錯誤字串在物理上到不了畫面。

## 步驟與產出

1. **`fetchText`**（`src/services/http.ts`）：把 `fetchJson` 重構出共用
   core（timeout、AbortSignal、`ApiRequestError` 同一條路徑），兩個薄
   reader 只差 `res.json()` / `res.text()`——鏡像關係不會漂移。
2. **`mapReportApi.ts`**：`loadMapBuildReport(baseUrl, buildId, signal?)`
   （buildId `encodeURIComponent`）；錯誤分類**只在 status===404 時**
   認契約碼（`build_not_found` / `artifact_not_available` /
   `artifact_not_found`），422、transport error、routing-level
   `"Not Found"` 全歸 `unknown`；下載採 fetchText → Blob → object URL →
   DOM-attached anchor click，檔名固定 `ai_system_map.md`，object URL
   下一個 macrotask 釋放（Firefox 相容）。
3. **ReadinessPanel**：對話框 header 下方獨立一列「Download report
   (.md)」入口（tablist 之外，所有 panel 狀態可見）；Sample mode 或
   build id 為 null 時隱藏；下載中/失敗（依分類文案）/成功三態都有呈現；
   三個契約 404 依 API_CONTRACT 指引停用按鈕（不提供無意義的 retry），
   `unknown` 保持可重試；`<BuildReportDownload>` 以 build id 為 key，
   換 build 自動重置狀態。`ReadinessPanel.tsx` 過時註記與對應測試 regex
   同步更新。
4. **契約核對**：`API_CONTRACT.md` 章節與後端實作逐欄一致（並對
   `map_build_routes.py` 原始碼再驗一次），補前端視角段落（為何不送
   `download=true`、送哪個 build id、Sample mode 隱藏、與「Generated
   Markdown」分頁是兩份不同文件）。

## 明確不碰（計畫排除項，已驗證）

- `viewerApi.ts` 的 `mapEndpoints` 死碼 fallback（FE-2 範圍）——未動。
- 「Generated Markdown」分頁行為——未動（僅過時註記文案更新）。
- `/api/map/report`——`frontend/src` 引用維持 0。

## 遇到的問題與解法

1. **jsdom 沒有 `URL.createObjectURL`**：測試 stub 這兩個 primitive，
   但其餘全走真物件——真 Blob（驗 MIME 與內容）、真 anchor（click 當下
   驗 `download`/`href`/`isConnected`、事後驗已移除）。
2. **required prop 的漣漪**：`buildId` 設為必填後 13 個
   `<ReadinessPanel>` call site 全部要補——由 tsc 逐一抓出補齊，不用
   `as` 蒙混。
3. **延遲 revoke 與測試 stub 的生命週期衝突**：self-review 抓到 timer
   活得比 stub 久的潛在 flake，修在測試等待邏輯而非刪掉延遲行為。

## 測試方式與結果

- TDD：三個實作 task 各有 RED→GREEN 證據（fetchText 5 紅→7 綠；
  mapReportApi 模組不存在→10 綠；ReadinessPanel 5 紅→12 綠）。
- 全套 gate：`pnpm lint` 0 errors（1 個既有 warning 在未觸碰檔案）、
  `pnpm test` **182/182**（36 檔）、`pnpm build` 綠。
- Reviewer 驗證：pin 歷史 build 下載打的是該 build 的 URL、Sample mode
  隱藏鏈路、錯誤文案不含原始錯誤字串、與後端 route 原始碼逐欄一致——
  全數通過，無 Critical/Important issue（4 個 minor 打磨項記錄於
  ledger，見 wrap-up REP）。

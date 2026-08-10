# 前端接上 build-scoped Markdown report 下載 — 實作計畫（交接版）

Status: **planned — 交接給前端 owner**（2026-08-10：後端端點已完成
並通過全部驗證；本計畫同日曾由後端側完整實作並通過
兩輪 review，因前後端分工，前端改動已自 repo 退回。完整參考實作以
patch 形式保留（§8），已驗證的設計決策與陷阱見 §7——照著做可以直接
一次到位。GitHub issue 待開，開立後回填編號）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者在 Viewer 內下載**當前檢視那個 build** 的
`ai_system_map.md`，透過後端端點
`GET /api/map-builds/{build_id}/artifacts/ai_system_map.md`。

**Architecture:** 純前端接線。後端端點由主計畫
`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/download.md`
提供，**已完成**（2026-08-10，含 `GET /api/map/report` 硬退役）——本計畫
不再被後端 gate。

**Tech Stack:** React + TypeScript、既有 `services/http.ts` 取用層。

---

## 1. 取代與分工

- **取代 FE-3**（`meeting_sync_2026_08_06/04-wire-frontend-map-report-download.md`，
  檔頭已標 superseded）：FE-3 接的是 process-wide `/api/map/report`，有
  「靜默給錯檔案」限制；該端點已於 2026-08-10 退役，本計畫打 build-scoped
  端點，FE-3 的「僅最新／歷史 build 停用」警示邏輯**全部不需要**。
- **不重複 FE-2**：`viewerApi.ts:11` 的 `mapEndpoints = ["/api/map", "/map"]`
  死碼 fallback 清理屬 FE-2
  （`meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`），
  本計畫不碰。

## 2. 後端契約現況（2026-08-10 已上線、已實測）

契約全文見 `frontend/API_CONTRACT.md` §「Build Artifact Download」，重點：

```http
GET /api/map-builds/{build_id}/artifacts/ai_system_map.md        # 行內讀取
GET /api/map-builds/{build_id}/artifacts/ai_system_map.md?download=true
```

- 200 body 是檔案**原始 bytes**（byte-identical，不做換行轉換），
  `Content-Type: text/markdown; charset=utf-8`。
- 404 三態（plain-string `detail`，檢查順序固定）：`artifact_not_found`
  （白名單外）→ `build_not_found`（build 不存在）→
  `artifact_not_available`（檔案不在磁碟）。
- `?download=banana` 這種格式錯誤回 **422** 且 `detail` 是 array——
  不能寫「所有錯誤都是 404」的 handler。
- routing 層對 `..%2F...` 回 FastAPI 預設 `404 {"detail": "Not Found"}`
  ——`detail` 不是三碼之一的 404 一律當 generic failure，不得對映。
- 所有回應不含 server-local absolute path。
- 可用 `scripts/trace_map_build_artifact.sh --start-server` 對本機驗證。

## 3. 流程

```text
  [Load Viewer]                              (existing, unchanged)
  map-builds latest / {build_id}  ---->  build_id + graph + readiness JSON
                                              |
                                              v
                                    canvas / Readiness panel

  [User clicks "Download report"]            (new in this plan)
  effective_build_id = activeBuildId ?? viewer_load_result.build_id
        |
        v
  GET /api/map-builds/{effective_build_id}/artifacts/ai_system_map.md
        |
        v
  markdown content -> Blob -> browser save as "ai_system_map.md"
```

載入畫面**只**打 map-builds；下載端點**只**在使用者點擊時打，不隨
map load 自動觸發。

## 4. 重要區別：這是第三份文件，不是取代既有 Markdown 分頁

| 文件 | 產生方式 | 內容 |
|---|---|---|
| ReadinessPanel「Generated Markdown」分頁 | **前端** `buildReadinessMarkdown` 即時產生 | readiness 評估 |
| `ai_system_map.md`（本計畫要接的） | **後端**發佈成 build sibling 檔案 | 系統地圖的人類可讀報告 |

兩者不是同一份，不可互相取代；既有分頁行為不變。

---

## Task 1: 新增 text 取用能力

**Files:**
- Modify: `frontend/src/services/http.ts`、`frontend/src/services/http.test.ts`

- [ ] **Step 1:** 新增 `fetchText`——與 `fetchJson` 共用同一個私有
  `request` core（timeout、caller-signal 與 timer 的區分、
  `ApiRequestError` 形狀、`finally clearTimeout` 全走同一條路徑），兩個
  薄 wrapper 只差 body reader 與預設 `Accept`；`readBody` 要 `await` 在
  timer 生效範圍內（stalled body 也要吃 timeout）
- [ ] **Step 2:** 單元測試：成功回傳字串、非 2xx 丟 `ApiRequestError`、
  timeout 行為與 `fetchJson` 一致

## Task 2: 新增 map report service

**Files:**
- Create: `frontend/src/services/mapReportApi.ts`、
  `frontend/src/services/mapReportApi.test.ts`

- [ ] **Step 1:** `loadMapBuildReport(baseUrl, buildId, signal?)` →
  `GET /api/map-builds/{buildId}/artifacts/ai_system_map.md`，回傳
  markdown 字串（`buildId` 需 `encodeURIComponent`，比照 `viewerApi.ts:71`）
- [ ] **Step 2:** 錯誤分類成 `MapReportError`（reason:
  `build_not_found` / `artifact_not_available` / `artifact_not_found` /
  `unknown`）：契約碼**只在 `status === 404` 時**採認；422、transport
  error、timeout、routing 層 `"Not Found"` 一律 `unknown`——原始錯誤
  字串在物理上到不了畫面
- [ ] **Step 3:** 下載採 **fetchText + Blob + object URL** 觸發存檔
  （檔名固定 `ai_system_map.md`；不送 `download=true`，理由見 §7-1）；
  anchor 必須先 append 進 document 再 click（Firefox），object URL 在
  **下一個 macrotask** 才 revoke（同 task revoke 可能取消下載）
- [ ] **Step 4:** service 測試（mock HTTP）：URL 逐字元斷言（含
  `%3A` encode）、三個 404 reason 對映、`unknown` 對映、真 Blob 內容與
  MIME、click 當下 anchor 的 `download`/`href`/`isConnected`、事後
  anchor 已移除、revoke **先驗證尚未發生**（`not.toHaveBeenCalled()`）
  再 flush macrotask 後驗證已發生——鎖住延遲 revoke 行為本身

## Task 3: 接進 UI

**Files:**
- Modify: `frontend/src/components/ReadinessPanel.tsx`、
  `frontend/src/components/ReadinessPanel.test.tsx`、
  `frontend/src/App.tsx`（傳 `buildId` prop）、`frontend/src/styles.css`

- [ ] **Step 1:** ReadinessPanel 對話框 header 下方獨立一列
  「Download report (.md)」入口（放 `role="tablist"` 之外——tablist 裡
  塞非 tab 按鈕是 a11y violation）；effective build id =
  `useViewerStore` 的 `activeBuildId ?? props.buildId`（`activeBuildId`
  在 `store/viewerStore.ts:10`；`buildId` prop 由 `App.tsx` 傳
  `payload.viewer_load_result.build_id`，nullable 見 `types.ts:266`）；
  `dataSourceMode !== "api"` 或 build id 為 null 時**隱藏**入口
- [ ] **Step 2:** 三種狀態明確呈現：下載中、失敗（依 reason 給文案，
  `role="status"` 朗讀）、成功；三個契約 404 對該 build 是**定局**——
  停用按鈕、各給不同文案（比照 API_CONTRACT 每碼的處理指引）；只有
  `unknown` 保持可重試
- [ ] **Step 3:** 文案語意是「下載**此 build** 的報告」（元件現有 UI
  文案為英文，沿用英文）；**不需要**任何「僅最新／歷史 build 停用」
  警示；pin 歷史 build 時入口照常可用
- [ ] **Step 4:** 元件以 build id 為 `key`（`<BuildReportDownload
  key={buildId}>`）——換 build 自動重置 settled 失敗狀態，A build 的
  定局不能鎖死 B build 的下載
- [ ] **Step 5:** 修正 `ReadinessPanel.tsx:228` 既有註記（現況寫
  「No standalone Markdown artifact preview or download is available…」，
  後端上線後已過時），並同步更新 `ReadinessPanel.test.tsx:86` 以該文案
  regex 的斷言，否則 `pnpm test` 會紅
- [ ] **Step 6:** 元件測試涵蓋：跟隨 latest 下載打 envelope 的
  build_id、pin 歷史 build 下載打的是**該** build_id、404 文案不洩漏
  原始錯誤字串、vanished build 導向 build history、換 build 重置失敗
  狀態、Sample mode 與無 build id 都不顯示入口

## Task 4: 契約文件補回前端段落

**Files:**
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1:** 後端已寫好「Build Artifact Download」章節（端點事實
  與每個錯誤碼的前端處理指引）。前端落地後，在該章節錯誤表之後**補回**
  以下兩段前端視角敘述（2026-08-10 曾隨參考實作寫入、隨退回移除，
  原文照抄即可）：

  > The viewer reads this endpoint through `services/mapReportApi.ts` and saves the
  > bytes itself (`Blob` + object URL + download anchor), so it never sends
  > `download=true`: a browser navigation would hand the response to the download
  > manager and hide exactly the 404 codes above. `loadMapBuildReport` turns each
  > code into a `MapReportError` reason and the UI renders copy per reason, so no
  > transport or backend error string reaches the screen. The build id it sends is
  > the one on screen — the pinned historical build when there is one, otherwise
  > `viewer_load_result.build_id` — and the entry is hidden in Sample mode, which
  > has no backend to read from. The saved file keeps the whitelist name
  > `ai_system_map.md`.
  >
  > That artifact is the build's rendered map report. It is a different document
  > from the Readiness dialog's "Generated Markdown" tab, which is plain text the
  > frontend generates from the inline `readiness-report/v1` payload; neither
  > substitutes for the other.

---

## 5. 驗收標準

1. 於 BuildHistoryMenu pin 歷史 build A（即使有較新的 B），下載內容與
   `outputs/build_<A>/ai_system_map.md` byte 一致。
2. 跟隨 latest 時，下載的 `build_id` 與畫面 envelope 的 `build_id` 相同。
3. 報告檔不存在時顯示明確狀態文案，不出現原始網路錯誤字串。
4. ReadinessPanel「Generated Markdown」分頁行為不變（兩份文件並存）。
5. `frontend/src` 內無任何 `/api/map/report` 引用（本來就是 0，維持 0）。
6. 延遲 revoke 行為被測試鎖定（同步 revoke 會讓測試失敗——已用
   bite-test 驗證過這個斷言真的咬得住）。
7. `pnpm lint`、`pnpm test`、`pnpm build` 全綠。

## 6. 風險

- ~~後端未合併先動工~~——後端已完成；動工前 `curl` 或
  `scripts/trace_map_build_artifact.sh` 對本機確認即可。
- **與 FE-2 的檔案重疊**：兩計畫都會碰 `viewerApi.ts` 周邊；先後合併時
  以 rebase 處理，功能無相依。
- **檔名寫死**：`ai_system_map.md` 與後端白名單一致；後端日後開放
  `.mmd` 時本 service 以參數化 `fileName` 擴充即可（本計畫不做）。

---

## 7. 已驗證的設計決策與陷阱（2026-08-10 參考實作的 review 結論）

以下每一條都在參考實作中做過、並被獨立 reviewer 驗證過——照抄能避開
全部已知的坑：

1. **不送 `download=true`**：瀏覽器 navigation 會把回應交給 download
   manager，前端就看不到 404 碼；改用 fetch 拿 bytes 自己存，錯誤狀態
   才可控可測。`Content-Disposition` 因此對前端無用武之地。
2. **錯誤分類只認 `status === 404` 的契約碼**：422（array detail）、
   routing 層 `"Not Found"`、timeout 全走 `unknown`——否則 backend 換
   framework 預設文案就會誤判。
3. **Firefox 兩件事**：anchor 必須 `document.body.append` 後才 click；
   object URL 要 `setTimeout(..., 0)` 延後 revoke（同 task revoke 可能
   取消剛啟動的下載）。測試要「先斷言 revoke 未發生、flush 後再斷言
   發生」，否則未來被「簡化」成同步 revoke 不會有測試抓。
4. **`<BuildReportDownload key={buildId}>`**：settled 404 是「該 build
   的定局」，key 重置讓它不會漏到別的 build（防禦性——目前換 build 時
   dialog 本來就會 unmount，但一行 key 讓這件事 correct-by-construction）。
5. **`buildId` 設為必填 prop**：讓 tsc 強迫每個 call site 表態自己指的
   是哪個 build——參考實作中這個決定靠 compiler 抓出 13 個 call site
   逐一補齊，沒有一個用 `as` 蒙混。
6. **jsdom 沒有 `URL.createObjectURL`**：只 stub 這兩個 primitive，
   其餘走真物件——真 Blob（驗 MIME + `await blob.text()` 驗內容）、真
   anchor（click 當下驗 `isConnected: true`）。不要把整條鏈 mock 成
   套套邏輯。
7. **停用 vs 可重試**：三個契約 404 都「對該 build 不會因重試而改變」
   ——停用按鈕並各給不同文案（`build_not_found` 導向 build history；
   `artifact_not_available` 明說該 build 沒發佈報告；`artifact_not_found`
   是契約不同步的 caller bug）；`unknown` 才保留重試。
8. **入口放對話框 header 下、所有 panel 狀態都可見**：unsupported
   contract 狀態時 inline 報告渲染不了，但該 build 的 artifact 可能
   存在——這時下載入口反而最有價值。
9. **選配打磨項**（參考實作的 reviewer minor，未做、可自行取捨）：
   停用瞬間鍵盤焦點會落回 `<body>`（可改 `aria-disabled` + no-op）；
   `unknown` 文案只點名 server 未啟動一種原因；「Saved…」措辭其實只能
   證明 click 已派發（可改「Sent to your downloads」）。

## 8. 參考實作 patch

同資料夾的
`frontend-build-scoped-report-download-reference.patch`（800 行、8 個
檔案：`http.ts`＋測試、`mapReportApi.ts`＋測試（新檔）、
`ReadinessPanel.tsx`＋測試、`App.tsx` 1 行接線、`styles.css` 6 行）。

- 這份 patch 擷取自 2026-08-10 通過全部 gate 的狀態（`pnpm lint` 0
  errors、`pnpm test` 182/182、`pnpm build` 綠），並經過 spec+quality
  review 與 scoped re-review。
- 在乾淨的 `frontend/` 上 `git apply <patch>` 可整包還原（擷取當下已
  `git apply --check` 驗證可乾淨套用於 HEAD `52931d6`）；也可以只當
  對照組、照 Task 1-4 自己寫。
- 套用後記得補 Task 4 的契約段落（patch 不含 `API_CONTRACT.md`——該檔
  的契約章節屬後端所有、已在 repo 裡）。

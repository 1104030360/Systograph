# 前端接上 `GET /api/map/report`（Markdown report 預覽／下載）實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue 待開。相關 issue #219
`[Frontend][Blocked] feat: connect safe build-scoped artifact preview and
download` 仍 OPEN——本計畫是它的**縮小範圍先行版**：只接現有的
process-wide Markdown 端點，不等 build-scoped artifact API）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** 待開（開立後回填編號；本計畫是前端工作包 FE-3，後端 umbrella
issue #277 不含本計畫，issue 由前端自行開立）

> **2026-08-06 ownership 註記：** 本計畫**全份為前端工作**（後端零改動），
> handoff 為工作包 **FE-3**（同資料夾的
> `frontend-web-boundary-refactor-handoff.md`）。
>
> **2026-08-07 搬移註記：** 本檔已依使用者指示自
> `docs/work/Timmy/schedule/plan/unfinish/refactor/` 搬到本 handoff 資料夾，
> 與 FE-3 工作包同住；refactor 佇列不再保留副本（原編號 04 保留於檔名，
> 索引見 `docs/work/Timmy/schedule/plan/unfinish/README.md`）。

> **2026-08-07 依賴確認：** 後端本輪執行的 Plans 01B/02B/03/05/06/07/08
> （umbrella issue #277）會刪掉 `GET /api/map`、`GET /map`、
> `POST /api/map/build`，但**明確保留 `GET /api/map/report`** 與它依賴的
> `session_store.latest_build_result`（見
> `docs/work/Timmy/schedule/plan/finish/refactor/02-retire-process-wide-api-map.md`
> 的「不動」清單、`plan/finish/refactor/03-retire-api-map-build.md` 的同名段落，以及
> Plan 08 的驗收標準）。因此本計畫依賴的端點與下方「已知限制」皆不會消失；唯一影響是
> 同檔案的鄰居 handler 被刪後，Source 段引用的 `map_routes.py`、
> `session_store.py` 行號會位移，行為與契約不變。

**Goal:** 讓前端可以取得並下載後端已發佈的 `ai_system_map.md`，透過現有的
`GET /api/map/report`（`?download=true` 觸發附件下載）。

**Architecture:** 純前端工作，後端不動。新增一支 text（非 JSON）取用的
service，接進既有 UI。**本計畫刻意不做** build-scoped artifact API 與
`.mmd` 下載——那兩項屬 #219 的完整範圍。

**Tech Stack:** React + TypeScript、既有 `services/http.ts` 取用層。

---

## ⚠️ 已知限制（實作與 UI 文案都必須反映）

**`GET /api/map/report` 回的是後端當下認定的那個 latest build 的 Markdown，
不是使用者當前正在檢視的那個 `build_id`。**

證據（`src/systograph/web/routes/map_routes.py:45-72`）：

```python
result = store.latest_build_result()   # 無 build_id 參數
if result is None or result.map_markdown_path is None:
    raise HTTPException(status_code=404, detail="map_markdown_not_available")
```

這個「latest」由預設的 `PersistentSessionStore`（`web/app.py:239`）解析，範圍比
「本次 process 內建過的圖」更寬（`web/session_store.py:204-218`）：

- 先回 process 內快取的那份 build result；而該快取會被其他 route 順手覆寫——
  `trace_routes.py:48`、`mapping_proposal_routes.py:126` 呼叫
  `store.build_result(project_id)`，它會把**該專案的最新 build** 寫回快取
  （`session_store.py:231`）。
- 快取為空時（例如後端剛重啟）改掃 durable state 中**所有專案**的 latest
  pointer，回其中最新的那個。所以它不只跨 build，還會**跨專案**。

實務後果：使用者若透過 BuildHistoryMenu 切到**歷史 build**，或在多專案情境
下操作，按下下載拿到的會是**另一份 md**（可能是別的 build，甚至別的專案），
而不是他畫面上正在看的那份。這是**靜默給錯檔案**，比報錯更糟。

因此本計畫的處理原則是 **UI 誠實標示，而非假裝正確**：

- 入口文案定位為「下載**最新**掃描報告」，不得寫成「下載這個 build 的報告」。
- 當使用者正在檢視歷史 build（`activeBuildId != null`）時，必須顯示
  明確提示或停用入口——不得讓使用者以為拿到的是當前 build 的內容。

**後續 refine：** 這段邏輯待 build-scoped artifact API 完成後修正（issue
#219；預期形狀類似 `GET /api/map-builds/{build_id}/artifacts/{name}` 加檔名
白名單，屆時可一併涵蓋 `system_map.mmd` 與 `execution_map.mmd`）。屆時本計畫
新增的 service 改指新端點、移除上述限制文案即可。

---

## Source（判準基線，2026-08-06 對程式碼查核；2026-08-07 複查行號與內容仍相符）

- `src/systograph/web/routes/map_routes.py:45-72` — 端點實作：
  `text/markdown; charset=utf-8`；`?download=true` 時加
  `Content-Disposition: attachment; filename="ai_system_map.md"`（檔名寫死）；
  取不到檔時 404 + `map_markdown_not_available`。
- `src/systograph/web/session_store.py:204-218` ＋ `src/systograph/web/app.py:239`
  — 預設 store 對「latest build」的解析規則（見上方「已知限制」）。
- `src/systograph/core/providers/output_artifact_policy.py:25` — 磁碟檔名
  `ai_system_map.md`（`system_map.mmd` / `execution_map.mmd` 同樣有發佈，
  但**沒有任何 HTTP 出口**，不在本計畫範圍）。
- `frontend/src/services/http.ts` — 目前**只有 `fetchJson`**（會 `res.json()`），
  取 markdown 需另一支 text 取用函式。
- `frontend/src/components/ReadinessPanel.tsx:228` — 現有註記明講
  「No standalone Markdown artifact preview or download is available without a
  safe build-scoped artifact endpoint」，本計畫落地後需同步修正。

## 重要區別：這是**第三份**文件，不是取代現有的 Markdown 分頁

| 文件 | 產生方式 | 內容 |
|---|---|---|
| ReadinessPanel「Generated Markdown」分頁 | **前端**由 `buildReadinessMarkdown(report, graph)` 即時產生 | readiness 評估 |
| `ai_system_map.md`（本計畫要接的） | **後端** `graph_markdown_renderer.render(graph)` 發佈成檔案 | 系統地圖的人類可讀報告 |

兩者**不是同一份**，不可互相取代。實作時不得把新內容覆蓋既有分頁。

---

## Task 1: 新增 text 取用能力

**Files:**
- Modify: `frontend/src/services/http.ts`

- [ ] **Step 1: 新增 `fetchText`（或等價函式）**——沿用 `fetchJson` 既有的
  timeout、`AbortSignal`、`ApiRequestError` 錯誤形狀，差別只在
  `res.text()` 而非 `res.json()`
- [ ] **Step 2: 單元測試**：成功回傳字串、非 2xx 丟 `ApiRequestError`、
  timeout 行為與 `fetchJson` 一致

## Task 2: 新增 map report service

**Files:**
- Create: `frontend/src/services/mapReportApi.ts`

- [ ] **Step 1: `loadMapReport(baseUrl, signal?)` → `GET /api/map/report`**，
  回傳 markdown 字串
- [ ] **Step 2: 404 `map_markdown_not_available` 對應成可辨識的狀態**
  （尚未掃描 / 報告不存在），不要當成一般網路錯誤
- [ ] **Step 3: 下載採 `?download=true`**——直接開啟該 URL 讓瀏覽器處理附件，
  或以 `fetchText` 取得後自行建 Blob；擇一並在測試中鎖定行為
- [ ] **Step 4: service 測試（mock HTTP）**

## Task 3: 接進 UI

**Files:**
- Modify: 承載入口的元件（建議 `ReadinessPanel.tsx`，或 `MapStatusBar.tsx`
  視版面決定）
- Modify: `frontend/src/components/ReadinessPanel.tsx:228` 的既有註記
- Modify: `frontend/src/components/ReadinessPanel.test.tsx:86` — 現有測試以
  `/No standalone Markdown artifact preview or download/` 斷言該註記文案，
  改文案時必須同步更新，否則 `pnpm test` 會紅

- [ ] **Step 1: 加入「Markdown report」預覽或下載入口**，載入中／
  失敗／無報告三種狀態都要有明確呈現
- [ ] **Step 2: 文案標示為「最新掃描報告」**，不得寫成「這個 build 的報告」
- [ ] **Step 3: 檢視歷史 build 時（`activeBuildId != null`）顯示提示或停用
  入口**——理由見上方「已知限制」
- [ ] **Step 4: 修正 `ReadinessPanel.tsx:228` 的註記**——Markdown artifact
  下載已可用（但仍非 build-scoped），不得留下已過時的敘述
- [ ] **Step 5: 元件測試涵蓋：正常載入、404 無報告、歷史 build 提示**

## Task 4: 契約文件

**Files:**
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1: 新增 `GET /api/map/report` 條目**——標明
  `text/markdown`、`?download=true`、404 code，以及
  **「回 process-wide 最新 build，非指定 build」**這項限制
- [ ] **Step 2: 註明 build-scoped 版本待 #219**

---

## 驗收標準

1. 掃描完成後，前端可預覽／下載 `ai_system_map.md`，內容與
   `outputs/build_<uuid>/ai_system_map.md` 一致。
2. 尚未掃描時顯示明確的「沒有報告」狀態，不出現原始網路錯誤字串。
3. 檢視歷史 build 時，UI 明確表達「這是最新報告、可能不是當前 build」，
   或停用該入口。
4. ReadinessPanel 既有的「Generated Markdown」分頁行為不變（兩份文件並存）。
5. `pnpm lint`、`pnpm test`、`pnpm build` 全綠。
6. `frontend/API_CONTRACT.md` 已記載此端點與其 process-wide 限制。

## 風險

- **靜默給錯檔案**：本計畫最大風險，已於 Task 3 Step 2/3 以 UI 誠實標示
  處理；若省略該步驟，使用者會在歷史 build 情境下拿到錯誤內容而不自知。
- **與 #219 的關係**：本計畫是縮小範圍先行版。#219 落地後應回頭把 service
  指向 build-scoped 端點並移除限制文案，而不是並存兩套入口。
- **`.mmd` 不在範圍**：`system_map.mmd`、`execution_map.mmd` 雖已發佈到磁碟
  且記錄於 build manifest，但**後端完全沒有 HTTP 出口**，需等 #219。

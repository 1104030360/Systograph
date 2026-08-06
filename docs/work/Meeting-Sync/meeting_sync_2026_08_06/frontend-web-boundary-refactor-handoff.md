# Frontend Handoff — Web 邊界收斂（refactor 01–07 的前端工作包）

- 日期：2026-08-06
- 來源：`docs/work/Timmy/schedule/plan/unfinish/refactor/`（後端 refactor 佇列）
- 分工：**後端（Timmy）**執行 refactor 各計畫的 backend 部分；**前端**負責本文件
  的三個工作包。各計畫檔是驗收標準的 canonical source，本文件是可自足執行的
  handoff 摘要——兩邊若有出入，以計畫檔為準。
- **安全保證：前端未動工前，不會有任何東西壞。** 後端所有 breaking 移除
  （implicit preflight 分支、`GET /api/map`／`GET /map`）都 gate 在對應前端
  工作包上線之後才執行。

---

## 執行順序與 gate 總表

| 工作包 | 內容 | 解鎖的後端動作 | 建議順序 |
|---|---|---|---|
| **FE-2** | API mode 空狀態 + 移除 `/api/map` fallback | Plan 02 Phase B（刪 `GET /api/map`、`GET /map`） | ① 最小、先做 |
| **FE-3** | Markdown report 預覽／下載 | 無（獨立功能，#219 縮小版） | ② 小、獨立 |
| **FE-1** | Explicit preflight 兩段式掃描 | Plan 01 Phase B（刪 `create_scan` implicit 分支） | ③ 最大、最後 |

FE-2 內部順序固定：**先補空狀態、再拔 fallback**（順序反了會出現無圖可讀的死角）。

---

## FE-2：API mode 空狀態 + 移除 `/api/map` fallback

Canonical：[`refactor/02-retire-process-wide-api-map.md`](../../Timmy/schedule/plan/unfinish/refactor/02-retire-process-wide-api-map.md) Phase A

### 背景

`viewerApi.ts:11,40-51` 目前在 build-scoped 讀取失敗時 fallback 到
`GET /api/map` → `GET /map`。後端要退役這兩個 process-wide demo 端點，
但有一個死角：**API mode 尚未 import 任何專案時**（`activeProjectId == null`），
`useViewerPayload.ts:19-21` 會跳過 primary 直接打 `/api/map`——它是這個情境
唯一撐著畫面的東西。先拔 fallback 會讓使用者看到原始錯誤字串。

### Task 1：補「尚未選定專案」空狀態（**必須先做**）

- Modify：`frontend/src/hooks/useViewerPayload.ts`、`frontend/src/App.tsx`
- API mode 且 `projectId == null` 且 `buildId == null` 時**不發 request**
  （react-query `enabled: false` 或等價短路）
- 顯示明確空狀態（例：「Import a project to load a map」），不得沿用網路錯誤文案
- 元件測試覆蓋此狀態

### Task 2：移除 fallback

- Modify：`frontend/src/services/viewerApi.ts`、`viewerApi.test.ts`
- 刪除 `mapEndpoints = ["/api/map", "/map"]` 常數與 `:40-51` fallback 迴圈
- `loadApiViewerPayload` 的 `projectId` 改必填（`string`），失敗直接拋原始錯誤
- **保留 `parseViewerPayload`**——`data/sampleMap.ts:5,27` 的 Sample 模式仍依賴
- 補測試：primary 失敗直接 reject，不再有第二次 fetch
- 順帶修掉一個 silent failure：現行 `:32` 的 `catch` 會吞掉 zod 解析錯誤，
  契約漂移時靜默降級到 demo 端點而非報錯——移除 fallback 後這個問題自然消失

### Task 3：`frontend/API_CONTRACT.md`

- 刪 `GET /api/map` 條目（§Map Loading 已於 2026-08-06 標成 deprecated fallback，
  上線後改為整段移除）
- 其餘提及 `/api/map` 的敘述（詳見計畫檔 Task 3）

### 驗收

未選專案顯示空狀態、不發 request；讀圖只剩 `map-builds/latest` 與
`map-builds/{build_id}`；primary 失敗（含契約解析錯誤）直接呈現錯誤。
`pnpm lint / test / build` 全綠。**上線後通知後端執行 Plan 02 Phase B。**

---

## FE-3：Markdown report 預覽／下載

Canonical：[`refactor/04-wire-frontend-map-report-download.md`](../../Timmy/schedule/plan/unfinish/refactor/04-wire-frontend-map-report-download.md)（全計畫皆前端，後端零改動）

### ⚠️ 先讀這個限制

`GET /api/map/report` 回的是 **process session 最新 build** 的
`ai_system_map.md`（`map_routes.py:45-72`，無 `build_id` 參數）。使用者若在看
**歷史 build**，下載到的會是最新那份——**靜默給錯檔案比報錯更糟**。因此 UI
必須誠實標示：

- 入口文案 =「下載**最新**掃描報告」，不得寫「這個 build 的報告」
- `activeBuildId != null`（正在看歷史 build）時：顯示提示或停用入口
- build-scoped 版本等 issue #219 的 artifact API，屆時本功能改指新端點即可

### Tasks

1. **`http.ts` 加 `fetchText`**——端點回 `text/markdown`，現有 `fetchJson`
   會 `res.json()` 直接炸；沿用同一套 timeout / AbortSignal / `ApiRequestError`
2. **新增 `services/mapReportApi.ts`**——`GET /api/map/report`；
   404 `map_markdown_not_available` 對應成「尚無報告」狀態而非網路錯誤；
   下載走 `?download=true`（附件名固定 `ai_system_map.md`）
3. **接進 UI**（建議 `ReadinessPanel` 或 `MapStatusBar`）——載入中／失敗／
   無報告三態 + 上述歷史 build 守門；並修掉 `ReadinessPanel.tsx:228` 那句
   「No standalone Markdown artifact preview or download is available…」
   （本功能上線後即過時）
4. **`API_CONTRACT.md` 新增條目**——含 process-wide 限制與 #219 註記

### 一個容易混淆的點

ReadinessPanel 現有的「Generated Markdown」分頁是**前端**由
`buildReadinessMarkdown()` 即時算的 readiness 文件；本工作包接的
`ai_system_map.md` 是**後端**發佈的系統地圖報告。**兩份不同文件，並存，
不可互相取代。**

---

## FE-1：Explicit preflight 兩段式掃描（最大的一包）

Canonical：[`refactor/01-explicit-preflight-cutover.md`](../../Timmy/schedule/plan/unfinish/refactor/01-explicit-preflight-cutover.md) Phase A

### 背景

現行前端（`projectScanApi.ts:10-37`）從未送 `preflight_request_id`，
100% 走後端的 implicit compatibility 分支（先掃 → 被
`requires_boundary_decision` 擋 → 決定 → 再掃）。設計主路徑（Plan 20）是
explicit 兩段式。前端遷移完成後，後端才會退役 implicit 分支。

### Task 1：preflight service + zod schema

- Create：`frontend/src/services/scanPreflightApi.ts`
- `POST /api/projects/{project_id}/scan-preflights`；關鍵欄位：
  `preflight_request_id`（之後掃描要帶的單號）、
  `required_boundary_proposals[]`（必決項目）、
  `reviewable_excluded_page`（可覆寫 soft exclusions，**有分頁**：
  `next_cursor`，一頁上限 100）、`summary` / `blocked_summaries` / `warnings`

### Task 2：流程反轉

- Modify：`frontend/src/services/projectScanApi.ts` 與掃描入口接線
- 從「先掃再補票（兩次請求）」改為
  「**preflight →（有 required 就出 decision UI）→ 帶單號掃一次**」
- `StartScanOptions` 加 `preflightRequestId`；payload 加 `preflight_request_id`
- 無 required 項目時 preflight 後直接掃（一步到位）

### Task 3：Decision UI 三規則（Plan 20 明定）

- required 項目**不預選**，全部有 explicit decision 才可 submit
- decisions **只送 delta**（explicit 改動 + required 回答），不 echo 整份清單
- 每筆帶 `fingerprint`（directory 用 manifest fingerprint）與
  `selection_scope`（檔案 `exact_file`／目錄 `recursive_directory`）

### Task 4：stale token 與 fallback

- `preflight_request_id` 是**世界指紋不是 session token**（由 candidate set
  digest / policy digest / safety version 決定；後端不存 preflight state，
  scan 時整份重算比對）
- 接住 409：`inventory_preflight_stale` /
  `inventory_selection_target_missing` / `inventory_selection_target_changed`
  → 自動重新 preflight → **重新**收集 decisions（不得沿用舊答案）
- rescan 一律開新 preflight
- `requires_boundary_decision` 的處理邏輯**保留**當例外路徑（帶單號掃描時
  後端仍會重新 enumeration，可能冒出新 required 項目）

### 驗收

全程只發一次 `POST /api/scans` 且必帶單號；required 未收齊不能 submit；
payload 只含 delta；stale 時自動重走且不靜默沿用。
**上線後通知後端執行 Plan 01 Phase B。**

---

## FYI（前端不需動作，但先知道）

- **Plan 03 / 05 / 06 的後端移除對前端零影響**：`POST /api/map/build`、
  `POST /api/viewer/load`、v1 operator rollback 寫入路徑——前端從未呼叫。
- **`operator_rollback_active` 欄位保留、永遠 `false`**（Plan 06 採選項 A），
  `contracts/viewer.ts:295` 的 zod 不需改。
- **Plan 07 會改變畫布元件的落帶**（plane 改由 canonical type 推導，
  slot 誤填不再畫錯帶）：欄位與值域不變、前端零改動，但佈局會視覺移動；
  後端會附 before/after 截圖。risk hint 一句文案將去除 "rag-core-v1" 字樣。
- **Plan 15（legacy v1 完全退役）目前 Gate-4 未過**：未來輪到時才有前端工作
  （移除 `legacy-v1` viewer 相容解析等），現階段不動。

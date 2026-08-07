# 2026-08-07 Refactor 計畫查核更新（Stage 1）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-07-web-boundary-backend-first-TODO.md`
- 分支：`refactor/web-boundary-and-legacy-retirement`
- Umbrella issue：#277
- 範圍：`docs/work/Timmy/schedule/plan/unfinish/refactor/01–08` 共 8 份計畫檔

## 實作邏輯

phase10 任務要求「先逐個更新計畫檔、確保每份都更新完才進下一步」。計畫檔是
後續實作 subagents 的唯一需求來源（brief），其中任何過時行號或錯誤歸屬都會
直接變成實作錯誤，因此以「逐檔獨立查核、事實逐條實測」為原則：

1. 8 份計畫檔各派一個 Opus subagent，唯一可編輯檔案就是它負責的那份計畫。
2. 每條事實性敘述（行號、引用計數、grep 結果、issue 狀態、gate 前提）都要
   對現行程式碼實測，過時就地修正；不改決策、不改結構、不勾未執行 checkbox。
3. 主 agent 最終 review 全部 diff，並裁定跨計畫層級的執行順序問題。

## 步驟

1. 讀取 8 份計畫 + 13.7/13.8（已 done）+ Linus 思考模式 + AGENTS.md +
   FE handoff 文件，確立「後端先行」範圍（01B/02B/03/05/06/07/08；04 歸前端）。
2. 實測基線：`uv run pytest` 1136 passed, 1 skipped；`pnpm test` 160 passed。
3. 確認計畫引用的 issue 狀態：#219 / #140 / #239 皆 OPEN，與計畫記載一致。
4. 開 umbrella issue #277（標題「refactor: Web 邊界收斂後端先行」）。
5. 平行派出 8 個查核 subagents（Opus, max effort），收攏回報。
6. 主 agent review 全部 diff；補 Plan 03 兩處執行順序註記。

## 查核結果摘要

| 計畫 | 實質修正 | 阻斷級 |
|---|---|---|
| 01 | 無（17 個裸呼叫點 / 11 檔清單實測完全吻合），僅回填 #277 | 無 |
| 02 | `API_CONTRACT.md:75` 具名的是 map/build，歸屬改到 Plan 03 | 無 |
| 03 | handler 行號 22-34、helper 行號 187/202、測試表用途細分、gate 敘述 | 無 |
| 04 | 事實全對；補 2026-08-07 依賴確認（`GET /api/map/report` 本輪保留） | 無 |
| 05 | `ViewerSessionService` 實際持有者更正（publisher/manifest；
  `MapBuildService` 僅轉交）；app.py 只注入 `PersistentSessionStore` | 無 |
| 06 | 六檔測試清單事實補註（後兩檔僅欄位斷言，採 (A) 免動） | 無 |
| 07 | `metadata.legacy_slot` 消費者清單更正（移除 materializer、補
  node/endpoint slot 標籤）；C3b 阻擋原因改為 public 契約 | 無 |
| 08 | 事實全對（session_store 12 處逐行吻合），僅回填 #277 | 無 |

## 執行期裁定（主 agent，記錄於計畫檔）

1. **執行順序**：01B → 05 → 03 → 02B → 08 → 06 → 07。01B 最先是為了先把
   「造 build」helper 收斂成 explicit preflight 流程，後續遷移一次到位；
   05 先於 03 讓 `trace_viewer_load.sh` 直接刪除、不做將被丟棄的改寫。
2. **Plan 03 保護註記**：`test_map_routes.py:11-33` 兼驗 `GET /api/map`，
   是該端點全樹唯一正向覆蓋，Plan 03 階段只改前置、保留讀取斷言。
3. **Plan 08 範圍追加**：旁路槽移除後 `projection_service` 注入
   （兩個 store 建構參數 + `app.py:239` 注入線）成為死碼，一併清除。
4. **Plan 06 範圍追加**：`map_build_pipeline.py:115-119` census 註解在
   Task 2 之後會變孤兒，於 Task 6 一併改寫。

## 遇到的問題與解法

- **13.7/13.8 檔案不在 phase10 指定路徑**：已完成並移至
  `plan/finish/s1-v2-cutover/`（status: done, 2026-07-29）。以 finish 版
  作為最終驗收基準，收尾時逐項複驗其護欄未被本次改動破壞。
- **計畫間檔案重疊**（`trace_viewer_load.sh`、`API_CONTRACT.md:37/:75`）：
  以執行順序裁定歸屬，並在兩側計畫檔互相註記，避免重工或 no-op。

## 測試方式與結果

- 本階段純文件變更，不影響程式行為；動工前基線：後端
  **1136 passed, 1 skipped**、前端 **160 passed**（動工後各階段再驗）。
- 8 份計畫檔 diff 逐行 review：僅事實對齊與註記，checkbox 全數未勾。

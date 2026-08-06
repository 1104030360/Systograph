# 退役 process-wide `/api/map` demo surface 實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue #277。使用者決策：整個移除
process-wide `/api/map` demo 讀圖路徑，正式讀圖收斂為 build-scoped 端點。
**Step 0 文件前置已於 2026-08-06 完成**，見下方「已完成的前置」）

> **2026-08-07 使用者決策 —— gate 解除，後端先行動工：** 前端會在後端之後補上
> handoff 工作包 FE-2，因此**後端不必等前端上線即可執行 Phase B**。Phase A
> 「必須先行」是**排程**約束，就此解除；其技術理由仍然成立，保留下來供判斷
> **合併時機**參考——Phase B 合併後到 FE-2 上線前，切到 API mode 但尚未 import
> 專案的情境會失去唯一還能回應的 `/api/map`，使用者直接看到錯誤字串，這段期間
> `main` 對前端是壞的，屬已知並接受的代價。
>
> 另註：Plan 08（移除 `ViewerPayload` 與 session 旁路槽）的 gate 是「Plan 02
> 與 05 都完成」，本計畫 Phase B 一旦執行，該 gate 即滿足。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填）

**Goal:** 移除 process-wide viewer demo **讀取**路徑——`GET /api/map`、
`GET /map` 兩個 handler 及其前端 fallback——讓 viewer 讀圖只剩 build-scoped
正式路徑（`GET /api/projects/{project_id}/map-builds/latest`、
`GET /api/map-builds/{build_id}`）。

> **範圍調整（2026-08-06）：** 原本一併涵蓋的 `POST /api/map/build` 已拆出為
> `03-retire-api-map-build.md` 獨立執行。理由：該端點**前端零引用**，不受
> Phase A gate 約束，可立即動工；本計畫的兩支讀取端點才是卡在前端 fallback。
> 兩份計畫互不阻擋，任一順序皆可；`03` 先完成時，本計畫 Task 7 對應敘述改為
> 只處理讀取端點。

**Architecture:** 這是 breaking API change 且橫跨 frontend / backend / scripts /
契約文件。`API-GUIDE.md:30-35` 目前把 `map/build → GET /api/map` 列為與 project
session 並列的**第一級「Viewer demo」流程**，本計畫等於刪掉其中一種流程，因此
必須同批更新契約文件，且必須先補上「API mode 尚未選定專案」的空狀態，否則會
留下無法讀圖的死角（見 Task 1 前置風險）。

**Tech Stack:** React + zod（前端 fallback 移除）、FastAPI（handler 移除）、
pytest web tests、curl trace scripts。

---

## Source（判準基線，均為 2026-08-06 對程式碼查核所得）

- `src/systograph/web/routes/map_routes.py`：四個 handler——
  `POST /api/map/build`(22)、`GET /api/map`(37)、`GET /api/map/report`(45)、
  `GET /map`(75)。
- `frontend/src/services/viewerApi.ts:11,40-51`：`mapEndpoints =
  ["/api/map", "/map"]`，primary 失敗後依序 fallback。
- `frontend/src/hooks/useViewerPayload.ts:8,19-21`：`projectId` 可為 `null`；
  API mode 且無 projectId 時，`loadApiViewerPayload` 會跳過 primary（`if
  (projectId)` 為 falsy）直接打 `/api/map`。
- `docs/API-GUIDE.md:30-35`（兩種流程表）、`:325-331`（`POST /api/map/build`
  更新 process-wide latest）、`:572-578`（`GET /api/map` legacy/demo）、
  `:611-613`（`GET /map`）。
- `frontend/API_CONTRACT.md:26-38`（deprecated fallback 區塊）、`:75`、`:278`、
  `:290`、`:393-394`。

## 範圍（明確界定）

**移除：** `GET /api/map`、`GET /map`。（`POST /api/map/build` 見 Plan 03。）

**不動：** `GET /api/map/report`——它雖住在同一個檔案，但回的是 Markdown
readiness report 而非 viewer payload，且狀態是**待接線**不是待退役：
issue **#219 `[Frontend][Blocked] feat: connect safe build-scoped artifact
preview and download`** 仍為 OPEN。本計畫與 Plan 03 都完成後 `map_routes.py`
只剩這一個 handler；是否連同檔案收斂由 #219 決定。

**不動：** `session_store` 的 `save_build_result` / `latest_build_result`
——正式 scan 流程仍透過 `save_committed_build_projection` 使用它們，且
`GET /api/map/report` 依賴 `latest_build_result`。`latest_viewer_payload`
（`session_store.py:125,198`）則是本計畫後即無呼叫者（現有唯一呼叫點就是要刪的
`map_routes.py:42,80`），但清除歸 Plan 08，本計畫同樣不動。

> **槽位收尾 → 已獨立為 `refactor/08-remove-viewer-payload-session-slot.md`。** 本計畫與 Plan 05（退役
> `POST /api/viewer/load`）都完成後，`_latest_viewer_payload` 槽、
> `save_viewer_payload`、以及 `save_build_result` 內「再包一份
> `ViewerPayload`」的那幾行（`session_store.py:117-120,190-193`）即成死碼，
> 適合開一個小 followup PR 一併移除；屆時同步評估 backend 的
> `ViewerPayload` pydantic model 是否還有使用者。
> **`ViewerLoadResult` / `graph_view_model` 必留**——正式 build-scoped
> 回應仍以它們為主體（`schemas.py:144`）。本計畫**不執行**槽位收尾，見 Plan 08。

**範圍外：** scan_id 主鍵重構、path-digest dedup 移除（2026-08-05 使用者決定
擱置）；explicit preflight cutover 另見 `01-explicit-preflight-cutover.md`。

---

## 已完成的前置（Step 0，2026-08-06）

文件不得先於程式碼宣告端點已移除（端點今天仍存在且前端仍依賴），因此先做
**deprecation 標記**而非刪除章節；章節刪除仍歸 Task 3 / Task 7，於對應程式碼
落地時才執行。

已套用：

- `docs/API-GUIDE.md`：「兩種流程」表 Viewer demo 列、Endpoint 總覽三列
  Runtime 改 **deprecated**、全域約定 State 列、§1 導言；
  `POST /api/map/build`（`:327-328`）與 `GET /api/map`（`:574-575`）兩節加上
  deprecation banner 並指向 build-scoped 替代路徑，`GET /map`（`:611-613`）
  一節標題標 deprecated 並註明與另兩支一同退役。
- `docs/API-GUIDE.md` §快速開始：**原本示範的是即將退役的 demo 捷徑**
  （`map/build` → `GET /api/map`），已改寫為 project session 流程
  （import → scans → `map-builds/latest`，含 `:` 需 URL-encode 為 `%3A` 的提醒），
  避免新讀者學到將被移除的路徑。
- `frontend/API_CONTRACT.md`：修正兩處**與現行程式碼不符**的舊敘述（非
  deprecation，是事實錯誤）——
  1. §Map Loading 原寫 `GET /api/map` 是 "Preferred endpoint"，實際主路徑是
     `GET /api/projects/{project_id}/map-builds/latest`
     （`viewerApi.ts:25-28` 註解明載）；已改寫並把 `/api/map`、`/map` 標為
     deprecated fallback。
  2. 原寫「After a completed scan, the frontend reloads `GET /api/map`」，
     實際 `completeScanFlow` 走 build-scoped latest；已更正。

尚未處理（刻意保留至 Phase B）：API-GUIDE 中的附帶提及（錯誤對照表、
「`POST /api/scans` / `map/build` 不會自動呼叫任何 endpoint」等敘述、
§2 比較表的 read surface 列）。這些描述的是**今天的真實行為**，端點還在時
提前刪除反而會讓文件失真。

---

## Phase A — Frontend（以 handoff 交付）

> **2026-08-06 前端工作已抽出：** 本區段（含全部 Task 細節）已 handoff 至
> `docs/work/Meeting-Sync/meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`（工作包 FE-2）。後端不執行本區段。
>
> **2026-08-07 更新：** 原本「必須先行；backend 移除前完成」的 gate **已解除**
> ——前端會於後端之後補上，後端不再等本區段上線即可進 Phase B。見文件開頭決策。
> 本區段內部順序（先補空狀態、再拔 fallback）仍然不變，那是前端自身的正確性
> 要求，與後端排程無關。

### Task 1: 補上「API mode 尚未選定專案」空狀態（**前置風險，必須先做**）

現況：切到 API mode 但還沒 import／scan 任何專案時，`activeProjectId` 為
`null`，唯一還能回應的就是 `/api/map`。若先刪 fallback 而不補空狀態，此情境
會直接丟 `Unable to load viewer payload...` 錯誤字串給使用者。

**Files:**
- Modify: `frontend/src/hooks/useViewerPayload.ts`
- Modify: `frontend/src/App.tsx`（state matrix：`:70-79` 的 `appState`；短路後
  `data` 為 undefined 且非 error，現行矩陣會停在 `loading`）
- Modify: `frontend/src/components/StateOverlay.tsx`（獨立元件檔；`:29`、`:44`
  硬寫 `GET {apiBaseUrl}/api/map` 文案，端點消失後必須改寫）

- [ ] **Step 1: API mode 且 `projectId == null` 且 `buildId == null` 時不發
  request**（react-query `enabled: false` 或等價短路）
- [ ] **Step 2: 顯示明確空狀態**（例如「Import a project to load a map」），
  不得沿用網路錯誤文案
- [ ] **Step 3: 元件測試覆蓋此狀態**

### Task 2: 移除 fallback

**Files:**
- Modify: `frontend/src/services/viewerApi.ts`
- Modify: `frontend/src/services/viewerApi.test.ts`

- [ ] **Step 1: 刪除 `mapEndpoints` 常數與 `:40-51` fallback 迴圈**
- [ ] **Step 2: `loadApiViewerPayload` 的 `projectId` 改為必填**（型別由
  `string | null | undefined` 收斂為 `string`），失敗直接拋出原始錯誤
- [ ] **Step 3: 確認 `parseViewerPayload` 仍被 `data/sampleMap.ts:5,27`
  使用——Sample 模式依賴它，不可一併刪除**
- [ ] **Step 4: 補測試：primary 失敗時直接 reject，不再有第二次 fetch**

> 註：移除 fallback 順帶修掉一個 silent failure——目前 `viewerApi.ts:32` 的
> `catch` 會吞掉 zod 解析錯誤，導致 build-scoped 契約漂移時靜默退回 demo
> 端點而非報錯。

### Task 3: 契約文件（前端側）

**Files:**
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1: 刪除 `:26-38` 的 deprecated fallback 區塊**（`GET /api/map`、
  `GET /map` 的 code block 與其後的說明段；`:15` 的 build-scoped latest 是
  正式主路徑，不得動）
- [ ] **Step 2: 複查 `:278`「After a completed scan…」敘述**——Step 0 已改寫
  為 build-scoped latest，確認未被回退即可
- [ ] **Step 3: `:393-394`「never refreshes process-wide `/api/map`」的敘述在
  端點消失後改寫或刪除，不得留下指向已不存在端點的說明；`:75` 具名的是
  `POST /api/map/build`（非 `/api/map`），與 `:290` 錯誤表提及
  `POST /api/map/build` 的列同屬 Plan 03（其 Task 4 Step 6 已列入兩處）**

---

## Phase B — Backend（2026-08-07 起 gate 解除，可立即動工；原為「Phase A 上線後」）

### Task 4: 移除 handler

**Files:**
- Modify: `src/systograph/web/routes/map_routes.py`

- [ ] **Step 1: 刪除 `get_api_map`(37) 與 `get_map_fallback`(75)**
  （`build_map`(22) 屬 Plan 03；若 03 尚未執行則保持不動）
- [ ] **Step 2: 清掉隨之無用的 import**（`MapBuildApiRequest` 的退役屬
  Plan 03；`ViewerPayload` response_model 若仍被其他 handler 使用則保留）
- [ ] **Step 3: `uv run ruff check src tests` + `uv run mypy src tests` 通過**

### Task 5: 測試遷移

整個 demo surface（含 Plan 03 的 `POST /api/map/build`）現有引用共 16 處、
6 個檔案（2026-08-06 實測）：

| 檔案 | 引用數 | 處理方向 |
|---|---:|---|
| `tests/web/test_map_routes.py` | 8 | 主要退役對象：`:29`、`:145` 讀 `/api/map`，`:30` 讀 `/map`；另 5 處 `POST /api/map/build` 屬 Plan 03。保留 `/api/map/report` 相關案例 |
| `tests/web/test_mapping_proposal_routes.py` | 2 | 改用 project scan 流程建立前置 build |
| `tests/web/test_mapping_routes.py` | 2 | 同上 |
| `tests/web/test_scan_boundary_routes.py` | 2 | 同上 |
| `tests/web/test_local_api_hardening.py` | 1 | 唯一引用是 `:20` 的 `POST /api/map/build`，屬 Plan 03，本計畫不動 |
| `tests/web/test_viewer_routes.py` | 1 | `:40` 用 `GET /api/map` 回讀 `POST /api/viewer/load` 的寫入結果；該端點只寫 `save_viewer_payload`（`viewer_routes.py:35`），**無 build-scoped 等價讀路徑**，處理方式待決 |

- [ ] **Step 1: 逐檔把「讀 process-wide latest」的斷言改為 build-scoped
  端點**；前置造 build 一律走 `import` → `scans`（或抽共用 helper 放
  `tests/helpers/`）。註：`/api/map/build` 相關前置由 Plan 03 處理
- [ ] **Step 2: 新增 regression：`GET /api/map`、`GET /map` 回 404**
- [ ] **Step 3: `uv run pytest -m web` 全綠**

### Task 6: Trace scripts

現有 10 支引用（2026-08-06 實測）：`trace_map_get.sh`、`trace_map_fallback.sh`、
`trace_map_build.sh`、`trace_map_report.sh`、`trace_viewer_load.sh`、
`trace_graph_projection_qa.sh`、`trace_scan_boundary_multi_decision_gate.sh`、
`test_mapping_proposal_llm.sh`、`trace_all.sh`、`lib/api_trace_common.sh`。

其中 `lib/api_trace_common.sh:87` 與 `test_mapping_proposal_llm.sh:95` 的
`wait_for_api()` 用 `curl -fsS "$API_BASE_URL/api/map"` 當後端就緒探測；共用 lib
被所有 trace script（含 `trace_all.sh`）引用，端點消失後整組會等滿 60 次重試後
以「Backend did not become available」失敗，因此必須一併遷移。

- [ ] **Step 1: 刪除純粹驗證已退役端點的腳本**（`trace_map_get.sh`、
  `trace_map_fallback.sh`；`trace_map_build.sh` 屬 Plan 03）
- [ ] **Step 2: 兩處 `wait_for_api()` 探測改打仍存在的端點；其餘腳本
  （`trace_graph_projection_qa.sh`、`trace_scan_boundary_multi_decision_gate.sh`）
  改用 project scan 流程取得 build**
- [ ] **Step 3: 從 `trace_all.sh` 移除已刪腳本（`:56`、`:58` 兩列），
  確認整組可跑**

### Task 7: API-GUIDE

**Files:**
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: 改寫 `:30-35`「兩種流程」表——移除 Viewer demo 那一列，
  只留 Project session（這是本計畫對外語意的核心變更）**
- [ ] **Step 2: 刪除 `GET /api/map（legacy / demo）` 與 `GET /map` 兩節**
  （`POST /api/map/build` 一節屬 Plan 03）
- [ ] **Step 3: Endpoint 總覽移除 `:56`、`:57` 兩列；`GET /api/map/report`
  一節保留**（錯誤對照表 `:1035-1046` 以狀態碼分列、沒有指名這兩支端點的列；
  `:1067` 具名的是 `POST /api/map/build`，屬 Plan 03）
- [ ] **Step 4: 全文 grep 確認無殘留指向已刪端點的敘述**

---

## 驗收標準

1. `GET /api/map`、`GET /map` 回 404，且有 regression test 鎖住。
2. API mode 未選專案時顯示明確空狀態，不發 request、不出現網路錯誤文案。
3. 前端讀圖只剩 `map-builds/latest` 與 `map-builds/{build_id}`；primary 失敗
   直接呈現錯誤（含契約解析錯誤），不再靜默降級。
4. `pnpm test`、`uv run pytest`、`ruff`、`mypy` 全綠；`scripts/trace_all.sh`
   可完整執行。
5. `docs/API-GUIDE.md` 與 `frontend/API_CONTRACT.md` 無指向已刪端點的殘留
   敘述；「兩種流程」已收斂為單一 project session 流程。
6. `GET /api/map/report` 行為不變（仍可讀取正式 scan 產生的最新報告）。

## 風險

- **API mode 空窗**：Task 1 未先完成就移除 fallback，會讓「切到 API mode 但
  未選專案」變成錯誤畫面。此為本計畫最高風險，故列為第一個 Task。
- **Breaking change**：任何直接讀 `GET /api/map` 的本機腳本或外部整合都會
  失效；退役需在 issue 與 API-GUIDE 明示，並指向 build-scoped 端點。
- **測試前置成本**：多個 web 測試檔用 demo 端點當廉價 fixture，改走正式
  scan 流程會拉長測試時間；建議抽共用 helper 而非逐檔複製。

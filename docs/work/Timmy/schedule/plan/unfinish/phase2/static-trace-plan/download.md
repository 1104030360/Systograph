# Build-scoped Markdown Report 下載 — 實作計畫

Status: **done**（2026-08-10 起草並於同日實作完成；GitHub issue／PR
開立後回填編號）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 build-scoped 下載端點
`GET /api/map-builds/{build_id}/artifacts/ai_system_map.md`，讓前端用
`build_id` 安全代讀「該 build」的 Markdown report；同一變更內退役
process-wide 的 `GET /api/map/report`。

**Architecture:** 後端新增一支 read-only 端點，複用既有
`MapBuildQueryService` 與 manifest 還原能力，**零新儲存、零新 DB**。
前端接線另立計畫（見 §5）。本計畫是 issue #219 的**最小切片**：只做
`.md` 下載，不做完整 `artifact_refs` 平台。

**取代關係：** 本計畫取代
`docs/work/Meeting-Sync/meeting_sync_2026_08_06/04-wire-frontend-map-report-download.md`
（FE-3：「前端接 process-wide `/api/map/report`」的縮小先行版）。FE-3 的
前提是後端暫時保留 `/api/map/report`；本計畫改走 build-scoped，FE-3 的
「靜默給錯檔案」限制隨之消失，該計畫不再執行（檔頭已標 superseded）。

---

## 1. 本計畫解決的兩個問題

### 問題 A：path 不得過牆（path oracle）

前端若拿到 server-local absolute path（如
`outputs/build_xxx/ai_system_map.md`），瀏覽器打不開也不該打——把 path
交給前端就是 #140 曾修掉的 path oracle 風險（`POST /api/viewer/load`
以刪除端點修復，見 `docs/API-GUIDE.md:111-113`）。

**解法：** 新端點只接受 `build_id` + 白名單內的檔名。路徑解析
（`build_id` → manifest → `map_markdown_path`）全在 server 端完成，
回應只有檔案內容與 headers，**不含任何 path**。

**明確排除：** `POST /api/scans` 回應的 `build_result` 目前仍含 `*_path`
absolute path（`docs/API-GUIDE.md:383` 已標註的既存缺口，target 是
Plan 06 safe `artifact_refs`）。本計畫不修它、也不會惡化它——屬獨立議題。

### 問題 B：只能下載「全域最新」

現行唯一下載口 `GET /api/map/report` 是 process-wide：讀
`SessionStore.latest_build_result()`，process 快取為空時掃 durable state
**所有 project** 的 latest pointer 取最新（`web/session_store.py:160-174`）。
使用者若正在檢視歷史 build 或在多專案情境操作，下載到的可能是
**別的 build、甚至別的 project** 的檔——靜默給錯檔案。

**解法：** 新端點吃 `build_id`。`MapBuildQueryService.get(build_id)`
（`core/services/map_build_query_service.py:43`）本來就能載入任意歷史
build 的 manifest；manifest 逐 build 保存 `map_markdown_path`
（`core/services/build_manifest_service.py:202`）；outputs 目錄逐 build
不可變（`outputs/build_<uuid>/`，`web/routes/scan_routes.py:212-213`）。
選 build A 下載到的就是 A 的檔，與「最新」無關。

---

## 2. 現況 vs 目標

```text
====================================================================================
  BEFORE: two disconnected read paths
====================================================================================

  Frontend                            Backend
  --------                            -------
  GET .../map-builds/latest   ---->   build_id + JSON envelope     (build-scoped, OK)
  GET /api/map-builds/{id}    <----   (readiness inline; no md content, no path)

  (not wired)                         GET /api/map/report          (process-wide!)
                                      reads "global latest" md
                                      -> may serve another build or project

====================================================================================
  AFTER: one identity, both reads build-scoped
====================================================================================

  Frontend                            Backend                            Disk
  --------                            -------                            ----
  1) GET .../map-builds/latest ---->  resolve project latest
     or  /api/map-builds/{id} <----   build_id + JSON envelope

  2) user clicks "Download"
     GET /api/map-builds/{build_id}/artifacts/ai_system_map.md?download=true
                              ---->   find_build_manifest(build_id)
                                      resolve map_markdown_path
                                      (server side only)           ---->  read file
                              <----   text/markdown + attachment header
```

身分與路徑的邊界（內容過牆，路徑不過牆）：

```text
  Frontend knows                        Backend only knows
  +----------------------+             +------------------------------------+
  | project_id           |   ids ==>   | ~/.systograph/... (manifests)      |
  | scan_id / build_id   |             | outputs/build_<id>/                |
  | file_name (basename) |  <== body   |   real path of ai_system_map.md    |
  +----------------------+             +------------------------------------+
```

---

## 3. API 契約設計

```http
GET /api/map-builds/{build_id}/artifacts/{file_name}
GET /api/map-builds/{build_id}/artifacts/{file_name}?download=true
```

| 項目 | 設計 |
|------|------|
| `file_name` | **白名單制**。本計畫只開 `ai_system_map.md` → manifest 的 `map_markdown_path` |
| 成功回應 | `200`，`text/markdown; charset=utf-8`，body 為檔案內容 |
| `?download=true` | 額外加 `Content-Disposition: attachment; filename="ai_system_map.md"`（檔名取自白名單） |
| 不帶 query | 行內檢視（同 `/api/map/report` 舊行為） |
| 回應內容 | **絕不含 absolute path**；也不回 `artifact_refs`（Plan 06 範圍） |

錯誤碼（皆為 JSON `detail`）：

| 狀況 | HTTP | `detail` |
|------|------|----------|
| `build_id` 不存在 | 404 | `build_not_found`（沿用 `GET /api/map-builds/{build_id}` 的既有碼） |
| `file_name` 不在白名單 | 404 | `artifact_not_found`（同時天然擋掉 path traversal——參數從不觸碰 filesystem） |
| 在白名單但 manifest 無路徑或檔案已不在磁碟 | 404 | `artifact_not_available` |

白名單設計為 `file_name → (manifest 欄位, media_type)` 對照表，之後要開
`system_map.mmd` / `execution_map.mmd`（manifest 已有
`system_map_mermaid_path` / `execution_map_mermaid_path`，
`build_manifest_service.py:203-206`）只需加兩列，**本計畫不做**。

---

## 4. 後端 Tasks

### Task 1：新增 build-scoped artifact 端點

**Files:**
- Modify: `src/systograph/web/routes/map_build_routes.py`

- [x] **Step 1:** 定義白名單常數
  `{"ai_system_map.md": ("map_markdown_path", "text/markdown; charset=utf-8")}`
- [x] **Step 2:** 新增 handler
  `GET /api/map-builds/{build_id}/artifacts/{file_name}`：
  依序檢查白名單（404 `artifact_not_found`）→
  `MapBuildQueryService.get(build_id)`（`KeyError` → 404 `build_not_found`）→
  取 manifest 還原的 path 欄位並確認 `is_file()`（否則 404
  `artifact_not_available`）→ 讀檔回 `Response`；`download=true` 時加
  attachment header。實作樣式比照現行 `map_routes.py:42-51`
- [x] **Step 3:** 依賴沿用既有 `web/dependencies.py` 的
  `map_build_query_service`，不新增 app.state 服務

### Task 2：測試

**Files:**
- Create/Modify: `tests/web/`（併入既有 map-builds 測試檔或新檔）

- [x] **Step 1: build 隔離**——同一 project 產生 build A、B 後，分別下載
  A 與 B，內容各自對應（不因 B 較新而拿到 B 的檔）
- [x] **Step 2:** 404 三態各一：未知 `build_id`（`build_not_found`）、
  白名單外檔名含 traversal 樣式（`artifact_not_found`）、檔案自磁碟移除
  （`artifact_not_available`）
- [x] **Step 3:** header 行為——無 query 不帶 `Content-Disposition`；
  `download=true` 帶固定檔名 attachment
- [x] **Step 4: 無 path 洩漏**——所有回應（含錯誤）body 與 headers 不含
  absolute path 片段
- [x] **Step 5:** 測試注入 temp state dir（既有慣例），不落真實
  `~/.systograph`

### Task 3：退役 `GET /api/map/report`

依 repo 原則（不留 compatibility layer，比照 #277 硬退役），與 Task 1
同一變更移除，不走「先 deprecated 再刪」：

**Files:**
- Delete: `src/systograph/web/routes/map_routes.py`（整檔僅此一支 handler）
- Modify: `src/systograph/web/app.py`（移除 router 註冊）
- Modify: `src/systograph/web/session_store.py`
- Delete/Rewrite: `tests/web/test_map_routes.py`
- Modify: `tests/unit/core/test_query_trace_boundaries.py`
- Modify: `tests/web/test_retired_endpoints.py`
- Rename: `scripts/trace_map_report.sh` →
  `scripts/trace_map_build_artifact.sh`
- Modify: `scripts/trace_all.sh`

- [x] **Step 1:** 刪 `map_routes.py` 與 `create_app()` 的註冊
- [x] **Step 2:** 清 `SessionStore` 的 `latest_build_result` 與只為它存在
  的 `_latest_build_result` 欄位——2026-08-10 查核唯一 caller 是
  `map_routes.py:30`；實作時以 `rg latest_build_result` 複核後，逐項移除：
  Protocol 宣告（`session_store.py:42`）；`InMemorySessionStore` 的
  `latest_build_result()`（`:102-103`）與欄位（init `:71`、寫入 `:98`）；
  `PersistentSessionStore` 的 `latest_build_result()`（`:160-174`）與欄位
  （init `:121`、寫入 `:158`、`build_result()` 尾端的快取回填 `:187`）。
  移除後兩個 store 的 `_latest_build_result` 都只剩 write-only 死欄位，
  故一併刪除；`PersistentSessionStore.save_build_result` 的 body 只有
  `:158` 那一行，會變成 no-op——**方法必須保留**以符合 Protocol，
  `save_committed_build_projection`（`:49-63`）仍會呼叫它，durable
  持久化本來就由 build pipeline 寫 repository，不經這裡
- [x] **Step 3:** `trace_map_report.sh` **更名**為
  `trace_map_build_artifact.sh`（scripts 一律照端點命名，退役後舊名失真，
  repo 原則不留舊名）並改打新端點：project import → scan → 從回應取
  `build_id` → `GET /api/map-builds/{build_id}/artifacts/ai_system_map.md`，
  驗證 200 與 `--download` 時的 `Content-Disposition: attachment`；
  `trace_all.sh:58` 的清單條目同步改 label 與檔名
- [x] **Step 4:** 舊測試改寫為新端點測試（與 Task 2 合併）；
  `test_map_routes.py` 內兩支與 `/api/map/report` 無關的測試**必須留存**、
  不得隨檔案刪除流失——CORS 白名單（`:98-104`）搬到
  `tests/web/test_local_api_hardening.py`、`/api/scan/events` SSE
  （`:106-118`）搬到 `tests/web/test_project_scan_routes.py`
  （或依實況擇一合適的既有／新測試檔）
- [x] **Step 5:** `tests/unit/core/test_query_trace_boundaries.py` 改綁
  `map_build_routes`——該測試意圖是「static map 讀取路徑不依賴 query-trace
  runtime」，`map_routes` 消失後改檢查新端點所在、同屬 map 讀取路徑的
  `map_build_routes` source（`:6` import、`:13` `inspect.getsource`），
  **不是整段刪除**；不改則 import 直接爆炸
- [x] **Step 6:** `tests/web/test_retired_endpoints.py` 比照既有樣式
  （`RETIRED_*_PATH` 常數 + 「client 回 404」與
  `assert_path_is_unregistered` 兩支測試）補 `GET /api/map/report`，
  對應 §6 驗收標準第 4 條

### Task 4：契約文件

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/MODEL-CONTRACT.md`
- Modify: `frontend/API_CONTRACT.md`

- [x] **Step 1:** Endpoint 總覽表：刪 `GET /api/map/report` 列、新增
  `GET /api/map-builds/{build_id}/artifacts/{file_name}`（流程欄 `build`）
- [x] **Step 2:** 移除「目前只有 `GET /api/map/report` 還是 process-wide」
  敘述（`API-GUIDE.md:73-74`）——改述為「已無 process-wide 端點」；
  §`GET /api/map/report`（`:541-561`）整段改寫為新端點章節
- [x] **Step 3:** 錯誤碼表（`:944`）：移除 `map_markdown_not_available`，
  補 `artifact_not_found` / `artifact_not_available`
- [x] **Step 4:** `frontend/API_CONTRACT.md` 同步新端點條目，並註明
  issue #219 其餘範圍（`.mmd`、artifact_refs、preview UI）仍 OPEN
- [x] **Step 5:** `docs/MODEL-CONTRACT.md:165` 的 Render 產物清單——
  `ai_system_map.md ← Epic 1 人類可讀報告（Plan 17 / GET /api/map/report）`
  的端點引用改為
  `GET /api/map-builds/{build_id}/artifacts/ai_system_map.md`

---

## 5. 前端接線（摘要）

前端工作全份另立計畫：
`docs/work/Meeting-Sync/meeting_sync_2026_08_10/frontend-build-scoped-report-download.md`。

> **2026-08-10 交接註記：** 前端接線曾於同日隨本計畫完整實作並通過
> review，因前後端分工（本 repo 這輪由後端 owner 負責）已自 working
> tree 退回，完整交接（含通過全部 gate 的 reference patch 與已驗證
> 設計決策）見上述前端計畫。§6 驗收第 1 條的 UI 級操作（BuildHistoryMenu
> 選 build 下載）隨之由前端計畫承接；後端已以 API 級測試鎖定同等保證
> （per-build 下載內容與磁碟 byte 一致，
> `tests/web/test_map_build_artifact_routes.py`）。

要點：`fetchText` 取用層 → `mapReportApi` service 打新端點 →
ReadinessPanel 下載入口（effective build id =
`activeBuildId ?? viewer_load_result.build_id`）。FE-3 的「歷史 build
停用/警示」邏輯**不需要了**——歷史 build 下載本來就正確。
`/api/map`、`/map` 死碼 fallback 的清理屬 **FE-2**（handoff 文件），
不在本計畫重複。

---

## 6. 驗收標準

1. 於 BuildHistoryMenu 選中歷史 build A（即使 B 較新），下載內容與
   `outputs/build_<A>/ai_system_map.md` byte 一致。
2. 新端點所有回應（成功與錯誤）不含 server-local absolute path。
3. 三種 404（`build_not_found` / `artifact_not_found` /
   `artifact_not_available`）行為與碼如 §3。
4. `GET /api/map/report` 回 404（路由不存在），repo 內（src / tests /
   scripts / 契約文件）已無任何引用——`tests/web/test_retired_endpoints.py`
   的退役常數（Task 3 Step 6 刻意留下的 404 迴歸樁）、`docs/API-GUIDE.md`
   退役端點清單中具名的那一筆（Task 4 刻意留下的退役佐證，與上述迴歸樁
   互為對照）與 `docs/work/**` 的歷史計畫、REP 紀錄不在此列，見 §10。
5. `uv run pytest`、`uv run ruff check src tests`、`uv run mypy src tests`
   全綠；`scripts/trace_all.sh` 對本機後端可跑通。
6. `docs/API-GUIDE.md`、`docs/MODEL-CONTRACT.md`、
   `frontend/API_CONTRACT.md` 與實作一致。

失敗判準：下載內容與畫面上的 `build_id` 不一致，或任何回應/log 出現
本機 absolute path。

---

## 7. 排除範圍

| 項目 | 去向 |
|------|------|
| `system_map.mmd` / `execution_map.mmd` 下載 | 白名單已預留，#219 後續切片 |
| `artifact_refs[]` 平台（sha256 / size / lazy load） | Plan 06 |
| `POST /api/scans` 回應的 `*_path` 清理 | 獨立議題（同屬 Plan 06 方向） |
| Markdown artifact 的 preview UI（非下載） | #219 後續 |

---

## 8. 風險

- **manifest 與磁碟不同步**：使用者手動刪 outputs 目錄後 manifest 仍指舊
  path——以 `artifact_not_available` 404 誠實回報，不 fallback 到別的 build。
- **退役影響面**：`/api/map/report` 的呼叫端在 repo 內僅 tests 與 trace
  scripts（2026-08-10 查核；docs 契約文件另有敘述性引用，完整清單見
  §10），前端從未接上（FE-3 未實作），無外部消費者。
- **與 FE-2/FE-3 的協調**：FE-3 已 superseded；FE-2（拔 `/api/map`
  fallback）與本計畫無依賴關係，可各自進行。

---

## 9. 決策記錄

- **Decision:** 兩段式（map-builds 拿 identity → build-scoped 端點代讀
  下載）；第二段是新端點，不是現行 `/api/map/report`，也絕不回傳 path。
- **Why now:** md 已逐 build 發佈、manifest 已保存路徑、query service 已
  能以 `build_id` 還原——缺口只剩一支安全讀取口。
- **Included:** 新端點 + 測試 + `/api/map/report` 硬退役 + 契約文件 +
  前端接線（另檔）。
- **Excluded:** 見 §7。
- **退役不走 deprecated 過渡：** 對話中曾提「先標 deprecated 穩定後再刪」，
  依 CLAUDE.md 工程原則（不留 compatibility layer）與 #277 前例改為直接
  移除；前端從未使用該端點，風險受控。

---

## 10. Source（判準基線，2026-08-10 對程式碼查核）

- `src/systograph/web/routes/map_routes.py:24-51` — 現行
  `GET /api/map/report`：headers、404 `map_markdown_not_available` 行為
- `src/systograph/web/session_store.py:160-174` +
  `src/systograph/web/app.py:234` — process-wide latest 的實際解析
  （跨 project、restart 後仍可回檔）
- `src/systograph/core/services/map_build_query_service.py:43-47` —
  `get(build_id)` → `find_build_manifest` → `BuildManifestService.load`
- `src/systograph/core/services/build_manifest_service.py:193-207` —
  manifest 還原 `map_markdown_path` 與兩個 `.mmd` path 欄位
- `src/systograph/web/routes/map_build_routes.py:82,97,112` — 既有
  build-scoped 路由與 `build_not_found` 錯誤碼樣式
- `src/systograph/web/routes/scan_routes.py:212-213` — outputs 目錄命名
  `outputs/build_<uuid>`
- `docs/API-GUIDE.md:36-37,59,73-74,383,466-477,541-561,944` — 契約現況
  （process-wide 標註、`*_path` 既存缺口、ArtifactRef 目標形狀、錯誤碼表）
- `/api/map/report` 引用清單（`rg` 全庫查核；`frontend/src` 0 筆）：
  - src：`web/routes/map_routes.py:24`、`web/app.py:67,244`
  - tests：`tests/web/test_map_routes.py`（4 處路徑字串）、
    `tests/unit/core/test_query_trace_boundaries.py:6,13`（import 並
    `inspect.getsource(map_routes)` **模組本身**，非路徑字串——由 Task 3
    Step 5 改綁 `map_build_routes`）
  - scripts：`scripts/trace_map_report.sh`、`scripts/trace_all.sh:58`
  - docs：`docs/API-GUIDE.md:59,74,541-561,944`、
    `docs/MODEL-CONTRACT.md:165`（兩處由 Task 4 處理）
  - `docs/work/**` 的歷史計畫與 REP 紀錄另有多筆引用，屬既成事實紀錄，
    比照 #277 前例**不改寫**；§6 驗收標準第 4 條的「docs」指契約文件
